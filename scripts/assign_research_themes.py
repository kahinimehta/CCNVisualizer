#!/usr/bin/env python3
"""Assign primary and secondary research themes to every submission."""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import normalize

from text_encoding import repair_submission_text
from topic_features import (
    ABSOLUTE_COSINE_FLOOR,
    BROAD_HINT_BOOST,
    MAX_ASSIGNED_TOPICS,
    RELEVANCE_RATIO,
    TOPIC_ANCHORS,
    is_metadata_keyword,
    normalize_keyword_phrase,
    sanitize_submission_keywords,
    submission_embedding_text,
    topic_prototype_text,
    vectorizer_stop_words,
)

ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "data" / "submissions.json"
DOCS_PATH = ROOT / "docs" / "data" / "submissions.json"
GOOGLE_TOPICS_PATH = ROOT / "data" / "google_topics.json"

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


def main() -> None:
    if not DATA_PATH.exists():
        raise SystemExit(f"Missing {DATA_PATH}")

    with DATA_PATH.open(encoding="utf-8") as fh:
        payload = json.load(fh)

    payload = apply_assignments(payload)
    write_payload(payload)

    try:
        from build_all_embeddings import build_payload, write_outputs as write_embedding_outputs

        embedding_payload = build_payload(payload["submissions"])
        write_embedding_outputs(embedding_payload)
    except Exception as exc:  # noqa: BLE001
        print(f"Warning: embeddings_all.json export skipped: {exc}")

    try:
        from build_abstracts_csv import build_from_payload

        build_from_payload(payload)
    except Exception as exc:  # noqa: BLE001
        print(f"Warning: abstracts.csv export skipped: {exc}")

    print(f"Assigned themes to {len(payload['submissions'])} submissions.")


if __name__ == "__main__":
    main()
