# CCN Submission Visualizer

Interactive exploration of CCN poster and paper archives (2017–2026).

## How data gets here

The dashboard never talks to ccneuro.org directly. Everything is precomputed offline and shipped as one CSV:

```
ccneuro.org archives
        │
        ▼  scrape_ccn.py (+ pdf_keywords.py, merge_2026_csv.py)
  submissions.json          ← raw archive: titles, abstracts, authors, keywords
        │
        ▼  assign_research_themes.py
  ┌─────────────────────────────────────┐
  │ 1. Clean keywords & repair encoding │
  │ 2. Assign 12 research themes        │
  │ 3. Build UMAP map (embeddings_all)  │
  │ 4. Export abstracts.csv             │
  └─────────────────────────────────────┘
        │
        ▼
  abstracts.csv  ──→  dashboard (docs/js/app.js)
```

**Step 1 — Scrape to JSON.** `scrape_ccn.py` pulls poster/paper records from CCN archives (2017–2026) into `data/submissions.json`. Keywords come from poster HTML, proceedings PDFs, or a token fallback. Citation fragments (`et al.`, page numbers, DOIs) and conference metadata labels are stripped at this stage.

**Step 2 — Clustering & themes.** `assign_research_themes.py` reads the JSON, runs the clustering/theme algorithm (see [IMPLEMENTATION.md](IMPLEMENTATION.md) for details), writes updated topics back to `submissions.json`, saves 2D map coordinates to `embeddings_all.json`, and exports `abstracts.csv`.

**Step 3 — Dashboard.** The browser loads only `docs/data/abstracts.csv`. Map coordinates (`umap_x`, `umap_y`), assigned topics, and all display fields are already in that file.

To refresh everything after a scrape:

```bash
pip install -r scripts/requirements.txt
python scripts/scrape_ccn.py              # rebuild submissions.json
python scripts/backfill_pdf_keywords.py   # refresh keywords (optional)
python scripts/assign_research_themes.py  # themes + UMAP + abstracts.csv
```

`assign_research_themes.py` is the single command that regenerates themes, the embedding map, and both copies of the CSV. You can also run `build_all_embeddings.py` or `build_abstracts_csv.py` individually.

The CSV is written as **UTF-8 with BOM** (`utf-8-sig`) so Excel and similar tools display non-English characters correctly. Text fields are passed through `repair_mojibake()` to fix UTF-8 bytes that were mis-read as Latin-1 during scraping.

## Data source

The dashboard loads **only** `data/abstracts.csv`. No other JSON or API calls are required at runtime.

### Core columns

| Column | Meaning |
|--------|---------|
| `year` | Conference year |
| `title` | Submission title |
| `author` | First author |
| `keywords` | Cleaned content keywords (metadata area labels and citation fragments removed) |
| `assigned_topics` | One or more of the **12 CCN research themes**, pipe-separated (` \| `), **ordered by importance** (best match first) |

### Additional columns (precomputed at build time)

These are written into the same CSV so the UI can link, search, and plot without extra files:

| Column | Meaning |
|--------|---------|
| `id` | Stable row identifier |
| `authors` | Full author list |
| `abstract` | Full abstract text (search only) |
| `umap_x`, `umap_y` | 2D map coordinates (weighted TF-IDF + UMAP; see IMPLEMENTATION.md) |
| `source_url` | Link to poster / PDF |
| `poster_number` | Poster number when available |

## The 12 research themes

Topics in `assigned_topics` are always drawn from this fixed list (CCN 2026 Activity Preferences):

1. RL, motor control & planning  
2. Naturalistic encoding/decoding  
3. Neural population geometry & dynamics  
4. Decision-making and metacognition  
5. Vision  
6. Language/auditory neuroscience  
7. LLMs, reasoning, interpretability  
8. Memory  
9. Social cognition & theory of mind  
10. Attention & cognitive control / executive function  
11. Clinical / computational psychiatry  
12. Methods, theory & everything else  

## Filters

- **Year** — all years or a single conference year  
- **Research theme** — matches any value in `assigned_topics`  
- **Search** — title, author(s), abstract, keywords, assigned topics  
- **Embedding map** — shows filtered rows; dot color = primary topic; click a dot to see all assigned topics in the list below  

## Charts

| Panel | What it uses from the CSV |
|-------|---------------------------|
| Theme ranking / year-over-year change | `assigned_topics` (multi-label counts) |
| Embedding map | `umap_x`, `umap_y`, `assigned_topics` |
| Paper list | `title`, `author`, `authors`, `year`, `assigned_topics`, `source_url` |

## Rebuilding `abstracts.csv`

See **How data gets here** above for the full workflow. In short: scrape → JSON → `assign_research_themes.py` → CSV → dashboard.
