"""Tests for OpencodeProvider — _project_root, start_new_session, session_id flow."""

import os
import pytest
from unittest.mock import patch, MagicMock


class TestProjectRoot:
    """Test _project_root resolves to repo root (4 levels up from adapter.py)."""

    def test_project_root_points_to_repo_root(self):
        from ai.infrastructure.providers.opencode import adapter
        expected = os.path.abspath(os.path.join(
            os.path.dirname(adapter.__file__), '..', '..', '..', '..', '..', '..'
        ))
        assert adapter._project_root == expected

    def test_project_root_is_valid_directory(self):
        from ai.infrastructure.providers.opencode import adapter
        assert os.path.isdir(adapter._project_root)

    def test_project_root_contains_apps_dir(self):
        from ai.infrastructure.providers.opencode import adapter
        assert os.path.isdir(os.path.join(adapter._project_root, 'apps'))


class TestOpenCodeBin:
    """Test OPENCODE_BIN points to existing binary."""

    def test_opencode_bin_path(self):
        from ai.infrastructure.providers.opencode import adapter
        assert adapter.OPENCODE_BIN.endswith('opencode')

    @pytest.mark.skipif(not os.path.exists(os.path.expanduser('~/.opencode/bin/opencode')),
                        reason="opencode binary not installed")
    def test_opencode_bin_exists(self):
        from ai.infrastructure.providers.opencode import adapter
        assert os.path.exists(adapter.OPENCODE_BIN)


class TestBuildCmd:
    """Test command building."""

    def test_basic_cmd(self):
        from ai.infrastructure.providers.opencode.adapter import OpencodeProvider
        provider = OpencodeProvider()
        cmd = provider._build_cmd(session_id=None)
        assert cmd[0].endswith('opencode')
        assert 'run' in cmd
        assert '--format' in cmd
        assert 'json' in cmd
        assert '--dangerously-skip-permissions' in cmd

    def test_cmd_does_not_contain_prompt(self):
        """Prompt must never be passed as a CLI argument (breaks ARG_MAX)."""
        from ai.infrastructure.providers.opencode.adapter import OpencodeProvider
        provider = OpencodeProvider()
        huge_prompt = 'x' * (1024 * 1024)
        cmd = provider._build_cmd(session_id=None)
        assert huge_prompt not in cmd
        assert all(len(arg) < 64 * 1024 for arg in cmd)

    def test_cmd_with_session_id(self):
        from ai.infrastructure.providers.opencode.adapter import OpencodeProvider
        provider = OpencodeProvider()
        cmd = provider._build_cmd(session_id='ses_123')
        assert '--session' in cmd
        assert 'ses_123' in cmd

    def test_cmd_without_session_id(self):
        from ai.infrastructure.providers.opencode.adapter import OpencodeProvider
        provider = OpencodeProvider()
        cmd = provider._build_cmd(session_id=None)
        assert '--session' not in cmd


class TestStdinTransport:
    """Prompt is piped via stdin, so large prompts never hit argv limits."""

    def test_run_subprocess_writes_stdin_data(self):
        """Verify Popen gets stdin=PIPE and stdin_data is written + closed."""
        import subprocess
        from ai.infrastructure.providers.opencode.adapter import OpencodeProvider
        import json

        events = [
            json.dumps({"type": "text", "part": {"text": "ok"}}),
        ]

        proc_mock = MagicMock()
        proc_mock.stdout = iter(events)
        proc_mock.returncode = 0
        proc_mock.wait.return_value = 0
        proc_mock.stdin = MagicMock()

        captured_kwargs = {}

        def mock_popen(*args, **kwargs):
            captured_kwargs.update(kwargs)
            return proc_mock

        with patch('subprocess.Popen', side_effect=mock_popen):
            provider = OpencodeProvider()
            provider._run_subprocess(['opencode', 'run'], timeout=10,
                                     stdin_data='test prompt')

        assert captured_kwargs.get('stdin') == subprocess.PIPE
        proc_mock.stdin.write.assert_called_once_with('test prompt')
        proc_mock.stdin.close.assert_called_once()

    def test_large_prompt_still_short_command(self):
        """A >1 MB prompt must not inflate the command line."""
        from ai.infrastructure.providers.opencode.adapter import OpencodeProvider
        provider = OpencodeProvider()
        huge_prompt = 'x' * (2 * 1024 * 1024)
        cmd = provider._build_cmd(session_id=None)
        assert len(cmd) == 5


class TestRunSubprocess:
    """Test subprocess uses start_new_session=True."""

    def test_start_new_session_flag(self):
        """Verify Popen is called with start_new_session=True."""
        import subprocess
        original_popen = subprocess.Popen

        captured_kwargs = {}

        def mock_popen(*args, **kwargs):
            captured_kwargs.update(kwargs)
            raise RuntimeError("Don't actually run")

        with patch('subprocess.Popen', side_effect=mock_popen):
            from ai.infrastructure.providers.opencode.adapter import OpencodeProvider
            provider = OpencodeProvider()
            try:
                provider._run_subprocess(['echo', 'test'], timeout=5)
            except RuntimeError:
                pass

        assert captured_kwargs.get('start_new_session') is True


