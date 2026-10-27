"""
Background worker that processes pending jobs via the AI provider.
Fetches the URL, hands off to the LLM for analysis/resume, then saves to DB.
Runs in a daemon thread — never blocks Flask.
"""
import os
import re
import json
import subprocess
import threading
import urllib.request
import uuid
from datetime import datetime
from shared.infrastructure.prompts.loader import load_prompt
from shared.infrastructure.process.logging_config import get_logger
from shared.infrastructure.utils import repair_llm_json

from shared.infrastructure.process_utils import (
    DB_PATH, PROJECT_ROOT, MIMO_BIN, TMP_DIR,
    ProcessManager, TempFileManager, MimoRunner, StatusBroadcaster,
    broadcaster,
)
from shared.infrastructure.process.models import StatusUpdate, LogEntry, ProcessingComplete, ProcessingError
from shared.infrastructure.config.app_config import (
    SCORING_FIT_WEIGHT, SCORING_SUCCESS_WEIGHT,
    LLM_DEFAULT_TIMEOUT, LLM_EXTRACT_JOB_TIMEOUT,
    FETCH_MAX_CONTENT_LENGTH, FETCH_COMPANY_MAX_LENGTH,
)

from dependencies import get_session_sync

# AI Agent Layer — unified LLM service
from shared.infrastructure.ai.compat import get_llm_service

# Unified Tool Layer — local-first URL fetching
from ai.infrastructure.tools.fetch import fetch_page

log = get_logger('worker')

VALID_GRADES = ['P', 'E', 'D', 'C', 'B', 'A', 'A+', 'A++']
GRADE_RANK = {g: i for i, g in enumerate(VALID_GRADES)}
NUMERIC_TO_GRADE = {
    range(0, 30): 'D', range(30, 50): 'C', range(50, 70): 'B',
    range(70, 80): 'A', range(80, 90): 'A+', range(90, 101): 'A++',
}

def normalize_score(score):
    """Ensure score is a valid letter grade. Converts numeric or invalid values."""
    if isinstance(score, str):
        s = score.strip().upper()
        # Handle variants like "a++", "A +", "a + +"
        s = s.replace(' ', '')
        if s in VALID_GRADES:
            return s
        # Try parsing as numeric
        try:
            n = int(float(s))
            return _numeric_to_grade(n)
        except (ValueError, TypeError):
            pass
    elif isinstance(score, (int, float)):
        return _numeric_to_grade(int(score))
    return 'P'

def _numeric_to_grade(n):
    """Convert a numeric score (0-100) to a letter grade."""
    n = max(0, min(100, n))
    for r, g in NUMERIC_TO_GRADE.items():
        if n in r:
            return g
    return 'P'

def calculate_overall_score(fit_score, success_score):
    """Calculate overall score as weighted average of fit and success scores."""
    if fit_score is None or success_score is None:
        return None
    return round(fit_score * SCORING_FIT_WEIGHT + success_score * SCORING_SUCCESS_WEIGHT, 1)

def score_to_grade(score):
    """Convert a numeric score (0-100) to a letter grade."""
    if score is None:
        return 'P'
    return _numeric_to_grade(int(score))

def _load_env():
    """Read .env file from project root into os.environ."""
    env_path = os.path.join(PROJECT_ROOT, '.env')
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    k, v = line.split('=', 1)
                    os.environ.setdefault(k.strip(), v.strip())
_load_env()

# --- DB helpers ---

def _update_step(pid, step, val, status=None, company=None, job_id=None, error=None):
    session = get_session_sync()
    try:
        from shared.infrastructure.process.repository import PendingJobRepository
        pending_repo = PendingJobRepository(session)
        fields = {step: val}
        if status:
            fields['status'] = status
        if company:
            fields['company'] = company
        if job_id:
            fields['job_id'] = job_id
        if error:
            fields['error'] = error
        pending_repo.update_fields(pid, **fields)
    finally:
        session.close()
    extra = {}
    if status:
        extra['status'] = status
    if company:
        extra['company'] = company
    if job_id:
        extra['job_id'] = job_id
    if error:
        extra['error'] = error
    broadcaster.step_update(StatusUpdate(
        table='job', pid=pid, step=step, val=val,
        extra=extra or None,
    ))

