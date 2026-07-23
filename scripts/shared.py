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


_COUNTRY_NAMES = frozenset(
    {
        "united states",
        "united kingdom",
        "usa",
        "uk",
        "u.s.",
        "u.s.a.",
        "u.k.",
        "netherlands",
        "germany",
        "france",
        "canada",
        "china",
        "japan",
        "switzerland",
        "australia",
        "italy",
        "spain",
        "israel",
        "belgium",
        "india",
        "hungary",
        "ireland",
        "turkey",
        "sweden",
        "austria",
        "denmark",
        "norway",
        "brazil",
        "korea",
        "south korea",
        "taiwan",
        "singapore",
        "mexico",
        "poland",
        "portugal",
        "finland",
        "russia",
        "new zealand",
        "czech republic",
        "czech",
        "slovakia",
        "greece",
        "chile",
        "argentina",
        "colombia",
        "hong kong",
        "scotland",
        "wales",
        "england",
        "republic of korea",
        "luxembourg",
        "estonia",
        "latvia",
        "lithuania",
        "romania",
        "bulgaria",
        "croatia",
        "serbia",
        "slovenia",
        "iceland",
        "ukraine",
        "pakistan",
        "thailand",
        "vietnam",
        "indonesia",
        "malaysia",
        "philippines",
        "south africa",
        "egypt",
        "saudi arabia",
        "uae",
        "united arab emirates",
        "qatar",
        "iran",
        "iraq",
        "peru",
        "uruguay",
        "venezuela",
        "cuba",
        "jamaica",
        "cyprus",
        "malta",
        "liechtenstein",
        "monaco",
        "andorra",
        "san marino",
        "vatican",
        "vatican city",
        "north macedonia",
        "bosnia",
        "bosnia and herzegovina",
        "albania",
        "georgia",
        "armenia",
        "azerbaijan",
        "kazakhstan",
        "morocco",
        "tunisia",
        "algeria",
        "nigeria",
        "kenya",
        "ghana",
        "ethiopia",
        "tanzania",
        "uganda",
        "nepal",
        "sri lanka",
        "bangladesh",
        "myanmar",
        "cambodia",
        "laos",
        "mongolia",
        "uzbekistan",
        "belarus",
        "moldova",
        "montenegro",
        "kosovo",
        "palestine",
        "lebanon",
        "jordan",
        "syria",
        "yemen",
        "oman",
        "kuwait",
        "bahrain",
        "brunei",
        "fiji",
        "papua new guinea",
        "new caledonia",
        "puerto rico",
        "costa rica",
        "panama",
        "guatemala",
        "honduras",
        "el salvador",
        "nicaragua",
        "dominican republic",
        "ecuador",
        "bolivia",
        "paraguay",
        "suriname",
        "guyana",
        "trinidad and tobago",
        "barbados",
        "bahamas",
        "iceland",
        "greenland",
        "faroe islands",
    }
)

_AFFILIATION_HINTS = (
    "university",
    "université",
    "universiteit",
    "universidad",
    "universität",
    "institute",
    "institut",
    "college",
    "hospital",
    "department",
    "dept.",
    "school of",
    "laboratory",
    "lab ",
    "labs",
    "centre",
    "center",
    "ctr.",
    "neurosci",
    "republic of",
    "berkeley",
    "stanford",
    "harvard",
    "oxford",
    "cambridge",
    "deepmind",
    "google",
    "max planck",
    "cnrs",
    "inria",
    "eth zurich",
    "eth zürich",
    "epfl",
    "caltech",
    "princeton",
    "columbia",
    "carnegie",
    "weizmann",
    "technion",
    "imperial college",
    "university college",
    "vrije",
    "johns hopkins",
    "tuebingen",
    "tübingen",
    "international",
    "neurospin",
    "kuleuven",
    "birkbeck",
    "vanderbilt",
    "amherst",
)

# Campus / city shorthands and orgs that appear as whole trailing author tokens.
_PLACE_OR_ORG_TOKENS = frozenset(
    {
        "davis",
        "daivs",  # common typo in CCN listings
        "san diego",
        "riverside",
        "los angeles",
        "irvine",
        "santa barbara",
        "santa cruz",
        "berkeley",
        "new york",
        "california",
        "massachusetts",
        "amherst",
        "hyderabad",
        "bangalore",
        "bengaluru",
        "kuleuven",
        "birkbeck",
        "vanderbilt",
        "neurospin",
        "cerco",
        "atr international",
        "vicarious ai",
        "idibaps",
        "mta wigner rcp",
        "wigner rcp",
        "deepmind",
        "google deepmind",
        "google brain",
        "openai",
        "meta ai",
        "facebook ai",
        "microsoft research",
    }
)


def _is_country_token(part: str) -> bool:
    cleaned = part.lower().strip(" .")
    if cleaned.startswith("the "):
        cleaned = cleaned[4:].strip()
    return cleaned in _COUNTRY_NAMES


def _is_affiliation_token(part: str) -> bool:
    """True for countries, labs, universities, and short org acronyms (MIT, NYU, …)."""
    cleaned = part.strip()
    if not cleaned:
        return False
    if _is_country_token(cleaned):
        return True
    lowered = cleaned.lower().strip(" .")
    if lowered in _PLACE_OR_ORG_TOKENS:
        return True
    if any(hint in lowered for hint in _AFFILIATION_HINTS):
        return True
    # Short org acronyms commonly appended after author lists.
    if re.fullmatch(r"[A-Z]{2,6}", cleaned):
        return True
    if re.match(r"^UC\b", cleaned):
        return True
    return False


