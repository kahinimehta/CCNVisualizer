# Implementation Reference

Technical documentation for all data sources, preprocessing pipelines, label assignment, and how each dashboard visualization is built.

**Related docs:** [DASHBOARD.md](DASHBOARD.md) (user guide) · [README.md](../README.md) (setup & updates)

---

## Architecture overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│  OFFLINE (Python scripts, run locally or via GitHub Actions)            │
├─────────────────────────────────────────────────────────────────────────┤
│  scrape_ccn.py          → 2018–2025 HTML archives (static, one-time)    │
│  merge_2026_csv.py      → 2026 pending posters CSV (routine updates)    │
│  ccn_abstract_clustering.ipynb → Gemma embeddings (scripts/ccn_embeddings.npy) │
│  build_cluster_viz.py   → UMAP coords + KMeans clusters                 │
│  assign_research_themes.py → primary_theme + secondary_topics on all rows │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  STATIC JSON (served from docs/data/)                                    │
│  submissions.json · embeddings_2026.json · google_topics.json           │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  BROWSER (docs/js/app.js)                                               │
│  fetch JSON → filter state → D3.js / d3-cloud render functions          │
└─────────────────────────────────────────────────────────────────────────┘
```

The dashboard is a **static site** — no backend API at runtime. All computation happens in Python during data prep; the browser only aggregates and draws precomputed fields.

---

## External services & libraries

### Runtime (browser)

| Resource | Version | URL | Used for |
|----------|---------|-----|----------|
| D3.js | 7.9.0 | `https://cdn.jsdelivr.net/npm/d3@7.9.0/dist/d3.min.js` | All charts, axes, scales, SVG rendering |
| d3-cloud | 1.2.7 | `https://cdn.jsdelivr.net/npm/d3-cloud@1.2.7/build/d3.layout.cloud.min.js` | Secondary topics word cloud layout |
| Open Sans | — | Google Fonts | UI typography |
| `fetch()` | — | Same-origin | Loads `docs/data/*.json` at page init |

No Google Forms API is called at runtime. The form link is reference-only for theme names.

### Offline (Python scraper / pipeline)

| Library | Role |
|---------|------|
| `requests` | HTTP GET to CCN archive sites |
| `beautifulsoup4` + `lxml` | HTML parsing |
| `numpy` | Embedding arrays |
| `scikit-learn` (`KMeans`) | 10-cluster assignment on 2026 abstracts |
| `umap-learn` (`UMAP`) | Dimensionality reduction (5D for clustering, 2D for map) |

### Embedding model (notebook only)

| Model | Source | Output |
|-------|--------|--------|
| `BAAI/bge-multilingual-gemma2` | Hugging Face / SentenceTransformers | `scripts/ccn_embeddings.npy` — shape `(617, 3584)` |

Embeddings are computed once in `scripts/ccn_abstract_clustering.ipynb` and cached to `ccn_embeddings.npy`. `build_cluster_viz.py` reads this file; it does not call Hugging Face at build time unless the notebook is re-run.

---

## Data sources

### 1. CCN conference archives (2018–2025) — static

Scraped via `scripts/scrape_ccn.py` using `requests` + BeautifulSoup. No official CCN API.

| Years | Site pattern | Listing page | Detail parsing |
|-------|--------------|--------------|----------------|
| 2018, 2019 | `https://{year}.ccneuro.org/` | `Papers/AcceptedPapers.html` | Legacy HTML (`ViewPaper` links, `PaperNum=` IDs) |
| 2022, 2023 | `https://{year}.ccneuro.org/` | `accepted_papers.html` | Legacy HTML (`view_paper` links) |
| 2024, 2025 | `https://{year}.ccneuro.org/` | MeetingTrakr poster listing | `/poster/?id=` detail pages |

**Note:** 2020 and 2021 are not in the archive config (no data for those years).

**Fields extracted per submission:**

| Field | Source | Notes |
|-------|--------|-------|
| `id` | Paper/poster ID from URL | e.g. `"1084"` (2018) or MeetingTrakr poster ID |
| `year` | Scrape config | 2018, 2019, 2022, 2023, 2024, 2025 |
| `title` | Listing or detail page | Required |
| `authors` | Detail page | Semicolon-separated affiliations when available |
| `abstract` | Detail page | Full text when published |
| `keywords` | Explicit field + derived | Merged from archive keywords and `derive_keywords()` (title/abstract tokens) |
| `topic_area` | MeetingTrakr topic column or legacy track | Lowercased first segment |
| `track` | Legacy session track name | Often empty for MeetingTrakr years |
| `poster_number` | MeetingTrakr listing column | Empty for legacy years |
| `source_url` | Constructed detail URL | Provenance link |
| `submission_type` | Hardcoded | `"poster"` for all scraped rows |

