# CCN Visualizer

Interactive dashboard for [Cognitive Computational Neuroscience (CCN)](https://ccneuro.org) poster and paper archives (2017–2026).

**Live:** https://ccn-visualizer.vercel.app/

## Quick start

```bash
pip install -r requirements.txt
cp .env.example .env   # ANTHROPIC_API_KEY (never commit)
python scripts/scrape.py --merge-2026
python scripts/build.py
python -m http.server 8080 --directory docs
```

## Docs

**[docs/GUIDE.md](docs/GUIDE.md)** — pipeline, data, theme assignment, dashboard filters, CI workflows.

**[THIRD_PARTY_LICENSES.md](THIRD_PARTY_LICENSES.md)** · [licenses on site](https://ccn-visualizer.vercel.app/licenses.html)

## Deploy

Pushes to `main` deploy the static `docs/` folder on Vercel. Rebuild and commit `docs/data/abstracts.csv` locally or via GitHub Actions (`Update 2026 Data` / `Scrape CCN Data`); see the guide.
