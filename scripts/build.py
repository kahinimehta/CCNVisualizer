#!/usr/bin/env python3
"""Step 2: Classify themes (Anthropic Claude), compute UMAP, export abstracts.csv.

Pipeline:
  scrape.py  →  submissions.json
  build.py   →  filter GAC updates + Anthropic themes + UMAP + abstracts.csv
  dashboard  →  reads docs/data/abstracts.csv

Dependencies:
  pip install -r requirements.txt

API key (never commit): copy .env.example → .env and set ANTHROPIC_API_KEY
"""

from __future__ import annotations

import csv
import json
import os
import re
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

from sklearn.feature_extraction.text import TfidfVectorizer
from umap.umap_ import UMAP  # avoid umap.__init__ → parametric_umap → tensorflow

from shared import (
    content_keywords,
    dashboard_keywords,
    is_gac_update,
    is_year_id_cache_key,
    normalize_field_text,
    reconcile_submission_keywords,
    repair_mojibake,
    repair_submission_text,
    sanitize_keyword_list,
    sanitize_submission_keywords,
    submission_embedding_text,
    submission_row_key,
    vectorizer_stop_words,
)

ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "data" / "submissions.json"
GOOGLE_TOPICS_PATH = ROOT / "data" / "google_topics.json"
LLM_CACHE_PATH = ROOT / "data" / "llm_theme_cache.json"
EMBEDDING_PATH = ROOT / "data" / "embeddings_all.json"
CSV_OUTPUT_PATHS = (ROOT / "data" / "abstracts.csv", ROOT / "docs" / "data" / "abstracts.csv")
CSV_TWO_TOPICS_PATH = ROOT / "docs" / "data" / "abstracts_2_topics.csv"
CSV_V3_PATH = ROOT / "docs" / "data" / "abstract_v_3.csv"
LIST_DELIMITER = " | "

DEFAULT_TOPICS = [
    "Reinforcement learning",
    "Motor control & planning",
    "Naturalistic encoding/decoding",
    "Neural population geometry & dynamics",
    "Decision-making and metacognition",
    "Vision",
    "Perception",
    "Language/auditory neuroscience",
    "AI, LLM, & Neural Networks",
    "Memory",
    "Social cognition & theory of mind",
    "Attention & cognitive control / executive function",
    "Clinical / computational psychiatry",
    "Methods and theory",
]

TOPIC_FALLBACK = "Methods and theory"
EVERYTHING_ELSE = "Everything else"
ANTHROPIC_MODEL_DEFAULT = "claude-opus-4-6"
MAX_SECONDARY_TOPICS = 4
MAX_LLM_RETRIES = 4
RETRY_BASE_SECONDS = 2.0

SYSTEM_PROMPT = """You categorize CCN (Cognitive Computational Neuroscience) conference submissions into research themes for a meetup dashboard.

Rules:
- Choose exactly ONE primary_theme: the single best-fit category for the paper's main contribution.
- Choose secondary_topics: every other category that clearly applies (0–4 items). Do not repeat the primary.
- Every submission must use one of the allowed categories; there is no catch-all category.
- Use official topic strings exactly as provided (case and punctuation must match)."""

UMAP_PARAMS = {
    "n_components": 2,
    "n_neighbors": 15,
    "min_dist": 0.12,
    "metric": "cosine",
    "random_state": 42,
}

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


def load_dotenv_if_available() -> None:
    env_path = ROOT / ".env"
    if not env_path.exists():
        return
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    load_dotenv(env_path)


def anthropic_api_key() -> str:
    load_dotenv_if_available()
    key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not key or key.startswith("sk-ant-api03-REPLACE"):
        raise SystemExit(
            "Missing Anthropic API key.\n\n"
            "  1. cp .env.example .env\n"
            "  2. Set ANTHROPIC_API_KEY in .env (gitignored)\n"
            "  3. pip install -r requirements.txt\n"
            "  4. python scripts/build.py\n\n"
            "Or pass --skip-classify to reuse existing assigned_topics in submissions.json."
        )
    return key


def anthropic_model() -> str:
    load_dotenv_if_available()
    return os.environ.get("ANTHROPIC_MODEL", ANTHROPIC_MODEL_DEFAULT).strip() or ANTHROPIC_MODEL_DEFAULT


def load_google_config() -> dict:
    if GOOGLE_TOPICS_PATH.exists():
        with GOOGLE_TOPICS_PATH.open(encoding="utf-8") as fh:
            return json.load(fh)
    return {"enabled": True, "topics": DEFAULT_TOPICS}


