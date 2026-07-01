# How the visualizer works

## Pipeline

```
ccneuro.org archives  →  submissions.json  →  abstracts.csv  →  dashboard (D3)
2026 CSV + embeddings  ↗
```

1. **`scrape_ccn.py`** — fetches submissions, splits `author_keywords` vs `extracted_keywords`, merges 2026 CSV, assigns themes.
2. **`assign_research_themes.py`** — maps keywords to Google Form research themes; stores `assigned_topics` (multi-label) and `cluster_track` (2026 embedding cluster).
3. **`build_abstracts_csv.py`** — exports the audit CSV to `data/abstracts.csv` and `docs/data/abstracts.csv`.
4. **`docs/js/app.js`** — loads the CSV with `d3.csv`, builds in-memory submission objects, renders charts.

## Keywords

| Source | Years | Field |
|--------|-------|-------|
| Author Keywords on poster page | 2024–2025 | `author_keywords` |
| 2026 CSV primary/secondary areas | 2026 | `author_keywords` |
| Official topic / track label | 2025, 2022–2023 | used for theme matching when author keywords missing |
| Title/abstract token fallback | 2018–2019 | `extracted_keywords` |

## Theme assignment

Priority:

1. Official CCN topic label → mapped Google Form theme
2. Keyword token match against theme lexicon
3. Soft boost from 2026 embedding cluster (when available)

`assigned_topics` holds every theme above threshold (not just one primary). The dashboard counts a submission in each listed theme.

## Embedding map (2026)

- Embeddings: Gemma → UMAP → KMeans (`build_cluster_viz.py`)
- `cluster_track` in CSV = cluster name for visual audit
- Map panel filters on `cluster_track`; theme charts filter on `assigned_topics`

## Frontend notes

- List fields in CSV use ` | ` as delimiter
- `google_topics.json` supplies the canonical 12 theme names for axes/legends
- `embeddings_2026.json` supplements CSV coordinates when present
