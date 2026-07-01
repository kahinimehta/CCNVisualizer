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
3. **`assign_research_themes.py`** — TF-IDF cosine similarity to topic prototype anchors; relevance-threshold multi-label assignment; also rebuilds UMAP + CSV.  
4. **`build_all_embeddings.py`** — weighted TF-IDF (title ×2, abstract ×3, cleaned keywords ×1) + UMAP 2D; metadata keywords excluded.  
5. **`build_abstracts_csv.py`** — exports the dashboard CSV with core columns plus precomputed map coords and links.

Shared helpers live in **`topic_features.py`** (metadata keyword stoplist, citation cleanup, anchor sets) and **`text_encoding.py`** (UTF-8 mojibake repair).

## CSV schema

**Core fields (what defines each submission for analysis):**

- `year`, `title`, `author`, `keywords`, `assigned_topics`

**Support fields (precomputed for the UI):**

- `id`, `authors`, `abstract`, `umap_x`, `umap_y`, `source_url`, `poster_number`

List-valued fields use ` | ` as the delimiter. Topics in `assigned_topics` are ordered by importance.

## Keyword column

`keywords` in the CSV stores **cleaned content keywords** (citation fragments and conference metadata area labels removed):

1. `author_keywords` when present (HTML, PDF, or substantive author text)  
2. otherwise `extracted_keywords` (title/abstract token fallback)  
3. otherwise legacy `keywords` on the submission record  

## Theme assignment

`topic_features.py` defines prototype anchor sets per theme. Scoring uses **weighted TF-IDF cosine similarity**:

- **Input text:** title ×2, abstract ×3, cleaned keywords ×1  
- **Excluded:** metadata area labels (`psychological / behavioral research`, `fmri`, `eeg`, etc.) and citation fragments (`et al.`, `p.`, DOIs)

Priority when building `assigned_topics`:

1. Official CCN topic/track label → mapped Google Form theme (specific labels only)  
2. Cosine similarity to topic prototypes — primary = highest score  
3. **Multi-label threshold:** keep topics scoring ≥ `max_score × 0.5` (floor 0.05), capped at 5  
4. Optional soft boost from 2026 Gemma embedding cluster

**LLMs, reasoning, interpretability** uses a strict LLM-specific anchor set (transformer, GPT, prompting, RLHF, chain-of-thought, etc.). General interpretability / RNN / symbolic-reasoning terms anchor **Methods, theory & everything else**.

There is no separate cluster label in the CSV — only the 12 research themes.

## Embedding map

- Coordinates come from `umap_x` / `umap_y` in the CSV (same weighted TF-IDF input as theme scoring, metadata keywords excluded)  
- Map respects the same year / search / topic filters as the paper list  
