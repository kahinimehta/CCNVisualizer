# How the visualizer works

## Pipeline

```
ccneuro.org archives  →  submissions.json  →  abstracts.csv  →  dashboard (D3)
2026 CSV + embeddings  ↗
```

1. **`scrape_ccn.py`** — fetches submissions, resolves keywords, merges 2026 CSV, assigns themes.
2. **`pdf_keywords.py`** — shared keyword resolution: HTML → PDF → fallback tokens.
3. **`assign_research_themes.py`** — maps keywords to Google Form research themes; stores `assigned_topics` and `cluster_track`.
4. **`build_abstracts_csv.py`** — exports the audit CSV to `data/abstracts.csv` and `docs/data/abstracts.csv`.
5. **`docs/js/app.js`** — loads the CSV with `d3.csv`, renders charts.

## Author keywords (preferred)

| Source | Years | Field |
|--------|-------|-------|
| Proceedings / authored PDF keyword line | 2017–2025 | `author_keywords` |
| `Keywords:` on poster HTML (MeetingTrakr) | 2024–2025 | `author_keywords` |
| 2026 CSV primary/secondary areas | 2026 | `author_keywords` |
| Official topic / track label | any year | used for theme matching when author keywords missing (not stored as author keywords) |
| Title/abstract token fallback | any year | `extracted_keywords` only |

### PDF extraction (`pdf_keywords.py`)

- **2017** — direct PDF URL from accepted-papers table; topic + keywords inside submission PDF.
- **2018–2019, 2022–2023** — detail page links to `proceedings/*.pdf`.
- **2024–2025** — detail page links to `/pdf/*_Authored.pdf` when HTML keywords are absent.

`backfill_pdf_keywords.py` re-runs enrichment for the full dataset and is safe to run after data updates.

## Theme assignment

Priority:

1. Official CCN topic label → mapped Google Form theme
2. Keyword token match against theme lexicon (uses `author_keywords` first, then abstract/title)
3. Soft boost from 2026 embedding cluster (when available)

`assigned_topics` holds every theme above threshold (multi-label). The dashboard counts a submission in each listed theme.

## Embedding map (2026)

- Embeddings: Gemma → UMAP → KMeans (`build_cluster_viz.py`)
- `cluster_track` in CSV = cluster name for visual audit
- Map panel filters on `cluster_track`; theme charts filter on `assigned_topics`

## Frontend notes

- List fields in CSV use ` | ` as delimiter
- `google_topics.json` supplies the canonical 12 theme names for axes/legends
- Theme-mix chart ignores the year filter so cross-year composition stays visible
