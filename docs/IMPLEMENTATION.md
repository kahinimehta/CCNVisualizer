# How the visualizer works

## Runtime

```
docs/data/abstracts.csv  →  docs/js/app.js (d3.csv)  →  dashboard
```

The browser loads **one file**: `abstracts.csv`. The 12 research theme names and colors are hardcoded in `app.js` as `GOOGLE_FORM_TOPICS`. No JSON, no live API calls.

---

## End-to-end workflow

```
ccneuro.org archives
        │
        ▼  scrape.py
        │
  submissions.json          data/submissions.json + docs/data/submissions.json
        │
        ▼  build.py
        │
        ├── ThemeScorer: TF-IDF cosine → assigned_topics on each row
        ├── UMAP projection → embeddings_all.json
        └── CSV export → abstracts.csv
        │
        ▼
  docs/data/abstracts.csv  →  dashboard
```

| Stage | Script | Output |
|-------|--------|--------|
| Scrape | `scrape.py` | `submissions.json` — titles, abstracts, authors, keywords |
| 2026 merge | `scrape.py --merge-2026` or `build.py --merge-2026` | Replaces 2026 rows from `ccn-2026-pending-posters.csv` |
| Keyword refresh | `scrape.py --refresh-keywords` | Author keywords from PDFs when HTML lacks them |
| Themes + map + CSV | `build.py` | Updated JSON, `embeddings_all.json`, `abstracts.csv` |
| Dashboard | `docs/js/app.js` | Reads CSV only |

### Script inventory

| Script | Purpose |
|--------|---------|
| `scrape.py` | **Step 1** — scrape CCN archives, merge 2026 CSV, refresh keywords; writes `submissions.json` |
| `build.py` | **Step 2** — theme assignment, UMAP coordinates, CSV export |

Both scripts are self-contained (shared helpers are inlined). Optional flags:

- `scrape.py --merge-2026` — merge provisional 2026 poster CSV
- `scrape.py --refresh-keywords` — re-extract keywords from HTML/PDF on existing JSON
- `scrape.py --add-2017` — re-scrape 2017 proceedings and merge
- `build.py --merge-2026` — merge 2026 CSV before building (for 2026-only updates)

Shared config: **`data/google_topics.json`** — optional override for the 12 theme names at build time (defaults to anchors in `build.py`).

CI workflows (`.github/workflows/`): **Update 2026 Data**, **Scrape CCN Data**, **Deploy GitHub Pages**.

---

## Clustering algorithm

The pipeline uses one shared text representation for both **theme assignment** and **UMAP map coordinates**. There is no separate cluster label in the CSV — only the 12 research themes and 2D coordinates.

### 1. Text preparation

Before any vectorization, each submission is cleaned:

- **Mojibake repair** — UTF-8 bytes mis-read as Latin-1 are fixed (`repair_mojibake()` in `build.py`).
- **Keyword sanitization** — citation fragments removed (`et al.`, `p. 12`, DOIs, URLs); conference metadata labels dropped (`psychological / behavioral research`, `fmri`, `eeg`, etc.).
- **Weighted document** — fields are concatenated with explicit weights so abstract content dominates noisy keywords:

  | Field | Weight |
  |-------|--------|
  | Title | ×2 |
  | Abstract | ×3 |
  | Cleaned content keywords | ×1 |

  Metadata area labels never enter the embedding text. Method tokens like `fmri`/`eeg` are stripped from keyword fields but can still appear naturally in abstracts.

Implementation: `submission_embedding_text()` in `build.py`.

### 2. TF-IDF vectorization

Both theme scoring and UMAP use scikit-learn `TfidfVectorizer`:

- **Features:** up to 8,000 (UMAP) / 10,000 (theme scorer) unigrams and bigrams
- **Stop words:** English + metadata token stoplist (`fmri`, `eeg`, `cognitive`, …)
- **Filters:** `min_df=2`, `max_df=0.95`, `sublinear_tf=True`

Each submission becomes a sparse TF-IDF vector in a vocabulary learned from the full corpus (~2,967 submissions).

### 3. Theme assignment (cosine similarity to prototypes)

