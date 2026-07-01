#!/usr/bin/env python3
"""Build 2D UMAP coordinates for all submissions (TF-IDF on title + abstract)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from umap import UMAP

ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "data" / "submissions.json"
OUT_PATHS = (ROOT / "docs" / "data" / "embeddings_all.json", ROOT / "data" / "embeddings_all.json")

UMAP_PARAMS = {
    "n_components": 2,
    "n_neighbors": 15,
    "min_dist": 0.12,
    "metric": "cosine",
    "random_state": 42,
}


def submission_text(submission: dict) -> str:
    title = (submission.get("title") or "").strip()
    abstract = (submission.get("abstract") or "").strip()
    blob = f"{title}. {abstract}".strip()
    return blob or title or "empty"


def build_payload(submissions: list[dict] | None = None) -> dict:
    if submissions is None:
        if not DATA_PATH.exists():
            raise SystemExit(f"Missing {DATA_PATH}")
        with DATA_PATH.open(encoding="utf-8") as fh:
            submissions = json.load(fh).get("submissions", [])

    if not submissions:
        raise SystemExit("No submissions found.")

    texts = [submission_text(sub) for sub in submissions]
    vectorizer = TfidfVectorizer(
        max_features=8000,
        stop_words="english",
        min_df=2,
        max_df=0.95,
        ngram_range=(1, 2),
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
            "method": "TF-IDF (title + abstract) + UMAP 2D, cosine metric",
        },
        "points": points,
    }


def write_outputs(payload: dict) -> None:
    for path in OUT_PATHS:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2, ensure_ascii=False)
        print(f"Wrote {path}")


def main() -> None:
    payload = build_payload()
    write_outputs(payload)
    print(f"Done. Exported {payload['metadata']['count']} embedding points across {len(payload['metadata']['years'])} years.")


if __name__ == "__main__":
    main()
