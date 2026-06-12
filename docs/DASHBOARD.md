# Submission Visualizer — Dashboard Guide

Interactive dashboard for CCN poster and paper archives (2018–2026), styled with CCN brand colors (navy, pink, blue, green).

**Live site:** https://ccn-visualizer.vercel.app/

**Research themes source:** [CCN 2026 Activity Preferences](https://docs.google.com/forms/d/1c-ZR7PkUNDVeRmncAK2nmdKA5ZwuZ8opTr8Brl-WOJI/viewform) (Google Form question 1)

**Implementation reference:** [IMPLEMENTATION.md](IMPLEMENTATION.md) — data sources, preprocessing, and how each chart is built.

## What gets updated

| Input | Role | When it changes |
|-------|------|-----------------|
| [Google Form](https://docs.google.com/forms/d/1c-ZR7PkUNDVeRmncAK2nmdKA5ZwuZ8opTr8Brl-WOJI/viewform) | Defines the 12 primary research theme names | Only if CCN changes question 1 options — edit `google_topics.json` manually |
| `data/ccn-2026-pending-posters.csv` | 2026 poster titles, abstracts, topic areas | Whenever CCN releases an updated 2026 list |
| Archive scrape (`2018`–`2025`) | Historical submissions | Static — already captured in `submissions.json` |

No form response data, analytics exports, or per-respondent assignments are used.

---

## Core concept: research themes

Every submission is assigned:

| Field | Role |
|-------|------|
| `primary_theme` | One of **12 Google Form topics** — drives all charts, filters, dropdown, and counts |
| `secondary_topics` | Up to 3 additional tags — embedding cluster names or runner-up themes; shown in the secondary-topics cloud and paper metadata only |

Nothing in the dashboard filters on raw keywords or legacy topic areas. Those fields are kept in the data for search and provenance only.

### The 12 primary themes (Google Form Q1)

From [CCN 2026 Activity Preferences](https://docs.google.com/forms/d/1c-ZR7PkUNDVeRmncAK2nmdKA5ZwuZ8opTr8Brl-WOJI/viewform), question 1 — *"Which topic would you best affiliate yourself with for lower Manhattan meetups?"*

| # | Primary theme |
|---|---------------|
| 1 | RL, motor control & planning |
| 2 | Naturalistic encoding/decoding |
| 3 | Neural population geometry & dynamics |
| 4 | Decision-making and metacognition |
| 5 | Vision |
| 6 | Language/auditory neuroscience |
| 7 | LLMs, reasoning, interpretability |
| 8 | Memory |
| 9 | Social cognition & theory of mind |
| 10 | Attention & cognitive control / executive function |
| 11 | Clinical / computational psychiatry |
| 12 | Methods, theory & everything else |

### How themes are assigned

| Years | Method |
|-------|--------|
| **2026** | UMAP embedding cluster → mapped to Google topic via `embedding_cluster_map` |
| **2018–2025** | Text match (title, abstract, topic area, keywords) against keyword profiles built from 2026 data |

Embedding cluster names (e.g. `Reinforcement Learning`, `Visual Cortex Models`) from the collaborator notebook may appear as **secondary topics** when they differ from the mapped Google primary.

### Embedding cluster → Google topic map

| Embedding cluster (2026) | Google primary theme |
|--------------------------|----------------------|
| Reinforcement Learning | RL, motor control & planning |
| Naturalistic Brain Encoding | Naturalistic encoding/decoding |
| Neural Population Dynamics | Neural population geometry & dynamics |
| Decision and Metacognition | Decision-making and metacognition |
| Visual Cortex Models | Vision |
| Computer Vision Models | Vision |
| Language Neuroscience | Language/auditory neuroscience |
| LLMs and Reasoning | LLMs, reasoning, interpretability |
| Cognition and Memory Systems | Memory |
| Neural Network Theory | Methods, theory & everything else |

Clusters without a direct meetup topic (e.g. social cognition, clinical psychiatry) are reached via text scoring for pre-2026 papers.

---

## Layout & responsive design

The dashboard uses a **single-column stack** inside a centered container (`max-width: 1080px`). Cards are full-width so content reads top-to-bottom on any screen.

```
┌──────────────────────────────────────┐
│ Header · filters · KPIs · year chips │
├──────────────────────────────────────┤
│ Submissions over time                │
│ Research theme ranking               │
│ Research themes over time            │
│   ├─ Total by research theme         │
│   └─ Year-over-year change           │
│ Embedding block (stacked)            │
│   ├─ Abstract embedding map (UMAP)   │
│   ├─ Matching submissions            │
│   ├─ Primary themes (donut)          │
│   ├─ Secondary topics (cloud)        │
│   └─ Research theme breakdown (bars) │
└──────────────────────────────────────┘
```

The **Total by research theme** and **Year-over-year change** panels sit side by side inside the “Research themes over time” card on wider viewports; they stack on narrow screens.

| Breakpoint | Behavior |
|------------|----------|
| **Desktop (≥900px)** | 1080px centered column; 4 KPI cards in a row; filters in a grid |
| **Tablet (720–899px)** | 2×2 KPI grid; filters wrap |
| **Mobile (<700px)** | Single-column filters; 2-column KPIs; collapsible sidebar overlay |

Sidebar navigation (Visualizer · CCN page · Licenses) collapses to icons on narrow viewports.

---

## Filters

All visualizations respect the same filter state:

- **Year** — single year or all years (dropdown + chip buttons)
- **Research theme** — dropdown lists all 12 primary themes with counts in the current filter
- **Search** — title, authors, primary theme, secondary topics, topic area

Clicking a theme on any chart (ranking bars, donut, UMAP points/legend, theme breakdown bars) applies the same filter. A **Clear theme filter** pill appears in the submissions header.

---

## Components

| Component | Data source | Filterable? |
|-----------|-------------|-------------|
| Submissions over time | Count by `year` | Indirectly (year filter) |
| Research theme ranking | `primary_theme` counts | Click bar → theme filter |
| Research themes over time | `primary_theme` × year | Respects filters; solid = annual, dashed = cumulative |
| Total by research theme | `primary_theme` all-time totals | Respects filters |
| Year-over-year change | `primary_theme` delta (latest year pair) | Respects filters |
| Abstract embedding map | 2026 UMAP coords, colored by mapped Google topic | Click point/legend → theme filter |
| Matching submissions | Filtered list | Shows primary + secondary tags |
| Primary research themes | `primary_theme` share (donut) | Click slice → theme filter |
| Secondary topics | `secondary_topics` frequency | Informational only |
| Research theme breakdown | `primary_theme` bars | Click bar → theme filter |

---

## `google_topics.json` schema

Config at `data/google_topics.json` and `docs/data/google_topics.json` (dashboard reads `docs/data/`):

```json
{
  "schema_version": 3,
  "enabled": true,
  "source": "CCN 2026 Activity Preferences — Google Form question 1",
  "form_url": "https://docs.google.com/forms/d/1c-ZR7PkUNDVeRmncAK2nmdKA5ZwuZ8opTr8Brl-WOJI/viewform",
  "question": "Which topic would you best affiliate yourself with for lower Manhattan meetups?",
  "topics": [ "...12 topic strings from the form..." ],
  "embedding_cluster_map": { "Embedding Cluster Name": "Google topic" }
}
```

| Field | Purpose |
|-------|---------|
| `form_url` | Link to the Google Form — canonical source for theme names |
| `topics` | The 12 primary theme names (copied from form question 1) |
| `embedding_cluster_map` | Maps 2026 embedding cluster labels → Google topics |

Keep both copies in sync. After editing topics, re-run `python scripts/assign_research_themes.py`.

---

## Data pipeline

### Routine update (2026 CSV only)

```bash
pip install -r scripts/requirements.txt

python scripts/merge_2026_csv.py          # replace 2026 rows from CSV
python scripts/build_cluster_viz.py       # rebuild docs/data/embeddings_2026.json
python scripts/assign_research_themes.py  # re-assign primary_theme / secondary_topics
```

Or run the **Update 2026 Data** GitHub Action.

### Full rebuild (rare)

```bash
python scripts/scrape_ccn.py           # re-scrape 2018–2025 + merge 2026 CSV + assign themes
python scripts/build_cluster_viz.py
python scripts/assign_research_themes.py
```

The **Scrape CCN Data** GitHub Action runs the full rebuild path.

---

## Key files

| Path | Purpose |
|------|---------|
| `data/ccn-2026-pending-posters.csv` | **Primary input for updates** — replace when CCN publishes new 2026 data |
| `data/google_topics.json` | 12 themes from [Google Form Q1](https://docs.google.com/forms/d/1c-ZR7PkUNDVeRmncAK2nmdKA5ZwuZ8opTr8Brl-WOJI/viewform) |
| `docs/index.html` | Dashboard markup |
| `docs/js/app.js` | Charts, filters, theme logic |
| `docs/js/sidebar.js` | Sidebar collapse |
| `docs/css/style.css` | CCN styling + responsive layout |
| `docs/data/submissions.json` | All submissions with `primary_theme`, `secondary_topics` |
| `docs/data/embeddings_2026.json` | 2026 UMAP coordinates + embedding cluster labels |
| `docs/data/google_topics.json` | Google Form topic list and cluster map |
| `scripts/assign_research_themes.py` | Theme assignment for entire archive |
| `scripts/ccn_abstract_clustering.ipynb` | Collaborator embedding/clustering notebook |