def _save_session_id(pid, session_id):
    """Save session_id to job."""
    session = get_session_sync()
    try:
        from jobs.infrastructure.repositories.sa_job_repository import SQLAlchemyJobRepository
        job_repo = SQLAlchemyJobRepository(session)
        job_repo.update_fields(pid, session_id=session_id)
    finally:
        session.close()
    broadcaster.step_update(StatusUpdate(
        table='job', pid=pid, step='session_id', val=0,
        extra={'session_id': session_id},
    ))

def _get_existing_id(url):
    """Check if a job with this URL already exists. Returns its uuid id or None."""
    session = get_session_sync()
    try:
        from jobs.infrastructure.repositories.sa_job_repository import SQLAlchemyJobRepository
        job_repo = SQLAlchemyJobRepository(session)
        return job_repo.get_id_by_url(url)
    finally:
        session.close()

def _insert_job(d):
    d = _normalize_job_data(d)
    now = datetime.now().isoformat()
    posted_at = d.get('posted_at') or _parse_posted_date(d.get('posted', ''))
    adv_at = d.get('adv_at') or _parse_adv_at(d.get('posted', ''))
    see_at = d.get('see_at') or now
    employment_types = d.get('employment_types', [])
    if isinstance(employment_types, str):
        try:
            employment_types = json.loads(employment_types)
        except:
            employment_types = []
    if not employment_types and d.get('employment_type'):
        employment_types = [d['employment_type']]
    normalized_et = []
    for et in employment_types:
        et_lower = (et or '').lower()
        if 'full' in et_lower:
            if 'Full-time' not in normalized_et:
                normalized_et.append('Full-time')
        elif 'part' in et_lower:
            if 'Part-time' not in normalized_et:
                normalized_et.append('Part-time')
        elif 'contract' in et_lower or 'freelance' in et_lower:
            if 'Contract' not in normalized_et:
                normalized_et.append('Contract')
        elif 'intern' in et_lower:
            if 'Internship' not in normalized_et:
                normalized_et.append('Internship')
        elif 'temp' in et_lower:
            if 'Temporary' not in normalized_et:
                normalized_et.append('Temporary')
    if not normalized_et:
        normalized_et = ['Full-time']

    work_types = d.get('work_types', [])
    if isinstance(work_types, str):
        try:
            work_types = json.loads(work_types)
        except:
            work_types = []
    if not work_types and d.get('work_type'):
        work_types = [d['work_type']]
    normalized_wt = []
    for wt in work_types:
        wt_lower = (wt or '').lower()
        if 'remote' in wt_lower:
            if 'Remote' not in normalized_wt:
                normalized_wt.append('Remote')
        elif 'hybrid' in wt_lower:
            if 'Hybrid' not in normalized_wt:
                normalized_wt.append('Hybrid')
        elif 'on-site' in wt_lower or 'onsite' in wt_lower or 'office' in wt_lower:
            if 'On-site' not in normalized_wt:
                normalized_wt.append('On-site')
    if not normalized_wt:
        normalized_wt = ['On-site']

    job_data = {
        'id': d['id'],
        'company': d['company'],
        'role': d['role'],
        'location': d['location'],
        'salary': d['salary'],
        'stack': d['stack'],
        'visa': d['visa'],
        'applicants': d['applicants'],
        'posted': d['posted'],
        'industry': d['industry'],
        'domain': d['domain'],
        'notes': d['notes'],
        'action': d['action'],
        'url': d['url'],
        'workflow_log': d.get('workflow_log', '[]'),
        'created_at': d.get('created_at', now),
        'posted_at': posted_at,
        'deleted': 0,
        'work_types': normalized_wt,
        'employment_types': normalized_et,
        'raw_description': d.get('raw_description'),
        'structured_description': d.get('structured_description'),
        'raw_file_path': d.get('raw_file_path'),
        'structured_file_path': d.get('structured_file_path'),
        'rescoring': d.get('rescoring', 0),
        'adv_at': adv_at,
        'see_at': see_at,
        'apply_reason': d.get('apply_reason', ''),
        'company_url': d.get('company_url'),
        'linkedin_url': d.get('linkedin_url'),
        'apply_time': d.get('apply_time'),
        'response_time': d.get('response_time'),
        'response_status': d.get('response_status'),
        'fit_score': d.get('fit_score'),
        'success_score': d.get('success_score'),
        'overall_score': d.get('overall_score'),
        'company_id': d.get('company_id'),
        'user_id': d.get('user_id', ''),
    }

    session = get_session_sync()
    try:
        from jobs.infrastructure.repositories.sa_job_repository import SQLAlchemyJobRepository
        job_repo = SQLAlchemyJobRepository(session, user_id=d.get('user_id', ''))
        job_repo.upsert(job_data)
    finally:
        session.close()


