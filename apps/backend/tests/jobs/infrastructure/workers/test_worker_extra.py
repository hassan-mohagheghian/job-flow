"""Additional coverage for worker.py — DB helpers, rescoring, streaming, LLM helpers, pipeline entry."""
import json
import os
import sys
import uuid
from datetime import datetime, timedelta
from types import ModuleType
from unittest.mock import patch, MagicMock

import pytest

from jobs.infrastructure.models.job_model import JobModel
from jobs.infrastructure.models.misc_models import SummaryModel
from rules.infrastructure.models.rule_model import RuleModel


def _seed_job(sa_session, id=None, url='https://example.com/job', **kw):
    data = dict(
        id=id or str(uuid.uuid7()), company='Acme', role='Engineer', location='Berlin',
        url=url, status='processing',
        raw_description='Engineer role responsibilities requirements python',
        rescoring=0, user_id='test-user',
    )
    data.update(kw)
    m = JobModel(**data)
    sa_session.add(m)
    sa_session.commit()
    sa_session.refresh(m)
    return m.id


def _full_job_dict(num=100):
    return {
        'id': f'job-{num}', 'company': 'Acme', 'role': 'Engineer', 'location': 'Munich, Germany',
        'salary': '120k', 'stack': 'Python, Go',
        'visa': 'Yes', 'applicants': '10', 'posted': '2 weeks ago',
        'industry': 'Tech', 'domain': 'job', 'notes': 'note', 'action': 'Apply Now',
        'url': f'https://example.com/{num}', 'work_type': 'remote',
        'posted_at': None, 'adv_at': None,
        'employment_type': 'full-time', 'work_types': ['Remote Work', 'Hybrid'],
        'raw_description': 'desc', 'structured_description': '{}',
    }


def _fake_dateutil():
    fake_dt = ModuleType('dateutil')
    fake_rel = ModuleType('dateutil.relativedelta')

    class _Relativedelta:
        def __init__(self, **kw):
            self._months = kw.get('months', 0)

        def __rsub__(self, other):
            return other - timedelta(days=30 * self._months)

    fake_rel.relativedelta = _Relativedelta
    fake_dt.relativedelta = fake_rel
    return patch.dict(sys.modules, {'dateutil': fake_dt, 'dateutil.relativedelta': fake_rel})


def _fake_dateutil_raising():
    fake_dt = ModuleType('dateutil')
    fake_rel = ModuleType('dateutil.relativedelta')

    class _RaisingRelativedelta:
        def __rsub__(self, other):
            raise RuntimeError('boom')

    fake_rel.relativedelta = _RaisingRelativedelta
    fake_dt.relativedelta = fake_rel
    return patch.dict(sys.modules, {'dateutil': fake_dt, 'dateutil.relativedelta': fake_rel})


class TestUpdateStep:
    def test_update_step_fields_and_broadcast(self, mock_get_session_worker):
        pid = _seed_job(mock_get_session_worker)
        from jobs.infrastructure.workers.worker import _update_step
        broadcaster = MagicMock()
        with patch('jobs.infrastructure.workers.worker.broadcaster', broadcaster):
            _update_step(pid, 'step_fetch', 1, status='processing', company='Acme', job_id='job-5', error=None)
        row = mock_get_session_worker.query(JobModel).filter(JobModel.id == pid).first()
        assert row.status == 'processing'
        assert row.company == 'Acme'
        broadcaster.step_update.assert_called_once()

    def test_update_step_minimal(self, mock_get_session_worker):
        pid = _seed_job(mock_get_session_worker)
        from jobs.infrastructure.workers.worker import _update_step
        with patch('jobs.infrastructure.workers.worker.broadcaster'):
            _update_step(pid, 'step_done', 1)

    def test_update_step_missing_row_still_broadcasts(self, mock_get_session_worker):
        from jobs.infrastructure.workers.worker import _update_step
        broadcaster = MagicMock()
        with patch('jobs.infrastructure.workers.worker.broadcaster', broadcaster):
            _update_step('99999', 'step_fetch', 1, error='oops')
        broadcaster.step_update.assert_called_once()
        evt = broadcaster.step_update.call_args[0][0]
        assert evt.extra == {'error': 'oops'}


