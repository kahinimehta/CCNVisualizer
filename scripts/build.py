#!/usr/bin/env python3
"""Step 2: Assign themes, compute UMAP coordinates, and export abstracts.csv.

Dependencies (install once):
  pip install numpy scikit-learn umap-learn
"""

from __future__ import annotations

import csv
import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS, TfidfVectorizer
from sklearn.preprocessing import normalize
from umap import UMAP

ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "data" / "submissions.json"
DOCS_PATH = ROOT / "docs" / "data" / "submissions.json"
GOOGLE_TOPICS_PATH = ROOT / "data" / "google_topics.json"
EMBEDDINGS_ALL_PATH = ROOT / "docs" / "data" / "embeddings_all.json"
EMBEDDING_OUT_PATHS = (ROOT / "docs" / "data" / "embeddings_all.json", ROOT / "data" / "embeddings_all.json")
CSV_OUTPUT_PATHS = (ROOT / "data" / "abstracts.csv", ROOT / "docs" / "data" / "abstracts.csv")
CSV_PATH_2026 = ROOT / "data" / "ccn-2026-pending-posters.csv"
LIST_DELIMITER = " | "

import re

from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS

# Conference area labels and method/format tags — not topical content.
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

# Topic prototype anchors — used for TF-IDF cosine scoring.
TOPIC_ANCHORS: dict[str, list[str]] = {
    "RL, motor control & planning": [
        "reinforcement learning",
        "reward",
        "motor control",
        "planning",
        "policy",
        "navigation",
        "action selection",
        "skill learning",
        "habit",
        "basal ganglia",
    ],
    "Naturalistic encoding/decoding": [
        "naturalistic",
        "encoding model",
        "decoding",
        "voxel-wise",
        "stimulus reconstruction",
        "movie",
        "narrative",
        "resting state",
        "natural scenes",
        "video",
    ],
    "Neural population geometry & dynamics": [
        "neural population",
        "population dynamics",
        "geometry",
        "manifold",
        "latent dynamics",
        "trajectory",
        "oscillation",
        "connectivity",
        "state space",
    ],
    "Decision-making and metacognition": [
        "decision making",
        "decision-making",
        "metacognition",
        "confidence",
        "choice",
        "judgment",
        "belief updating",
        "inference",
        "evidence accumulation",
    ],
    "Vision": [
        "visual",
        "vision",
        "retina",
        "v1",
        "v2",
        "retinotopic",
        "scene perception",
        "optic flow",
        "gaze",
        "saccade",
        "conscious vision",
        "visual awareness",
        "perceptual",
    ],
    "Language/auditory neuroscience": [
        "language",
        "auditory",
        "speech",
        "semantic",
        "syntax",
        "word",
        "listening",
        "voice",
        "reading",
        "phonology",
    ],
    "LLMs, reasoning, interpretability": [
        "large language model",
        "language model",
        "llm",
        "transformer",
        "gpt",
        "chatgpt",
        "prompt",
        "prompting",
        "in-context learning",
        "rlhf",
        "chain-of-thought",
        "chain of thought",
        "foundation model",
        "instruction tuning",
        "fine-tuning",
        "generative model",
        "pretrained",
    ],
    "Memory": [
        "memory",
        "hippocampus",
        "recall",
        "working memory",
        "episodic",
        "retrieval",
        "spatial memory",
        "consolidation",
    ],
    "Social cognition & theory of mind": [
        "social cognition",
        "theory of mind",
        "mentalizing",
        "social interaction",
        "empathy",
        "tom",
        "agent",
        "cooperation",
        "mental state",
    ],
    "Attention & cognitive control / executive function": [
        "attention",
        "executive function",
        "cognitive control",
        "task switching",
        "inhibition",
        "working memory control",
        "predictive processing",
        "conflict monitoring",
    ],
    "Clinical / computational psychiatry": [
        "clinical",
        "psychiatry",
        "depression",
        "schizophrenia",
        "patient",
        "disorder",
        "mental health",
        "autism",
        "anxiety",
        "bipolar",
    ],
    "Methods, theory & everything else": [
        "method",
        "benchmark",
        "framework",
        "simulation",
        "theory",
        "analysis toolkit",
        "interpretability",
        "explainability",
        "attention mechanism",
        "recurrent neural network",
        "rnn",
        "lstm",
        "symbolic reasoning",
        "generalization",
        "statistical",
    ],
}

