#!/usr/bin/env python3
"""Assign research themes via Anthropic Claude (Opus 4.6 by default).

API key (never commit):
  - Local: copy `.env.example` → `.env` and set ANTHROPIC_API_KEY
  - CI / cloud agent: export ANTHROPIC_API_KEY or add it as a repository secret

Usage (from repo root):
  pip install anthropic python-dotenv
  python scripts/build.py --llm-themes
  python scripts/build.py --llm-themes --llm-limit 10   # smoke test
"""

from __future__ import annotations

import json
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CACHE_PATH = ROOT / "data" / "llm_theme_cache.json"
DEFAULT_MODEL = "claude-opus-4-6"
MAX_SECONDARY_TOPICS = 4
MAX_RETRIES = 4
RETRY_BASE_SECONDS = 2.0

SYSTEM_PROMPT = """You categorize CCN (Cognitive Computational Neuroscience) conference submissions into research themes for a meetup dashboard.

Rules:
- Choose exactly ONE primary_theme: the single best-fit category for the paper's main contribution.
- Choose secondary_topics: every other category that clearly applies (0–4 items). Do not repeat the primary.
- Prefer a specific real category over "Everything else" whenever the paper has any clear topical fit, even if the fit is partial or the paper spans methods + application.
- Use "Everything else" as primary ONLY when the submission does not meaningfully match any other category.
- Use official topic strings exactly as provided (case and punctuation must match)."""


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
            "  2. Add your key to ANTHROPIC_API_KEY in .env (file is gitignored)\n"
            "  3. pip install anthropic python-dotenv\n"
            "  4. python scripts/build.py --llm-themes\n\n"
            "For CI or cloud agents, set ANTHROPIC_API_KEY as an environment secret "
            "(never commit the key to the repo)."
        )
    return key


def anthropic_model() -> str:
    load_dotenv_if_available()
    return os.environ.get("ANTHROPIC_MODEL", DEFAULT_MODEL).strip() or DEFAULT_MODEL


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
        "\nRespond with JSON only, no markdown fences:\n"
        '{"primary_theme": "...", "secondary_topics": ["...", "..."]}'
    )
    return "\n".join(parts)


def parse_llm_json(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    return json.loads(text)


def normalize_assignment(raw: dict, topics: list[str], fallback: str) -> tuple[str, list[str], list[str]]:
    topic_set = set(topics)
    primary = str(raw.get("primary_theme", "")).strip()
    if primary not in topic_set:
        primary = fallback

    secondaries: list[str] = []
    for item in raw.get("secondary_topics") or []:
        name = str(item).strip()
        if name in topic_set and name != primary and name not in secondaries:
            secondaries.append(name)
        if len(secondaries) >= MAX_SECONDARY_TOPICS:
            break

    assigned = [primary, *secondaries]
    return primary, secondaries, assigned


def classify_submission(client, submission: dict, topics: list[str], *, fallback: str) -> tuple[str, list[str], list[str]]:
    model = anthropic_model()
    message = client.messages.create(
        model=model,
        max_tokens=512,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": submission_prompt(submission, topics)}],
    )
    text_blocks = [block.text for block in message.content if hasattr(block, "text") and block.text]
    if not text_blocks:
        raise ValueError("empty model response")
    raw = parse_llm_json(text_blocks[0])
    return normalize_assignment(raw, topics, fallback)


def load_cache() -> dict:
    if not CACHE_PATH.exists():
        return {"version": 1, "model": anthropic_model(), "assignments": {}}
    with CACHE_PATH.open(encoding="utf-8") as fh:
        return json.load(fh)


def save_cache(cache: dict) -> None:
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    cache["updated_at"] = datetime.now(timezone.utc).isoformat()
    cache["model"] = anthropic_model()
    with CACHE_PATH.open("w", encoding="utf-8") as fh:
        json.dump(cache, fh, indent=2, ensure_ascii=False)


def submission_cache_key(submission: dict) -> str:
    return str(submission.get("id") or submission.get("poster_number") or submission.get("title", ""))


def apply_llm_theme_assignments(
    submissions: list[dict],
    topics: list[str],
    *,
    fallback: str,
    limit: int | None = None,
    refresh: bool = False,
) -> dict:
    """Assign themes via Claude. Returns stats dict."""
    try:
        import anthropic
    except ImportError as exc:
        raise SystemExit("Install LLM dependencies: pip install anthropic python-dotenv") from exc

    api_key = anthropic_api_key()
    client = anthropic.Anthropic(api_key=api_key)
    cache = load_cache()
    assignments: dict = cache.setdefault("assignments", {})

    strict = os.environ.get("LLM_THEME_STRICT", "").strip() in {"1", "true", "yes"}
    todo: list[dict] = []
    for submission in submissions:
        key = submission_cache_key(submission)
        if not key:
            continue
        if refresh or key not in assignments:
            todo.append(submission)
        if limit is not None and len(todo) >= limit:
            break

    print(f"LLM theme assignment: model={anthropic_model()}, cache={CACHE_PATH.name}, "
          f"pending={len(todo)}, cached={len(assignments)}")

    errors = 0
    for index, submission in enumerate(todo, start=1):
        key = submission_cache_key(submission)
        for attempt in range(MAX_RETRIES):
            try:
                primary, secondary, assigned = classify_submission(
                    client, submission, topics, fallback=fallback
                )
                assignments[key] = {
                    "primary_theme": primary,
                    "secondary_topics": secondary,
                    "assigned_topics": assigned,
                    "assigned_at": datetime.now(timezone.utc).isoformat(),
                }
                save_cache(cache)
                if index % 25 == 0 or index == len(todo):
                    print(f"  classified {index}/{len(todo)} …")
                break
            except Exception as exc:
                if attempt + 1 >= MAX_RETRIES:
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
        "cache_path": str(CACHE_PATH.relative_to(ROOT)),
        "classified_now": len(todo) - errors,
        "cache_hits": applied,
        "errors": errors,
        "pending_without_cache": len(submissions) - applied,
    }