class TestSaveSessionId:
    def test_saves_session_and_broadcasts(self, mock_get_session_worker):
        pid = _seed_job(mock_get_session_worker)
        from jobs.infrastructure.workers.worker import _save_session_id
        broadcaster = MagicMock()
        with patch('jobs.infrastructure.workers.worker.broadcaster', broadcaster):
            _save_session_id(pid, 'sess_abc')
        row = mock_get_session_worker.query(JobModel).filter(JobModel.id == pid).first()
        assert row.session_id == 'sess_abc'
        broadcaster.step_update.assert_called_once()


class TestInsertJob:
    @pytest.mark.parametrize('et,expected', [
        ('Full-time', 'Full-time'), ('full time', 'Full-time'), ('part-time', 'Part-time'),
        ('Contract', 'Contract'), ('freelance', 'Contract'), ('internship', 'Internship'),
        ('temporary', 'Temporary'), ('anything else', 'Full-time'),
    ])
    def test_employment_type_normalization(self, mock_get_session_worker, et, expected):
        from jobs.infrastructure.workers.worker import _insert_job
        d = _full_job_dict()
        d['employment_type'] = et
        d['employment_types'] = []
        _insert_job(d)
        row = mock_get_session_worker.query(JobModel).filter(JobModel.id == d['id']).first()
        assert row.employment_types == [expected]

    def test_work_types_from_string(self, mock_get_session_worker):
        from jobs.infrastructure.workers.worker import _insert_job
        d = _full_job_dict()
        d['work_types'] = json.dumps(['Remote', 'On-site'])
        _insert_job(d)
        row = mock_get_session_worker.query(JobModel).filter(JobModel.id == d['id']).first()
        assert row.work_types == ['Remote', 'On-site']

    def test_work_types_invalid_string_falls_back(self, mock_get_session_worker):
        from jobs.infrastructure.workers.worker import _insert_job
        d = _full_job_dict()
        d['work_types'] = 'not-json{{'
        d['work_type'] = ''
        _insert_job(d)
        row = mock_get_session_worker.query(JobModel).filter(JobModel.id == d['id']).first()
        assert row.work_types == ['On-site']

    def test_work_types_from_single_work_type(self, mock_get_session_worker):
        from jobs.infrastructure.workers.worker import _insert_job
        d = _full_job_dict()
        d['work_types'] = []
        d['work_type'] = 'hybrid'
        _insert_job(d)
        row = mock_get_session_worker.query(JobModel).filter(JobModel.id == d['id']).first()
        assert row.work_types == ['Hybrid']


    def test_upsert_existing(self, mock_get_session_worker):
        from jobs.infrastructure.workers.worker import _insert_job
        pid = _seed_job(mock_get_session_worker, id='job-50')
        d = _full_job_dict(num=50)
        d['company'] = 'Updated'
        _insert_job(d)
        row = mock_get_session_worker.query(JobModel).filter(JobModel.id == 'job-50').first()
        assert row.company == 'Updated'
        assert row.id == pid


class TestParseDates:
    def test_parse_posted_date_month(self):
        from jobs.infrastructure.workers.worker import _parse_posted_date
        with _fake_dateutil():
            result = _parse_posted_date('2 months ago')
        assert result is not None

    def test_parse_posted_date_exception_returns_none(self):
        from jobs.infrastructure.workers.worker import _parse_posted_date
        with _fake_dateutil_raising():
            assert _parse_posted_date('1 month ago') is None

    def test_parse_posted_date_no_match(self):
        from jobs.infrastructure.workers.worker import _parse_posted_date
        assert _parse_posted_date('some gibberish text') is None

    def test_parse_adv_at_empty(self):
        from jobs.infrastructure.workers.worker import _parse_adv_at
        result = _parse_adv_at('')
        assert result is not None

    def test_parse_adv_at_hours(self):
        from jobs.infrastructure.workers.worker import _parse_adv_at
        assert _parse_adv_at('5 hours ago') is not None

    def test_parse_adv_at_days(self):
        from jobs.infrastructure.workers.worker import _parse_adv_at
        assert _parse_adv_at('3 days ago') is not None

    def test_parse_adv_at_weeks(self):
        from jobs.infrastructure.workers.worker import _parse_adv_at
        assert _parse_adv_at('1 week ago') is not None

    def test_parse_adv_at_month_plain(self):
        from jobs.infrastructure.workers.worker import _parse_adv_at
        with _fake_dateutil():
            assert _parse_adv_at('1 month') is not None

    def test_parse_adv_at_month_plus(self):
        from jobs.infrastructure.workers.worker import _parse_adv_at
        with _fake_dateutil():
            assert _parse_adv_at('4 months+') is not None

    def test_parse_adv_at_exception(self):
        from jobs.infrastructure.workers.worker import _parse_adv_at
        with _fake_dateutil_raising():
            assert _parse_adv_at('1 month') is not None