def _parse_posted_date(posted_text):
    """Parse relative posted text like '~2 weeks ago' into ISO datetime."""
    if not posted_text or posted_text in ('Active', 'N/A', 'Not specified'):
        return None
    now = datetime.now()
    posted_text = posted_text.lower().strip()
    try:
        if 'hour' in posted_text:
            hours = int(''.join(filter(str.isdigit, posted_text)) or 1)
            from datetime import timedelta
            return (now - timedelta(hours=hours)).isoformat()
        elif 'day' in posted_text:
            days = int(''.join(filter(str.isdigit, posted_text)) or 1)
            from datetime import timedelta
            return (now - timedelta(days=days)).isoformat()
        elif 'week' in posted_text:
            weeks = int(''.join(filter(str.isdigit, posted_text)) or 1)
            from datetime import timedelta
            return (now - timedelta(weeks=weeks)).isoformat()
        elif 'month' in posted_text:
            months = int(''.join(filter(str.isdigit, posted_text)) or 1)
            from dateutil.relativedelta import relativedelta
            return (now - relativedelta(months=months)).isoformat()
    except Exception:
        return None
    return None


def _parse_adv_at(posted_text):
    """Estimate when the job was advertised. If no specific datetime, return current datetime.
    For human-readable text like '1 month', '1 month+', '4 months+':
    - exact like '1 month' -> 1 month ago
    - with '+' like '1 month+' -> 1.5 months ago (adds 0.5)
    - '4 months+' -> 4.5 months ago
    """
    now = datetime.now()
    if not posted_text or posted_text in ('Active', 'N/A', 'Not specified'):
        return now.isoformat()
    posted_text = posted_text.lower().strip()
    has_plus = '+' in posted_text
    try:
        if 'hour' in posted_text:
            hours = int(''.join(filter(str.isdigit, posted_text)) or 1)
            from datetime import timedelta
            return (now - timedelta(hours=hours)).isoformat()
        elif 'day' in posted_text:
            days = int(''.join(filter(str.isdigit, posted_text)) or 1)
            from datetime import timedelta
            return (now - timedelta(days=days)).isoformat()
        elif 'week' in posted_text:
            weeks = int(''.join(filter(str.isdigit, posted_text)) or 1)
            from datetime import timedelta
            return (now - timedelta(weeks=weeks)).isoformat()
        elif 'month' in posted_text:
            months = int(''.join(filter(str.isdigit, posted_text)) or 1)
            if has_plus:
                months += 0.5
            from dateutil.relativedelta import relativedelta
            return (now - relativedelta(months=months)).isoformat()
    except Exception:
        pass
    return now.isoformat()

def _save_job_workflow_log(job_id, log_json):
    """Save workflow log to the jobs table."""
    session = get_session_sync()
    try:
        from jobs.infrastructure.repositories.sa_job_repository import SQLAlchemyJobRepository
        job_repo = SQLAlchemyJobRepository(session)
        job_repo.update_workflow_log(job_id, log_json)
    finally:
        session.close()

def _insert_summary(d):
    session = get_session_sync()
    try:
        from jobs.infrastructure.repositories.sa_summary_repository import SQLAlchemySummaryRepository
        summary_repo = SQLAlchemySummaryRepository(session)
        summary_repo.upsert(d)
    finally:
        session.close()

