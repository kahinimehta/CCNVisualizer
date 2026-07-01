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
EMBEDDINGS_ALL_PATH = ROOT / "docs" / "data" / "embeddings_all.json"
EMBEDDINGS_2026_PATH = ROOT / "docs" / "data" / "embeddings_2026.json"
GOOGLE_TOPICS_PATH = ROOT / "data" / "google_topics.json"

GOOGLE_FORM_TOPICS = [
    "RL, motor control & planning",
    "Naturalistic encoding/decoding",
    "Neural population geometry & dynamics",
    "Decision-making and metacognition",
    "Vision",
    "Language/auditory neuroscience",
    "LLMs, reasoning, interpretability",
    "Memory",
    "Social cognition & theory of mind",
    "Attention & cognitive control / executive function",
    "Clinical / computational psychiatry",
    "Methods, theory & everything else",
]

EMBEDDING_TO_GOOGLE = {
    "Reinforcement Learning": "RL, motor control & planning",
    "Naturalistic Brain Encoding": "Naturalistic encoding/decoding",
    "Neural Population Dynamics": "Neural population geometry & dynamics",
    "Decision and Metacognition": "Decision-making and metacognition",
    "Visual Cortex Models": "Vision",
    "Computer Vision Models": "Vision",
    "Language Neuroscience": "Language/auditory neuroscience",
    "LLMs and Reasoning": "LLMs, reasoning, interpretability",
    "Cognition and Memory Systems": "Memory",
    "Neural Network Theory": "Methods, theory & everything else",
}

# Official CCN topic labels → Google Form meetup themes.
# Keys are lowercased; values must match GOOGLE_FORM_TOPICS exactly.
CCN_TOPIC_MAP: dict[str, str] = {
    # 2025 MeetingTrakr taxonomy
    "visual processing & computational vision": "Vision",
    "object recognition & visual attention": "Vision",
    "reward, value & social decision making": "Decision-making and metacognition",
    "memory, spatial cognition & skill learning": "Memory",
    "predictive processing & cognitive control": "Attention & cognitive control / executive function",
    "language & communication": "Language/auditory neuroscience",
    "brain networks & neural dynamics": "Neural population geometry & dynamics",
    "methods & computational tools": "Methods, theory & everything else",
    # 2022–2023 legacy track / topic column — handled via BROAD_TOPIC_HINTS
    # 2017 proceedings PDF topic labels
    "artificial intelligence": "LLMs, reasoning, interpretability",
    "neuroscience": "Neural population geometry & dynamics",
    "psychology": "Decision-making and metacognition",
    "linguistics": "Language/auditory neuroscience",
    "philosophy": "Methods, theory & everything else",
    "engineering": "Methods, theory & everything else",
    "mathematics": "Methods, theory & everything else",
    # 2026 pending-poster CSV primary_area (stored lowercased in topic_area)
    "computational cognitive science / cognitive modeling": "Decision-making and metacognition",
    "theoretical / computational neuroscience": "Methods, theory & everything else",
    "experimental neuroscience (systems / cognitive)": "Neural population geometry & dynamics",
    "artificial intelligence / machine learning": "LLMs, reasoning, interpretability",
    "psychological / behavioral research": "Decision-making and metacognition",
}

# Coarse archive labels: nudge several themes instead of forcing one primary.
BROAD_TOPIC_HINTS: dict[str, list[str]] = {
    "cognitive science": [
        "Decision-making and metacognition",
        "Naturalistic encoding/decoding",
        "Neural population geometry & dynamics",
        "Methods, theory & everything else",
    ],
}

BROAD_HINT_BOOST = 3.0
PHRASE_MATCH_BOOST = 12.0
KEYWORD_TOKEN_BOOST = 8.0

TOPIC_KEYWORDS: dict[str, list[str]] = {
    "RL, motor control & planning": [
        "reinforcement", "reward", "motor", "planning", "policy", "navigation", "action", "skill",
    ],
    "Naturalistic encoding/decoding": [
        "naturalistic", "encoding", "decoding", "fmri", "eeg", "movie", "stimulus", "resting",
        "neuroimaging", "meg", "ecog", "bold", "narrative", "video",
    ],
    "Neural population geometry & dynamics": [
        "population", "dynamics", "geometry", "manifold", "latent", "trajectory", "oscillation",
        "network", "connectivity",
    ],
    "Decision-making and metacognition": [
        "decision", "metacognition", "confidence", "choice", "judgment", "belief", "inference",
        "cognitive", "behavioral", "psychology",
    ],
    "Vision": [
        "visual", "vision", "retina", "v1", "v2", "retinotopic", "scene", "optic", "gaze", "saccade",
    ],
    "Language/auditory neuroscience": [
        "language", "auditory", "speech", "semantic", "syntax", "word", "listening", "voice", "reading",
    ],
    "LLMs, reasoning, interpretability": [
        "llm", "language model", "reasoning", "interpretability", "transformer", "gpt", "prompt",
        "foundation model",
    ],
    "Memory": ["memory", "hippocampus", "recall", "working memory", "episodic", "retrieval", "spatial"],
    "Social cognition & theory of mind": [
        "social", "theory mind", "mentalizing", "interaction", "communication", "empathy", "tom",
    ],
    "Attention & cognitive control / executive function": [
        "attention", "executive", "cognitive control", "switching", "inhibition", "predictive",
    ],
    "Clinical / computational psychiatry": [
        "clinical", "psychiatry", "depression", "schizophrenia", "patient", "disorder", "mental health",
    ],
    "Methods, theory & everything else": [
        "theory", "method", "benchmark", "framework", "analysis", "toolkit", "simulation",
    ],
}