def active_topics(config: dict) -> list[str]:
    if config.get("enabled") and config.get("topics"):
        topics = list(config["topics"])
    else:
        topics = list(DEFAULT_TOPICS)
    return [topic for topic in topics if topic != EVERYTHING_ELSE]


def submission_prompt(submission: dict, topics: list[str]) -> str:
    title = (submission.get("title") or "").strip()
    abstract = (submission.get("abstract") or "").strip()
    keywords = submission.get("keywords") or submission.get("author_keywords") or []
    if isinstance(keywords, list):
        keywords = ", ".join(str(k) for k in keywords if k)
    track = (submission.get("topic_area") or submission.get("track") or "").strip()
    year = submission.get("year", "")

    topic_list = "\n".join(f"- {name}" for name in topics)
    parts = [
        "Allowed categories (use these strings exactly):",
        topic_list,
        "",
        f"Year: {year}",
        f"Title: {title}",
    ]
    if track:
        parts.append(f"Conference track/area: {track}")
    if keywords:
        parts.append(f"Keywords: {keywords}")
    if abstract:
        parts.append(f"Abstract: {abstract}")
    parts.append(
        '\nRespond with JSON only, no markdown fences:\n'
        '{"primary_theme": "...", "secondary_topics": ["...", "..."]}'
    )
    return "\n".join(parts)