def _check_result_file(result_path):
    if not os.path.exists(result_path):
        tmp_dir = os.path.dirname(result_path)
        dir_exists = os.path.isdir(tmp_dir)
        dir_writable = os.access(tmp_dir, os.W_OK) if dir_exists else False
        raise RuntimeError(
            f"Result file not found: {result_path} "
            f"(TMP_DIR={tmp_dir} exists={dir_exists} writable={dir_writable})"
        )

def _mark(pid, step, company=None, job_id=None):
    _update_step(pid, step, 1, company=company, job_id=job_id)

def _get_item(pid):
    """Re-read the job from DB to check for status changes (pause/stop)."""
    session = get_session_sync()
    try:
        from shared.infrastructure.process.repository import PendingJobRepository
        pending_repo = PendingJobRepository(session)
        return pending_repo.get(pid)
    finally:
        session.close()

def _is_paused_or_stopped(pid):
    """Check if job was paused or stopped (status changed to non-processing)."""
    item = _get_item(pid)
    if not item:
        return True  # Item deleted, stop
    return item['status'] not in ('processing',)

def rescore(job_id):
    """Re-score an existing job without the full pipeline.
    Reads the raw description, runs AI analysis, and updates the job."""
    session = get_session_sync()
    try:
        from jobs.infrastructure.repositories.sa_job_repository import SQLAlchemyJobRepository
        job_repo = SQLAlchemyJobRepository(session)
        j = job_repo.get_by_id(job_id)
    finally:
        session.close()

    if not j:
        log.warning("worker.rescore_not_found", job_id=job_id)
        return

    url = j['url']
    raw_desc = j.get('raw_description', '')
    if not raw_desc:
        raw_path = j.get('raw_file_path', '')
        if raw_path and os.path.exists(raw_path):
            with open(raw_path) as f:
                raw_desc = f.read()
    if not raw_desc:
        log.warning("worker.rescore_no_raw", job_id=job_id)
        session = get_session_sync()
        try:
            from jobs.infrastructure.repositories.sa_job_repository import SQLAlchemyJobRepository
            job_repo = SQLAlchemyJobRepository(session)
            job_repo.update_fields(job_id, rescoring=0)
        finally:
            session.close()
        return

    job_file = os.path.join(TMP_DIR, f'rescore_{job_id}.txt')
    try:
        with open(job_file, 'w') as f:
            f.write(raw_desc)

        rules = _load_rules()
        resume_path = os.path.join(PROJECT_ROOT, 'inputs', 'original', 'resume.txt')

        # Use a unique pid per rescore run to avoid file conflicts
        rescore_pid = f'rescore_{job_id}_{int(datetime.now().timestamp()*1000)}'
        prompt = load_prompt('job_processing/step8_score',
            url=url, job_file=job_file, resume_file=resume_path,
            tmp_dir=TMP_DIR, pid=rescore_pid, next_num=job_id, rules=rules)

        returncode, output_lines, _, captured_result = _stream_provider_output(
            [MIMO_BIN, 'run', prompt, '--format', 'json', '--dangerously-skip-permissions'],
            cwd=PROJECT_ROOT,
            env={**os.environ, 'NO_COLOR': '1'},
            timeout=LLM_DEFAULT_TIMEOUT,
            pid=rescore_pid,
        )

        if returncode != 0:
            error_msg = f"exit code {returncode}"
            for line in output_lines:
                try:
                    evt = json.loads(line)
                    if evt.get('type') == 'text':
                        error_msg = evt.get('part', {}).get('text', error_msg)[:300]
                except json.JSONDecodeError:
                    continue
            raise RuntimeError(f"mimo failed: {error_msg}")

        data = captured_result.get('result') or captured_result.get('pending_result')
        if not data:
            result_path = os.path.join(TMP_DIR, f'pending_result_{rescore_pid}.json')
            _check_result_file(result_path)
            with open(result_path) as f:
                data = json.load(f)
            try: os.remove(result_path)
            except OSError: pass

        analyzed_data = data['job']

        # Parse numeric scores from provider output
        fit_score_raw = analyzed_data.get('fit_score')
        success_score_raw = analyzed_data.get('success_score')
        fit_score = max(0, min(100, int(fit_score_raw))) if fit_score_raw is not None else None
        success_score = max(0, min(100, int(success_score_raw))) if success_score_raw is not None else None

        # Compute overall_score: (fit * 0.6) + (success * 0.4)
        overall_score = None
        if fit_score is not None and success_score is not None:
            overall_score = int(round(fit_score * SCORING_FIT_WEIGHT + success_score * SCORING_SUCCESS_WEIGHT))

        # Legacy summary grade fields (the summaries table keeps them).
        score_grade = normalize_score(analyzed_data.get('score', overall_score))
        success_grade = normalize_score(analyzed_data.get('success', success_score))
        match_grade = analyzed_data.get('match') or (
            'High' if overall_score is not None and overall_score >= 80
            else 'Medium' if overall_score is not None and overall_score >= 60
            else 'Low'
        )

        # Update the existing job with new scores
        job_data = {
            'id': job_id,
            'company': analyzed_data.get('company', j['company']),
            'role': analyzed_data.get('role', j['role']),
            'location': analyzed_data.get('location', j.get('location', 'Not specified')),
            'fit_score': fit_score,
            'success_score': success_score,
            'overall_score': overall_score,
            'salary': analyzed_data.get('salary', j.get('salary', 'Not specified')),
            'stack': analyzed_data.get('stack', j.get('stack', '')),
            'visa': analyzed_data.get('visa', j.get('visa', 'Uncertain')),
            'applicants': analyzed_data.get('applicants', j.get('applicants', 'Not specified')),
            'posted': analyzed_data.get('posted', j.get('posted', 'Not specified')),
            'posted_at': analyzed_data.get('posted_at', j.get('posted_at')),
            'adv_at': analyzed_data.get('adv_at', j.get('adv_at')),
            'see_at': j.get('see_at'),
            'apply_reason': analyzed_data.get('apply_reason', j.get('apply_reason', '')),
            'industry': analyzed_data.get('industry', j.get('industry', '')),
            'domain': analyzed_data.get('domain', j.get('domain', '')),
            'notes': analyzed_data.get('notes', j.get('notes', '')),
            'action': analyzed_data.get('action', j.get('action', '')),
            'work_types': analyzed_data.get('work_types', j.get('work_types', [])),
            'employment_types': analyzed_data.get('employment_types', j.get('employment_types', ['Full-time'])),
            'workflow_log': analyzed_data.get('workflow_log', j.get('workflow_log', '[]')),
            'raw_description': raw_desc,
            'structured_description': j.get('structured_description'),
            'raw_file_path': j.get('raw_file_path'),
            'structured_file_path': j.get('structured_file_path'),
        }

        _insert_job(job_data)
        _insert_summary({
            'job_id': job_id, 'company': job_data['company'],
            'match': match_grade, 'score': score_grade,
            'summary': data.get('summary', {}).get('summary', ''),
            'stack': job_data['stack'],
            'resumeFit': data.get('summary', {}).get('resumeFit', ''),
            'note': data.get('summary', {}).get('note', ''),
            'url': url,
        })

        # Clear rescoring flag
        session = get_session_sync()
        try:
            from jobs.infrastructure.repositories.sa_job_repository import SQLAlchemyJobRepository
            job_repo = SQLAlchemyJobRepository(session)
            job_repo.update_fields(job_id, rescoring=0)
        finally:
            session.close()

        log.info("worker.rescore_done", job_id=job_id, company=job_data['company'], score=score_grade)

    except Exception as e:
        log.error("worker.rescore_failed", job_id=job_id, error=str(e))
        # Clear rescoring flag on failure
        session = get_session_sync()
        try:
            from jobs.infrastructure.repositories.sa_job_repository import SQLAlchemyJobRepository
            job_repo = SQLAlchemyJobRepository(session)
            job_repo.update_fields(job_id, rescoring=0)
        finally:
            session.close()
    finally:
        try: os.remove(job_file)
        except OSError: pass