**Keyword derivation** (`derive_keywords`): tokenizes title and abstract (English stopwords removed), takes top title tokens + most common abstract terms, merges with explicit keywords. Noise terms (city names, month names, `"ccn"`, etc.) are filtered via `NOISE_KEYWORDS`.

### 2. CCN 2026 pending posters — routine updates

**File:** `data/ccn-2026-pending-posters.csv`

**Merged by:** `scripts/merge_2026_csv.py` (replaces all `year === 2026` rows in `submissions.json`)

| CSV column | Maps to | Notes |
|------------|---------|-------|
| `or_number` | `poster_number`, `id` prefix | `id` = `2026-{or_number}` |
| `title` | `title` | |
| `abstract` | `abstract` | |
| `primary_area` | `topic_area` (first segment, lowercased) | CCN topic taxonomy from CSV |
| `secondary_area` | Used in topic normalization only | Split on `+`, `;`, `,` |
| `track` | `track` | e.g. `Extended_Abstracts` |
| `status` | Not stored on submission | Used in embedding JSON only |

Authors are empty for 2026 CSV rows. Keywords are derived from title/abstract/topic_area.

### 3. Google Form — theme taxonomy only

**Link:** [CCN 2026 Activity Preferences](https://docs.google.com/forms/d/1c-ZR7PkUNDVeRmncAK2nmdKA5ZwuZ8opTr8Brl-WOJI/viewform)

**File:** `data/google_topics.json` / `docs/data/google_topics.json`

The 12 strings in `topics` were copied manually from form question 1 (*"Which topic would you best affiliate yourself with for lower Manhattan meetups?"*). No form responses or analytics are ingested.

---

## Output data files

### `submissions.json`

**Path:** `data/submissions.json` and `docs/data/submissions.json` (identical copies)

```json
{
  "metadata": { "years", "total_count", "scraped_at", "source", "csv_2026", "research_theme_method", ... },
  "submissions": [ { "id", "year", "title", "authors", "abstract", "keywords", "topic_area",
                     "primary_theme", "secondary_topics", ... } ],
  "stats": { "counts_by_year", "overall_top", "by_year", "topics_by_year", "cooccurrence",
             "research_themes" }
}
```

| Field | Produced by | Description |
|-------|-------------|-------------|
| `primary_theme` | `assign_research_themes.py` | One of 12 Google Form topics |
| `secondary_topics` | `assign_research_themes.py` | Up to 3 strings: embedding cluster name + runner-up themes |
| `stats.counts_by_year` | `scrape_ccn.py` / `merge_2026_csv.py` | Submission count per year — used by year line chart |
| `stats.research_themes` | `assign_research_themes.py` | Precomputed theme aggregates (not used directly by frontend) |

### `embeddings_2026.json`

**Produced by:** `scripts/build_cluster_viz.py`

```json
{
  "metadata": { "count", "n_clusters", "method", "embeddings_source", "csv_source" },
  "clusters": [ { "id", "name", "count" } ],
  "points": [ { "id", "x", "y", "cluster", "cluster_name", "title", "primary_area",
                "secondary_area", "poster_number", "status" } ]
}
```

| Field | How obtained |
|-------|--------------|
| `x`, `y` | UMAP 2D projection of `ccn_embeddings.npy` (cosine metric, 15 neighbors, min_dist 0.15) |
| `cluster`, `cluster_name` | KMeans (k=10) on 5D UMAP reduction of same embeddings |
| `cluster_name` labels | Hardcoded map in `build_cluster_viz.py` `CLUSTER_NAMES` — originally from collaborator notebook (Claude-assisted naming of BERTopic clusters) |

**Cluster name → Google theme** mapping lives in `google_topics.json` → `embedding_cluster_map`.

### `google_topics.json`

Schema version 3. See [DASHBOARD.md](DASHBOARD.md#google_topicsjson-schema).

---

## Theme assignment algorithm

**Script:** `scripts/assign_research_themes.py`  
**Runs on:** Every submission in `submissions.json`

### Step 1 — Build keyword profiles per Google theme

For each of the 12 themes, accumulate token weights from:

1. **Hand-tuned `TOPIC_KEYWORDS`** — domain terms per theme (weight ×4 per token)
2. **2026 embedding points** — for each point, tokens from `primary_area` (×3), `secondary_area` (×2), `title` (×1), attributed to the Google theme mapped from that point's `cluster_name`

### Step 2 — Score each submission

Tokenize `title + abstract + topic_area + keywords`. For each theme, sum profile weights for matching tokens; add +2 per token that appears in the theme name itself.

### Step 3 — Assign primary theme

| Condition | Primary theme |
|-----------|---------------|
| 2026 submission with known embedding cluster in `embedding_cluster_map` | Mapped Google topic |
| Otherwise | Highest-scoring theme; if score ≤ 0 → `"Methods, theory & everything else"` |

### Step 4 — Assign secondary topics (up to 3)

1. Include raw embedding cluster name if present and different from primary
2. Add other themes scoring ≥ 35% of primary score, ranked by score

Pre-2026 papers never have embedding clusters; they rely entirely on text scoring.

---

## Embedding pipeline (2026 only)

```
ccn-2026-pending-posters.csv
        │
        ▼
ccn_abstract_clustering.ipynb
  · SentenceTransformer("BAAI/bge-multilingual-gemma2")
  · encode(abstracts) → ccn_embeddings.npy  [617 × 3584]
        │
        ▼
build_cluster_viz.py
  · UMAP(5D, cosine) → KMeans(k=10) → cluster IDs
  · UMAP(2D, cosine) → scatter coordinates
  · Attach CLUSTER_NAMES + CSV metadata per point
        │
        ▼
embeddings_2026.json
```

When the 2026 CSV changes, embeddings must be regenerated in the notebook (new abstracts → new `ccn_embeddings.npy`) before running `build_cluster_viz.py`.

---

## Frontend initialization

**File:** `docs/js/app.js` → `init()`

```javascript
Promise.all([
  fetch("data/submissions.json"),           // required
  fetch("data/embeddings_2026.json"),       // optional
  fetch("data/google_topics.json"),         // optional
])
```

On load:

1. `state.data`, `state.embeddings`, `state.googleTopics` populated
2. `buildThemeClassifier()` — builds in-browser token profiles (fallback if `primary_theme` missing)
3. `renderAll()` — draws every chart from filtered data

### Global filter state

| State key | UI control | Effect |
|-----------|------------|--------|
| `selectedYear` | Year dropdown + chip buttons | Filters submissions by `year`; highlights year on line chart |
| `selectedTheme` | Theme dropdown + chart clicks | Filters submissions where `primary_theme` matches |
| `search` | Search input | Substring match on title, authors, primary/secondary themes, topic_area |

`filteredSubmissions()` applies all three. Most charts use filtered data; the year line chart uses global `stats.counts_by_year` (unfiltered totals).

---

## Visualizations

### KPI cards (`#kpi-row`)

| KPI | Data | Algorithm |
|-----|------|-----------|
| Total submissions | `metadata.total_count` | Static from JSON |
| Matching filter | `filteredSubmissions().length` | Count after filters |
| Research themes | `google_topics.topics.length` | Always 12 when form config loaded |
| Years covered | `metadata.years.length` | Count of distinct years |

**Library:** D3 selection join on `.kpi-card` divs (no SVG chart).

---

### Submissions over time (`#year-chart`)

| Input | `state.data.stats.counts_by_year` |
| Algorithm | D3 `scalePoint` × `scaleLinear`; `d3.line` with `curveMonotoneX`; circles per year |
| Labels | X: conference year; Y: submission count |
| Interaction | Click circle → set year filter |

**Note:** Uses archive-wide counts, not filtered submission list.

---

### Research theme ranking (`#theme-bars`)

| Input | `primaryThemeCounts(filteredSubmissions())` |
| Algorithm | Horizontal bar chart — `scaleBand` + `scaleLinear` |
| Labels | Y: full `primary_theme` string; bar width: count |
| Label source | `submission.primary_theme` from Python assignment |
| Interaction | Click bar → theme filter |

---

### Research themes over time (`#themes-over-time-chart`)

| Input | Filtered submissions; `researchThemeNames()` for theme list; `metadata.years` for X axis |
| Algorithm | Per theme: annual counts by year + running cumulative sum; two `d3.line` paths per theme (solid = annual, dashed = cumulative) |
| Labels | X: year; Y: count; legend: 12 Google Form theme names |
| Colors | `d3.scaleOrdinal(CHART_PALETTE)` |

---

### Total by research theme (`#theme-totals-chart`)

| Input | `themeTotals(filteredSubmissions())` — all years in current filter |
| Algorithm | Horizontal bars, sorted descending by count |
| Labels | Full theme names |

---

### Year-over-year change (`#theme-delta-chart`)

| Input | `researchThemeDeltas(filteredSubmissions())` |
| Algorithm | Finds latest consecutive year pair with any theme data; `delta = count(toYear) - count(fromYear)` per theme; bars sorted by `|delta|` |
| Labels | Subtitle shows e.g. `2025 → 2026`; bar color green if Δ≥0, pink if Δ<0 |
| Interaction | Tooltip shows from-count, to-count, delta |

---

### Abstract embedding map (`#embedding-chart`)

| Input | `embeddings_2026.json` → `points[]` |
| Algorithm | D3 scatter: `scaleLinear` on UMAP `x`,`y`; circles colored by `mapClusterToTheme(cluster_name)` |
| Point labels (tooltip) | `title`, `poster_number`, mapped primary theme, embedding cluster name, `primary_area` from CSV |
| Legend labels | Unique Google primary themes present in 2026 data |
| Color | `CHART_PALETTE` ordinal scale by Google theme |
| Opacity | Dimmed to 0.18 when a theme filter is active and point doesn't match |
| Interaction | Click point or legend → theme filter |

**Mapping:** `mapClusterToTheme()` looks up `cluster_name` in `google_topics.embedding_cluster_map`; falls back to raw cluster name if unmapped.

---

### Matching submissions (`#paper-list`)

| Input | `filteredSubmissions()` sorted by year desc, then title |
| Algorithm | D3 HTML join — no chart |
| Labels shown | Title (link to `source_url` if set), authors, year, poster #, primary theme tag, secondary topic tags |
| Interaction | Theme tags reflect active filter; "Clear theme filter" button when `selectedTheme` set |

---

### Primary research themes donut (`#topic-chart`)

| Input | `primaryThemeDistribution(filteredSubmissions())` |
| Algorithm | `d3.pie` + `d3.arc` (donut, inner radius 52%); percentage labels on slices > 8% |
| Labels | Arc = `primary_theme`; tooltip shows count and % |
| Interaction | Click slice → theme filter |

---

### Secondary topics cloud (`#word-cloud`)

| Input | `secondaryTopicCounts(filteredSubmissions())` — top 40 by frequency |
| Algorithm | `d3.layout.cloud()` — font size scaled 12–44px by count; random 0°/90° rotation |
| Labels | Raw strings from `submission.secondary_topics[]` |
| Label sources | Embedding cluster names + runner-up Google themes from Python assignment |
| Interaction | Tooltip only (not a filter) |

---

### Research theme breakdown (`#cluster-bars-chart`)

| Input | All 12 themes from `researchThemeNames()`, counts from filtered submissions |
| Algorithm | Horizontal bars; includes themes with zero count |
| Labels | Truncated theme names (22 chars) on Y axis |
| Interaction | Click bar → theme filter |

Functionally similar to ranking chart but shows full theme list including zeros.

---

## Label provenance summary

| Label type | Where it comes from | Used in |
|------------|---------------------|---------|
| **Google Form primary themes** (12) | Manually copied from [form Q1](https://docs.google.com/forms/d/1c-ZR7PkUNDVeRmncAK2nmdKA5ZwuZ8opTr8Brl-WOJI/viewform) → `google_topics.json` | All theme charts, filters, dropdown |
| **Embedding cluster names** (10) | KMeans on 2026 abstracts; names from collaborator notebook / `CLUSTER_NAMES` dict | UMAP tooltips, `secondary_topics`, cluster→theme map |
| **CCN topic areas** (2026 CSV) | `primary_area`, `secondary_area` columns | Search, UMAP tooltips, profile building |
| **Archive topic areas** (2024–25) | MeetingTrakr listing column | Search, theme text scoring |
| **Derived keywords** | `scrape_ccn.py` tokenization | Search only; not used for theme charts |
| **Conference years** | Scrape config + CSV merge | Year filter, time series |

---

## What to re-run when data changes

| Change | Steps |
|--------|-------|
| New 2026 CSV | `merge_2026_csv.py` → re-encode in notebook if abstracts changed → `build_cluster_viz.py` → `assign_research_themes.py` |
| Google Form topic names change | Edit `google_topics.json` (both copies) → `assign_research_themes.py` |
| Re-scrape archives (rare) | `scrape_ccn.py` → `build_cluster_viz.py` → `assign_research_themes.py` |

GitHub Action **Update 2026 Data** automates the CSV merge + cluster + theme steps (assumes `ccn_embeddings.npy` is already current).

---

## Key source files

| File | Role |
|------|------|
| `scripts/scrape_ccn.py` | Archive HTML scraper |
| `scripts/merge_2026_csv.py` | 2026 CSV merge |
| `scripts/build_cluster_viz.py` | UMAP + KMeans export |
| `scripts/assign_research_themes.py` | Theme classification |
| `scripts/ccn_abstract_clustering.ipynb` | Gemma embedding generation |
| `scripts/ccn_embeddings.npy` | Cached 617×3584 embedding matrix |
| `docs/js/app.js` | All visualization logic |
| `docs/index.html` | Chart containers + CDN script tags |
