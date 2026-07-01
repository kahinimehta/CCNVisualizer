# How the visualizer works

## Pipeline

```
ccneuro.org archives  →  submissions.json  →  abstracts.csv  →  dashboard (D3)
                              ↓
                    assign_research_themes.py
                              ↓
                    build_all_embeddings.py (TF-IDF + UMAP, all years)
```

1. **`scrape_ccn.py`** — fetches submissions, resolves keywords, merges 2026 CSV, assigns themes.
2. **`pdf_keywords.py`** — shared keyword resolution: HTML → PDF → fallback tokens.
3. **`assign_research_themes.py`** — maps keywords to the 12 Google Form research themes; stores `assigned_topics` (multi-label).
4. **`build_all_embeddings.py`** — TF-IDF on title + abstract for every submission, then 2D UMAP → `embeddings_all.json` + CSV `umap_x` / `umap_y`.
5. **`build_abstracts_csv.py`** — exports the audit CSV to `data/abstracts.csv` and `docs/data/abstracts.csv`.
6. **`docs/js/app.js`** — loads the CSV with `d3.csv`, renders charts.

Optional legacy path for 2026 Gemma embeddings: `build_cluster_viz.py` + `embeddings_2026.json` (used only as a soft boost during theme assignment, not shown in the UI).

## Author keywords (preferred)

| Source | Years | Field |
|--------|-------|-------|
| Proceedings / authored PDF keyword line | 2017–2025 | `author_keywords` |
| `Keywords:` on poster HTML (MeetingTrakr) | 2024–2025 | `author_keywords` |
| 2026 CSV primary/secondary areas | 2026 | `author_keywords` |
| Official topic / track label | any year | used for theme matching when author keywords missing |
| Title/abstract token fallback | any year | `extracted_keywords` only |

## Theme assignment

Priority:

1. Official CCN topic label → mapped Google Form theme
2. Keyword token match against theme lexicon (uses `author_keywords` first, then abstract/title)
3. Optional soft boost from 2026 Gemma embedding cluster **mapped to the same Google theme** (internal only)

`assigned_topics` holds every theme above threshold (multi-label). There is no separate user-facing cluster label.

## Embedding map (all years)

- Coordinates: TF-IDF (title + abstract) → UMAP 2D (`build_all_embeddings.py`)
- **Pie-slice dots:** each assigned topic gets an equal arc; colors match the 12-topic legend
- Map respects **year**, **search**, and **topic** filters (same as the paper list)
- Click/tap a dot → scroll to that submission in Matching submissions

## Frontend notes

- List fields in CSV use ` | ` as delimiter
- `google_topics.json` supplies the canonical 12 theme names and colors
- Year-over-year theme chart ignores the year filter so cross-year composition stays visible