class TestDbHelpers:
    def test_mark(self, mock_get_session_worker):
        pid = _seed_job(mock_get_session_worker)
        from jobs.infrastructure.workers.worker import _mark
        with patch('jobs.infrastructure.workers.worker._update_step') as mock_update, \
             patch('jobs.infrastructure.workers.worker.broadcaster'):
            _mark(pid, 'step_fetch', company='Acme', job_id='job-3')
        mock_update.assert_called_once_with(pid, 'step_fetch', 1, company='Acme', job_id='job-3')

    def test_get_item(self, mock_get_session_worker):
        pid = _seed_job(mock_get_session_worker, status='queued')
        from jobs.infrastructure.workers.worker import _get_item
        item = _get_item(pid)
        assert item['id'] == pid
        assert item['status'] == 'queued'

    def test_get_item_missing(self, mock_get_session_worker):
        from jobs.infrastructure.workers.worker import _get_item
        assert _get_item('99999') is None

    def test_save_workflow_log(self, mock_get_session_worker):
        pid = _seed_job(mock_get_session_worker)
        from jobs.infrastructure.workers.worker import _save_job_workflow_log
        _save_job_workflow_log(pid, json.dumps([{'step': 'a', 'msg': 'b'}]))
        row = mock_get_session_worker.query(JobModel).filter(JobModel.id == pid).first()
        assert json.loads(row.workflow_log)[0]['step'] == 'a'

    def test_insert_summary(self, mock_get_session_worker):
        from jobs.infrastructure.workers.worker import _insert_summary
        _insert_summary({'job_id': 'job-7', 'company': 'Acme', 'match': 'High', 'score': 'A',
                         'summary': 'sum', 'stack': 'py', 'resumeFit': 'rf', 'note': 'n', 'url': 'u'})
        row = mock_get_session_worker.query(SummaryModel).filter(SummaryModel.job_id == 'job-7').first()
        assert row.company == 'Acme'
        assert row.summary == 'sum'

    def test_check_result_file_exists(self, tmp_path):
        from jobs.infrastructure.workers.worker import _check_result_file
        p = tmp_path / 'result.json'
        p.write_text('{}')
        _check_result_file(str(p))

    def test_check_result_file_missing_raises(self, tmp_path):
        from jobs.infrastructure.workers.worker import _check_result_file
        with pytest.raises(RuntimeError, match='Result file not found'):
            _check_result_file(str(tmp_path / 'nope.json'))

    def test_mark_old_job_deleted(self, mock_get_session_worker):
        id1 = _seed_job(mock_get_session_worker, id='dup-1', url='https://dup.com')
        id2 = _seed_job(mock_get_session_worker, id='dup-2', url='https://dup.com')
        from jobs.infrastructure.workers.worker import _mark_old_job_deleted
        _mark_old_job_deleted('https://dup.com', exclude_id=id2)
        row1 = mock_get_session_worker.query(JobModel).filter(JobModel.id == id1).first()
        row2 = mock_get_session_worker.query(JobModel).filter(JobModel.id == id2).first()
        assert row1.deleted == 1
        assert row2.deleted == 0


class TestNormalizeJobDataExtra:
    def test_location_with_parentheses(self):
        from jobs.infrastructure.workers.worker import _normalize_job_data
        d = {'location': 'Munich (Germany)'}
        result = _normalize_job_data(d)
        assert result['location'] == 'Munich'

