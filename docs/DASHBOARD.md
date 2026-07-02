# CCN Submission Visualizer

Interactive exploration of CCN poster and paper archives (2017–2026).

## How data gets here

The dashboard never talks to ccneuro.org directly. Everything is precomputed offline and shipped as one CSV:

```
ccneuro.org archives
        │
        ▼  scrape.py
  submissions.json          ← raw archive: titles, abstracts, authors, keywords
        │
        ▼  build.py
  ┌─────────────────────────────────────┐
  │ 1. Clean keywords & repair encoding │
  │ 2. Assign 15 themes (Anthropic)     │
  │ 3. Build UMAP map (embeddings_all)  │
  │ 4. Export abstracts.csv             │
  └─────────────────────────────────────┘
        │
        ▼
  abstracts.csv  ──→  dashboard (docs/js/app.js)
```

**Step 1 — Scrape to JSON.** `scrape.py` pulls poster/paper records from CCN archives (2017–2026) into `data/submissions.json`. Keywords come from poster HTML, proceedings PDFs, or a token fallback. Citation fragments (`et al.`, page numbers, DOIs) and conference metadata labels are stripped at this stage.

**Step 2 — Themes, map, CSV.** `build.py` reads the JSON, classifies each submission with **Anthropic Claude** (primary + secondary themes), computes UMAP coordinates for the embedding map, writes topics back to `submissions.json`, saves 2D coordinates to `embeddings_all.json`, and exports `abstracts.csv`. See [IMPLEMENTATION.md](IMPLEMENTATION.md) for details.

**Step 3 — Dashboard.** The browser loads only `docs/data/abstracts.csv`. Map coordinates (`umap_x`, `umap_y`), assigned topics, and all display fields are already in that file.

### Rebuild commands

```bash
pip install -r requirements.txt
cp .env.example .env   # set ANTHROPIC_API_KEY
python scripts/scrape.py --merge-2026        # rebuild submissions.json
python scripts/scrape.py --refresh-keywords  # refresh keywords (optional)
python scripts/build.py                      # Anthropic themes + UMAP + abstracts.csv
```

`build.py` is the single command that regenerates themes, the embedding map, and both copies of the CSV. Use `--skip-classify` to rebuild UMAP/CSV without API calls (reuses existing topics in JSON).

For **2026-only updates**, replace `data/ccn-2026-pending-posters.csv` and run `python scripts/build.py --merge-2026`. GitHub Actions: **Update 2026 Data** or **Scrape CCN Data** (full archive). Both require the `ANTHROPIC_API_KEY` repository secret.

The CSV is written as **UTF-8 with BOM** (`utf-8-sig`) so Excel displays non-English characters correctly. Text fields pass through `repair_mojibake()` to fix UTF-8 bytes mis-read as Latin-1 during scraping.

### Build artifacts vs runtime

| File | Used by dashboard? |
|------|-------------------|
| `docs/data/abstracts.csv` | **Yes** — sole runtime data source |
| `data/submissions.json` | No — intermediate scrape/build artifact |
| `data/embeddings_all.json` | No — optional debug artifact; UMAP coords are in the CSV |
| `data/google_topics.json` | No — optional theme-name override at build time only |
| `data/llm_theme_cache.json` | No — Anthropic cache (gitignored) |

---

## Data source

The dashboard loads **only** `docs/data/abstracts.csv` (relative to the `docs/` site root). No JSON or API calls at runtime.

### Core columns

| Column | Meaning |
|--------|---------|
| `year` | Conference year |
| `title` | Submission title |
| `author` | First author |
| `keywords` | Cleaned content keywords (metadata area labels and citation fragments removed) |
| `assigned_topics` | One or more of the **15 CCN research themes**, pipe-separated (` \| `), **ordered by importance** (primary first) |

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

## The 15 research themes

Topics in `assigned_topics` are drawn from this fixed list ([CCN 2026 Activity Preferences](https://docs.google.com/forms/d/1c-ZR7PkUNDVeRmncAK2nmdKA5ZwuZ8opTr8Brl-WOJI/viewform), question 1):

1. Reinforcement learning  
2. Motor control & planning  
3. Naturalistic encoding/decoding  
4. Neural population geometry & dynamics  
5. Decision-making and metacognition  
6. Vision  
7. Perception  
8. Language/auditory neuroscience  
9. AI, LLM, & Neural Networks  
10. Memory  
11. Social cognition & theory of mind  
12. Attention & cognitive control / executive function  
13. Clinical / computational psychiatry  
14. Methods and theory  
15. Everything else  

Theme names and colors in the UI are defined in `docs/js/app.js`. To change names at build time, edit `data/google_topics.json` and re-run `build.py`.

## Filters

- **Year** — all years or a single conference year (header dropdown + year chips)  
- **Research theme** — header dropdown lists all 15 themes; matches any value in `assigned_topics`  
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
python -m http.server 8080 --directory docs
```

Open http://localhost:8080

Further implementation detail: [IMPLEMENTATION.md](IMPLEMENTATION.md)
