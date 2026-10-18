# Prompt 086 - Fix LLM Prompt "Argument list too long" for Large Prompts

## Objective

Company analysis (and any other large LLM prompt) fails for the opencode
provider with:

```
RuntimeError: [analyze_company] The AI returned an analysis that does not match
the required format. (LLM call failed: [Errno 7] Argument list too long:
'~/.opencode/bin/opencode')
```

Root cause: `OpencodeProvider._build_cmd` passes the entire prompt as a single
CLI argument (`opencode run <prompt> ...`). Linux `execve` caps a single
argument at `MAX_ARG_STRLEN` (32 pages ≈ 131 KB), so company analysis prompts
(company text + scoring rules + schema) exceed the limit and the subprocess
launch fails with `[Errno 7]`. The provider error is then surfaced by
`AnalyzeCompanyNode` as a clean "format mismatch" failure.

Fix: pass the prompt to `opencode run` via **stdin** (opencode reads the message
from stdin when no positional message is given) instead of argv. `MimoProvider`
shares the identical defect and gets the same fix.

## Current State

- `apps/backend/ai/infrastructure/providers/opencode/adapter.py:158`:
  `_build_cmd` embeds `prompt` into the command list.
- `apps/backend/ai/infrastructure/providers/mimo/adapter.py:196`: same pattern.
- The LLM providers are invoked with the prompt from
  `AnalyzeCompanyNode` (`llm.generate_structured(prompt, schema=schema)`), which
  is a single combined prompt containing extracted company text and scoring
  rules — easily > 131 KB.

## Implementation Steps

1. `opencode/adapter.py`:
   - `_build_cmd(session_id)` — drop the prompt positional; keep
     `run --format json --dangerously-skip-permissions` and optional `--session`.
   - `generate`/`_run_subprocess` — pipe the prompt to the child via
     `stdin=subprocess.PIPE`; write stdin from a daemon thread (avoids pipe
     deadlock when prompt > 64 KB) and close it before/while reading stdout.
   - Both the initial call and the session-retry call pass `stdin_data=prompt`.
2. `mimo/adapter.py`: mirror the same change (identical `_build_cmd`/`_run_subprocess`).
3. Update `test_opencode_adapter.py`:
   - `_build_cmd` no longer contains the prompt; assert prompt is absent.
   - `_run_subprocess` writes `stdin_data` to `proc.stdin` and closes it.
   - A large prompt (e.g. 1 MB) produces a short command list (regression test
     for the reported `[Errno 7]`).

## Testing Requirements

- Backend: `uv run pytest apps/backend/tests/ai/infrastructure/providers/ -v`
  and the processing company analysis suite — all green.
- The opencode provider reads stdin correctly (verified manually:
  `echo "Say hello only" | opencode run --format json` returns a JSON event
  stream with exit code 0).

## Constraints

- Bug fix → SemVer PATCH bump to **3.5.1** in all version locations
  (`VERSION`, `CHANGELOG.md`, `pyproject.toml`, `apps/frontend/package.json`)
  and tag `v3.5.1`; `./scripts/check-version.sh` must pass.
- Do not change `analyze_company` prompt/schema logic; only fix the transport.
