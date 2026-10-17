"""Tests for canonical job-source identification (job_source_rules)."""

import pytest

from jobs.domain.services.job_source_rules import (
    canonicalize_domain,
    display_name_for_domain,
    extract_hostname,
    resolve_source,
)


class TestExtractHostname:
    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("https://www.indeed.com/viewjob?jk=1", "www.indeed.com"),
            ("http://jobs.example.com:8080/x", "jobs.example.com"),
            ("//bare.path.com/thing", "bare.path.com"),
            ("bare.host.io", "bare.host.io"),
            ("  https://spaced.io/x  ", "spaced.io"),
            (None, None),
            ("", None),
            ("   ", None),
            ("https://", None),
        ],
    )
    def test_variants(self, raw, expected):
        assert extract_hostname(raw) == expected


class TestCanonicalizeDomain:
    @pytest.mark.parametrize(
        "host,expected",
        [
            ("www.indeed.com", "indeed.com"),
            ("indeed.com.", "indeed.com"),
            ("WWW.Example.COM", "example.com"),
            ("de.indeed.co.uk", "indeed.com"),
            ("indeed.de", "indeed.com"),
            ("de.linkedin.com", "linkedin.com"),
            ("mx.glassdoor.com", "glassdoor.com"),
            ("www.merojob.com.np", "merojob.com"),
            ("jobs.stepstone.de", "stepstone.com"),
            ("hk.jobsdb.com", "jobsdb.com"),
            ("board.example.org", "board.example.org"),
            ("unknown.io", "unknown.io"),
            (None, None),
            ("", None),
            ("localhost", None),
        ],
    )
    def test_rules(self, host, expected):
        assert canonicalize_domain(host) == expected

    def test_alias_map_records_are_explicit(self):
        """Board list stays curated: each entry is (label, tlds, canonical)."""
        rules = __import__("jobs.domain.services.job_source_rules", fromlist=["KNOWN_BOARDS"])
        for label, tlds, canonical in rules.KNOWN_BOARDS:
            assert label and tlds and canonical.startswith(f"{label}.")


class TestResolveSource:
    @pytest.mark.parametrize(
        "url,expected",
        [
            ("https://www.indeed.com/viewjob?jk=xyz", "indeed.com"),
            ("https://www.linkedin.com/jobs/view/123456", "linkedin.com"),
            ("ftp://weird.jobzone.example.com/x", "weird.jobzone.example.com"),
            ("", None),
            (None, None),
            ("not a url at all", None),
        ],
    )
    def test_end_to_end(self, url, expected):
        assert resolve_source(url) == expected


class TestDisplayName:
    def test_caps_registrable_label(self):
        assert display_name_for_domain("indeed.com") == "Indeed.com"

    def test_unknown_when_missing(self):
        assert display_name_for_domain(None) == "Unknown"
