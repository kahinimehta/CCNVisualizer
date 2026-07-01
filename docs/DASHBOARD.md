# CCN Submission Visualizer

Interactive exploration of CCN poster and paper archives (2017–2026).

## Data source

The dashboard loads **only** `data/abstracts.csv`. No other JSON or API calls are required at runtime.

### Core columns

| Column | Meaning |
|--------|---------|
| `year` | Conference year |
| `title` | Submission title |
| `author` | First author |
| `keywords` | Keywords from the extraction pipeline (`extracted_keywords` when available; author keywords as fallback) |
| `assigned_topics` | One or more of the **12 CCN research themes**, pipe-separated (` \| `), **ordered by importance** (best match first) |

### Additional columns (precomputed at build time)

These are written into the same CSV so the UI can link, search, and plot without extra files:

| Column | Meaning |
|--------|---------|
| `id` | Stable row identifier |
| `authors` | Full author list |
| `abstract` | Full abstract text (search only) |
| `umap_x`, `umap_y` | 2D map coordinates (TF-IDF + UMAP on title + abstract) |
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
- **Embedding map** — shows filtered rows; pie-slice dots encode every assigned topic  

## Charts

| Panel | What it uses from the CSV |
|-------|---------------------------|
| Theme ranking / year-over-year change | `assigned_topics` (multi-label counts) |
| Embedding map | `umap_x`, `umap_y`, `assigned_topics` |
| Paper list | `title`, `author`, `authors`, `year`, `assigned_topics`, `source_url` |

## Rebuilding `abstracts.csv`

Pipeline scripts produce `submissions.json`; the CSV export is the dashboard artifact:

```bash
pip install -r scripts/requirements.txt
python scripts/scrape_ccn.py              # rebuild submissions.json
python scripts/backfill_pdf_keywords.py   # refresh keywords
python scripts/assign_research_themes.py  # themes + UMAP + abstracts.csv
```

`assign_research_themes.py` runs theme assignment, rebuilds `embeddings_all.json`, and writes both copies of `abstracts.csv`. You can also run `build_all_embeddings.py` or `build_abstracts_csv.py` individually.
