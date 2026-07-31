"""Detect jobs that live behind a paid subscription.

Detection is URL-based (high precision). We check two places:

1. **The stored `url`** — where the scraper says the listing lives.
2. **URLs embedded in the description** — because RemoteOK / WWR / HN
   listings often keep their own URL as the primary link but embed the
   *real* apply URL in the body. If the outbound apply URL points at a
   paid site, we mark the row paywalled.

Free-account-required boards (LinkedIn, Indeed, Wellfound, Otta, etc.)
are considered accessible — users don't have to pay to apply there.

Fuzzy phrase-matching against the description was tried and produced too
many false positives (e.g. "Spotify Premium subscription" listed as a
company perk got flagged). Kept out.
"""
import re
from urllib.parse import urlparse

# Sites that require a paid membership to see the listing / contact info.
PAYWALLED_DOMAINS = {
    "flexjobs.com",
    "theladders.com",
    "ladders.com",
    "virtualvocations.com",
    "ratracerebellion.com",
    "premium.jobs",
}

_URL_RE = re.compile(r'https?://[^\s<>"\']+', re.IGNORECASE)


def _host(url: str) -> str:
    if not url:
        return ""
    try:
        host = (urlparse(url).hostname or "").lower()
        return host[4:] if host.startswith("www.") else host
    except Exception:
        return ""


def is_paywalled_url(url: str) -> bool:
    host = _host(url)
    if not host:
        return False
    for domain in PAYWALLED_DOMAINS:
        if host == domain or host.endswith("." + domain):
            return True
    return False


def _description_has_paywalled_link(description: str) -> bool:
    if not description:
        return False
    for url in _URL_RE.findall(description):
        if is_paywalled_url(url):
            return True
    return False


def classify_accessibility(url: str, description: str = "") -> str:
    if is_paywalled_url(url) or _description_has_paywalled_link(description):
        return "paywalled"
    return "accessible"
