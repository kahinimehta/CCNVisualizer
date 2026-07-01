# CCN Submission Visualizer

Interactive exploration of CCN poster and paper archives (2018–2026).

## Data

The live dashboard reads **`data/abstracts.csv`** — one row per submission with:

| Column | Meaning |
|--------|---------|
| `title`, `first_author`, `year`, `authors` | Bibliographic fields |
| `author_keywords` | Keywords authors provided (or 2026 CSV research areas) |
| `extracted_keywords` | Algorithm tokens for 2018–2019 archives without author keyword fields |
| `abstract` | Full abstract text |
| `assigned_topics` | Research themes matched from keywords (multiple allowed, ` \| ` separated) |
| `umap_x`, `umap_y` | Map coordinates for 2026 |
| `cluster_track` | Embedding cluster label for 2026 audit (last column) |

## Filters

- **Year** — all years or a single conference year
- **Research theme** — matches any value in `assigned_topics` for that row
- **Search** — title, authors, abstract, keywords, topics, cluster track
- **Embedding map** — click a cluster track to filter 2026 submissions by `cluster_track`

## Charts

| Panel | What it counts |
|-------|----------------|
| Theme ranking / donut / over time | Each assigned topic separately (multi-tagged submissions count in every matching theme) |
| Word cloud | Frequency of assigned topics in the current filter |
| Embedding map | 2026 UMAP layout colored by `cluster_track` |
| Paper list | All assigned topics + cluster track when present |

## Updating data

```bash
pip install -r scripts/requirements.txt
python scripts/scrape_ccn.py          # rebuild JSON from ccneuro.org
python scripts/build_abstracts_csv.py # regenerate abstracts.csv from JSON
```

The scraper also writes `abstracts.csv` automatically after theme assignment.