TITLE_WEIGHT = 2
ABSTRACT_WEIGHT = 3
KEYWORD_WEIGHT = 1

RELEVANCE_RATIO = 0.5
ABSOLUTE_COSINE_FLOOR = 0.05
MAX_ASSIGNED_TOPICS = 5
BROAD_HINT_BOOST = 0.04


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


def sanitize_keyword_list(keywords: list[str]) -> list[str]:
    seen: set[str] = set()
    cleaned: list[str] = []
    for keyword in keywords or []:
        normalized = normalize_keyword_phrase(str(keyword))
        if not normalized or len(normalized) <= 2:
            continue
        if is_metadata_keyword(normalized):
            continue
        if normalized in seen:
            continue
        seen.add(normalized)
        cleaned.append(normalized)
    return cleaned


def sanitize_submission_keywords(submission: dict) -> None:
    for field in ("author_keywords", "extracted_keywords", "keywords"):
        submission[field] = sanitize_keyword_list(list(submission.get(field) or []))


def content_keywords(submission: dict) -> list[str]:
    for field in ("author_keywords", "extracted_keywords", "keywords"):
        values = sanitize_keyword_list(list(submission.get(field) or []))
        if values:
            return values
    return []


def is_weak_keyword_set(keywords: list[str]) -> bool:
    cleaned = sanitize_keyword_list(keywords)
    return not cleaned


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


def topic_prototype_text(theme: str) -> str:
    anchors = TOPIC_ANCHORS.get(theme, [])
    parts: list[str] = []
    for anchor in anchors:
        repeat = 3 if " " in anchor else 2
        parts.extend([anchor] * repeat)
    return " ".join(parts) or theme.lower()


def vectorizer_stop_words() -> list[str]:
    return sorted(ENGLISH_STOP_WORDS | METADATA_KEYWORD_TOKENS)

import re

# Typical signs of UTF-8 bytes interpreted as Latin-1 (e.g. Ã¶ → ö).
_MOJIBAKE_MARKERS = re.compile(r"[ÃÄÅÆÇÐÑØÞßàáâãäåæçèéêëìíîïðñòóôõö÷øùúûüýþÿ\u0080-\u009f]")


def repair_mojibake(text: str) -> str:
    """Fix UTF-8-as-Latin-1 mojibake when possible; otherwise return unchanged."""
    if not text or not _MOJIBAKE_MARKERS.search(text):
        return text
    try:
        return text.encode("latin-1").decode("utf-8")
    except (UnicodeDecodeError, UnicodeEncodeError):
        return text


def repair_submission_text(submission: dict) -> None:
    """Normalize text fields on a submission dict in place."""
    for field in ("title", "authors", "abstract", "topic_area", "track"):
        if field in submission and submission[field]:
            submission[field] = repair_mojibake(str(submission[field]))

    for field in ("author_keywords", "extracted_keywords", "keywords", "secondary_topics", "assigned_topics"):
        values = submission.get(field)
        if not values:
            continue
        submission[field] = [repair_mojibake(str(value)) for value in values if value]

    if submission.get("primary_theme"):
        submission["primary_theme"] = repair_mojibake(str(submission["primary_theme"]))





GOOGLE_FORM_TOPICS = list(TOPIC_ANCHORS.keys())

CCN_TOPIC_MAP: dict[str, str] = {
    "visual processing & computational vision": "Vision",
    "object recognition & visual attention": "Vision",
    "reward, value & social decision making": "Decision-making and metacognition",
    "memory, spatial cognition & skill learning": "Memory",
    "predictive processing & cognitive control": "Attention & cognitive control / executive function",
    "language & communication": "Language/auditory neuroscience",
    "brain networks & neural dynamics": "Neural population geometry & dynamics",
    "methods & computational tools": "Methods, theory & everything else",
    "artificial intelligence": "LLMs, reasoning, interpretability",
    "neuroscience": "Neural population geometry & dynamics",
    "psychology": "Decision-making and metacognition",
    "linguistics": "Language/auditory neuroscience",
    "philosophy": "Methods, theory & everything else",
    "engineering": "Methods, theory & everything else",
    "mathematics": "Methods, theory & everything else",
    "theoretical / computational neuroscience": "Methods, theory & everything else",
    "experimental neuroscience (systems / cognitive)": "Neural population geometry & dynamics",
    "artificial intelligence / machine learning": "LLMs, reasoning, interpretability",
}