def parse_llm_json(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    return json.loads(text)


def normalize_assignment(raw: dict, topics: list[str]) -> tuple[str, list[str], list[str]]:
    topic_set = set(topics)
    primary = str(raw.get("primary_theme", "")).strip()
    if primary not in topic_set or primary == EVERYTHING_ELSE:
        primary = ""

    secondaries: list[str] = []
    for item in raw.get("secondary_topics") or []:
        name = str(item).strip()
        if name in topic_set and name != EVERYTHING_ELSE and name != primary and name not in secondaries:
            secondaries.append(name)
        if len(secondaries) >= MAX_SECONDARY_TOPICS:
            break

    if not primary:
        if secondaries:
            primary = secondaries.pop(0)
        else:
            primary = TOPIC_FALLBACK

    assigned = [primary, *secondaries]
    return primary, secondaries, assigned


def migrate_everything_else(submission: dict) -> bool:
    assigned = list(submission.get("assigned_topics") or [])
    if not assigned:
        primary = str(submission.get("primary_theme") or "").strip()
        secondaries = list(submission.get("secondary_topics") or [])
        if primary:
            assigned = [primary, *[s for s in secondaries if s and s != primary]]

    new_assigned = [topic for topic in assigned if topic and topic != EVERYTHING_ELSE]
    if not new_assigned:
        new_assigned = [TOPIC_FALLBACK]

    changed = new_assigned != assigned
    submission["assigned_topics"] = new_assigned
    submission["primary_theme"] = new_assigned[0]
    submission["secondary_topics"] = new_assigned[1:]
    return changed


def migrate_all_everything_else(submissions: list[dict]) -> int:
    changed = sum(1 for submission in submissions if migrate_everything_else(submission))
    if changed:
        print(f"Migrated {changed} submission(s) off '{EVERYTHING_ELSE}'.")
    return changed


def classify_submission(client, submission: dict, topics: list[str]) -> tuple[str, list[str], list[str]]:
    message = client.messages.create(
        model=anthropic_model(),
        max_tokens=512,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": submission_prompt(submission, topics)}],
    )
    text_blocks = [block.text for block in message.content if hasattr(block, "text") and block.text]
    if not text_blocks:
        raise ValueError("empty model response")
    return normalize_assignment(parse_llm_json(text_blocks[0]), topics)


def load_llm_cache(submissions: list[dict] | None = None) -> dict:
    if not LLM_CACHE_PATH.exists():
        return {"version": 1, "model": anthropic_model(), "key_schema": "year:id", "assignments": {}}
    with LLM_CACHE_PATH.open(encoding="utf-8") as fh:
        cache = json.load(fh)
    if submissions:
        cache, reopened = migrate_llm_cache_assignments(cache, submissions)
        if reopened:
            print(
                f"Migrated LLM cache to year:id keys; "
                f"{reopened} collision submission(s) will be re-classified."
            )
            save_llm_cache(cache)
    return cache


def migrate_llm_cache_assignments(cache: dict, submissions: list[dict]) -> tuple[dict, int]:
    """Convert legacy id-only cache keys to year:id (one owner per reused id)."""
    if cache.get("key_schema") == "year:id":
        return cache, 0

    assignments: dict = cache.setdefault("assignments", {})
    if not assignments:
        cache["key_schema"] = "year:id"
        return cache, 0

    if any(is_year_id_cache_key(key) for key in assignments):
        cache["key_schema"] = "year:id"
        return cache, 0

    by_id: dict[str, list[dict]] = defaultdict(list)
    for submission in submissions:
        paper_id = str(submission.get("id") or submission.get("poster_number") or "")
        if paper_id:
            by_id[paper_id].append(submission)

    new_assignments: dict = {}
    reopened = 0

    for old_key, value in assignments.items():
        group = by_id.get(str(old_key), [])
        if not group:
            continue
        if len(group) == 1:
            new_assignments[submission_row_key(group[0])] = value
            continue

        owner = group[-1]
        new_assignments[submission_row_key(owner)] = value
        reopened += len(group) - 1

    cache["assignments"] = new_assignments
    cache["key_schema"] = "year:id"
    cache["migrated_from_id_only_at"] = datetime.now(timezone.utc).isoformat()
    return cache, reopened


def save_llm_cache(cache: dict) -> None:
    LLM_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    cache["updated_at"] = datetime.now(timezone.utc).isoformat()
    cache["model"] = anthropic_model()
    with LLM_CACHE_PATH.open("w", encoding="utf-8") as fh:
        json.dump(cache, fh, indent=2, ensure_ascii=False)


def submission_cache_key(submission: dict) -> str:
    return submission_row_key(submission)


def classify_with_anthropic(
    submissions: list[dict],
    topics: list[str],
    *,
    limit: int | None = None,
    refresh: bool = False,
) -> dict:
    try:
        import anthropic
    except ImportError as exc:
        raise SystemExit("Install dependencies: pip install -r requirements.txt") from exc

    client = anthropic.Anthropic(api_key=anthropic_api_key())
    cache = load_llm_cache(submissions)
    assignments: dict = cache.setdefault("assignments", {})
    strict = os.environ.get("LLM_THEME_STRICT", "").strip().lower() in {"1", "true", "yes"}

    todo: list[dict] = []
    for submission in submissions:
        key = submission_cache_key(submission)
        if not key:
            continue
        if refresh or key not in assignments:
            todo.append(submission)
        if limit is not None and len(todo) >= limit:
            break

    print(
        f"Anthropic classification: model={anthropic_model()}, "
        f"pending={len(todo)}, cached={len(assignments)}"
    )

    errors = 0
    for index, submission in enumerate(todo, start=1):
        key = submission_cache_key(submission)
        for attempt in range(MAX_LLM_RETRIES):
            try:
                primary, secondary, assigned = classify_submission(client, submission, topics)
                assignments[key] = {
                    "primary_theme": primary,
                    "secondary_topics": secondary,
                    "assigned_topics": assigned,
                    "assigned_at": datetime.now(timezone.utc).isoformat(),
                }
                save_llm_cache(cache)
                if index % 25 == 0 or index == len(todo):
                    print(f"  classified {index}/{len(todo)} …")
                break
            except Exception as exc:
                if attempt + 1 >= MAX_LLM_RETRIES:
                    errors += 1
                    print(f"  WARN failed {key}: {exc}")
                    if strict:
                        raise
                    break
                time.sleep(RETRY_BASE_SECONDS * (2**attempt))

    applied = 0
    for submission in submissions:
        key = submission_cache_key(submission)
        cached = assignments.get(key)
        if not cached:
            continue
        submission["primary_theme"] = cached["primary_theme"]
        submission["secondary_topics"] = list(cached["secondary_topics"])
        submission["assigned_topics"] = list(cached["assigned_topics"])
        applied += 1

    return {
        "model": anthropic_model(),
        "classified_now": len(todo) - errors,
        "cache_hits": applied,
        "errors": errors,
        "pending_without_cache": len(submissions) - applied,
    }


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


def apply_assignments(
    payload: dict,
    *,
    skip_classify: bool = False,
    classify_limit: int | None = None,
    classify_refresh: bool = False,
) -> dict:
    config = load_google_config()
    topics = active_topics(config)
    submissions = payload["submissions"]

    for submission in submissions:
        repair_submission_text(submission)
        reconcile_submission_keywords(submission)

    if skip_classify:
        theme_method = "Skipped classification; reused assigned_topics from submissions.json"
        missing = sum(1 for s in submissions if not s.get("assigned_topics"))
        if missing:
            print(f"WARNING: {missing} submissions have no assigned_topics.")
    else:
        stats = classify_with_anthropic(
            submissions,
            topics,
            limit=classify_limit,
            refresh=classify_refresh,
        )
        pending = stats["pending_without_cache"]
        if pending:
            print(
                f"WARNING: {pending} submissions have no LLM assignment "
                "(run without --classify-limit to classify all)."
            )
        theme_method = (
            f"Anthropic {stats['model']}; dominant + secondary from title/abstract/keywords/track; "
            f"auto-assigned with some manual spot-checks; cache data/llm_theme_cache.json; "
            f"classified_now={stats['classified_now']}, errors={stats['errors']}"
        )

    for submission in submissions:
        submission.pop("cluster_track", None)

    migrate_all_everything_else(submissions)

    payload.setdefault("stats", {})
    payload["stats"]["research_themes"] = compute_theme_stats(submissions, topics)
    payload["metadata"]["research_themes_assigned_at"] = datetime.now(timezone.utc).isoformat()
    payload["metadata"]["research_theme_method"] = theme_method
    payload["metadata"]["keyword_source"] = (
        "author_keywords prefer poster HTML, proceedings/authored PDFs (2017-2025), or 2026 topic areas; "
        "extracted_keywords only when no author keywords are available; citation fragments and "
        "metadata area labels stripped before export"
    )
    payload["metadata"]["keyword_years"] = sorted({sub["year"] for sub in submissions if sub.get("keywords")})
    payload["metadata"]["google_topics_source"] = config.get("source")
    return payload


def write_payload(payload: dict) -> None:
    with DATA_PATH.open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, ensure_ascii=False)
    print(f"Wrote {DATA_PATH}")