Themes are **not** discovered by clustering submissions. Each of the 12 CCN research themes has a **prototype anchor document** built from curated terms in `TOPIC_ANCHORS` (e.g. Vision: `visual`, `conscious vision`, `retinotopic`; Clinical: `schizophrenia`, `depression`, …).

`ThemeScorer` in `build.py`:

1. Builds TF-IDF vectors for all submissions **and** all 12 prototype documents in one fit.
2. L2-normalizes vectors so dot product = **cosine similarity**.
3. Scores each submission against every prototype; highest similarity → primary topic.

**Multi-label assignment:**

- Keep all themes with similarity ≥ `max_score × 0.5` (absolute floor **0.05**)
- Cap at **5** topics per submission
- Primary topic is always first in `assigned_topics`

**Overrides and soft boosts:**

1. **Official CCN label** — specific conference topic/track strings map directly to a theme (broad labels like `psychological / behavioral research` do *not* force a primary; they only nudge scores by +0.04).
2. **Broad area hints** — coarse archive labels nudge several themes without overriding title/abstract signal.

**LLM vs Methods split:** the theme **LLMs, reasoning, interpretability** uses a strict anchor set (transformer, GPT, prompting, RLHF, chain-of-thought, in-context learning, …). General interpretability / RNN / symbolic-reasoning terms anchor **Methods, theory & everything else**.

### 4. UMAP map coordinates

After themes are assigned, `build.py` projects every submission into 2D for the dashboard map:

1. Same weighted TF-IDF text as above (via `submission_embedding_text`).
2. **UMAP** (`umap-learn`) with:
   - `n_neighbors=15`, `min_dist=0.12`
   - `metric=cosine`
   - `random_state=42` (reproducible layout)
3. Output: `{ id, x, y, year, title, poster_number }` per point in `embeddings_all.json`.

These `x`/`y` values are copied into `abstracts.csv` as `umap_x` and `umap_y`. The map shows **semantic neighborhoods** — papers with similar title/abstract language land near each other — independent of the 12 theme labels.

### 5. CSV export

`build.py` joins:

- Core fields from `submissions.json` (title, author, keywords, `assigned_topics`, …)
- UMAP coordinates from `embeddings_all.json`
- Mojibake-repaired text, UTF-8 BOM encoding for Excel

The dashboard never reads `submissions.json` or `embeddings_all.json` at runtime.

---

## CSV schema

**Core fields:** `year`, `title`, `author`, `keywords`, `assigned_topics`

**Support fields:** `id`, `authors`, `abstract`, `umap_x`, `umap_y`, `source_url`, `poster_number`

List-valued fields use ` | ` as the delimiter. Topics in `assigned_topics` are ordered by importance (primary first).

## Keyword column

`keywords` in the CSV stores **cleaned content keywords**:

1. `author_keywords` when present (HTML, PDF, or substantive author text)
2. otherwise `extracted_keywords` (title/abstract token fallback)
3. otherwise legacy `keywords` on the submission record

Citation fragments and metadata area labels are stripped before export.

## Embedding map (UI)

- Coordinates from `umap_x` / `umap_y` in the CSV (all years, 2017–2026)
- Dot **color** = primary topic (`assigned_topics[0]`)
- Click/tap a dot → scrolls to that submission in **Matching submissions** and shows **all** assigned topics (primary labeled)
- Map topic dropdown lists all 12 themes; filter matches any assigned topic; non-matches are dimmed
- Legend: “Primary topic (dot color)”
- Map respects year / search / topic filters

## Frontend notes

- Theme colors index into `GOOGLE_FORM_TOPICS` in `app.js`
- Year-over-year theme chart ignores the year filter so cross-year trends stay visible
- Header theme dropdown and map topic dropdown stay in sync
- KPI row shows total submissions, filtered count, theme count, and year span

## Python dependencies

Build pipeline only (not loaded by the static dashboard):

| Step | Packages |
|------|----------|
| `scrape.py` | `requests`, `beautifulsoup4`, `lxml`, `pypdf` |
| `build.py` | `numpy`, `scikit-learn`, `umap-learn` |

Install for both steps: `pip install requests beautifulsoup4 lxml pypdf numpy scikit-learn umap-learn`