IGNORED_TOPIC_LABELS = {"view pdf", "view paper pdf", ""}
GENERIC_KEYWORD_LABELS = {"cognitive science", "cognitive"}

CLUSTER_BOOST_FACTOR = 0.35

THEME_STOPWORDS = {
    "the", "and", "for", "with", "from", "that", "this", "using", "based", "study", "results",
    "show", "human", "brain", "neural", "model", "models", "data", "analysis", "abstract",
    "computational", "control", "learning", "perception", "image", "cortex",
}

TOKEN_RE = re.compile(r"[a-z][a-z0-9\-]{2,}")


def load_google_config() -> dict:
    if GOOGLE_TOPICS_PATH.exists():
        with GOOGLE_TOPICS_PATH.open(encoding="utf-8") as fh:
            return json.load(fh)
    return {"enabled": True, "topics": GOOGLE_FORM_TOPICS}


def active_topics(config: dict) -> list[str]:
    if config.get("enabled") and config.get("topics"):
        return list(config["topics"])
    return GOOGLE_FORM_TOPICS


def embedding_map(config: dict) -> dict[str, str]:
    return config.get("embedding_cluster_map") or EMBEDDING_TO_GOOGLE


def tokenize(text: str) -> list[str]:
    return [t for t in TOKEN_RE.findall((text or "").lower()) if t not in THEME_STOPWORDS]


def normalize_topic_label(label: str) -> str:
    return (label or "").strip().lower()


def official_theme_from_label(label: str, topics: list[str]) -> str | None:
    normalized = normalize_topic_label(label)
    if normalized in IGNORED_TOPIC_LABELS:
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
            scores[theme] = scores.get(theme, 0) + BROAD_HINT_BOOST


def conference_label(submission: dict) -> str:
    for field in ("topic_area", "track"):
        normalized = normalize_topic_label(submission.get(field, ""))
        if normalized and normalized not in IGNORED_TOPIC_LABELS:
            return normalized
    return ""


def is_weak_keyword_set(keywords: list[str]) -> bool:
    if not keywords:
        return True
    normalized = {kw.lower().strip() for kw in keywords if kw}
    if not normalized:
        return True
    return normalized.issubset(GENERIC_KEYWORD_LABELS)


def scoring_blob(submission: dict) -> str:
    parts = [submission.get("title", ""), submission.get("abstract", "")]
    keywords = list(submission.get("keywords") or [])
    if not is_weak_keyword_set(keywords):
        parts.append(" ".join(keywords))
    parts.extend(submission.get("author_keywords") or [])
    parts.extend(submission.get("extracted_keywords") or [])
    return " ".join(part for part in parts if part)


def author_keyword_text(submission: dict) -> str:
    return scoring_blob(submission)


def score_submission(submission: dict, topics: list[str]) -> dict[str, float]:
    text_lower = scoring_blob(submission).lower()
    tokens = tokenize(scoring_blob(submission))
    token_set = set(tokens)
    scores: dict[str, float] = {}
    for theme in topics:
        score = 0.0
        for phrase in TOPIC_KEYWORDS.get(theme, []):
            if " " in phrase:
                if phrase in text_lower:
                    score += PHRASE_MATCH_BOOST
            elif phrase in token_set:
                score += KEYWORD_TOKEN_BOOST
        for term in tokenize(theme):
            if term in token_set:
                score += 2
        scores[theme] = float(score)
    return scores


