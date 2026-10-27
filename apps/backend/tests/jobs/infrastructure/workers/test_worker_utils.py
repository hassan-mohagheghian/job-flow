"""Tests for worker.py utility functions — scoring, normalization, DB helpers."""

import pytest
from unittest.mock import patch, MagicMock

from shared.infrastructure.database.sqlalchemy_config import Base
import jobs.infrastructure.models.job_model


class TestNormalizeScore:
    def test_valid_grades_passthrough(self):
        from jobs.infrastructure.workers.worker import normalize_score
        for grade in ['P', 'E', 'D', 'C', 'B', 'A', 'A+', 'A++']:
            assert normalize_score(grade) == grade

    def test_lowercase_converted(self):
        from jobs.infrastructure.workers.worker import normalize_score
        assert normalize_score('a') == 'A'
        assert normalize_score('a++') == 'A++'
        assert normalize_score('b') == 'B'

    def test_numeric_integer(self):
        from jobs.infrastructure.workers.worker import normalize_score
        assert normalize_score(95) == 'A++'
        assert normalize_score(85) == 'A+'
        assert normalize_score(75) == 'A'
        assert normalize_score(60) == 'B'
        assert normalize_score(40) == 'C'
        assert normalize_score(20) == 'D'

    def test_numeric_string(self):
        from jobs.infrastructure.workers.worker import normalize_score
        assert normalize_score('95') == 'A++'
        assert normalize_score('85') == 'A+'
        assert normalize_score('75') == 'A'

    def test_numeric_float(self):
        from jobs.infrastructure.workers.worker import normalize_score
        assert normalize_score(92.5) == 'A++'

    def test_none_returns_pending(self):
        from jobs.infrastructure.workers.worker import normalize_score
        assert normalize_score(None) == 'P'

    def test_invalid_string_returns_pending(self):
        from jobs.infrastructure.workers.worker import normalize_score
        assert normalize_score('invalid') == 'P'
        assert normalize_score('') == 'P'

    def test_boundary_values(self):
        from jobs.infrastructure.workers.worker import normalize_score
        assert normalize_score(0) == 'D'
        assert normalize_score(29) == 'D'
        assert normalize_score(30) == 'C'
        assert normalize_score(49) == 'C'
        assert normalize_score(50) == 'B'
        assert normalize_score(69) == 'B'
        assert normalize_score(70) == 'A'
        assert normalize_score(79) == 'A'
        assert normalize_score(80) == 'A+'
        assert normalize_score(89) == 'A+'
        assert normalize_score(90) == 'A++'
        assert normalize_score(100) == 'A++'

    def test_clamping(self):
        from jobs.infrastructure.workers.worker import normalize_score
        assert normalize_score(-10) == 'D'
        assert normalize_score(150) == 'A++'


class TestScoreToGrade:
    def test_none_returns_pending(self):
        from jobs.infrastructure.workers.worker import score_to_grade
        assert score_to_grade(None) == 'P'

    def test_numeric_conversion(self):
        from jobs.infrastructure.workers.worker import score_to_grade
        assert score_to_grade(95) == 'A++'
        assert score_to_grade(75) == 'A'


class TestCalculateOverallScore:
    def test_weighted_average(self):
        from jobs.infrastructure.workers.worker import calculate_overall_score
        result = calculate_overall_score(80, 60)
        expected = round(80 * 0.6 + 60 * 0.4, 1)
        assert result == expected

    def test_none_fit_score(self):
        from jobs.infrastructure.workers.worker import calculate_overall_score
        assert calculate_overall_score(None, 60) is None

    def test_none_success_score(self):
        from jobs.infrastructure.workers.worker import calculate_overall_score
        assert calculate_overall_score(80, None) is None

    def test_both_none(self):
        from jobs.infrastructure.workers.worker import calculate_overall_score
        assert calculate_overall_score(None, None) is None

    def test_extreme_values(self):
        from jobs.infrastructure.workers.worker import calculate_overall_score
        assert calculate_overall_score(100, 100) == 100.0
        assert calculate_overall_score(0, 0) == 0.0


class TestNormalizeJobData:
    def test_known_city_extraction(self):
        from jobs.infrastructure.workers.worker import _normalize_job_data
        d = {'location': 'Munich, Bavaria, Germany'}
        result = _normalize_job_data(d)
        assert result['location'] == 'Munich'

    def test_unknown_city_kept(self):
        from jobs.infrastructure.workers.worker import _normalize_job_data
        d = {'location': 'Springfield, USA'}
        result = _normalize_job_data(d)
        assert 'Springfield' in result['location']

