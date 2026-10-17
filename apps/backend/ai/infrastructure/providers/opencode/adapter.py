"""Opencode CLI provider — wraps the existing opencode CLI integration.

SRP: Only handles opencode CLI communication.
OCP: Extends LLMProvider without modifying it.
DIP: Depends on LLMProvider abstraction.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import threading
from typing import Any, Callable, Optional

from ..base import LLMProvider, ProviderConfig, ProviderResponse
from shared.infrastructure.config.app_config import LLM_DEFAULT_TIMEOUT, SUBPROCESS_STDIN_JOIN_TIMEOUT
from shared.infrastructure.process.logging_config import get_logger

log = get_logger("opencode.provider")

_project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', '..', '..'))
OPENCODE_BIN = os.path.expanduser('~/.opencode/bin/opencode')

_ANSI_RE = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')


class OpencodeProvider(LLMProvider):
    """Provider that delegates to opencode CLI as a subprocess.

    Wraps the existing opencode CLI integration — handles session awareness,
    JSON event parsing, and process lifecycle. Agents should never
    call opencode CLI directly; they go through this provider.
    """

    def __init__(self, config: Optional[ProviderConfig] = None):
        super().__init__(config or ProviderConfig(name="opencode"))

    def generate(
        self,
        prompt: str,
        context: Optional[dict] = None,
        timeout: Optional[int] = None,
    ) -> ProviderResponse:
        """Run opencode CLI with a prompt and return the text response."""
        context = context or {}
        timeout = timeout or self._config.timeout
        session_id = context.get("session_id")

        cmd = self._build_cmd(session_id)
        returncode, output_lines, discovered_session_id = self._run_subprocess(
            cmd, timeout=timeout, stdin_data=prompt
        )

        # Retry without session if it was invalid/expired
        if returncode != 0 and session_id and self._is_session_error(output_lines):
            cmd = self._build_cmd(session_id=None)
            returncode, output_lines, discovered_session_id = self._run_subprocess(
                cmd, timeout=timeout, stdin_data=prompt
            )

        text_parts = []
        for line in output_lines:
            try:
                evt = json.loads(line)
                if evt.get('type') == 'text':
                    text = evt.get('part', {}).get('text', '')
                    if text:
                        text_parts.append(text)
            except json.JSONDecodeError:
                pass

        content = '\n'.join(text_parts)

        if returncode != 0:
            if content:
                # The CLI sometimes exits nonzero on trailing errors even
                # though the model's full answer streamed — surfacing it
                # lets callers validate/parse instead of fail-fast.
                log.warning(
                    "opencode.provider.nonzero_exit_with_content",
                    returncode=returncode,
                    content_chars=len(content),
                )
            else:
                non_json = [
                    _ANSI_RE.sub('', l).strip()
                    for l in output_lines
                    if not l.startswith('{')
                ]
                content = '\n'.join(non_json[:5])
                raise RuntimeError(
                    f"opencode failed (exit code {returncode}): {content[:300]}"
                )

        return ProviderResponse(
            content=content,
            metadata={"returncode": returncode, "lines": len(output_lines)},
            provider="opencode",
            model="opencode-cli",
        )

    def generate_structured(
        self,
        prompt: str,
        schema: Optional[dict] = None,
        context: Optional[dict] = None,
        timeout: Optional[int] = None,
    ) -> ProviderResponse:
        """Run opencode CLI expecting JSON output via stdout (no temp files)."""
        structured_prompt = prompt
        if schema:
            structured_prompt += f"\n\nRespond ONLY with valid JSON matching this schema:\n{json.dumps(schema)}"
        else:
            structured_prompt += "\n\nRespond ONLY with a valid JSON object. Do not write any files."

        response = self.generate(structured_prompt, context=context, timeout=timeout)
        content = response.content.strip()

        result = self._extract_json(content)
        if result is not None:
            return ProviderResponse(
                content=result,
                metadata=response.metadata,
                provider="opencode",
                model="opencode-cli",
            )

        raise RuntimeError(f"Failed to parse opencode JSON output\nRaw output: {content[:500]}")

    def _extract_json(self, content: str) -> Optional[str]:
        """Extract JSON from text content, handling markdown code blocks and surrounding text."""
        if not content:
            return None

        stripped = content.strip()
        if stripped.startswith("```"):
            lines = stripped.splitlines()
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].startswith("```"):
                lines = lines[:-1]
            stripped = "\n".join(lines).strip()

        try:
            json.loads(stripped)
            return stripped
        except json.JSONDecodeError:
            pass

        start = stripped.find('{')
        end = stripped.rfind('}')
        if start != -1 and end != -1 and end > start:
            candidate = stripped[start:end+1]
            try:
                json.loads(candidate)
                return candidate
            except json.JSONDecodeError:
                pass

        return None

    def _is_session_error(self, output_lines: list[str]) -> bool:
        """Check if the failure is due to an invalid/expired session."""
        for line in output_lines:
            cleaned = _ANSI_RE.sub('', line).strip().lower()
            if 'session not found' in cleaned:
                return True
        return False

    def _build_cmd(self, session_id: Optional[str] = None) -> list:
        """Build opencode CLI command.

        The prompt is NOT passed as a CLI argument — opencode reads the message
        from stdin. Passing large prompts via argv exceeds Linux's MAX_ARG_STRLEN
        and raises OSError [Errno 7] "Argument list too long".
        """
        cmd = [OPENCODE_BIN, 'run', '--format', 'json', '--dangerously-skip-permissions']
        if session_id:
            cmd.extend(['--session', session_id])
        return cmd

    @staticmethod
    def _write_stdin(proc: subprocess.Popen, data: str) -> None:
        """Write the prompt to the child's stdin from a worker thread."""
        try:
            proc.stdin.write(data)
            proc.stdin.close()
        except (BrokenPipeError, OSError, ValueError):
            try:
                proc.stdin.close()
            except Exception:
                pass

    def _run_subprocess(
        self,
        cmd: list,
        timeout: int = LLM_DEFAULT_TIMEOUT,
        cwd: Optional[str] = None,
        on_event: Optional[Callable] = None,
        on_session_id: Optional[Callable] = None,
        stdin_data: Optional[str] = None,
    ) -> tuple[int, list[str], Optional[str]]:
        """Run opencode subprocess with streaming output and event callbacks.

        The prompt is written to the child's stdin (from a daemon thread) so
        arbitrarily large prompts never hit the OS argv limit.

        Returns (returncode, output_lines, session_id).
        """
        env = {**os.environ, 'NO_COLOR': '1'}
        proc = subprocess.Popen(
            cmd,
            cwd=cwd or _project_root,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            env=env,
            start_new_session=True,
        )

        stdin_writer = None
        if stdin_data:
            stdin_writer = threading.Thread(
                target=self._write_stdin, args=(proc, stdin_data), daemon=True
            )
            stdin_writer.start()

        all_lines = []
        session_id = None
        timed_out = threading.Event()

        def watchdog():
            timed_out.wait(timeout)
            if not timed_out.is_set():
                try:
                    proc.kill()
                except OSError:
                    pass

        timer = threading.Thread(target=watchdog, daemon=True)
        timer.start()

        try:
            for raw_line in proc.stdout:
                line = raw_line.rstrip('\n')
                if not line:
                    continue
                all_lines.append(line)
                try:
                    evt = json.loads(line)

                    # Extract session_id
                    if not session_id:
                        sid = (evt.get('sessionID') or evt.get('session_id')
                               or evt.get('sessionId'))
                        if not sid and 'session' in evt and isinstance(evt['session'], dict):
                            sid = evt['session'].get('id') or evt['session'].get('ID')
                        if sid:
                            session_id = sid
                            if on_session_id:
                                try:
                                    on_session_id(sid)
                                except Exception:
                                    pass

                    # Forward event to callback
                    if on_event:
                        try:
                            on_event(evt)
                        except Exception:
                            pass

                except json.JSONDecodeError:
                    pass

            timed_out.set()
            proc.wait()
            if stdin_writer is not None:
                stdin_writer.join(timeout=SUBPROCESS_STDIN_JOIN_TIMEOUT)
            return proc.returncode, all_lines, session_id

        except Exception:
            timed_out.set()
            try:
                proc.kill()
            except OSError:
                pass
            proc.wait()
            if stdin_writer is not None:
                stdin_writer.join(timeout=SUBPROCESS_STDIN_JOIN_TIMEOUT)
            raise
        finally:
            timed_out.set()