def assign_themes(
    submission: dict,
    topics: list[str],
    embedding_lookup: dict[str, str],
    cluster_map: dict[str, str],
) -> tuple[str, list[str], list[str]]:
    sub_id = submission.get("id", "")
    poster = str(submission.get("poster_number") or "")
    cluster = embedding_lookup.get(sub_id) or embedding_lookup.get(f"2026-{poster}")
    cluster_theme = cluster_map.get(cluster) if cluster else None

    official = official_theme_from_label(conference_label(submission), topics)

    scores = score_submission(submission, topics)
    apply_label_hints(conference_label(submission), scores, topics)
    if cluster_theme:
        boost = max(max(scores.values(), default=0) * CLUSTER_BOOST_FACTOR, 4.0)
        scores[cluster_theme] = scores.get(cluster_theme, 0) + boost

    ranked = sorted(scores.items(), key=lambda item: -item[1])

    if official:
        primary = official
    else:
        primary, top_score = ranked[0]
        if top_score <= 0:
            primary = "Methods, theory & everything else"

    threshold = (scores.get(primary, 0) or ranked[0][1]) * 0.35
    secondary: list[str] = []
    if cluster_theme and cluster_theme != primary and cluster_theme not in secondary:
        secondary.append(cluster_theme)
    for theme, score in ranked:
        if theme == primary or score < threshold:
            continue
        if theme not in secondary:
            secondary.append(theme)
        if len(secondary) >= 3:
            break
    google_secondaries = [theme for theme in secondary if theme in topics]
    assigned_topics = list(dict.fromkeys([primary, *google_secondaries]))
    return primary, secondary[:3], assigned_topics


def compute_theme_stats(submissions: list[dict], topics: list[str]) -> dict:
    by_year: dict[str, Counter] = defaultdict(Counter)
    totals: Counter = Counter()
    secondary_totals: Counter = Counter()

    for sub in submissions:
        for topic in sub.get("assigned_topics") or []:
            if not topic:
                continue
            year = str(sub["year"])
            by_year[year][topic] += 1
            totals[topic] += 1
        for topic in sub.get("secondary_topics") or []:
            if topic in topics:
                secondary_totals[topic] += 1

    return {
        "research_themes": topics,
        "primary_by_year": {year: counter.most_common() for year, counter in by_year.items()},
        "primary_totals": totals.most_common(),
        "secondary_totals": secondary_totals.most_common(30),
    }


def apply_assignments(payload: dict, embeddings: dict) -> dict:
    config = load_google_config()
    topics = active_topics(config)
    cluster_map = embedding_map(config)

    points = embeddings.get("points", [])
    embedding_lookup: dict[str, str] = {}
    for point in points:
        cluster_name = point.get("cluster_name")
        if not cluster_name:
            continue
        mapped = cluster_map.get(cluster_name, cluster_name)
        embedding_lookup[point["id"]] = cluster_name
        if point.get("poster_number"):
            embedding_lookup[f"2026-{point['poster_number']}"] = cluster_name

    for submission in payload["submissions"]:
        primary, secondary, assigned_topics = assign_themes(
            submission, topics, embedding_lookup, cluster_map
        )
        submission["primary_theme"] = primary
        submission["secondary_topics"] = secondary
        submission["assigned_topics"] = assigned_topics
        submission.pop("cluster_track", None)

    payload.setdefault("stats", {})
    payload["stats"]["research_themes"] = compute_theme_stats(payload["submissions"], topics)
    payload["metadata"]["research_themes_assigned_at"] = datetime.now(timezone.utc).isoformat()
    payload["metadata"]["research_theme_method"] = (
        "Google Form Q1 topics; official CCN topic labels mapped first; "
        "submission keywords matched to themes (author keywords, else topic/track, "
        "else archive text fallback for 2018-2019); optional soft boost from "
        "2026 embedding cluster mapped to the same Google topic set"
    )
    payload["metadata"]["keyword_source"] = (
        "author_keywords prefer poster HTML, proceedings/authored PDFs (2017-2025), or 2026 CSV; "
        "extracted_keywords only when no author keywords are available"
    )
    keyword_years = sorted({sub["year"] for sub in payload["submissions"] if sub.get("keywords")})
    payload["metadata"]["keyword_years"] = keyword_years
    payload["metadata"]["google_topics_source"] = config.get("source")
    return payload


def write_payload(payload: dict) -> None:
    for path in (DATA_PATH, DOCS_PATH):
        with path.open("w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2, ensure_ascii=False)
        print(f"Wrote {path}")


def load_embeddings() -> dict | None:
    for path in (EMBEDDINGS_2026_PATH,):
        if path.exists():
            with path.open(encoding="utf-8") as fh:
                return json.load(fh)
    return None


def main() -> None:
    if not DATA_PATH.exists():
        raise SystemExit(f"Missing {DATA_PATH}")

    with DATA_PATH.open(encoding="utf-8") as fh:
        payload = json.load(fh)
    embeddings = load_embeddings()
    if embeddings:
        payload = apply_assignments(payload, embeddings)
    else:
        print("Warning: no 2026 embedding clusters found; assigning themes from keywords only.")

    write_payload(payload)

    try:
        from build_abstracts_csv import build_from_payload

        build_from_payload(payload)
    except Exception as exc:  # noqa: BLE001
        print(f"Warning: abstracts.csv export skipped: {exc}")

    print(f"Assigned themes to {len(payload['submissions'])} submissions.")


if __name__ == "__main__":
    main()
