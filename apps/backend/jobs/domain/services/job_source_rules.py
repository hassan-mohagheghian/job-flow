"""Job source identification — canonical domain resolution from job URLs.

Source identity rules (see docs/api/jobs/job-sources-dashboard.md):

- The source of a job is the *job board / recruitment site* the listing URL
  points to, derived from the URL hostname.
- ``www`` prefixes, ports, trailing dots and URL paths are irrelevant.
- Known boards that span many ccTLDs canonicalize to one registrable identity
  via an explicit, testable alias suffix map (never substring guessing — only
  listed suffixes canonicalize).
- A job whose URL cannot be resolved has no source (dashboard "Unknown").
"""

from __future__ import annotations

from urllib.parse import urlsplit

from shared.infrastructure.process.logging_config import get_logger

log = get_logger("job_source_rules")

# Multi-TLD boards whose regional variants are one source. Each entry lists
# the explicit TLDs we recognize for the board label; exactly the listed
# hosts (optionally with subdomains) canonicalize — no substring guessing.
# Format: (board_label, recognized_tlds, canonical_registrable_domain)
KNOWN_BOARDS: tuple[tuple[str, tuple[str, ...], str], ...] = (
    ("indeed", ("com", "co.uk", "de", "at", "ch", "au", "ca", "fr", "es", "it", "nl", "mx", "in"), "indeed.com"),
    ("linkedin", ("com",), "linkedin.com"),
    ("glassdoor", ("com",), "glassdoor.com"),
    ("merojob", ("com", "com.np"), "merojob.com"),
    ("stepstone", ("com", "de", "at"), "stepstone.com"),
    ("jobsdb", ("com",), "jobsdb.com"),
    ("reed", ("co.uk",), "reed.co.uk"),
    ("monster", ("com", "de", "co.uk"), "monster.com"),
    ("careerjet", ("com",), "careerjet.com"),
    ("jobteaser", ("com",), "jobteaser.com"),
    ("welcometothejungle", ("com",), "welcometothejungle.com"),
)


def _board_canonical(host: str) -> str | None:
    for label, tlds, canonical in KNOWN_BOARDS:
        for tld in tlds:
            if host == f"{label}.{tld}" or host.endswith(f".{label}.{tld}"):
                return canonical
    return None


def extract_hostname(url: str | None) -> str | None:
    """Return the lowercased hostname of a job URL, or None when absent/invalid.

    Accepts ``https://host/path``, ``//host/...``, bare ``host`` and
    ``host:8080``. Never raises — unparseable input yields None.
    """
    if not url or not url.strip():
        return None
    try:
        raw = url.strip()
        if "://" not in raw and not raw.startswith("//"):
            raw = f"https://{raw}"
        host = urlsplit(raw).hostname
    except ValueError:
        return None
    if not host:
        return None
    return host.lower().rstrip(".")


def canonicalize_domain(host: str | None) -> str | None:
    """Canonicalize a hostname to its source identity, or None.

    - lowercases, strips ``www.`` prefix and trailing dots;
    - applies the explicit known-board alias map (suffix, not substring);
    - unknown TLD variants remain their own distinct source.
    """
    if not host:
        return None
    cleaned = host.lower().strip().rstrip(".")
    while cleaned.startswith("www."):
        cleaned = cleaned[4:]
    if not cleaned or "." not in cleaned:
        return None
    canonical = _board_canonical(cleaned)
    if canonical:
        log.debug(
            "job_source_rules.canonicalized", host=cleaned, canonical=canonical
        )
        return canonical
    return cleaned


def resolve_source(url: str | None) -> str | None:
    """Full resolution: job URL → canonical source domain (or None)."""
    return canonicalize_domain(extract_hostname(url))


def display_name_for_domain(domain: str | None) -> str:
    """Human display name for a canonical domain (``indeed.com`` → ``Indeed.com``)."""
    if not domain:
        return "Unknown"
    return domain[:1].upper() + domain[1:]
