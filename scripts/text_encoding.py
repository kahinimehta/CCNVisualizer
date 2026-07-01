"""Repair common UTF-8 mojibake in scraped archive text."""

from __future__ import annotations

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

    for field in ("primary_theme",):
        if submission.get(field):
            submission[field] = repair_mojibake(str(submission[field]))
