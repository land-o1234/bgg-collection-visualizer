# BGG Collection Visualizer - Copilot Instructions

## Project Overview

This is a static web application that visualizes BoardGameGeek (BGG) collections as interactive graphs. The system consists of Python scripts for data generation from the BGG XML API and a JavaScript frontend for visualization.

## Architecture

### Backend (Python)
- **`src/bgg.py`**: BGG XML API client with retry logic and rate limiting
- **`src/similarity.py`**: Game similarity computation using Jaccard and cosine similarity
- **`src/generate_data.py`**: Main script that generates JSON data files for the frontend

### Frontend (JavaScript)
- **`static/index.html`**: Main web application interface
- **`static/app.js`**: Cytoscape.js graph visualization and interaction logic
- **`static/style.css`**: Dark theme styling with CSS Grid layout

### Data Flow
1. Fetch user's BGG collection via XML API
2. Retrieve detailed game information (mechanics, categories, ratings)
3. Compute pairwise similarities and generate recommendation candidates
4. Export as JSON files (`nodes.json`, `edges.json`, `recs.json`)
5. Load data in interactive web visualization

## Development Guidelines

### Python Code Style
- Use type hints for function parameters and return values
- Follow logging best practices with structured log messages
- Implement retry logic for external API calls
- Handle BGG API rate limiting (202 status codes)
- Use descriptive variable names (`edge_threshold`, `rec_search_terms`)

### JavaScript Code Style
- Use async/await for API calls and data loading
- Implement error handling for missing data files
- Use meaningful DOM element IDs and CSS classes
- Handle user interactions with event listeners
- Follow functional programming patterns where possible

### Data Processing
- **Similarity Algorithm**: 50% mechanics Jaccard + 30% categories Jaccard + 20% numeric cosine
- **Threshold Filtering**: Default similarity threshold of 0.35
- **JSON Structure**: Maintain compatibility between Python export and JavaScript import
- **Error Handling**: Graceful degradation when optional data (recs.json) is missing

### BGG API Integration
- **Rate Limiting**: Always implement delays between requests
- **Retry Logic**: Handle 202 responses (processing) and network timeouts
- **Data Validation**: Verify collection visibility and username validity
- **XML Parsing**: Robust handling of BGG's inconsistent XML responses

### Visualization Features
- **Graph Layout**: Cytoscape.js with cose layout for physics simulation
- **Search**: Real-time filtering by game name
- **Details Panel**: Show game metadata, neighbors, and recommendations
- **Responsive Design**: Grid layout with fixed sidebar and flexible graph area

## Common Tasks

### Adding New Similarity Metrics
1. Implement the metric function in `src/similarity.py`
2. Update `compute_game_similarity()` to include the new metric
3. Adjust weights in the weighted combination
4. Test with sample data to validate results

### Extending BGG API Features
1. Add new API functions to `src/bgg.py`
2. Include retry logic and error handling
3. Update data structures in `generate_data.py`
4. Modify JSON export format if needed

### Frontend Enhancements
1. Update visualization in `static/app.js`
2. Add corresponding HTML elements in `static/index.html`
3. Style new elements in `static/style.css`
4. Ensure responsive design is maintained

## File Dependencies

- **Python dependencies**: `requirements.txt` - requests, xmltodict, networkx, numpy
- **JavaScript dependencies**: Cytoscape.js (loaded via CDN)
- **Data files**: Generated in `docs/data/` directory for GitHub Pages compatibility
- **Configuration**: `.github/workflows/generate-data.yml` for automated updates

## Deployment

The application is designed for GitHub Pages deployment:
- Static files served from repository root
- Data files in `docs/data/` directory
- GitHub Actions workflow for automated data updates
- No server-side processing required at runtime

## Testing Strategy

- Test BGG API integration with different usernames and edge cases
- Validate similarity computations with known game pairs
- Test frontend with various data sizes and missing files
- Verify responsive design across different screen sizes
- Test GitHub Actions workflow with sample data

## Performance Considerations

- BGG API calls are rate-limited and can be slow
- Large collections may require chunked processing
- Graph rendering performance depends on number of nodes and edges
- JSON file sizes should be monitored for large collections
- Use edge thresholds to limit graph complexity

## Error Handling Patterns

- Always validate BGG API responses before processing
- Provide meaningful error messages for common issues
- Gracefully handle missing or corrupted data files
- Log warnings for non-critical failures
- Implement fallback behavior for optional features

## Development Workflow

### Local Development
```bash
# Setup environment
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
pip install -r requirements.txt

# Generate test data (requires BGG username)
python src/generate_data.py --username YourBGGUsername --out-dir docs/data

# Serve static files locally
python -m http.server -d . 8000
# Visit: http://localhost:8000/static/
```

### GitHub Actions Integration
- Workflow triggers: daily schedule (6 AM UTC) and manual dispatch
- Automated data updates commit to `docs/data/` directory
- GitHub Pages serves the static site from repository root
- Environment variables: `BGG_USERNAME`, `EDGE_THRESHOLD`

## Code Patterns

### API Client Pattern (BGG)
```python
def _request_with_retry(url: str, params: Dict[str, Any] = None) -> Optional[ET.Element]:
    for attempt in range(MAX_RETRIES):
        # Handle 202 processing status, implement delays
        # Parse XML responses, validate structure
```

### Similarity Computation Pattern
```python
def compute_game_similarity(game1: Dict, game2: Dict) -> float:
    # Extract mechanics and categories as sets
    # Compute Jaccard similarities for categorical data
    # Compute cosine similarity for numerical features
    # Return weighted combination
```

### Frontend Data Loading Pattern
```javascript
async function loadJSON(path) {
    const res = await fetch(path);
    if (!res.ok) throw new Error(`Failed to load ${path}: ${res.status}`);
    return await res.json();
}
```
```