def _fail(pid, msg, step=None):
    """Mark job as failed with error message and which step failed."""
    STEP_LABELS = {
        'fetch': 'Fetching job page',
        'validate': 'Validating content',
        'extract_raw': 'Extracting raw info',
        'extract_struct': 'Structuring data',
        'summary': 'Building summary',
        'score': 'Scoring & analyzing',
        'resume': 'Saving results',
        'done': 'Finalizing',
        'ai': 'AI analysis',
        'worker': 'Processing',
    }
    label = STEP_LABELS.get(step, step) if step else 'Processing'
    error_msg = f"[{label}] {msg}" if step else msg
    _update_step(pid, 'step_done', 0, status='failed', error=error_msg)
    broadcaster.error(ProcessingError(
        table='job', pid=pid, msg=error_msg, step=step,
    ))

def _log(pid, step, msg):
    """Append a workflow log entry."""
    session = get_session_sync()
    try:
        from shared.infrastructure.process.repository import PendingJobRepository
        from shared.infrastructure.process.models import WorkflowLogEntry
        pending_repo = PendingJobRepository(session)
        pending_repo.append_log(pid, WorkflowLogEntry(step=step, msg=msg))
    finally:
        session.close()
    broadcaster.log(LogEntry(
        table='job', pid=pid, step=step, msg=msg,
    ))