def normalize_author_names(authors: str) -> str:
    """Keep only person names: drop emails, labs, countries, and university footnotes.

    Example:
      "Ada Lovelace 1 ( ada@x.edu ), Alan Turing 2,3 ; 1 Uni A, 2 Uni B, 3 Lab C"
      → "Ada Lovelace, Alan Turing"
      "Jane Doe, MIT, United States" → "Jane Doe"
    """
    if not authors:
        return ""

    text = normalize_field_text(authors)
    lowered_full = text.lower()
    # Scrape noise sometimes lands in the author field.
    if lowered_full.startswith("presentation time"):
        return ""

    # Name block is before affiliation footnotes ("… ; 1 University…").
    text = text.split(";", 1)[0].strip()
    if not text:
        return ""

    # Drop emails and empty parentheticals (keep nicknames like "Lune (Pierre) Bellec").
    text = re.sub(r"\([^)]*@[^)]*\)", " ", text)
    text = re.sub(r"\(\s*\)", " ", text)
    text = re.sub(r"\s+", " ", text).strip()

    parts = [part.strip() for part in re.split(r"\s*,\s*", text) if part.strip()]
    # 2018–2022 listings often append ", Lab/Uni, Country" after the name list.
    while parts and _is_affiliation_token(parts[-1]):
        parts.pop()

    names: list[str] = []
    for part in parts:
        # Affiliation markers split as their own tokens: "Name 2,3" → "Name 2", "3".
        if re.fullmatch(r"\d+", part):
            continue
        # Glued affiliation start: "1Ctr. for Neurosci…" — stop; rest is not names.
        if re.match(r"^\d+[A-Za-z]", part):
            break
        if _is_affiliation_token(part):
            break
        # Trailing footnotes / superscripts: "Name 1", "Name 2,3", "Name*", "Name†".
        part = re.sub(r"(?:\s*[\d†‡*#]+(?:\s*,\s*[\d†‡*#]+)*)+\s*$", "", part)
        part = re.sub(r"\s+", " ", part).strip(" ,;")
        if not part or re.fullmatch(r"\d+", part):
            continue
        if _is_affiliation_token(part):
            break
        if part not in names:
            names.append(part)

    return ", ".join(names)


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


YEARS_TOPIC_AREA_KEYWORDS = frozenset({2025})
IGNORED_CONFERENCE_LABELS = frozenset({"view pdf", "view paper pdf", ""})


def conference_topic_label(submission: dict) -> str | None:
    for raw in (submission.get("topic_area"), submission.get("track")):
        label = re.sub(r"\s+", " ", str(raw or "").strip())
        if not label:
            continue
        if label.lower() in IGNORED_CONFERENCE_LABELS:
            continue
        return label.lower()
    return None


def conference_topic_keywords(submission: dict) -> list[str]:
    label = conference_topic_label(submission)
    return [label] if label else []


def reconcile_submission_keywords(submission: dict) -> None:
    """Drop scraped prose fragments and keep keywords in sync."""
    sanitize_submission_keywords(submission)

    author = sanitize_keyword_list(list(submission.get("author_keywords") or []))
    if author:
        keywords = author[:MAX_KEYWORD_LIST_SIZE]
        submission["author_keywords"] = keywords
        submission["keywords"] = keywords
        return

    if submission.get("year") in YEARS_TOPIC_AREA_KEYWORDS:
        topic_kw = conference_topic_keywords(submission)
        if topic_kw:
            submission["keywords"] = topic_kw
            submission["extracted_keywords"] = []
            return

    extracted = sanitize_keyword_list(list(submission.get("extracted_keywords") or []))
    if extracted:
        submission["keywords"] = extracted[:MAX_KEYWORD_LIST_SIZE]
        return

    topic_kw = conference_topic_keywords(submission)
    if topic_kw:
        submission["keywords"] = topic_kw
        return

    title_kw = derive_title_keywords(str(submission.get("title") or ""))
    if title_kw:
        submission["keywords"] = title_kw


def dashboard_keywords(submission: dict) -> list[str]:
    """Keywords for CSV/dashboard display; preserves conference topic-area labels."""
    reconciled = [str(kw).strip() for kw in (submission.get("keywords") or []) if str(kw).strip()]
    if reconciled:
        return reconciled[:MAX_KEYWORD_LIST_SIZE]

    author = sanitize_keyword_list(list(submission.get("author_keywords") or []))
    if author:
        return author[:MAX_KEYWORD_LIST_SIZE]

    topic_kw = conference_topic_keywords(submission)
    if topic_kw:
        return topic_kw

    extracted = sanitize_keyword_list(list(submission.get("extracted_keywords") or []))
    if extracted:
        return extracted[:MAX_KEYWORD_LIST_SIZE]

    return derive_title_keywords(str(submission.get("title") or ""))


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
    for field in ("title", "abstract", "topic_area", "track"):
        if field in submission and submission[field]:
            submission[field] = normalize_field_text(str(submission[field]))

    if submission.get("authors"):
        submission["authors"] = normalize_author_names(str(submission["authors"]))

    for field in ("author_keywords", "extracted_keywords", "keywords", "secondary_topics", "assigned_topics"):
        values = submission.get(field)
        if not values:
            continue
        submission[field] = [repair_mojibake(str(value)) for value in values if value]

    if submission.get("primary_theme"):
        submission["primary_theme"] = repair_mojibake(str(submission["primary_theme"]))
