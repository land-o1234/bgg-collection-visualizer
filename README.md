# Board Game Collection Visualizer (Web App)

This is a static web app that visualizes your BoardGameGeek (BGG) collection as an interactive graph with search and a details sidebar.

- Frontend: Pure HTML/JS/CSS (no backend required at runtime)
- Data: Precomputed JSON (`data/nodes.json`, `data/edges.json`) built by a small Python script using the BGG XML API.

## Features
- Interactive graph (pan, zoom, drag)
- Click a game to see:
  - Mechanics, categories, rating, weight, players, playtime
  - Directly related games (graph neighbors) with similarity edge weights
- Search by game name (highlights and selects)

## Generate data (one-time or whenever your collection changes)

1) Install Python deps:
```
python -m venv .venv
. .venv/Scripts/activate  # Windows
# or: source .venv/bin/activate
pip install -r requirements.txt
```

2) Generate JSON for your username:
```
python src/generate_data.py --username InspiringChicken --edge-threshold 0.35 --out-dir data
```

This creates:
- `data/nodes.json`: games in your collection with their attributes
- `data/edges.json`: pairwise similarity edges above threshold

3) Open the web app:
- Double-click `static/index.html` to open in your browser, or serve it:
  - Python: `python -m http.server -d static 8000` then go to http://localhost:8000

## Deploy (GitHub Pages)
- Serve the `static/` folder at your GitHub Pages site and ensure `data/` is published alongside (e.g., at the repo root or a `docs/` folder).
- Optionally add a GitHub Action to rebuild data nightly and commit the updated JSON.

## Notes
- Direct browser calls to BGG are blocked by CORS and can be slow; this design avoids that by precomputing data.
- “Recommendations” for non-owned games typically require a broader catalog and an additional API (e.g., Board Game Atlas). We can add that later behind a build step or serverless function.

## License
MIT