def _load_rules(context='job'):
    """Load enabled scoring rules from DB, filtered by context, ordered by priority desc.

    Args:
        context: 'job' loads SHARED + JOB rules only.
                 'company' loads SHARED + company-type rules (caller must pass correct scopes).

    Validation: Job processor must NEVER load COMPANY_PRODUCT or COMPANY_RECRUITING rules.
    """
    session = get_session_sync()
    try:
        from rules.infrastructure.repositories.sa_rule_repository import SQLAlchemyRuleRepository
        rule_repo = SQLAlchemyRuleRepository(session)
        rows = rule_repo.get_enabled_by_scopes(['SHARED', 'JOB'])
    finally:
        session.close()

    if not rows:
        return "No scoring rules set."
    lines = []
    current_cat = None
    for r in rows:
        cat = r['category']
        if cat != current_cat:
            current_cat = cat
            lines.append(f"\n── {cat.upper()} {'─' * (35 - len(cat))}")
        weight = r["priority"]
        lines.append(f"  #{r['priority']:>3}  {r['key']} (weight:{weight}): {r['value']}")
    return '\n'.join(lines)

def _extract_structured_description(raw_text, num):
    """Extract structured job info from raw description using LLM service."""
    prompt = load_prompt('job_processing/step4_extract_struct',
        raw_content=raw_text[:FETCH_MAX_CONTENT_LENGTH])

    llm = get_llm_service()
    resp = llm.generate_structured(
        prompt,
        timeout=LLM_EXTRACT_JOB_TIMEOUT,
    )
    return resp.content

def _extract_all(raw_text, pid, session_id=None):
    """Combined extraction: validate + structured + summary in one LLM call."""
    prompt = load_prompt('job_processing/step3_extract_raw',
        content=raw_text[:FETCH_MAX_CONTENT_LENGTH])

    llm = get_llm_service()
    resp = llm.generate_structured(
        prompt,
        context={"pid": str(pid), "session_id": session_id},
        timeout=LLM_EXTRACT_JOB_TIMEOUT,
    )
    # Save session_id from response
    resp_session_id = resp.metadata.get("session_id")
    if resp_session_id:
        _save_session_id(pid, resp_session_id)
    # Parse the JSON content from the response
    try:
        return json.loads(resp.content)
    except (json.JSONDecodeError, TypeError):
        return None

def _mark_old_job_deleted(url, exclude_id=None):
    """Mark old job with same URL as deleted when rescore/requeue creates a new one."""
    session = get_session_sync()
    try:
        from jobs.infrastructure.repositories.sa_job_repository import SQLAlchemyJobRepository
        job_repo = SQLAlchemyJobRepository(session)
        job_repo.set_deleted_by_url(url, exclude_id)
    finally:
        session.close()

def _normalize_job_data(d):
    """Normalize the job location field."""
    import re
    from cities.domain.entities.city import CityNormalizer

    def extract_cities(text):
        if not text:
            return []
        cities = []
        text = re.sub(r'\(.*?\)', '', text)  # Remove parentheses
        parts = re.split(r'[,/\|]', text)
        for part in parts:
            part = part.strip()
            if not part:
                continue
            canonical, _ = CityNormalizer.normalize(part)
            if canonical and canonical not in cities:
                cities.append(canonical)
        return cities

    # Normalize location
    location = d.get('location', '')
    if location:
        # Extract just city from "Munich, Bavaria, Germany" -> "Munich"
        cities = extract_cities(location)
        if cities:
            d['location'] = cities[0]

    return d