class TestFailAndLog:
    def test_fail_with_step(self, mock_get_session_worker):
        pid = _seed_job(mock_get_session_worker)
        from jobs.infrastructure.workers.worker import _fail
        broadcaster = MagicMock()
        with patch('jobs.infrastructure.workers.worker.broadcaster', broadcaster):
            _fail(pid, 'Network timeout', step='fetch')
        row = mock_get_session_worker.query(JobModel).filter(JobModel.id == pid).first()
        assert row.status == 'failed'
        assert '[Fetching job page]' in row.error
        broadcaster.error.assert_called_once()

    def test_fail_without_step(self, mock_get_session_worker):
        pid = _seed_job(mock_get_session_worker)
        from jobs.infrastructure.workers.worker import _fail
        with patch('jobs.infrastructure.workers.worker.broadcaster'):
            _fail(pid, 'Generic error')
        row = mock_get_session_worker.query(JobModel).filter(JobModel.id == pid).first()
        assert row.error == 'Generic error'

    def test_fail_unknown_step(self, mock_get_session_worker):
        pid = _seed_job(mock_get_session_worker)
        from jobs.infrastructure.workers.worker import _fail
        with patch('jobs.infrastructure.workers.worker.broadcaster'):
            _fail(pid, 'msg', step='mystery')
        row = mock_get_session_worker.query(JobModel).filter(JobModel.id == pid).first()
        assert '[mystery] msg' in row.error

    def test_log_appends(self, mock_get_session_worker):
        pid = _seed_job(mock_get_session_worker)
        from jobs.infrastructure.workers.worker import _log
        broadcaster = MagicMock()
        with patch('jobs.infrastructure.workers.worker.broadcaster', broadcaster):
            _log(pid, 'fetch', 'Fetching page...')
        row = mock_get_session_worker.query(JobModel).filter(JobModel.id == pid).first()
        logs = json.loads(row.workflow_log)
        assert logs[-1]['msg'] == 'Fetching page...'
        broadcaster.log.assert_called_once()


class TestLoadRules:
    def test_no_rules(self, mock_get_session_worker):
        from jobs.infrastructure.workers.worker import _load_rules
        assert _load_rules('job') == 'No scoring rules set.'

    def test_with_rules(self, mock_get_session_worker):
        sa_session = mock_get_session_worker
        sa_session.add(RuleModel(category='fit', rule_type='job', scope='JOB', key='python',
                                 value='Strong', priority=10, user_id='test-user'))
        sa_session.add(RuleModel(category='company', rule_type='job', scope='SHARED', key='scale',
                                 value='Large', priority=20, user_id='test-user'))
        sa_session.commit()
        from jobs.infrastructure.workers.worker import _load_rules
        result = _load_rules('job')
        assert 'FIT' in result
        assert 'python' in result
        assert 'scale' in result


class TestLLMHelpers:
    def test_extract_structured_description(self, mock_get_session_worker):
        from jobs.infrastructure.workers.worker import _extract_structured_description
        llm = MagicMock()
        llm.generate_structured.return_value.content = '{"title": "X"}'
        with patch('jobs.infrastructure.workers.worker.get_llm_service', return_value=llm), \
             patch('jobs.infrastructure.workers.worker.load_prompt', return_value='p'):
            assert _extract_structured_description('raw text', 5) == '{"title": "X"}'

    def test_extract_all_with_session_id(self, mock_get_session_worker):
        from jobs.infrastructure.workers.worker import _extract_all
        llm = MagicMock()
        llm.generate_structured.return_value.content = '{"company": "Acme"}'
        llm.generate_structured.return_value.metadata = {'session_id': 'sid123'}
        with patch('jobs.infrastructure.workers.worker.get_llm_service', return_value=llm), \
             patch('jobs.infrastructure.workers.worker.load_prompt', return_value='p'), \
             patch('jobs.infrastructure.workers.worker._save_session_id') as mock_save:
            result = _extract_all('raw', 5)
        assert result == {'company': 'Acme'}
        mock_save.assert_called_once_with(5, 'sid123')

    def test_extract_all_bad_json(self, mock_get_session_worker):
        from jobs.infrastructure.workers.worker import _extract_all
        llm = MagicMock()
        llm.generate_structured.return_value.content = 'not-json'
        llm.generate_structured.return_value.metadata = {}
        with patch('jobs.infrastructure.workers.worker.get_llm_service', return_value=llm), \
             patch('jobs.infrastructure.workers.worker.load_prompt', return_value='p'):
            assert _extract_all('raw', 5) is None


