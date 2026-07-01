# How the visualizer works

## Runtime

```
data/abstracts.csv  →  docs/js/app.js (d3.csv)  →  dashboard
```

The browser loads **one file**: `abstracts.csv`. The 12 research theme names and colors are defined in `app.js`.

## Build pipeline

```
ccneuro.org archives  →  submissions.json  →  abstracts.csv
                              ↓
                    assign_research_themes.py
                              ↓
                    build_all_embeddings.py
                              ↓
                    build_abstracts_csv.py
```

1. **`scrape_ccn.py`** — fetches submissions, resolves keywords, merges 2026 CSV.  
2. **`pdf_keywords.py`** — keyword resolution: HTML → PDF → token fallback.  
3. **`assign_research_themes.py`** — scores each submission against the 12 Google Form themes; writes `assigned_topics` in priority order (primary first, then secondaries).  
4. **`build_all_embeddings.py`** — TF-IDF on title + abstract, UMAP 2D for every row.  
5. **`build_abstracts_csv.py`** — exports the dashboard CSV with core columns plus precomputed map coords and links.

## CSV schema

**Core fields (what defines each submission for analysis):**

- `year`, `title`, `author`, `keywords`, `assigned_topics`

**Support fields (precomputed for the UI):**

- `id`, `authors`, `abstract`, `umap_x`, `umap_y`, `source_url`, `poster_number`

List-valued fields use ` | ` as the delimiter. Topics in `assigned_topics` are ordered by importance.

The CSV is exported as **UTF-8 with BOM** (`utf-8-sig`). `text_encoding.repair_mojibake()` fixes common UTF-8-as-Latin-1 corruption in titles, authors, and abstracts before export.

## Keyword column

`keywords` in the CSV stores extraction-pipeline output:

1. `extracted_keywords` when present (title/abstract token fallback)  
2. otherwise `author_keywords` (HTML, PDF, or 2026 CSV areas)  
3. otherwise legacy `keywords` on the submission record  

## Theme assignment

Priority when building `assigned_topics`:

1. Official CCN topic/track label → mapped Google Form theme (specific labels only)  
2. Keyword scoring against the theme lexicon — **title matches count double** (phrases like `conscious vision` beat generic area keywords)  
3. Soft boost from broad area labels such as `psychological / behavioral research` (nudge only; never override title/abstract)  
4. Optional soft boost from 2026 Gemma embedding cluster mapped to the same 12 themes (internal to `assign_research_themes.py` only)

There is no separate cluster label in the CSV — only the 12 research themes.

## Embedding map

- Coordinates come from `umap_x` / `umap_y` in the CSV  
- Each dot is a **pie slice per assigned topic** (equal arcs, fixed 12-color palette)  
- Map respects the same year / search / topic filters as the paper list  

## Frontend notes

- Pie-slice colors index into `GOOGLE_FORM_TOPICS` in `app.js`  
- Year-over-year theme chart ignores the year filter so cross-year trends stay visible  