BROAD_TOPIC_HINTS: dict[str, list[str]] = {
    "cognitive science": [
        "Decision-making and metacognition",
        "Naturalistic encoding/decoding",
        "Neural population geometry & dynamics",
        "Methods, theory & everything else",
    ],
    "psychological / behavioral research": [
        "Decision-making and metacognition",
        "Attention & cognitive control / executive function",
    ],
    "computational cognitive science / cognitive modeling": [
        "Decision-making and metacognition",
        "Methods, theory & everything else",
    ],
}

IGNORED_TOPIC_LABELS = {"view pdf", "view paper pdf", ""}
METHODS_FALLBACK = "Methods, theory & everything else"


class ThemeScorer:
    """TF-IDF cosine similarity between submissions and topic prototype anchors."""

    def __init__(self, submissions: list[dict], topics: list[str]) -> None:
        self.topics = topics
        self.submission_texts = [submission_embedding_text(submission) for submission in submissions]
        prototype_texts = [topic_prototype_text(topic) for topic in topics]
        corpus = self.submission_texts + prototype_texts
        self.vectorizer = TfidfVectorizer(
            max_features=10000,
            stop_words=vectorizer_stop_words(),
            min_df=2,
            max_df=0.95,
            ngram_range=(1, 2),
            sublinear_tf=True,
        )
        matrix = self.vectorizer.fit_transform(corpus)
        submission_count = len(submissions)
        self.submission_vectors = normalize(matrix[:submission_count], norm="l2", axis=1)
        self.prototype_vectors = normalize(matrix[submission_count:], norm="l2", axis=1)

    def score_index(self, index: int) -> dict[str, float]:
        vector = self.submission_vectors[index]
        similarities = (vector @ self.prototype_vectors.T).toarray().ravel()
        return {theme: float(similarities[idx]) for idx, theme in enumerate(self.topics)}


def load_google_config() -> dict:
    if GOOGLE_TOPICS_PATH.exists():
        with GOOGLE_TOPICS_PATH.open(encoding="utf-8") as fh:
            return json.load(fh)
    return {"enabled": True, "topics": GOOGLE_FORM_TOPICS}


def active_topics(config: dict) -> list[str]:
    if config.get("enabled") and config.get("topics"):
        return list(config["topics"])
    return GOOGLE_FORM_TOPICS


def normalize_topic_label(label: str) -> str:
    return normalize_keyword_phrase(label)


def official_theme_from_label(label: str, topics: list[str]) -> str | None:
    normalized = normalize_topic_label(label)
    if normalized in IGNORED_TOPIC_LABELS or is_metadata_keyword(normalized):
        return None
    if normalized in BROAD_TOPIC_HINTS:
        return None
    mapped = CCN_TOPIC_MAP.get(normalized)
    if mapped and mapped in topics:
        return mapped
    return None


def apply_label_hints(label: str, scores: dict[str, float], topics: list[str]) -> None:
    normalized = normalize_topic_label(label)
    for theme in BROAD_TOPIC_HINTS.get(normalized, []):
        if theme in topics:
            scores[theme] = scores.get(theme, 0.0) + BROAD_HINT_BOOST


def conference_label(submission: dict) -> str:
    for field in ("topic_area", "track"):
        normalized = normalize_topic_label(submission.get(field, ""))
        if normalized and normalized not in IGNORED_TOPIC_LABELS:
            return normalized
    return ""


def assign_themes(
    submission: dict,
    topics: list[str],
    scorer: ThemeScorer,
    submission_index: int,
) -> tuple[str, list[str], list[str]]:
    official = official_theme_from_label(conference_label(submission), topics)
    scores = scorer.score_index(submission_index)
    apply_label_hints(conference_label(submission), scores, topics)

    ranked = sorted(scores.items(), key=lambda item: (-item[1], item[0]))
    max_score = ranked[0][1] if ranked else 0.0

    if official:
        primary = official
    elif max_score >= ABSOLUTE_COSINE_FLOOR:
        primary = ranked[0][0]
    else:
        primary = METHODS_FALLBACK

    threshold = max(max_score * RELEVANCE_RATIO, ABSOLUTE_COSINE_FLOOR)
    assigned: list[str] = []
    for theme, score in ranked:
        if score < threshold:
            continue
        if theme not in assigned:
            assigned.append(theme)
        if len(assigned) >= MAX_ASSIGNED_TOPICS:
            break

    if primary not in assigned:
        assigned.insert(0, primary)
    else:
        assigned = [primary, *[theme for theme in assigned if theme != primary]]

    secondary = assigned[1:]
    return primary, secondary, assigned