def build_umap(submissions: list[dict]) -> dict:
    if not submissions:
        raise SystemExit("No submissions found.")

    for submission in submissions:
        repair_submission_text(submission)
        reconcile_submission_keywords(submission)

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
                "Weighted TF-IDF (title x2, abstract x3, cleaned keywords x1) + UMAP 2D; cosine distance between TF-IDF vectors"
            ),
        },
        "points": points,
    }


def write_embedding_outputs(payload: dict) -> None:
    EMBEDDING_PATH.parent.mkdir(parents=True, exist_ok=True)
    with EMBEDDING_PATH.open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, ensure_ascii=False)
    print(f"Wrote {EMBEDDING_PATH}")


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
    if any(hint in tail for hint in AFFILIATION_HINTS) or re.search(r"\b(states|kingdom|republic)\b", tail):
        return parts[0]
    return parts[0]


def join_list(values: list[str]) -> str:
    return LIST_DELIMITER.join(value for value in values if value)


def assigned_topics(submission: dict) -> list[str]:
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
        year = point.get("year", "")
        paper_id = point.get("id", "")
        lookup[submission_row_key({"year": year, "id": paper_id})] = point
        if point.get("poster_number"):
            lookup[f"2026-{point['poster_number']}"] = point
    return lookup


def build_csv_rows(payload: dict, embeddings: dict) -> list[dict[str, str]]:
    submissions = payload.get("submissions", [])
    embedding_lookup = embedding_index(embeddings)
    rows: list[dict[str, str]] = []

    for submission in sorted(
        submissions,
        key=lambda item: (item.get("year", 0), str(item.get("title", "")).lower()),
    ):
        sub_id = submission.get("id", "")
        poster = str(submission.get("poster_number") or "")
        point = (
            embedding_lookup.get(submission_row_key(submission))
            or embedding_lookup.get(f"2026-{poster}")
        )
        authors = submission.get("authors", "")

        rows.append(
            {
                "id": sub_id,
                "year": str(submission.get("year", "")),
                "title": normalize_field_text(submission.get("title", "")),
                "author": normalize_field_text(first_author(authors)),
                "keywords": join_list(dashboard_keywords(submission)),
                "assigned_topics": join_list(assigned_topics(submission)),
                "authors": normalize_field_text(authors),
                "abstract": normalize_field_text(submission.get("abstract", "")),
                "umap_x": "" if not point else str(point.get("x", "")),
                "umap_y": "" if not point else str(point.get("y", "")),
                "source_url": submission.get("source_url", ""),
                "poster_number": poster,
            }
        )
    return rows


