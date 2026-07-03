# CCN Visualizer

Interactive dashboard for [Cognitive Computational Neuroscience (CCN)](https://ccneuro.org) poster and paper archives (2017–2026).

**Live site:** https://ccn-visualizer.vercel.app/

## Quick start

```bash
pip install -r requirements.txt
cp .env.example .env   # set ANTHROPIC_API_KEY (never commit .env)
python scripts/scrape.py --merge-2026
python scripts/build.py
python -m http.server 8080 --directory docs
```

Open http://localhost:8080

## Documentation

All pipeline, data, theme, and build details are in one place:

**[docs/GUIDE.md](docs/GUIDE.md)** · [on the live site](https://ccn-visualizer.vercel.app/GUIDE.md)

Licenses: [THIRD_PARTY_LICENSES.md](THIRD_PARTY_LICENSES.md)

## Deploy

Pushes to `main` deploy the static `docs/` folder (Vercel). Data rebuilds run separately — locally or via GitHub Actions with the `ANTHROPIC_API_KEY` repository secret.
