#!/usr/bin/env python3
"""Build 2D embedding cluster visualization data for the CCN 2026 dashboard."""

from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from sklearn.cluster import KMeans
from umap import UMAP

ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = ROOT / "data" / "ccn-2026-pending-posters.csv"
EMBEDDINGS_PATH = ROOT / "scripts" / "ccn_embeddings.npy"
OUT_DATA = ROOT / "docs" / "data" / "embeddings_2026.json"
OUT_MIRROR = ROOT / "data" / "embeddings_2026.json"

N_CLUSTERS = 10
N_UMAP_COMPONENTS = 5
UMAP_CLUSTER_PARAMS = {
    "n_components": N_UMAP_COMPONENTS,
    "n_neighbors": 15,
    "min_dist": 0.0,
    "metric": "cosine",
    "random_state": 42,
}
UMAP_2D_PARAMS = {
    "n_components": 2,
    "n_neighbors": 15,
    "min_dist": 0.15,
    "metric": "cosine",
    "random_state": 42,
}
KMEANS_PARAMS = {"n_clusters": N_CLUSTERS, "random_state": 42, "n_init": "auto"}

CLUSTER_NAMES = {
    0: "Cognition and Memory Systems",
    1: "Decision and Metacognition",
    2: "Naturalistic Brain Encoding",
    3: "Neural Population Dynamics",
    4: "Reinforcement Learning",
    5: "LLMs and Reasoning",
    6: "Language Neuroscience",
    7: "Neural Network Theory",
    8: "Computer Vision Models",
    9: "Visual Cortex Models",
}


def load_rows() -> list[dict[str, str]]:
    with CSV_PATH.open(encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def build_payload() -> dict:
    rows = load_rows()
    embeddings = np.load(EMBEDDINGS_PATH)
    if len(rows) != embeddings.shape[0]:
        raise ValueError(
            f"Row count ({len(rows)}) does not match embeddings ({embeddings.shape[0]})."
        )

    reduced = UMAP(**UMAP_CLUSTER_PARAMS).fit_transform(embeddings)
    clusters = KMeans(**KMEANS_PARAMS).fit_predict(reduced)
    coords = UMAP(**UMAP_2D_PARAMS).fit_transform(embeddings)

    cluster_counts: dict[int, int] = {}
    points = []
    for idx, row in enumerate(rows):
        cluster_id = int(clusters[idx])
        cluster_counts[cluster_id] = cluster_counts.get(cluster_id, 0) + 1
        poster = (row.get("or_number") or "").strip()
        points.append(
            {
                "id": f"2026-{poster or idx + 1}",
                "x": float(coords[idx, 0]),
                "y": float(coords[idx, 1]),
                "cluster": cluster_id,
                "cluster_name": CLUSTER_NAMES.get(cluster_id, f"Cluster {cluster_id}"),
                "title": (row.get("title") or "").strip(),
                "primary_area": (row.get("primary_area") or "").strip(),
                "secondary_area": (row.get("secondary_area") or "").strip(),
                "poster_number": poster,
                "status": (row.get("status") or "").strip(),
            }
        )

    cluster_summary = [
        {
            "id": cluster_id,
            "name": CLUSTER_NAMES.get(cluster_id, f"Cluster {cluster_id}"),
            "count": cluster_counts.get(cluster_id, 0),
        }
        for cluster_id in sorted(CLUSTER_NAMES)
    ]

    return {
        "metadata": {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "year": 2026,
            "count": len(points),
            "n_clusters": N_CLUSTERS,
            "embeddings_source": str(EMBEDDINGS_PATH.relative_to(ROOT)),
            "csv_source": str(CSV_PATH.relative_to(ROOT)),
            "method": "UMAP 2D + KMeans on Gemma embeddings (see ccn_abstract_clustering.ipynb)",
        },
        "clusters": cluster_summary,
        "points": points,
    }


def write_outputs(payload: dict) -> None:
    for path in (OUT_DATA, OUT_MIRROR):
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2, ensure_ascii=False)
        print(f"Wrote {path}")


def main() -> None:
    payload = build_payload()
    write_outputs(payload)
    print(f"Done. Exported {payload['metadata']['count']} embedding points.")


if __name__ == "__main__":
    main()