# --- URL fetcher (uses unified Tool Layer) ---

def _fetch_multi_source(url, notes, links, pid):
    """Fetch content from multiple sources (notes + links).

    Uses the unified Tool Layer's fetch_page for local-first URL fetching.
    """
    parts = []

    # Add text notes
    for note in notes:
        if note.get('type') == 'text' and note.get('content'):
            parts.append(f"[NOTE] {note['content']}")

    # Fetch URL from the main job URL
    if url:
        try:
            page = fetch_page(url)
            if page.is_ok:
                parts.append(page.plain_text)
            else:
                _log(pid, 'fetch', f'URL fetch failed: {page.error.message if page.error else "Unknown error"}')
        except Exception as e:
            _log(pid, 'fetch', f'URL fetch failed: {e}')

    # Fetch URL-type notes (e.g. LinkedIn URLs submitted via notes field)
    for note in notes:
        if note.get('type') == 'url' and note.get('content'):
            note_url = note['content'].strip()
            if note_url.startswith('http') and note_url not in url:
                try:
                    page = fetch_page(note_url)
                    if page.is_ok:
                        parts.append(f"[URL] {page.plain_text}")
                    else:
                        _log(pid, 'fetch', f'Note URL fetch failed ({note_url[:60]}): {page.error.message if page.error else "Failed"}')
                except Exception as e:
                    _log(pid, 'fetch', f'Note URL fetch failed ({note_url[:60]}): {e}')

    # Fetch each link URL
    for link in links:
        link_url = link.get('url', '')
        if link_url and link_url.startswith('http'):
            try:
                page = fetch_page(link_url)
                if page.is_ok:
                    parts.append(f"[{link.get('title', 'Link')}] {page.plain_text}")
                else:
                    _log(pid, 'fetch', f'Link fetch failed ({link_url}): {page.error.message if page.error else "Failed"}')
            except Exception as e:
                _log(pid, 'fetch', f'Link fetch failed ({link_url}): {e}')

    return '\n\n'.join(parts)[:FETCH_COMPANY_MAX_LENGTH] if parts else ''


def _fetch_url(url):
    """Fetch a URL using the unified Tool Layer.

    Local-first approach: fetch → preprocess → return cleaned text.
    Raises RuntimeError for backward compatibility with existing callers.
    """
    page = fetch_page(url)
    if page.is_ok:
        return page.plain_text
    else:
        raise RuntimeError(page.error.message if page.error else f"Failed to fetch URL: {url}")

def _validate_job_content(raw_text, pid):
    """Validate and extract main job section from fetched content using LLM service."""
    prompt = load_prompt('job_processing/step2_validate', content=raw_text[:FETCH_MAX_CONTENT_LENGTH])

    try:
        llm = get_llm_service()
        resp = llm.generate_structured(
            prompt,
            context={"pid": str(pid)},
            timeout=LLM_EXTRACT_JOB_TIMEOUT,
        )
        return json.loads(resp.content)
    except Exception:
        pass
    # Fallback: heuristic validation
    job_keywords = ['engineer', 'developer', 'software', 'senior', 'backend', 'frontend',
                    'python', 'devops', 'sre', 'platform', 'role', 'responsibilities',
                    'requirements', 'qualifications', 'experience', 'apply', 'salary']
    text_lower = raw_text.lower()
    matches = sum(1 for kw in job_keywords if kw in text_lower)
    return {'valid': matches >= 2, 'content': raw_text, 'reason': f'Heuristic: {matches} job keywords found', 'title': None, 'company': None}

# --- Streaming subprocess execution ---

def _build_provider_cmd(prompt, session_id=None):
    """Build provider CLI command with optional session resumption. (Legacy — kept for compatibility)"""
    cmd = [MIMO_BIN, 'run', prompt, '--format', 'json', '--dangerously-skip-permissions']
    if session_id:
        cmd.extend(['--session', session_id])
    return cmd


