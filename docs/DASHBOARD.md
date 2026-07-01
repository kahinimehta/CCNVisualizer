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

### Rebuild commands

```bash
pip install -r scripts/requirements.txt
python scripts/scrape_ccn.py              # rebuild submissions.json
python scripts/backfill_pdf_keywords.py   # refresh keywords (optional)
python scripts/assign_research_themes.py  # themes + UMAP + abstracts.csv
```

`assign_research_themes.py` is the single command that regenerates themes, the embedding map, and both copies of the CSV. You can also run `build_all_embeddings.py` or `build_abstracts_csv.py` individually.

For **2026-only updates**, replace `data/ccn-2026-pending-posters.csv` and run `merge_2026_csv.py` followed by `assign_research_themes.py`. GitHub Actions: **Update 2026 Data** or **Scrape CCN Data** (full archive).

The CSV is written as **UTF-8 with BOM** (`utf-8-sig`) so Excel displays non-English characters correctly. Text fields pass through `repair_mojibake()` to fix UTF-8 bytes mis-read as Latin-1 during scraping.

### Build artifacts vs runtime

| File | Used by dashboard? |
|------|-------------------|
| `docs/data/abstracts.csv` | **Yes** — sole runtime data source |
| `data/submissions.json`, `docs/data/submissions.json` | No — intermediate build artifact |
| `embeddings_all.json` | No — UMAP coords are copied into the CSV |
| `google_topics.json` | No — optional theme-name override at build time only |

---

## Data source

The dashboard loads **only** `data/abstracts.csv`. No JSON or API calls at runtime.

### Core columns

| Column | Meaning |
|--------|---------|
| `year` | Conference year |
| `title` | Submission title |
| `author` | First author |
| `keywords` | Cleaned content keywords (metadata area labels and citation fragments removed) |
| `assigned_topics` | One or more of the **12 CCN research themes**, pipe-separated (` \| `), **ordered by importance** (primary first) |

### Additional columns (precomputed at build time)

| Column | Meaning |
|--------|---------|
| `id` | Stable row identifier |
| `authors` | Full author list |
| `abstract` | Full abstract text (search only) |
| `umap_x`, `umap_y` | 2D map coordinates (weighted TF-IDF + UMAP; see IMPLEMENTATION.md) |
| `source_url` | Link to poster / PDF |
| `poster_number` | Poster number when available |

List-valued fields use ` | ` as the delimiter.

## The 12 research themes

Topics in `assigned_topics` are drawn from this fixed list ([CCN 2026 Activity Preferences](https://docs.google.com/forms/d/1c-ZR7PkUNDVeRmncAK2nmdKA5ZwuZ8opTr8Brl-WOJI/viewform), question 1):

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

Theme names and colors in the UI are defined in `docs/js/app.js`. To change names at build time, edit `data/google_topics.json` and re-run `assign_research_themes.py`.

## Filters

- **Year** — all years or a single conference year (header dropdown + year chips)  
- **Research theme** — header dropdown lists all 12 themes; matches any value in `assigned_topics`  
- **Search** — title, author(s), abstract, keywords, assigned topics  
- **Embedding map topic dropdown** — same theme filter, scoped to the map panel; default shows all topics with dots colored by **primary** topic only  

## Charts & panels

| Panel | What it uses from the CSV |
|-------|---------------------------|
| KPI summary | Row count, year span, theme count |
| Submissions over time | `year` |
| Research theme ranking | `assigned_topics` (multi-label counts in current filter) |
| Year-over-year change | `assigned_topics` share between two selected years (ignores year filter) |
| Embedding map | `umap_x`, `umap_y`, `assigned_topics` — dot color = primary topic; click/tap to jump to paper list |
| Matching submissions | `title`, `author`, `authors`, `year`, `assigned_topics`, `source_url` |

## Local preview

```bash
pip install -r scripts/requirements.txt
python -m http.server 8080 --directory docs
```

Open http://localhost:8080

Further implementation detail: [IMPLEMENTATION.md](IMPLEMENTATION.md)
