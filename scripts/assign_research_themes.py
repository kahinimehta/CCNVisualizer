#!/usr/bin/env python3
"""Assign primary and secondary research themes to every submission."""

from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "data" / "submissions.json"
DOCS_PATH = ROOT / "docs" / "data" / "submissions.json"
EMBEDDINGS_PATH = ROOT / "docs" / "data" / "embeddings_2026.json"

RESEARCH_THEMES = [
    "Cognition and Memory Systems",
    "Decision and Metacognition",
    "Naturalistic Brain Encoding",
    "Neural Population Dynamics",
    "Reinforcement Learning",
    "LLMs and Reasoning",
    "Language Neuroscience",
    "Neural Network Theory",
    "Computer Vision Models",
    "Visual Cortex Models",
]

THEME_STOPWORDS = {
    "the", "and", "for", "with", "from", "that", "this", "using", "based", "study", "results",
    "show", "human", "brain", "neural", "model", "models", "data", "analysis", "abstract",
}

TOKEN_RE = re.compile(r"[a-z][a-z0-9\-]{2,}")


def tokenize(text: str) -> list[str]:
    return [t for t in TOKEN_RE.findall((text or "").lower()) if t not in THEME_STOPWORDS]


def build_profiles(points: list[dict]) -> dict[str, Counter]:
    profiles = {theme: Counter() for theme in RESEARCH_THEMES}
    for point in points:
        theme = point.get("cluster_name")
        if theme not in profiles:
            continue
        weights = profiles[theme]
        for term in tokenize(point.get("primary_area", "")):
            weights[term] += 3
        for term in tokenize(point.get("secondary_area", "")):
            weights[term] += 2
        for term in tokenize(point.get("title", "")):
            weights[term] += 1
    return profiles


def score_submission(submission: dict, profiles: dict[str, Counter]) -> dict[str, float]:
    text = " ".join(
        [
            submission.get("title", ""),
            submission.get("abstract", ""),
            submission.get("topic_area", ""),
            " ".join(submission.get("keywords", [])),
        ]
    )
    tokens = tokenize(text)
    scores: dict[str, float] = {}
    for theme in RESEARCH_THEMES:
        score = sum(profiles[theme].get(term, 0) for term in tokens)
        for term in tokenize(theme):
            if term in tokens:
                score += 2
        scores[theme] = float(score)
    return scores


def assign_themes(
    submission: dict,
    profiles: dict[str, Counter],
    embedding_lookup: dict[str, str],
) -> tuple[str, list[str]]:
    sub_id = submission.get("id", "")
    poster = str(submission.get("poster_number") or "")
    if submission.get("year") == 2026:
        primary = embedding_lookup.get(sub_id) or embedding_lookup.get(f"2026-{poster}")
        if primary:
            scores = score_submission(submission, profiles)
            secondary = [
                theme
                for theme, score in sorted(scores.items(), key=lambda item: -item[1])
                if theme != primary and score > 0
            ][:3]
            return primary, secondary

    scores = score_submission(submission, profiles)
    ranked = sorted(scores.items(), key=lambda item: -item[1])
    primary, top_score = ranked[0]
    if top_score <= 0:
        primary = RESEARCH_THEMES[1]

    threshold = top_score * 0.35 if top_score > 0 else 0
    secondary = [theme for theme, score in ranked[1:] if theme != primary and score >= threshold][:3]
    return primary, secondary


def compute_theme_stats(submissions: list[dict]) -> dict:
    by_year: dict[str, Counter] = defaultdict(Counter)
    totals: Counter = Counter()
    secondary_totals: Counter = Counter()

    for sub in submissions:
        primary = sub.get("primary_theme")
        if not primary:
            continue
        year = str(sub["year"])
        by_year[year][primary] += 1
        totals[primary] += 1
        for topic in sub.get("secondary_topics", []):
            secondary_totals[topic] += 1

    return {
        "research_themes": RESEARCH_THEMES,
        "primary_by_year": {year: counter.most_common() for year, counter in by_year.items()},
        "primary_totals": totals.most_common(),
        "secondary_totals": secondary_totals.most_common(30),
    }


def apply_assignments(payload: dict, embeddings: dict) -> dict:
    points = embeddings.get("points", [])
    profiles = build_profiles(points)
    embedding_lookup: dict[str, str] = {}
    for point in points:
        embedding_lookup[point["id"]] = point["cluster_name"]
        if point.get("poster_number"):
            embedding_lookup[f"2026-{point['poster_number']}"] = point["cluster_name"]

    for submission in payload["submissions"]:
        primary, secondary = assign_themes(submission, profiles, embedding_lookup)
        submission["primary_theme"] = primary
        submission["secondary_topics"] = secondary

    payload.setdefault("stats", {})
    payload["stats"]["research_themes"] = compute_theme_stats(payload["submissions"])
    payload["metadata"]["research_themes_assigned_at"] = datetime.now(timezone.utc).isoformat()
    payload["metadata"]["research_theme_method"] = (
        "2026: embedding cluster label; other years: text match to 2026 cluster profiles"
    )
    return payload


def write_payload(payload: dict) -> None:
    for path in (DATA_PATH, DOCS_PATH):
        with path.open("w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2, ensure_ascii=False)
        print(f"Wrote {path}")


def main() -> None:
    if not DATA_PATH.exists():
        raise SystemExit(f"Missing {DATA_PATH}")
    if not EMBEDDINGS_PATH.exists():
        raise SystemExit(f"Missing {EMBEDDINGS_PATH}. Run build_cluster_viz.py first.")

    with DATA_PATH.open(encoding="utf-8") as fh:
        payload = json.load(fh)
    with EMBEDDINGS_PATH.open(encoding="utf-8") as fh:
        embeddings = json.load(fh)

    payload = apply_assignments(payload, embeddings)
    write_payload(payload)
    print(f"Assigned themes to {len(payload['submissions'])} submissions.")


if __name__ == "__main__":
    main()