class TestNonzeroExitWithContent:
    """Regression (prompt 222): opencode sometimes exits 1 after streaming a
    complete answer; the content must surface for validation/retry instead of
    being discarded in a RuntimeError (which fail-fasted job analysis)."""

    @staticmethod
    def _run_generate(events, returncode):
        import json as _json
        from ai.infrastructure.providers.opencode.adapter import OpencodeProvider

        proc_mock = MagicMock()
        proc_mock.stdout = iter(events)
        proc_mock.returncode = returncode
        proc_mock.wait.return_value = returncode
        proc_mock.stdin = MagicMock()

        with patch('subprocess.Popen', return_value=proc_mock):
            provider = OpencodeProvider()
            return provider.generate('test prompt', timeout=5)

    @staticmethod
    def _event(text):
        import json as _json
        return _json.dumps({"type": "text", "part": {"text": text}})

    def test_nonzero_exit_with_content_returns_content(self):
        import json as _json

        events = [self._event(_json.dumps({"scores": {"fit": 8}}))]
        resp = self._run_generate(events, returncode=1)
        assert _json.loads(resp.content) == {"scores": {"fit": 8}}
        assert resp.metadata["returncode"] == 1

    def test_nonzero_exit_without_content_raises(self):
        events = ['not-a-json-event']
        with pytest.raises(RuntimeError, match="exit code 1"):
            self._run_generate(events, returncode=1)

    def test_generate_structured_parses_json_after_nonzero_exit(self):
        import json as _json
        from ai.infrastructure.providers.opencode.adapter import OpencodeProvider

        events = [
            self._event('```json\n{"scores": {"fit": 8}}\n```'),
        ]
        proc_mock = MagicMock()
        proc_mock.stdout = iter(events)
        proc_mock.returncode = 1
        proc_mock.wait.return_value = 1
        proc_mock.stdin = MagicMock()

        with patch('subprocess.Popen', return_value=proc_mock):
            provider = OpencodeProvider()
            resp = provider.generate_structured('prompt', timeout=5)

        assert _json.loads(resp.content) == {"scores": {"fit": 8}}


class TestSchemaEcho:
    """Regression (prompt 235): models sometimes echo the output schema as
    {"type": "object", "properties": {<data>}}, which used to validate while
    silently dropping title/company/location."""

    @staticmethod
    def _run_structured(text, prompt="prompt", schema=None):
        import json as _json
        from ai.infrastructure.providers.opencode.adapter import OpencodeProvider

        line = _json.dumps({"type": "text", "part": {"text": text}})
        provider = OpencodeProvider()
        with patch.object(
            provider, "_run_subprocess", return_value=(0, [line], None)
        ) as run:
            resp = provider.generate_structured(prompt, schema=schema, timeout=5)
        sent_prompt = run.call_args.kwargs.get("stdin_data") or run.call_args.args[-1]
        return resp, sent_prompt

    def test_unwraps_schema_wrapper(self):
        import json as _json
        from ai.infrastructure.parsers import unwrap_schema_echo

        wrapped = {
            "type": "object",
            "properties": {
                "title": "Developer Advocate",
                "company": "SerpApi",
                "location": "Worldwide",
            },
            "scores": {"fit": 50, "success": 40},
            "recommendation": "skip",
        }
        assert unwrap_schema_echo(wrapped) == {
            "title": "Developer Advocate",
            "company": "SerpApi",
            "location": "Worldwide",
            "scores": {"fit": 50, "success": 40},
            "recommendation": "skip",
        }
        # A plain payload is returned untouched.
        plain = {"title": "X"}
        assert unwrap_schema_echo(plain) is plain
        # A pure schema definition is left for validation to reject.
        pure = {"type": "object", "properties": {"title": {"type": "string"}}}
        assert unwrap_schema_echo(pure) is pure

    def test_generate_structured_unwraps_schema_echo(self):
        import json as _json

        wrapped = _json.dumps(
            {
                "type": "object",
                "properties": {
                    "title": "Developer Advocate",
                    "company": "SerpApi",
                    "location": "Worldwide",
                },
                "scores": {"fit": 50, "success": 40},
            }
        )
        resp, _ = self._run_structured(wrapped)
        data = _json.loads(resp.content)
        assert data["title"] == "Developer Advocate"
        assert data["company"] == "SerpApi"
        assert data["location"] == "Worldwide"
        assert data["scores"] == {"fit": 50, "success": 40}
        assert "properties" not in data

    def test_does_not_duplicate_schema_already_in_prompt(self):
        import json as _json

        schema = {"type": "object", "properties": {"title": {"type": "string"}}}
        prompt = (
            "Extract the job.\n\nRespond ONLY with valid JSON matching exactly "
            f"this schema:\n{_json.dumps(schema)}"
        )
        _, sent = self._run_structured('{"title": "X"}', prompt=prompt, schema=schema)
        assert sent.count("Respond ONLY with valid JSON matching") == 1
        assert "Return the DATA object itself" in sent

    def test_appends_schema_when_prompt_has_none(self):
        import json as _json

        schema = {"type": "object", "properties": {"title": {"type": "string"}}}
        _, sent = self._run_structured('{"title": "X"}', prompt="Extract the job.", schema=schema)
        assert sent.count("Respond ONLY with valid JSON matching") == 1
        assert _json.dumps(schema) in sent
        assert "Return the DATA object itself" in sent


