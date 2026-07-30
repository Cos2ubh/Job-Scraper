"""Pure-Python TF-IDF match scoring.

Resume text (+ optional keyword list) is compared against each job's
title + tags + description. Returns a percentage 0-100 based on
cosine similarity of TF-IDF vectors, boosted by a keyword-intersection bonus.
"""
import math
import re
from collections import Counter
from typing import Iterable

_TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9\+\#\.]{1,}")

STOPWORDS = {
    "the", "and", "for", "with", "you", "your", "our", "are", "will", "can",
    "have", "has", "this", "that", "from", "into", "who", "what", "when",
    "where", "how", "why", "which", "any", "all", "one", "two", "may", "not",
    "but", "was", "were", "been", "being", "they", "them", "their", "there",
    "here", "his", "her", "its", "about", "over", "under", "than", "then",
    "such", "some", "each", "also", "other", "would", "should", "could",
    "must", "job", "jobs", "role", "roles", "team", "work", "working",
    "candidate", "candidates", "experience", "years", "year", "please",
    "we're", "we", "us", "you'll", "you're", "a", "an", "of", "in", "on",
    "to", "at", "by", "or", "is", "be", "as", "it", "if", "do", "so",
}


def tokenize(text: str) -> list[str]:
    if not text:
        return []
    return [
        t.lower() for t in _TOKEN_RE.findall(text)
        if t.lower() not in STOPWORDS and len(t) > 1
    ]


def _tf(tokens: list[str]) -> dict[str, float]:
    if not tokens:
        return {}
    counts = Counter(tokens)
    total = float(len(tokens))
    return {term: count / total for term, count in counts.items()}


def _idf(docs: list[list[str]]) -> dict[str, float]:
    n = len(docs)
    if n == 0:
        return {}
    df: Counter = Counter()
    for doc in docs:
        for term in set(doc):
            df[term] += 1
    return {term: math.log((1 + n) / (1 + freq)) + 1 for term, freq in df.items()}


def _vec(tokens: list[str], idf: dict[str, float]) -> dict[str, float]:
    tf = _tf(tokens)
    return {term: freq * idf.get(term, 0.0) for term, freq in tf.items()}


def _cosine(a: dict[str, float], b: dict[str, float]) -> float:
    if not a or not b:
        return 0.0
    common = set(a.keys()) & set(b.keys())
    dot = sum(a[t] * b[t] for t in common)
    na = math.sqrt(sum(v * v for v in a.values()))
    nb = math.sqrt(sum(v * v for v in b.values()))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def build_scorer(resume_text: str, keywords: str = ""):
    """Return a function `score(job) -> float 0..100`.

    Corpus (for IDF) is built lazily per batch by calling `scorer.prime(jobs)`.
    """
    resume_tokens = tokenize(resume_text)
    keyword_set = {k.strip().lower() for k in keywords.split(",") if k.strip()}
    if keyword_set:
        resume_tokens.extend(list(keyword_set) * 2)  # weight explicit keywords

    class Scorer:
        def __init__(self):
            self.idf: dict[str, float] = {}
            self.resume_vec: dict[str, float] = {}

        def prime(self, job_texts: Iterable[str]) -> None:
            docs = [resume_tokens] + [tokenize(t) for t in job_texts]
            self.idf = _idf(docs)
            self.resume_vec = _vec(resume_tokens, self.idf)

        def score(self, job_text: str) -> float:
            if not self.resume_vec:
                return 0.0
            job_tokens = tokenize(job_text)
            if not job_tokens:
                return 0.0
            job_vec = _vec(job_tokens, self.idf)
            cos = _cosine(self.resume_vec, job_vec)  # 0..1

            bonus = 0.0
            if keyword_set:
                job_set = set(job_tokens)
                overlap = len(keyword_set & job_set) / max(1, len(keyword_set))
                bonus = overlap * 0.25  # up to +25 points from keyword hits

            raw = min(1.0, cos * 1.4 + bonus)
            return round(raw * 100, 1)

    scorer = Scorer()
    return scorer


def job_text(job) -> str:
    parts = [
        job.title or "",
        job.tags or "",
        job.description or "",
    ]
    return " \n ".join(parts)