def _stream_provider_output(cmd, cwd, env, timeout, pid, resume_session_id=None):
    """Run provider with streaming output via LLM Service.

    Returns (returncode, all_lines, session_id, result_dict).
    result_dict is captured from Write tool output events — no file I/O needed.
    """
    prompt = cmd[2] if len(cmd) > 2 else ""

    llm = get_llm_service()
    captured_result = {}

    def on_event(evt):
        _handle_provider_event(pid, evt)
        _capture_write_tool_output(evt, captured_result)

    def on_session_id(sid):
        _save_session_id(pid, sid)

    try:
        resp = llm.generate_streaming(
            prompt,
            context={
                "session_id": resume_session_id,
                "pid": pid,
                "cwd": cwd,
            },
            timeout=timeout,
            on_event=on_event,
            on_session_id=on_session_id,
        )

        all_lines = resp.metadata.get("lines", [])
        session_id = resp.metadata.get("session_id")
        returncode = resp.metadata.get("returncode", 0)

        if not session_id:
            session_id = f"ai_{uuid.uuid4().hex[:12]}"
            _save_session_id(pid, session_id)

        if not captured_result and resp.content:
            try:
                parsed = repair_llm_json(resp.content)
                if isinstance(parsed, dict):
                    captured_result['result'] = parsed
            except Exception:
                pass

        return returncode, all_lines, session_id, captured_result

    except RuntimeError as e:
        if "timed out" in str(e):
            return -9, [], resume_session_id, {}
        raise


def _capture_write_tool_output(evt: dict, captured: dict) -> None:
    """Capture Write tool output from streaming events into a dict."""
    if evt.get("type") == "tool_use":
        part = evt.get("part", {})
        state = part.get("state", {})
        title = state.get("title", "")
        output = state.get("output", "")
        if output and title:
            captured[title] = output
    # Also capture result from tool_finish or step_finish with result data
    if evt.get("type") == "step_finish":
        part = evt.get("part", {})
        result = part.get("result") or part.get("output")
        if result:
            captured["result"] = result


def _handle_provider_event(pid, evt):
    """Process a single JSON event the moment it arrives on stdout.

    This function is the extension point for real-time delivery:
    - Log to DB (already wired via _log)
    - Push to WebSocket / SSE / queue / callback — add here
    """
    event_type = evt.get('type', '')

    if event_type == 'text':
        text = evt.get('part', {}).get('text', '')
        if text:
            _log(pid, 'ai', f'text: {text[:200]}')

    elif event_type == 'tool_use':
        part = evt.get('part', {})
        tool = part.get('tool', 'unknown')
        state = part.get('state', {})
        status = state.get('status', '')
        title = state.get('title', '')
        _log(pid, 'ai', f'tool: {tool} [{status}] {title}')

    elif event_type == 'step_finish':
        part = evt.get('part', {})
        reason = part.get('reason', '')
        tokens = part.get('tokens', {})
        _log(pid, 'ai',
             f'step_finish: {reason} ({tokens.get("total", 0)} tokens)')


# --- Main pipeline ---

def process_job(pid):
    """Process a pending job using LangGraph state management.

    Delegates to JobWorker which uses the LangGraph job graph.
    """
    from shared.infrastructure.process_utils import (
        ProcessManager, TempFileManager, MimoRunner, broadcaster,
    )
    from shared.infrastructure.process.repository import PendingJobRepository
    from dependencies import get_session_sync

    session = get_session_sync()
    try:
        pending_repo = PendingJobRepository(session)
        proc_mgr = ProcessManager()
        temp_mgr = TempFileManager()
        provider_runner = MimoRunner(proc_mgr)

        from jobs.infrastructure.workers.job_worker import JobWorker
        worker = JobWorker(
            pending_repo=pending_repo,
            process_mgr=proc_mgr,
            temp_mgr=temp_mgr,
            provider_runner=provider_runner,
            broadcaster=broadcaster,
        )
        worker.process(pid)
    finally:
        session.close()
        try:
            from shared.infrastructure.config.queue import get_queue_manager
            get_queue_manager().signal_job_done(pid)
        except Exception:
            pass
