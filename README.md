# CCN Visualizer

Interactive dashboard for [Cognitive Computational Neuroscience (CCN)](https://ccneuro.org) poster and paper archives (2017–2026).

**Live:** https://ccn-visualizer.vercel.app/

## Quick start

```bash
pip install -r requirements.txt
cp .env.example .env   # ANTHROPIC_API_KEY (never commit)
python scripts/scrape.py
python scripts/build.py
python -m http.server 8080 --directory docs
```

Keyword/text cleanup only (no LLM or UMAP):

```bash
python scripts/build.py --repair-only
```

## Docs

**[docs/GUIDE.md](docs/GUIDE.md)** — pipeline and maintenance (linked from the live site footer).

**[THIRD_PARTY_LICENSES.md](THIRD_PARTY_LICENSES.md)** · [licenses on site](https://ccn-visualizer.vercel.app/licenses.html)

## Deploy

Pushes to `main` deploy the static `docs/` folder on Vercel. Rebuild and commit `docs/data/abstracts_2_topics.csv` after scrape/build runs; see the guide.