class TestFetch:
    def test_fetch_multi_source_ok(self, mock_get_session_worker):
        from jobs.infrastructure.workers.worker import _fetch_multi_source
        page = MagicMock()
        page.is_ok = True
        page.plain_text = 'Job page content'
        with patch('jobs.infrastructure.workers.worker.fetch_page', return_value=page), \
             patch('jobs.infrastructure.workers.worker._log'):
            result = _fetch_multi_source('https://job.com', [
                {'type': 'text', 'content': 'manual note'},
                {'type': 'url', 'content': 'https://note.com'},
            ], [{'url': 'https://link.com', 'title': 'Link'}], 1)
        assert 'manual note' in result
        assert 'Job page content' in result
        assert 'Link' in result

    def test_fetch_multi_source_failures_and_exceptions(self, mock_get_session_worker):
        from jobs.infrastructure.workers.worker import _fetch_multi_source
        bad_page = MagicMock()
        bad_page.is_ok = False
        bad_page.error.message = '404'
        pages = {'https://job.com': bad_page, 'https://note.com': bad_page, 'https://link.com': bad_page}
        def _fake_fetch(url, **kw):
            if url in ('https://boom.com', 'https://boom-link.com'):
                raise ValueError('network down')
            return pages.get(url, bad_page)
        logs = []
        with patch('jobs.infrastructure.workers.worker.fetch_page', side_effect=_fake_fetch), \
             patch('jobs.infrastructure.workers.worker._log', side_effect=lambda *a, **k: logs.append(a)):
            result = _fetch_multi_source('https://job.com', [
                {'type': 'url', 'content': 'https://note.com'},
                {'type': 'url', 'content': 'https://boom.com'},
            ], [{'url': 'https://link.com'}, {'url': 'https://boom-link.com'}], 1)
        assert result == ''
        assert len(logs) >= 4

    def test_fetch_multi_source_main_url_exception(self, mock_get_session_worker):
        from jobs.infrastructure.workers.worker import _fetch_multi_source
        def _raising_fetch(url, **kw):
            raise ValueError('main url exploded')
        with patch('jobs.infrastructure.workers.worker.fetch_page', side_effect=_raising_fetch), \
             patch('jobs.infrastructure.workers.worker._log') as mock_log:
            result = _fetch_multi_source('https://boom-main.com', [], [], 1)
        assert result == ''
        mock_log.assert_called_once()

    def test_fetch_multi_source_empty(self, mock_get_session_worker):
        from jobs.infrastructure.workers.worker import _fetch_multi_source
        with patch('jobs.infrastructure.workers.worker.fetch_page'), \
             patch('jobs.infrastructure.workers.worker._log'):
            assert _fetch_multi_source('', [], [], 1) == ''

    def test_fetch_url_ok(self):
        from jobs.infrastructure.workers.worker import _fetch_url
        page = MagicMock()
        page.is_ok = True
        page.plain_text = 'text'
        with patch('jobs.infrastructure.workers.worker.fetch_page', return_value=page):
            assert _fetch_url('https://job.com') == 'text'

    def test_fetch_url_raises(self):
        from jobs.infrastructure.workers.worker import _fetch_url
        page = MagicMock()
        page.is_ok = False
        page.error.message = 'Network error'
        with patch('jobs.infrastructure.workers.worker.fetch_page', return_value=page), \
             pytest.raises(RuntimeError, match='Network error'):
            _fetch_url('https://job.com')


class TestValidateJobContent:
    def test_llm_returns_valid(self, mock_get_session_worker):
        from jobs.infrastructure.workers.worker import _validate_job_content
        llm = MagicMock()
        llm.generate_structured.return_value.content = '{"valid": true, "title": "Engineer"}'
        with patch('jobs.infrastructure.workers.worker.get_llm_service', return_value=llm), \
             patch('jobs.infrastructure.workers.worker.load_prompt', return_value='p'):
            assert _validate_job_content('text', 1) == {'valid': True, 'title': 'Engineer'}

    def test_llm_bad_json_fallback_valid(self, mock_get_session_worker):
        from jobs.infrastructure.workers.worker import _validate_job_content
        llm = MagicMock()
        llm.generate_structured.return_value.content = 'broken'
        with patch('jobs.infrastructure.workers.worker.get_llm_service', return_value=llm), \
             patch('jobs.infrastructure.workers.worker.load_prompt', return_value='p'):
            result = _validate_job_content('software engineer developer python', 1)
        assert result['valid'] is True

    def test_llm_exception_fallback_invalid(self, mock_get_session_worker):
        from jobs.infrastructure.workers.worker import _validate_job_content
        llm = MagicMock()
        llm.generate_structured.side_effect = RuntimeError('boom')
        with patch('jobs.infrastructure.workers.worker.get_llm_service', return_value=llm), \
             patch('jobs.infrastructure.workers.worker.load_prompt', return_value='p'):
            result = _validate_job_content('plain text with no keywords at all', 1)
        assert result['valid'] is False