def compute_theme_stats(submissions: list[dict], topics: list[str]) -> dict:
    by_year: dict[str, Counter] = defaultdict(Counter)
    totals: Counter = Counter()
    secondary_totals: Counter = Counter()

    for sub in submissions:
        assigned = sub.get("assigned_topics") or []
        if not assigned:
            continue
        primary = assigned[0]
        year = str(sub["year"])
        by_year[year][primary] += 1
        totals[primary] += 1
        for topic in assigned[1:]:
            if topic in topics:
                secondary_totals[topic] += 1

    return {
        "research_themes": topics,
        "primary_by_year": {year: counter.most_common() for year, counter in by_year.items()},
        "primary_totals": totals.most_common(),
        "secondary_totals": secondary_totals.most_common(30),
    }


def apply_assignments(payload: dict) -> dict:
    config = load_google_config()
    topics = active_topics(config)

    submissions = payload["submissions"]
    for submission in submissions:
        repair_submission_text(submission)
        sanitize_submission_keywords(submission)

    scorer = ThemeScorer(submissions, topics)

    for index, submission in enumerate(submissions):
        primary, secondary, assigned_topics = assign_themes(
            submission,
            topics,
            scorer,
            index,
        )
        submission["primary_theme"] = primary
        submission["secondary_topics"] = secondary
        submission["assigned_topics"] = assigned_topics
        submission.pop("cluster_track", None)

    payload.setdefault("stats", {})
    payload["stats"]["research_themes"] = compute_theme_stats(submissions, topics)
    payload["metadata"]["research_themes_assigned_at"] = datetime.now(timezone.utc).isoformat()
    payload["metadata"]["research_theme_method"] = (
        "Google Form Q1 topics; weighted TF-IDF cosine similarity to topic prototype anchors "
        "(title x2, abstract x3, cleaned keywords x1; metadata keywords excluded); "
        f"multi-label threshold max_score * {RELEVANCE_RATIO} (floor {ABSOLUTE_COSINE_FLOOR}), "
        f"cap {MAX_ASSIGNED_TOPICS}; official CCN labels override primary when specific"
    )
    payload["metadata"]["keyword_source"] = (
        "author_keywords prefer poster HTML, proceedings/authored PDFs (2017-2025), or 2026 CSV; "
        "extracted_keywords only when no author keywords are available; citation fragments and "
        "metadata area labels stripped before scoring"
    )
    keyword_years = sorted({sub["year"] for sub in submissions if sub.get("keywords")})
    payload["metadata"]["keyword_years"] = keyword_years
    payload["metadata"]["google_topics_source"] = config.get("source")
    return payload


def write_payload(payload: dict) -> None:
    for path in (DATA_PATH, DOCS_PATH):
        with path.open("w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2, ensure_ascii=False)
        print(f"Wrote {path}")





from umap import UMAP



UMAP_PARAMS = {
    "n_components": 2,
    "n_neighbors": 15,
    "min_dist": 0.12,
    "metric": "cosine",
    "random_state": 42,
}


def build_payload(submissions: list[dict] | None = None) -> dict:
    if submissions is None:
        if not DATA_PATH.exists():
            raise SystemExit(f"Missing {DATA_PATH}")
        with DATA_PATH.open(encoding="utf-8") as fh:
            submissions = json.load(fh).get("submissions", [])

    if not submissions:
        raise SystemExit("No submissions found.")

    for submission in submissions:
        repair_submission_text(submission)

    texts = [submission_embedding_text(sub) for sub in submissions]
    vectorizer = TfidfVectorizer(
        max_features=8000,
        stop_words=vectorizer_stop_words(),
        min_df=2,
        max_df=0.95,
        ngram_range=(1, 2),
        sublinear_tf=True,
    )
    matrix = vectorizer.fit_transform(texts)
    coords = UMAP(**UMAP_PARAMS).fit_transform(matrix)

    points = []
    for idx, submission in enumerate(submissions):
        points.append(
            {
                "id": submission.get("id", ""),
                "x": float(coords[idx, 0]),
                "y": float(coords[idx, 1]),
                "year": submission.get("year"),
                "title": (submission.get("title") or "").strip(),
                "poster_number": str(submission.get("poster_number") or ""),
            }
        )

    years = sorted({sub.get("year") for sub in submissions if sub.get("year") is not None})
    return {
        "metadata": {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "count": len(points),
            "years": years,
            "method": (
                "Weighted TF-IDF (title x2, abstract x3, cleaned keywords x1; metadata keywords "
                "excluded) + UMAP 2D, cosine metric"
            ),
        },
        "points": points,
    }


def write_embedding_outputs(payload: dict) -> None:
    for path in EMBEDDING_OUT_PATHS:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2, ensure_ascii=False)
        print(f"Wrote {path}")







