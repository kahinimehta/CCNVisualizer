"""Shared text cleanup and embedding helpers for scrape.py and build.py."""

from __future__ import annotations

import re

from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS

METADATA_KEYWORD_PHRASES = frozenset(
    {
        "psychological / behavioral research",
        "computational cognitive science / cognitive modeling",
        "theoretical / computational neuroscience",
        "experimental neuroscience (systems / cognitive)",
        "artificial intelligence / machine learning",
        "methods & computational tools",
        "brain networks & neural dynamics",
        "visual processing & computational vision",
        "object recognition & visual attention",
        "reward, value & social decision making",
        "memory, spatial cognition & skill learning",
        "predictive processing & cognitive control",
        "language & communication",
        "extended abstract",
        "extended abstracts",
        "cognitive science",
        "neuroscience",
        "psychology",
        "engineering",
        "mathematics",
        "philosophy",
        "artificial intelligence",
        "linguistics",
    }
)

METADATA_KEYWORD_TOKENS = frozenset(
    {
        "fmri",
        "eeg",
        "meg",
        "ecog",
        "bold",
        "neuroimaging",
        "psychological",
        "behavioral",
        "computational",
        "modeling",
        "experimental",
        "systems",
        "cognitive",
        "abstract",
        "poster",
        "paper",
        "proceedings",
    }
)

GENERIC_KEYWORD_LABELS = frozenset({"cognitive science", "cognitive"})

CITATION_FRAGMENT_RES = (
    re.compile(r"\bet\s+al\.?", re.I),
    re.compile(r"\bp\.?\s*\d+(?:\s*[-–—]\s*\d+)?", re.I),
    re.compile(r"\bpp\.?\s*\d+", re.I),
    re.compile(r"\bdoi\s*[:.]?\s*\S+", re.I),
    re.compile(r"https?://\S+", re.I),
    re.compile(r"\bvol\.?\s*\d+", re.I),
    re.compile(r"\bno\.?\s*\d+", re.I),
    re.compile(r"\(\s*\d{4}[a-z]?\s*\)", re.I),
)

TITLE_WEIGHT = 2
ABSTRACT_WEIGHT = 3
KEYWORD_WEIGHT = 1

MAX_KEYWORD_CHARS = 72
MAX_KEYWORD_WORDS = 8
MAX_KEYWORD_LIST_SIZE = 8
CORRUPT_KEYWORD_SOURCE_COUNT = 15

KEYWORD_VERBS = frozenset(
    {
        "begin",
        "show",
        "shows",
        "using",
        "used",
        "note",
        "noted",
        "found",
        "make",
        "see",
        "seen",
        "give",
        "given",
        "provide",
        "provides",
        "suggest",
        "suggests",
        "demonstrate",
        "demonstrates",
        "maintain",
        "asked",
        "chairing",
        "inhibit",
    }
)

BAD_KEYWORD_FIRST_WORDS = frozenset({"they", "this", "these", "those", "as", "we", "our", "it", "its", "blue"})

BAD_KEYWORD_PREFIXES = (
    "including ",
    "and ",
    "as well",
    "as noted",
    "such as ",
    "however ",
    "therefore ",
    "although ",
    "more importantly",
    "consistent with ",
    "previous work ",
    "in contrast ",
)

TITLE_KEYWORD_STOPWORDS = frozenset(
    {
        "a",
        "an",
        "the",
        "of",
        "for",
        "in",
        "on",
        "to",
        "and",
        "with",
        "from",
        "by",
        "via",
        "using",
        "model",
        "models",
        "study",
        "studies",
        "toward",
        "towards",
        "between",
        "across",
        "into",
        "through",
        "during",
        "within",
        "without",
        "based",
        "new",
        "novel",
    }
)

_MOJIBAKE_MARKERS = re.compile(
    r"[ÃÄÅÆÇÐÑØÞßàáâãäåæçèéêëìíîïðñòóôõö÷øùúûüýþÿ\u0080-\u009f]"
)

GAC_UPDATE_TITLE_RE = re.compile(r"^\[\s*GAC\s+update\s*\]", re.I)
YEAR_ID_CACHE_KEY_RE = re.compile(r"^\d{4}:")