class TestSessionIdFlow:
    """Test session_id is passed through context and saved."""

    def test_session_id_extracted_from_events(self):
        """Verify _run_subprocess extracts session_id from JSON events."""
        from ai.infrastructure.providers.opencode.adapter import OpencodeProvider
        import json

        events = [
            json.dumps({"type": "step_start", "sessionID": "ses_test123"}),
            json.dumps({"type": "text", "part": {"text": "hello"}}),
            json.dumps({"type": "step_finish"}),
        ]

        proc_mock = MagicMock()
        proc_mock.stdout = iter(events)
        proc_mock.returncode = 0
        proc_mock.wait.return_value = 0

        with patch('subprocess.Popen', return_value=proc_mock):
            provider = OpencodeProvider()
            returncode, lines, session_id = provider._run_subprocess(
                ['test'], timeout=10
            )

        assert returncode == 0
        assert session_id == "ses_test123"
        assert len(lines) == 3

    def test_session_id_none_when_no_events(self):
        from ai.infrastructure.providers.opencode.adapter import OpencodeProvider
        import json

        events = [
            json.dumps({"type": "text", "part": {"text": "hello"}}),
        ]

        proc_mock = MagicMock()
        proc_mock.stdout = iter(events)
        proc_mock.returncode = 0
        proc_mock.wait.return_value = 0

        with patch('subprocess.Popen', return_value=proc_mock):
            provider = OpencodeProvider()
            returncode, lines, session_id = provider._run_subprocess(
                ['test'], timeout=10
            )

        assert session_id is None

    def test_session_id_callback_called(self):
        from ai.infrastructure.providers.opencode.adapter import OpencodeProvider
        import json

        events = [
            json.dumps({"type": "step_start", "sessionID": "ses_cb_test"}),
        ]

        proc_mock = MagicMock()
        proc_mock.stdout = iter(events)
        proc_mock.returncode = 0
        proc_mock.wait.return_value = 0

        callback = MagicMock()

        with patch('subprocess.Popen', return_value=proc_mock):
            provider = OpencodeProvider()
            provider._run_subprocess(
                ['test'], timeout=10, on_session_id=callback
            )

        callback.assert_called_once_with("ses_cb_test")


class TestExtractAllSessionId:
    """Test _extract_all passes and saves session_id."""

    def test_extract_all_passes_session_id(self):
        """Verify _extract_all passes session_id in context."""
        from jobs.infrastructure.workers.worker import _extract_all
        from unittest.mock import patch, MagicMock

        mock_resp = MagicMock()
        mock_resp.content = '{"valid": true}'
        mock_resp.metadata = {"session_id": "ses_extract_test"}

        mock_llm = MagicMock()
        mock_llm.generate_structured.return_value = mock_resp

        with patch('jobs.infrastructure.workers.worker.get_llm_service', return_value=mock_llm), \
             patch('jobs.infrastructure.workers.worker.load_prompt', return_value='test prompt'), \
             patch('jobs.infrastructure.workers.worker._save_session_id') as mock_save:

            result = _extract_all("test content", 999, session_id="ses_prev_123")

        mock_llm.generate_structured.assert_called_once()
        call_args = mock_llm.generate_structured.call_args
        context = call_args[1]['context'] if 'context' in call_args[1] else call_args[0][1] if len(call_args[0]) > 1 else {}
        assert context.get('session_id') == 'ses_prev_123'

        mock_save.assert_called_once_with(999, 'ses_extract_test')

    def test_extract_all_saves_none_session_id(self):
        """When provider returns no session_id, _save_session_id is not called."""
        from jobs.infrastructure.workers.worker import _extract_all
        from unittest.mock import patch, MagicMock

        mock_resp = MagicMock()
        mock_resp.content = '{"valid": true}'
        mock_resp.metadata = {}

        mock_llm = MagicMock()
        mock_llm.generate_structured.return_value = mock_resp

        with patch('jobs.infrastructure.workers.worker.get_llm_service', return_value=mock_llm), \
             patch('jobs.infrastructure.workers.worker.load_prompt', return_value='test prompt'), \
             patch('jobs.infrastructure.workers.worker._save_session_id') as mock_save:

            result = _extract_all("test content", 999)

        mock_save.assert_not_called()