LIST_DELIMITER = " | "

# Core columns (documented in DASHBOARD.md) plus precomputed fields the UI needs.
CSV_FIELDS = [
    "id",
    "year",
    "title",
    "author",
    "keywords",
    "assigned_topics",
    "authors",
    "abstract",
    "umap_x",
    "umap_y",
    "source_url",
    "poster_number",
]

AFFILIATION_HINTS = (
    "university",
    "college",
    "institute",
    "institut",
    "laboratory",
    "laboratoire",
    "school",
    "center",
    "centre",
    "hospital",
    "department",
    "faculty",
    "academy",
    "google",
    "microsoft",
    "meta",
    "united states",
    "united kingdom",
    "netherlands",
    "germany",
    "france",
    "canada",
    "australia",
    "switzerland",
    "sweden",
    "israel",
    "japan",
    "china",
    "india",
    "singapore",
)


def first_author(authors: str) -> str:
    if not authors:
        return ""
    block = authors.split(";")[0].strip()
    if not block:
        return ""
    parts = [part.strip() for part in block.split(",") if part.strip()]
    if not parts:
        return ""
    if len(parts) == 1:
        return parts[0]
    tail = parts[1].lower()
    if any(hint in tail for hint in AFFILIATION_HINTS) or re.search(
        r"\b(states|kingdom|republic)\b", tail
    ):
        return parts[0]
    return parts[0]


def join_list(values: list[str]) -> str:
    return LIST_DELIMITER.join(value for value in values if value)


def keyword_fields(submission: dict) -> tuple[list[str], list[str]]:
    author = list(submission.get("author_keywords") or [])
    extracted = list(submission.get("extracted_keywords") or [])
    if author or extracted:
        return author, extracted

    keywords = list(submission.get("keywords") or [])
    year = submission.get("year")
    if year in (2018, 2019):
        return [], keywords
    return keywords, []


def dashboard_keywords(submission: dict) -> list[str]:
    """Keywords column: cleaned content keywords (metadata/citation fragments removed)."""
    return content_keywords(submission) or sanitize_keyword_list(list(submission.get("keywords") or []))


def assigned_topics(submission: dict) -> list[str]:
    """Topics in order of importance (primary first, then secondaries)."""
    assigned = list(submission.get("assigned_topics") or [])
    if assigned:
        return assigned
    topics: list[str] = []
    primary = submission.get("primary_theme", "")
    if primary:
        topics.append(primary)
    for topic in submission.get("secondary_topics") or []:
        if topic and topic not in topics:
            topics.append(topic)
    return topics


def embedding_index(embeddings: dict) -> dict[str, dict]:
    lookup: dict[str, dict] = {}
    for point in embeddings.get("points", []):
        lookup[point["id"]] = point
        if point.get("poster_number"):
            lookup[f"2026-{point['poster_number']}"] = point
    return lookup


def load_embeddings(submissions: list[dict]) -> dict:
    if EMBEDDINGS_ALL_PATH.exists():
        with EMBEDDINGS_ALL_PATH.open(encoding="utf-8") as fh:
            return json.load(fh)


    print("embeddings_all.json missing — computing UMAP coordinates…")
    return build_payload(submissions)


def build_rows(payload: dict, embeddings: dict | None = None) -> list[dict[str, str]]:
    submissions = payload.get("submissions", [])
    embedding_lookup = embedding_index(embeddings or load_embeddings(submissions))
    rows: list[dict[str, str]] = []

    for submission in sorted(
        submissions,
        key=lambda item: (item.get("year", 0), str(item.get("title", "")).lower()),
    ):
        sub_id = submission.get("id", "")
        poster = str(submission.get("poster_number") or "")
        point = embedding_lookup.get(sub_id) or embedding_lookup.get(f"2026-{poster}")
        authors = submission.get("authors", "")

        rows.append(
            {
                "id": sub_id,
                "year": str(submission.get("year", "")),
                "title": repair_mojibake(submission.get("title", "")),
                "author": repair_mojibake(first_author(authors)),
                "keywords": join_list(dashboard_keywords(submission)),
                "assigned_topics": join_list(assigned_topics(submission)),
                "authors": repair_mojibake(authors),
                "abstract": repair_mojibake(submission.get("abstract", "")),
                "umap_x": "" if not point else str(point.get("x", "")),
                "umap_y": "" if not point else str(point.get("y", "")),
                "source_url": submission.get("source_url", ""),
                "poster_number": poster,
            }
        )
    return rows


