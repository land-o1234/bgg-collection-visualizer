# Board Game Collection Visualizer

Board Game Collection Visualizer is a static web application that visualizes BoardGameGeek (BGG) collections as interactive graphs. It consists of a Python data generation script that fetches collection data from BGG's XML API and a pure HTML/CSS/JavaScript frontend for visualization.

Always reference these instructions first and fallback to search or bash commands only when you encounter unexpected information that does not match the info here.

## Working Effectively

### Bootstrap and Setup
- Create Python virtual environment: `python3 -m venv .venv`
- Activate virtual environment: `source .venv/bin/activate` (Linux/Mac) or `.venv/Scripts/activate` (Windows)
- Install Python dependencies: `pip install -r requirements.txt` -- NEVER CANCEL: Can take 5-10 minutes due to numpy/scipy dependencies. Set timeout to 15+ minutes.
- NOTE: Network connectivity issues may prevent pip install from completing. If pip fails with timeouts, document the specific error.

### Data Generation (Python)
- **CRITICAL**: The repository initially contains missing Python modules (`bgg.py` and `similarity.py`) that are required for data generation
- If missing, these modules must be created to interface with BGG's XML API and compute game similarities
- Generate data: `python src/generate_data.py --username [BGG_USERNAME] --edge-threshold 0.35 --out-dir data`
- NEVER CANCEL: Data generation takes 5-15 minutes depending on collection size and BGG API response times. Set timeout to 30+ minutes.
- The script creates `data/nodes.json` (games) and `data/edges.json` (similarity relationships)
- BGG API is rate-limited and may return 202 status requiring retries - this is normal behavior

### Web Application
- Start HTTP server from repository root: `python3 -m http.server 8000`
- Access web app: `http://localhost:8000/static/`
- **IMPORTANT**: Server must run from repository root (not static/ directory) so the app can access `../data/` relative paths
- **CRITICAL DEPENDENCY ISSUE**: The web app relies on Cytoscape.js from CDN (https://unpkg.com/cytoscape@3.30.2/dist/cytoscape.min.js)
- If CDN access is blocked, the graph visualization will not work, showing an empty graph area
- The sidebar UI loads correctly even without the graphing library

## Validation

### Data Generation Validation
- Verify sample data generation works: Use a known public BGG username (e.g., "InspiringChicken")
- Check output files exist: `ls -la data/` should show `nodes.json` and `edges.json`
- Validate JSON format: `python -m json.tool data/nodes.json > /dev/null` should not error
- ALWAYS test with small collections first before attempting large ones

### Web Application Validation
- ALWAYS verify the HTTP server serves from the correct directory (repository root, not static/)
- Test data loading: Check browser console for 200 status on `../data/nodes.json` and `../data/edges.json`
- **Manual UI Testing Required**: 
  - Verify sidebar loads with search box and game details sections
  - If Cytoscape loads successfully, test clicking nodes and search functionality
  - Take screenshot to verify visual state
- **Known Issues**: CDN dependencies may fail in restricted network environments

### Complete End-to-End Test Scenario
1. Set up Python environment (15 minutes)
2. Generate data for a test collection (30 minutes)
3. Start web server from repository root
4. Navigate to `http://localhost:8000/static/`
5. Verify UI loads and data is accessible
6. Test basic interactions if graph library loads

## Network and Environment Limitations

### Known Network Issues
- `pip install` may timeout due to PyPI connectivity issues
- BGG XML API may be slow or temporarily unavailable
- Cytoscape.js CDN may be blocked in restricted environments
- **NEVER CANCEL network operations** - they may take significantly longer than expected

### Workarounds for Network Issues
- For pip timeouts: Retry with `--timeout=300` flag or install packages individually
- For BGG API issues: Implement retry logic with exponential backoff (already included in bgg.py)
- For CDN issues: Download Cytoscape.js locally and modify HTML to use local copy

## Common Tasks

### Repository Structure
```
.
├── README.md
├── requirements.txt           # Python dependencies  
├── .gitignore                # Excludes .venv/, data/, __pycache__/
├── src/
│   ├── generate_data.py      # Main data generation script
│   ├── bgg.py               # BGG XML API interface (may need creation)
│   └── similarity.py        # Game similarity computation (may need creation)
├── static/
│   ├── index.html           # Web app entry point
│   ├── app.js              # Main JavaScript application
│   └── style.css           # Styling
└── data/                   # Generated JSON files (created by Python script)
    ├── nodes.json          # Game data
    └── edges.json          # Similarity edges
```

### Key Dependencies
- **Python**: requests, xmltodict, networkx, numpy (see requirements.txt)
- **JavaScript**: Cytoscape.js (loaded from CDN)
- **Data**: BGG XML API (external dependency)

### Timing Expectations
- Virtual environment setup: 1-2 minutes
- Python dependency installation: 5-15 minutes (NEVER CANCEL)
- Data generation: 5-30 minutes depending on collection size (NEVER CANCEL)
- Web server startup: Immediate
- Web app loading: 2-5 seconds if CDN works, may fail if blocked

## Development Notes

### Missing Modules Issue
If `bgg.py` and `similarity.py` are missing, they need to be created with these interfaces:
- `bgg.get_collection(username: str) -> List[Dict]`: Fetch user's BGG collection
- `bgg.get_things(game_ids: List[int]) -> Dict[int, Dict]`: Fetch detailed game information
- `similarity.compute_similarity_edges(games: Dict, threshold: float) -> List[Tuple]`: Compute game similarities

### Configuration
- Default similarity threshold: 0.35 (configurable via `--edge-threshold`)
- BGG API rate limiting: 1-2 second delays between requests (built into bgg.py)
- Server port: 8000 (configurable with http.server)

### Troubleshooting
- "Module not found" errors: Check virtual environment activation and pip install completion
- "Failed to load data" alerts: Verify HTTP server runs from repository root, not static/ directory
- Empty graph area: CDN blocked, check browser console for Cytoscape loading errors
- BGG API errors: Verify username is correct and collection is public

ALWAYS run complete end-to-end validation after making changes to ensure the pipeline works correctly.