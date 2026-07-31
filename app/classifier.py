"""Keyword-based classifiers for experience level and job category.

Both run at upsert time (see orchestrator) so the values are stored on the
row and can be indexed + filtered in SQL. Deliberately dumb regexes over
title + description + tags — no ML dependency, no LLM call. Improves with
better keyword lists, not with a smarter model.
"""
import re
from typing import Iterable


# ---------------------------------------------------------------------------
# Experience level
# ---------------------------------------------------------------------------
# Order matters: check senior first (most specific), then fresher, then mid.

_SENIOR_RE = re.compile(
    r"\b("
    r"senior|sr\.?|lead|principal|staff|"
    r"architect|director|head\s+of|vp\s+of|chief|"
    r"(?:5|6|7|8|9|10|11|12|15)\s*\+?\s*(?:years?|yrs?)|"
    r"(?:5|6|7|8|9|10|11|12|15)-\d+\s*(?:years?|yrs?)"
    r")\b",
    re.IGNORECASE,
)

_FRESHER_RE = re.compile(
    r"\b("
    r"fresher|freshers|entry[-\s]?level|junior|jr\.?|"
    r"graduate|new\s+grad|recent\s+graduate|"
    r"intern|internship|trainee|apprentice|"
    r"no\s+experience|0[-\s]?[12]?\s*(?:years?|yrs?)|"
    r"(?:zero|one)\s+years?"
    r")\b",
    re.IGNORECASE,
)

_MID_RE = re.compile(
    r"\b("
    r"mid[-\s]?level|mid[-\s]?senior|"
    r"[234]\s*\+?\s*(?:years?|yrs?)|"
    r"[234]-\d+\s*(?:years?|yrs?)|"
    r"intermediate"
    r")\b",
    re.IGNORECASE,
)


def classify_experience(title: str, description: str, tags: Iterable[str] | None = None) -> str:
    tag_str = " ".join(tags) if tags else ""
    # Title carries most signal for seniority
    header_scope = f"{title or ''} {tag_str}"
    body_scope = (description or "")[:1500]

    if _SENIOR_RE.search(header_scope) or _SENIOR_RE.search(body_scope):
        return "senior"
    if _FRESHER_RE.search(header_scope) or _FRESHER_RE.search(body_scope):
        return "fresher"
    if _MID_RE.search(header_scope) or _MID_RE.search(body_scope):
        return "mid"
    return "unknown"


# ---------------------------------------------------------------------------
# Category
# ---------------------------------------------------------------------------

_TECH_TOKENS = {
    "engineer", "engineering", "developer", "programmer", "coder", "swe",
    "software", "backend", "back-end", "back end", "frontend", "front-end",
    "front end", "fullstack", "full-stack", "full stack", "devops", "sre",
    "site reliability", "data engineer", "data scientist", "data analyst",
    "analytics engineer", "ml engineer", "machine learning", "ai engineer",
    "artificial intelligence", "computer vision", "nlp", "security engineer",
    "cybersecurity", "penetration", "cloud engineer", "platform engineer",
    "infrastructure", "systems engineer", "sysadmin", "database", "dba",
    "qa engineer", "sdet", "test engineer", "embedded", "firmware",
    "ios developer", "android developer", "mobile developer", "web developer",
    "python", "java", "javascript", "typescript", "golang", "rust engineer",
    "kotlin", "scala", "elixir", "ruby on rails", "django", "node.js",
    "react", "angular", "vue", "kubernetes", "docker", "terraform", "aws",
    "azure", "gcp", "solutions architect", "technical lead", "tech lead",
    "blockchain", "smart contract", "solidity",
}

_DESIGN_TOKENS = {
    "designer", "design", "ux", "ui", "ux/ui", "product design",
    "graphic design", "visual design", "motion design", "illustrator",
    "brand designer", "creative director", "art director",
}

_PRODUCT_TOKENS = {
    "product manager", "product management", "product owner",
    "product ops", "technical product manager", "tpm", "group product",
    "senior product", "junior product", "associate product",
}

_BUSINESS_TOKENS = {
    "sales", "account executive", "ae", "sdr", "bdr", "account manager",
    "customer success", "cs manager", "support engineer", "customer support",
    "marketing", "content marketing", "growth", "seo", "sem",
    "brand manager", "community manager", "social media",
    "recruiter", "talent", "human resources", "hr", "people ops",
    "finance", "accountant", "controller", "cfo", "bookkeeper",
    "operations", "ops manager", "coo", "administrative", "executive assistant",
    "business analyst", "business development", "bizdev", "consultant",
    "legal", "paralegal", "compliance",
}


def _match_any(haystack: str, tokens: Iterable[str]) -> bool:
    return any(token in haystack for token in tokens)


def classify_category(title: str, tags: Iterable[str] | None = None) -> str:
    tag_str = " ".join(tags) if tags else ""
    haystack = f"{title or ''} {tag_str}".lower()

    # Order matters: product manager contains "product" which some tech roles
    # might also carry (e.g. "product engineer" → tech). Check product first
    # only if the exact phrase "product manager" or "product owner" appears.
    if _match_any(haystack, _PRODUCT_TOKENS):
        return "product"
    if _match_any(haystack, _TECH_TOKENS):
        return "technical"
    if _match_any(haystack, _DESIGN_TOKENS):
        return "design"
    if _match_any(haystack, _BUSINESS_TOKENS):
        return "business"
    return "other"