class TestProviderStreaming:
    def test_build_provider_cmd_with_session(self):
        from jobs.infrastructure.workers.worker import _build_provider_cmd
        cmd = _build_provider_cmd('my prompt', session_id='sess1')
        assert '--session' in cmd
        assert 'sess1' in cmd

    def test_build_provider_cmd_without_session(self):
        from jobs.infrastructure.workers.worker import _build_provider_cmd
        cmd = _build_provider_cmd('my prompt')
        assert '--session' not in cmd

    def test_stream_provider_output_full(self, mock_get_session_worker):
        from jobs.infrastructure.workers.worker import _stream_provider_output
        resp = MagicMock()
        resp.metadata = {'lines': ['line1'], 'session_id': 'sess-ok', 'returncode': 0}
        resp.content = ''

        def _fake_stream(prompt, context=None, timeout=None, on_event=None, on_session_id=None):
            on_event({'type': 'tool_use', 'part': {'tool': 'write', 'state': {'title': 'x.txt', 'output': 'DATA', 'status': 'done'}}})
            on_event({'type': 'step_finish', 'part': {'reason': 'done', 'tokens': {'total': 10}}})
            on_session_id('sess-ok')
            return resp

        llm = MagicMock()
        llm.generate_streaming.side_effect = _fake_stream
        with patch('jobs.infrastructure.workers.worker.get_llm_service', return_value=llm), \
             patch('jobs.infrastructure.workers.worker._save_session_id'), \
             patch('jobs.infrastructure.workers.worker._log'):
            rc, lines, sid, captured = _stream_provider_output(['bin', 'run', 'prompt'], '.', {}, 30, 1)
        assert rc == 0
        assert lines == ['line1']
        assert sid == 'sess-ok'
        assert captured['x.txt'] == 'DATA'

    def test_stream_provider_generates_session_id(self, mock_get_session_worker):
        from jobs.infrastructure.workers.worker import _stream_provider_output
        resp = MagicMock()
        resp.metadata = {'lines': [], 'returncode': 1}
        resp.content = ''
        llm = MagicMock()
        llm.generate_streaming.return_value = resp
        with patch('jobs.infrastructure.workers.worker.get_llm_service', return_value=llm), \
             patch('jobs.infrastructure.workers.worker._save_session_id') as mock_save:
            rc, lines, sid, captured = _stream_provider_output(['bin', 'run', 'prompt'], '.', {}, 30, 1)
        assert rc == 1
        assert sid.startswith('ai_')
        mock_save.assert_called_once()

    def test_stream_provider_repairs_content(self, mock_get_session_worker):
        from jobs.infrastructure.workers.worker import _stream_provider_output
        resp = MagicMock()
        resp.metadata = {'lines': [], 'session_id': 's', 'returncode': 0}
        resp.content = '{"a": 1}'
        llm = MagicMock()
        llm.generate_streaming.return_value = resp
        with patch('jobs.infrastructure.workers.worker.get_llm_service', return_value=llm), \
             patch('jobs.infrastructure.workers.worker._save_session_id'), \
             patch('jobs.infrastructure.workers.worker.repair_llm_json', return_value={'a': 1}):
            rc, lines, sid, captured = _stream_provider_output(['bin', 'run', 'prompt'], '.', {}, 30, 1)
        assert captured['result'] == {'a': 1}

    def test_stream_provider_timed_out(self, mock_get_session_worker):
        from jobs.infrastructure.workers.worker import _stream_provider_output
        llm = MagicMock()
        llm.generate_streaming.side_effect = RuntimeError('request timed out')
        with patch('jobs.infrastructure.workers.worker.get_llm_service', return_value=llm):
            rc, lines, sid, captured = _stream_provider_output(['bin', 'run', 'prompt'], '.', {}, 30, 1, resume_session_id='old')
        assert rc == -9
        assert sid == 'old'

    def test_stream_provider_repair_exception_swallowed(self, mock_get_session_worker):
        from jobs.infrastructure.workers.worker import _stream_provider_output
        resp = MagicMock()
        resp.metadata = {'lines': [], 'session_id': 's', 'returncode': 0}
        resp.content = '{"a": 1}'
        llm = MagicMock()
        llm.generate_streaming.return_value = resp
        with patch('jobs.infrastructure.workers.worker.get_llm_service', return_value=llm), \
             patch('jobs.infrastructure.workers.worker._save_session_id'), \
             patch('jobs.infrastructure.workers.worker.repair_llm_json', side_effect=RuntimeError('parse error')):
            rc, lines, sid, captured = _stream_provider_output(['bin', 'run', 'prompt'], '.', {}, 30, 1)
        assert captured == {}

    def test_stream_provider_other_error_raises(self, mock_get_session_worker):
        from jobs.infrastructure.workers.worker import _stream_provider_output
        llm = MagicMock()
        llm.generate_streaming.side_effect = RuntimeError('server exploded')
        with patch('jobs.infrastructure.workers.worker.get_llm_service', return_value=llm), \
             pytest.raises(RuntimeError, match='server exploded'):
            _stream_provider_output(['bin', 'run', 'prompt'], '.', {}, 30, 1)