def derive_two_topic_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    derived: list[dict[str, str]] = []
    for row in rows:
        topics = [topic for topic in row.get("assigned_topics", "").split(LIST_DELIMITER) if topic]
        derived.append({**row, "assigned_topics": join_list(topics[:2])})
    return derived


def derive_v3_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    """Drop Methods and theory unless it is in the top two assigned topics."""
    derived: list[dict[str, str]] = []
    for row in rows:
        topics = [topic for topic in row.get("assigned_topics", "").split(LIST_DELIMITER) if topic]
        kept = [
            topic
            for index, topic in enumerate(topics)
            if topic != "Methods and theory" or index < 2
        ]
        derived.append({**row, "assigned_topics": join_list(kept)})
    return derived


def write_csv_rows(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {path}")


def write_csv(rows: list[dict[str, str]]) -> None:
    for path in CSV_OUTPUT_PATHS:
        write_csv_rows(path, rows)
    write_csv_rows(CSV_TWO_TOPICS_PATH, derive_two_topic_rows(rows))
    write_csv_rows(CSV_V3_PATH, derive_v3_rows(rows))


def filter_gac_updates(payload: dict) -> dict:
    submissions = payload.get("submissions", [])
    kept = [sub for sub in submissions if not is_gac_update(sub.get("title", ""))]
    removed = len(submissions) - len(kept)
    if removed:
        print(f"Excluded {removed} GAC update submission(s) from build.")
        payload["submissions"] = kept
        payload.setdefault("metadata", {})["gac_updates_excluded"] = removed
        payload["metadata"]["total_count"] = len(kept)
        years = sorted({sub.get("year") for sub in kept if sub.get("year") is not None})
        payload["metadata"]["years"] = years
    return payload


def repair_payload(payload: dict) -> dict:
    for submission in payload.get("submissions", []):
        repair_submission_text(submission)
        reconcile_submission_keywords(submission)
    return payload


def run_repair_only() -> None:
    if not DATA_PATH.exists():
        raise SystemExit(f"Missing {DATA_PATH}. Run scripts/scrape.py first.")
    with DATA_PATH.open(encoding="utf-8") as fh:
        payload = json.load(fh)

    payload = repair_payload(payload)
    write_payload(payload)

    if EMBEDDING_PATH.exists():
        with EMBEDDING_PATH.open(encoding="utf-8") as fh:
            embeddings = json.load(fh)
    else:
        embeddings = {"points": []}

    write_csv(build_csv_rows(payload, embeddings))
    print(f"Repaired text fields for {len(payload.get('submissions', []))} submissions.")


def run_build(
    payload: dict | None = None,
    *,
    skip_classify: bool = False,
    classify_limit: int | None = None,
    classify_refresh: bool = False,
) -> dict:
    if payload is None:
        if not DATA_PATH.exists():
            raise SystemExit(f"Missing {DATA_PATH}. Run scripts/scrape.py first.")
        with DATA_PATH.open(encoding="utf-8") as fh:
            payload = json.load(fh)

    payload = filter_gac_updates(payload)

    payload = apply_assignments(
        payload,
        skip_classify=skip_classify,
        classify_limit=classify_limit,
        classify_refresh=classify_refresh,
    )
    write_payload(payload)

    embeddings = build_umap(payload["submissions"])
    write_embedding_outputs(embeddings)
    write_csv(build_csv_rows(payload, embeddings))

    print(f"Built dashboard artifacts for {len(payload['submissions'])} submissions.")
    return payload


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        description="Classify themes (Anthropic), compute UMAP, write abstracts.csv"
    )
    parser.add_argument(
        "--skip-classify",
        action="store_true",
        help="Skip Anthropic; keep existing assigned_topics in submissions.json",
    )
    parser.add_argument(
        "--classify-limit",
        type=int,
        default=None,
        metavar="N",
        help="Only call the API for the first N uncached submissions",
    )
    parser.add_argument(
        "--classify-refresh",
        action="store_true",
        help="Ignore cache and re-classify (respects --classify-limit if set)",
    )
    parser.add_argument(
        "--repair-only",
        action="store_true",
        help="Sanitize keywords/abstracts in submissions.json and rewrite abstracts.csv (no API/UMAP)",
    )
    args = parser.parse_args()
    if args.repair_only:
        run_repair_only()
        return
    run_build(
        skip_classify=args.skip_classify,
        classify_limit=args.classify_limit,
        classify_refresh=args.classify_refresh,
    )


if __name__ == "__main__":
    main()