class TestFetchUrl:
    @patch('jobs.infrastructure.workers.worker.fetch_page')
    def test_fetch_invalid_url_raises(self, mock_fetch_page):
        from ai.infrastructure.tools.models import FetchError, FetchedPage
        mock_fetch_page.return_value = FetchedPage(
            url='https://this-domain-does-not-exist-12345.invalid',
            status='failed',
            error=FetchError(
                code='FETCH_FAILED',
                message='Network error: <urlopen error name not resolved>',
                url='https://this-domain-does-not-exist-12345.invalid',
            ),
        )
        from jobs.infrastructure.workers.worker import _fetch_url
        with pytest.raises(RuntimeError, match="Network error|Failed to fetch"):
            _fetch_url("https://this-domain-does-not-exist-12345.invalid")

    @patch('jobs.infrastructure.workers.worker.urllib.request.urlopen')
    def test_fetch_404_raises(self, mock_urlopen):
        import urllib.error
        mock_urlopen.side_effect = urllib.error.HTTPError(
            url='http://test', code=404, msg='Not Found', hdrs=None, fp=None
        )
        from jobs.infrastructure.workers.worker import _fetch_url
        with pytest.raises(RuntimeError, match="Page not found"):
            _fetch_url("http://test")

    @patch('jobs.infrastructure.workers.worker.urllib.request.urlopen')
    def test_fetch_403_raises(self, mock_urlopen):
        import urllib.error
        mock_urlopen.side_effect = urllib.error.HTTPError(
            url='http://test', code=403, msg='Forbidden', hdrs=None, fp=None
        )
        from jobs.infrastructure.workers.worker import _fetch_url
        with pytest.raises(RuntimeError, match="Access denied"):
            _fetch_url("http://test")


class TestParsePostedDate:
    def test_hours_ago(self):
        from jobs.infrastructure.workers.worker import _parse_posted_date
        result = _parse_posted_date('3 hours ago')
        assert result is not None

    def test_days_ago(self):
        from jobs.infrastructure.workers.worker import _parse_posted_date
        result = _parse_posted_date('2 days ago')
        assert result is not None

    def test_weeks_ago(self):
        from jobs.infrastructure.workers.worker import _parse_posted_date
        result = _parse_posted_date('1 week ago')
        assert result is not None

    def test_months_ago(self):
        from jobs.infrastructure.workers.worker import _parse_posted_date
        result = _parse_posted_date('1 month ago')
        assert result is None or isinstance(result, str)

    def test_active_returns_none(self):
        from jobs.infrastructure.workers.worker import _parse_posted_date
        assert _parse_posted_date('Active') is None

    def test_empty_returns_none(self):
        from jobs.infrastructure.workers.worker import _parse_posted_date
        assert _parse_posted_date('') is None

    def test_na_returns_none(self):
        from jobs.infrastructure.workers.worker import _parse_posted_date
        assert _parse_posted_date('N/A') is None


class TestGetExistingId:
    def test_existing_url(self, sa_session):
        from jobs.infrastructure.workers.worker import _get_existing_id
        from jobs.infrastructure.models.job_model import JobModel
        job = JobModel(id="existing-id-123", company="Test", role="Dev", url="https://example.com", user_id="test-user")
        sa_session.add(job)
        sa_session.commit()
        with patch('jobs.infrastructure.workers.worker.get_session_sync', return_value=sa_session):
            assert _get_existing_id('https://example.com') == "existing-id-123"

    def test_new_url(self, sa_session):
        from jobs.infrastructure.workers.worker import _get_existing_id
        with patch('jobs.infrastructure.workers.worker.get_session_sync', return_value=sa_session):
            assert _get_existing_id('https://new.com') is None


class TestIsPausedOrStopped:
    def test_item_deleted_returns_true(self):
        from jobs.infrastructure.workers.worker import _is_paused_or_stopped
        with patch('jobs.infrastructure.workers.worker._get_item') as mock_get:
            mock_get.return_value = None
            assert _is_paused_or_stopped(1) is True

    def test_processing_returns_false(self):
        from jobs.infrastructure.workers.worker import _is_paused_or_stopped
        with patch('jobs.infrastructure.workers.worker._get_item') as mock_get:
            mock_get.return_value = {'status': 'processing'}
            assert _is_paused_or_stopped(1) is False

    def test_paused_returns_true(self):
        from jobs.infrastructure.workers.worker import _is_paused_or_stopped
        with patch('jobs.infrastructure.workers.worker._get_item') as mock_get:
            mock_get.return_value = {'status': 'paused'}
            assert _is_paused_or_stopped(1) is True

    def test_queued_returns_true(self):
        from jobs.infrastructure.workers.worker import _is_paused_or_stopped
        with patch('jobs.infrastructure.workers.worker._get_item') as mock_get:
            mock_get.return_value = {'status': 'queued'}
            assert _is_paused_or_stopped(1) is True