class TestProviderEvents:
    def test_capture_write_tool_output(self):
        from jobs.infrastructure.workers.worker import _capture_write_tool_output
        captured = {}
        _capture_write_tool_output({'type': 'tool_use', 'part': {'state': {'title': 'a.json', 'output': '{}'}}}, captured)
        assert captured['a.json'] == '{}'
        _capture_write_tool_output({'type': 'step_finish', 'part': {'result': 'res'}}, captured)
        assert captured['result'] == 'res'
        _capture_write_tool_output({'type': 'tool_use', 'part': {'state': {}}}, captured)
        _capture_write_tool_output({'type': 'step_finish', 'part': {}}, captured)

    def test_handle_provider_event_text(self, mock_get_session_worker):
        from jobs.infrastructure.workers.worker import _handle_provider_event
        with patch('jobs.infrastructure.workers.worker._log') as mock_log:
            _handle_provider_event(1, {'type': 'text', 'part': {'text': 'hello world'}})
            mock_log.assert_called_once()
        with patch('jobs.infrastructure.workers.worker._log') as mock_log:
            _handle_provider_event(1, {'type': 'text', 'part': {'text': ''}})
            mock_log.assert_not_called()

    def test_handle_provider_event_tool_use(self, mock_get_session_worker):
        from jobs.infrastructure.workers.worker import _handle_provider_event
        with patch('jobs.infrastructure.workers.worker._log') as mock_log:
            _handle_provider_event(1, {'type': 'tool_use', 'part': {'tool': 'bash', 'state': {'status': 'done', 'title': 't'}}})
            mock_log.assert_called_once()

    def test_handle_provider_event_step_finish(self, mock_get_session_worker):
        from jobs.infrastructure.workers.worker import _handle_provider_event
        with patch('jobs.infrastructure.workers.worker._log') as mock_log:
            _handle_provider_event(1, {'type': 'step_finish', 'part': {'reason': 'r', 'tokens': {'total': 5}}})
            mock_log.assert_called_once()

    def test_handle_provider_event_other(self, mock_get_session_worker):
        from jobs.infrastructure.workers.worker import _handle_provider_event
        with patch('jobs.infrastructure.workers.worker._log') as mock_log:
            _handle_provider_event(1, {'type': 'unknown', 'part': {}})
            mock_log.assert_not_called()


class TestProcessJob:
    def test_process_job_delegates(self, mock_get_session_worker):
        from jobs.infrastructure.workers.worker import process_job
        with patch('jobs.infrastructure.workers.job_worker.JobWorker') as MockJobWorker, \
             patch('shared.infrastructure.config.queue.get_queue_manager') as mock_qm:
            process_job(123)
        MockJobWorker.return_value.process.assert_called_once_with(123)
        mock_qm.return_value.signal_job_done.assert_called_once_with(123)

    def test_process_job_signal_failure_swallowed(self, mock_get_session_worker):
        from jobs.infrastructure.workers.worker import process_job
        with patch('jobs.infrastructure.workers.job_worker.JobWorker') as MockJobWorker, \
             patch('shared.infrastructure.config.queue.get_queue_manager') as mock_qm:
            mock_qm.side_effect = RuntimeError('no queue')
            process_job(123)
        MockJobWorker.return_value.process.assert_called_once_with(123)