def write_csv(rows: list[dict[str, str]]) -> None:
    for path in CSV_OUTPUT_PATHS:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8-sig", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=CSV_FIELDS)
            writer.writeheader()
            writer.writerows(rows)
        print(f"Wrote {path}")


def build_from_payload(payload: dict, embeddings: dict | None = None) -> list[dict[str, str]]:
    submissions = payload.get("submissions", [])
    coords = embeddings or load_embeddings(submissions)
    rows = build_rows(payload, coords)
    write_csv(rows)
    return rows





def merge_2026_csv(payload: dict) -> dict:
    if not CSV_PATH_2026.exists():
        print(f"No 2026 CSV at {CSV_PATH_2026}; skipping merge.")
        return payload
    YEAR = 2026
    def normalize_topic_area(primary: str, secondary: str = "") -> str:
        parts = [p.strip() for p in re.split(r"[+;,]", f"{primary},{secondary}") if p.strip()]
        return parts[0].lower() if parts else ""
    def author_keywords_from_csv(row: dict[str, str]) -> list[str]:
        keywords: list[str] = []
        for field in ("primary_area", "secondary_area"):
            raw = (row.get(field) or "").strip()
            if not raw:
                continue
            for part in re.split(r"[+;,]", raw):
                kw = part.strip()
                if kw:
                    keywords.append(kw)
        return keywords
    with CSV_PATH_2026.open(encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    new_rows = []
    for row in rows:
        if not (row.get("title") or "").strip():
            continue
        poster = (row.get("or_number") or "").strip()
        title = (row.get("title") or "").strip()
        abstract = (row.get("abstract") or "").strip()
        primary = (row.get("primary_area") or "").strip()
        secondary = (row.get("secondary_area") or "").strip()
        topic_area = normalize_topic_area(primary, secondary)
        author_kw = sanitize_keyword_list(author_keywords_from_csv(row))
        keywords = author_kw or ([topic_area] if topic_area else [])
        new_rows.append({"id": f"2026-{poster or title[:24]}", "year": YEAR, "title": title, "authors": "", "abstract": abstract, "author_keywords": author_kw, "extracted_keywords": [], "keywords": keywords, "topic_area": topic_area, "track": (row.get("track") or "").strip(), "poster_number": poster, "source_url": "https://2026.ccneuro.org/", "submission_type": "poster"})
    kept = [s for s in payload.get("submissions", []) if s.get("year") != YEAR]
    payload["submissions"] = kept + new_rows
    payload.setdefault("metadata", {})
    payload["metadata"]["total_count"] = len(payload["submissions"])
    payload["metadata"]["years"] = sorted({s["year"] for s in payload["submissions"]})
    payload["metadata"]["csv_2026"] = {"path": str(CSV_PATH_2026.relative_to(ROOT)), "merged_at": datetime.now(timezone.utc).isoformat(), "count": len(new_rows)}
    print(f"Merged {len(new_rows)} rows from {CSV_PATH_2026.name}")
    return payload

def run_build(payload: dict | None = None, *, merge_2026: bool = False) -> dict:
    if payload is None:
        if not DATA_PATH.exists():
            raise SystemExit(f"Missing {DATA_PATH}")
        with DATA_PATH.open(encoding="utf-8") as fh:
            payload = json.load(fh)
    if merge_2026:
        payload = merge_2026_csv(payload)
    payload = apply_assignments(payload)
    write_payload(payload)
    embedding_payload = build_payload(payload["submissions"])
    write_embedding_outputs(embedding_payload)
    build_from_payload(payload, embedding_payload)
    print(f"Built dashboard artifacts for {len(payload['submissions'])} submissions.")
    return payload

def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="Build themes, UMAP map, and abstracts.csv")
    parser.add_argument("--merge-2026", action="store_true")
    args = parser.parse_args()
    run_build(merge_2026=args.merge_2026)

if __name__ == "__main__":
    main()