def submission_row_key(submission: dict) -> str:
    """Stable per-paper key; CCN reuses numeric ids across years."""
    year = submission.get("year", "")
    paper_id = str(submission.get("id") or submission.get("poster_number") or submission.get("title", ""))
    return f"{year}:{paper_id}"


def is_year_id_cache_key(key: str) -> bool:
    return bool(YEAR_ID_CACHE_KEY_RE.match(str(key)))


def is_gac_update(title: str) -> bool:
    """True for CCN Generative Adversarial Collaboration update posters (not regular submissions)."""
    return bool(GAC_UPDATE_TITLE_RE.match((title or "").strip()))


def strip_citation_fragments(text: str) -> str:
    if not text:
        return ""
    cleaned = text
    for pattern in CITATION_FRAGMENT_RES:
        cleaned = pattern.sub(" ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" ,.;")
    return cleaned.strip()


def normalize_keyword_phrase(keyword: str) -> str:
    return strip_citation_fragments(re.sub(r"\s+", " ", (keyword or "").strip().lower()))


def is_metadata_keyword(keyword: str) -> bool:
    normalized = normalize_keyword_phrase(keyword)
    if not normalized:
        return True
    if normalized in METADATA_KEYWORD_PHRASES:
        return True
    if normalized in GENERIC_KEYWORD_LABELS:
        return True
    tokens = re.findall(r"[a-z][a-z0-9\-]{2,}", normalized)
    if tokens and all(token in METADATA_KEYWORD_TOKENS for token in tokens):
        return True
    return False


def normalize_field_text(text: str) -> str:
    if not text:
        return ""
    cleaned = repair_mojibake(str(text))
    cleaned = cleaned.replace("\r\n", "\n").replace("\r", "\n")
    cleaned = re.sub(r"\s*\n\s*", " ", cleaned)
    return re.sub(r"\s+", " ", cleaned).strip()


def is_plausible_keyword(keyword: str) -> bool:
    normalized = normalize_keyword_phrase(keyword)
    if not normalized:
        return False
    if len(normalized) > MAX_KEYWORD_CHARS:
        return False
    words = normalized.split()
    if len(words) > MAX_KEYWORD_WORDS:
        return False
    if len(words) == 1 and re.fullmatch(r"\d{4}", words[0]):
        return False
    if words[0] in BAD_KEYWORD_FIRST_WORDS:
        return False
    if any(word in KEYWORD_VERBS for word in words):
        return False
    if re.search(r"[.!?]\s", normalized):
        return False
    if "(" in normalized and ")" not in normalized:
        return False
    if any(normalized.startswith(prefix) for prefix in BAD_KEYWORD_PREFIXES):
        return False
    if len(normalized) > 36 and ("," in normalized or ";" in normalized):
        return False
    prose_markers = (" the ", " and ", " that ", " which ", " with ", " from ", " into ", " their ")
    if len(words) >= 6 and any(marker in f" {normalized} " for marker in prose_markers):
        return False
    return True


def derive_title_keywords(title: str, limit: int = 5) -> list[str]:
    tokens = re.findall(r"[a-z][a-z0-9\-]{2,}", (title or "").lower())
    cleaned: list[str] = []
    seen: set[str] = set()
    for token in tokens:
        if token in TITLE_KEYWORD_STOPWORDS or token in seen:
            continue
        if is_metadata_keyword(token):
            continue
        seen.add(token)
        cleaned.append(token)
        if len(cleaned) >= limit:
            break
    return cleaned


def looks_corrupted_keyword_source(cleaned: list[str]) -> bool:
    if len(cleaned) <= MAX_KEYWORD_LIST_SIZE:
        return False
    singles = sum(1 for kw in cleaned if " " not in kw)
    if singles and singles / len(cleaned) >= 0.35:
        return True
    if any(len(kw) > 60 for kw in cleaned):
        return True
    if sum(1 for kw in cleaned if not is_plausible_keyword(kw)) > 0:
        return True
    return False


def compact_corrupted_keywords(keywords: list[str], cleaned: list[str]) -> list[str]:
    if len(cleaned) <= MAX_KEYWORD_LIST_SIZE:
        return cleaned
    if len(keywords or []) <= CORRUPT_KEYWORD_SOURCE_COUNT and not looks_corrupted_keyword_source(cleaned):
        return cleaned[:MAX_KEYWORD_LIST_SIZE]
    if not looks_corrupted_keyword_source(cleaned):
        return cleaned[:MAX_KEYWORD_LIST_SIZE]

    compact = [
        kw
        for kw in cleaned
        if 2 <= len(kw.split()) <= 4 and len(kw) <= 36 and "(" not in kw and is_plausible_keyword(kw)
    ]
    if len(compact) >= 2:
        return compact[:MAX_KEYWORD_LIST_SIZE]
    return []


def sanitize_keyword_list(keywords: list[str]) -> list[str]:
    seen: set[str] = set()
    cleaned: list[str] = []
    for keyword in keywords or []:
        normalized = normalize_keyword_phrase(str(keyword))
        if not normalized or len(normalized) <= 2:
            continue
        if is_metadata_keyword(normalized):
            continue
        if not is_plausible_keyword(normalized):
            continue
        if normalized in seen:
            continue
        seen.add(normalized)
        cleaned.append(normalized)
    return compact_corrupted_keywords(list(keywords or []), cleaned)


def sanitize_submission_keywords(submission: dict) -> None:
    for field in ("author_keywords", "extracted_keywords", "keywords"):
        submission[field] = sanitize_keyword_list(list(submission.get(field) or []))


def reconcile_submission_keywords(submission: dict) -> None:
    """Drop scraped prose fragments and keep keywords in sync."""
    sanitize_submission_keywords(submission)
    keywords = content_keywords(submission)
    if len(keywords) > MAX_KEYWORD_LIST_SIZE:
        keywords = keywords[:MAX_KEYWORD_LIST_SIZE]
    if not keywords:
        keywords = derive_title_keywords(str(submission.get("title") or ""))
    if keywords:
        submission["keywords"] = keywords
        if submission.get("author_keywords"):
            submission["author_keywords"] = keywords
        return

    topic_area = normalize_keyword_phrase(str(submission.get("topic_area") or ""))
    track = normalize_keyword_phrase(str(submission.get("track") or ""))
    fallback = next(
        (label for label in (topic_area, track) if label and not is_metadata_keyword(label)),
        None,
    )
    if fallback:
        submission["keywords"] = [fallback]


def content_keywords(submission: dict) -> list[str]:
    for field in ("author_keywords", "extracted_keywords", "keywords"):
        values = sanitize_keyword_list(list(submission.get(field) or []))
        if values:
            return values
    return []


def submission_embedding_text(submission: dict) -> str:
    """Build weighted embedding text: abstract-heavy, metadata keywords excluded."""
    title = (submission.get("title") or "").strip()
    abstract = (submission.get("abstract") or "").strip()
    chunks: list[str] = []
    if title:
        chunks.extend([title] * TITLE_WEIGHT)
    if abstract:
        chunks.extend([abstract] * ABSTRACT_WEIGHT)
    keywords = content_keywords(submission)
    if keywords:
        keyword_blob = " ".join(keywords)
        chunks.extend([keyword_blob] * KEYWORD_WEIGHT)
    blob = ". ".join(chunks).strip()
    return blob or title or "empty"


def vectorizer_stop_words() -> list[str]:
    return sorted(ENGLISH_STOP_WORDS | METADATA_KEYWORD_TOKENS)


def repair_mojibake(text: str) -> str:
    if not text or not _MOJIBAKE_MARKERS.search(text):
        return text
    try:
        return text.encode("latin-1").decode("utf-8")
    except (UnicodeDecodeError, UnicodeEncodeError):
        return text


def repair_submission_text(submission: dict) -> None:
    for field in ("title", "authors", "abstract", "topic_area", "track"):
        if field in submission and submission[field]:
            submission[field] = normalize_field_text(str(submission[field]))

    for field in ("author_keywords", "extracted_keywords", "keywords", "secondary_topics", "assigned_topics"):
        values = submission.get(field)
        if not values:
            continue
        submission[field] = [repair_mojibake(str(value)) for value in values if value]

    if submission.get("primary_theme"):
        submission["primary_theme"] = repair_mojibake(str(submission["primary_theme"]))
