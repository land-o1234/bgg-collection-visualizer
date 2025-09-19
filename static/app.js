async function loadJSON(path) {
  const res = await fetch(path);
  if (!res.ok) throw new Error(`Failed to load ${path}: ${res.status}`);
  return await res.json();
}

function format(value, fallback = "N/A") {
  return (value === null || value === undefined || value === "") ? fallback : value;
}

function edgeId(a, b) {
  return a < b ? `${a}-${b}` : `${b}-${a}`;
}

async function main() {
  // Expect these JSON files to be available at ../docs/data relative to static/
  const nodes = await loadJSON("../docs/data/nodes.json");
  const edges = await loadJSON("../docs/data/edges.json");

  // Build Cytoscape elements
  const elements = [];
  for (const n of nodes) elements.push({ data: { id: String(n.id), ...n } });
  for (const e of edges) {
    elements.push({ data: { id: edgeId(String(e.source), String(e.target)), source: String(e.source), target: String(e.target), weight: e.weight } });
  }

  const cy = cytoscape({
    container: document.getElementById("graph"),
    style: [
      { selector: "node",
        style: {
          "background-color": "#38bdf8",
          "label": "data(label)",
          "color": "#e5e7eb",
          "font-size": 10,
          "text-outline-width": 2,
          "text-outline-color": "#082f49",
          "text-valign": "center",
          "text-halign": "center",
          "width": 14, "height": 14
        }},
      { selector: "edge",
        style: {
          "line-color": "#475569",
          "opacity": "mapData(weight, 0.3, 1.0, 0.3, 0.9)",
          "width": "mapData(weight, 0.3, 1.0, 1, 4)",
          "curve-style": "haystack",
          "haystack-radius": 0.6
        }},
      { selector: "node:selected",
        style: { "background-color": "#22d3ee", "text-outline-color": "#0f172a" }},
      { selector: ".dim",
        style: { "opacity": 0.15 }},
      { selector: ".highlight",
        style: { "background-color": "#22d3ee", "opacity": 1.0 }}
    ],
    elements,
    layout: { name: "cose", animate: false, nodeRepulsion: 400000, idealEdgeLength: 80, gravity: 80 }
  });

  const titleEl = document.getElementById("game-title");
  const metaEl = document.getElementById("meta");
  const neighEl = document.getElementById("neighbors");
  const recsEl = document.getElementById("recs");
  const searchInput = document.getElementById("search");
  const searchResults = document.getElementById("search-results");

  function showNodeDetails(n) {
    if (!n) return;
    const d = n.data();
    titleEl.textContent = d.name || d.label || `Game ${d.id}`;
    metaEl.innerHTML = `
      <div><b>Rating:</b> ${format(d.averagerating)}</div>
      <div><b>Weight:</b> ${format(d.averageweight)}</div>
      <div><b>Players:</b> ${format(d.minplayers)} – ${format(d.maxplayers)}</div>
      <div><b>Time:</b> ${format(d.playingtime)} min</div>
      <div><b>Mechanics:</b> ${Array.isArray(d.mechanics) ? d.mechanics.join(", ") : ""}</div>
      <div><b>Categories:</b> ${Array.isArray(d.categories) ? d.categories.join(", ") : ""}</div>
      <div><b>BGG:</b> <a href="${d.bggUrl}" target="_blank" rel="noopener">Open page</a></div>
    `;

    // List neighbors sorted by edge weight desc
    const neighbors = cy.edges(`[source = "${d.id}"], [target = "${d.id}"]`)
      .map(e => {
        const other = e.source().id() === String(d.id) ? e.target() : e.source();
        return { node: other, weight: e.data("weight") };
      })
      .sort((a,b) => b.weight - a.weight);

    neighEl.innerHTML = neighbors.map(nw => {
      const nd = nw.node.data();
      return `<div data-id="${nd.id}" class="neighbor"><b>${nd.label}</b> — ${nw.weight.toFixed(2)}</div>`;
    }).join("");

    // Hook neighbor clicks
    neighEl.querySelectorAll(".neighbor").forEach(el => {
      el.addEventListener("click", () => {
        const id = el.getAttribute("data-id");
        const node = cy.getElementById(String(id));
        if (node) selectNode(node);
      });
    });
  }

  function dimAllExcept(node) {
    cy.elements().removeClass("dim highlight");
    if (!node) return;
    const neighborhood = node.closedNeighborhood(); // node + connected edges+nodes
    cy.elements().difference(neighborhood).addClass("dim");
    node.addClass("highlight");
  }

  function selectNode(node) {
    cy.nodes().unselect();
    node.select();
    dimAllExcept(node);
    showNodeDetails(node);
    // Center/zoom softly
    cy.animate({ fit: { eles: node.closedNeighborhood(), padding: 50 } }, { duration: 300 });
  }

  cy.on("tap", "node", evt => {
    selectNode(evt.target);
  });

  // Simple search with relevance scoring
  searchInput.addEventListener("input", e => {
    const q = e.target.value.trim().toLowerCase();
    if (!q) { searchResults.innerHTML = ""; return; }
    
    // Score matches by relevance
    const matches = cy.nodes()
      .filter(n => (n.data("label") || "").toLowerCase().includes(q))
      .map(n => {
        const label = (n.data("label") || "").toLowerCase();
        const rating = parseFloat(n.data("averagerating")) || 0;
        
        // Calculate relevance score
        let score = 0;
        const index = label.indexOf(q);
        
        // Position bonus: earlier matches score higher
        score += (100 - index) / 100;
        
        // Exact word match bonus
        const words = label.split(/\s+/);
        if (words.some(word => word === q)) score += 2;
        
        // Start of word bonus
        if (words.some(word => word.startsWith(q))) score += 1;
        
        // Rating bonus (normalized)
        score += rating / 10;
        
        return { node: n, score, label: n.data("label") };
      })
      .sort((a, b) => b.score - a.score)
      .slice(0, 12);
    
    searchResults.innerHTML = matches.map(m => `<div data-id="${m.node.id()}">${m.label}</div>`).join("");
    searchResults.querySelectorAll("div").forEach(div => {
      div.addEventListener("click", () => {
        const id = div.getAttribute("data-id");
        const node = cy.getElementById(id);
        if (node) selectNode(node);
        searchResults.innerHTML = "";
        searchInput.value = "";
      });
    });
  });

  // Optional: try to load static recommendations if you add docs/data/recs.json later
  try {
    const recs = await loadJSON("../docs/data/recs.json"); // expected: { [id]: [{id,name,score,bggUrl}] }
    recsEl.innerHTML = "<em>Click a game to see recommendations</em>";
    cy.on("select", "node", evt => {
      const id = String(evt.target.id());
      const list = recs[id] || [];
      if (!list.length) {
        recsEl.innerHTML = "<em>No recommendations for this game.</em>";
      } else {
        recsEl.innerHTML = list.map(r => `<div><a href="${r.bggUrl}" target="_blank" rel="noopener">${r.name}</a> — score ${r.score.toFixed(2)}</div>`).join("");
      }
    });
  } catch (e) {
    // recs.json is optional; ignore if missing
  }

  // Auto-select a central node (highest degree) for first view
  const degrees = cy.nodes().map(n => ({ n, deg: n.degree() })).sort((a,b) => b.deg - a.deg);
  if (degrees[0]) selectNode(degrees[0].n);
}

main().catch(err => {
  console.error(err);
  // Check if it's a cytoscape issue
  if (err.message && err.message.includes('cytoscape is not defined')) {
    loadSimpleFallback();
  } else {
    alert("Failed to load data. Make sure ../docs/data/nodes.json and ../docs/data/edges.json exist.");
  }
});

// Simple fallback when Cytoscape.js is not available
async function loadSimpleFallback() {
  try {
    const nodes = await loadJSON("../docs/data/nodes.json");
    const edges = await loadJSON("../docs/data/edges.json");
    
    document.getElementById('graph').innerHTML = `
      <div style="display: flex; align-items: center; justify-content: center; height: 100%; color: #e5e7eb; text-align: center; padding: 20px;">
        <div>
          <h2>🎲 Collection Overview</h2>
          <p><strong>Successfully loaded ${nodes.length} games with ${edges.length} similarity connections!</strong></p>
          <p>Cytoscape.js library needed for interactive graph. For now, browse your collection:</p>
          <div style="margin-top: 20px;">
            <button onclick="showGamesList()" style="
              background: #22d3ee; 
              color: #0f172a; 
              border: none; 
              padding: 10px 20px; 
              border-radius: 6px; 
              cursor: pointer;
              font-weight: bold;
              margin: 5px;
            ">Show Games List</button>
            <button onclick="showConnectionsGrid()" style="
              background: #38bdf8; 
              color: #0f172a; 
              border: none; 
              padding: 10px 20px; 
              border-radius: 6px; 
              cursor: pointer;
              font-weight: bold;
              margin: 5px;
            ">Show Connections</button>
          </div>
          <div id="fallback-content" style="margin-top: 20px; max-height: 400px; overflow-y: auto;"></div>
        </div>
      </div>
    `;
    
    // Store data globally for the fallback functions
    window.fallbackData = { nodes, edges };
    
    // Enable search functionality
    setupFallbackSearch();
    
  } catch (error) {
    document.getElementById('graph').innerHTML = `
      <div style="display: flex; align-items: center; justify-content: center; height: 100%; color: #e5e7eb; text-align: center; padding: 20px;">
        <div>
          <h2>❌ Data Loading Error</h2>
          <p>Could not load game data from ../docs/data/</p>
          <p>Error: ${error.message}</p>
        </div>
      </div>
    `;
  }
}

function setupFallbackSearch() {
  const searchInput = document.getElementById('search');
  const searchResults = document.getElementById('search-results');
  
  if (!searchInput || !window.fallbackData) return;
  
  searchInput.addEventListener('input', (e) => {
    const query = e.target.value.trim().toLowerCase();
    
    if (!query) {
      searchResults.innerHTML = '';
      return;
    }
    
    const { nodes } = window.fallbackData;
    const matches = nodes
      .filter(game => game.name && game.name.toLowerCase().includes(query))
      .map(game => {
        const name = game.name.toLowerCase();
        const rating = parseFloat(game.averagerating) || 0;
        
        // Calculate relevance score
        let score = 0;
        const index = name.indexOf(query);
        
        // Position bonus: earlier matches score higher
        score += (100 - index) / 100;
        
        // Exact word match bonus
        const words = name.split(/\s+/);
        if (words.some(word => word === query)) score += 2;
        
        // Start of word bonus
        if (words.some(word => word.startsWith(query))) score += 1;
        
        // Rating bonus (normalized)
        score += rating / 10;
        
        return { game, score };
      })
      .sort((a, b) => b.score - a.score)
      .slice(0, 8)
      .map(({ game }) => game);
    
    searchResults.innerHTML = matches.map(game => `
      <div onclick="showGameDetails('${game.id}')" style="
        padding: 6px 8px; 
        margin-top: 6px; 
        border-radius: 6px; 
        background: #0b1220; 
        cursor: pointer;
        border-left: 2px solid #22d3ee;
      ">
        <strong>${game.name}</strong><br>
        <small style="color: #9ca3af;">
          ${game.averagerating ? `★ ${parseFloat(game.averagerating).toFixed(1)}` : ''} | 
          ${game.averageweight ? `⚖ ${parseFloat(game.averageweight).toFixed(1)}` : ''}
        </small>
      </div>
    `).join('');
  });
}

function showGameDetails(gameId) {
  const { nodes, edges } = window.fallbackData;
  const game = nodes.find(n => n.id === gameId);
  
  if (!game) return;
  
  // Update game title and meta
  document.getElementById('game-title').textContent = game.name;
  document.getElementById('meta').innerHTML = `
    <p><strong>Rating:</strong> ${game.averagerating ? parseFloat(game.averagerating).toFixed(2) : 'N/A'}</p>
    <p><strong>Complexity:</strong> ${game.averageweight ? parseFloat(game.averageweight).toFixed(2) : 'N/A'}</p>
    <p><strong>Players:</strong> ${game.minplayers}-${game.maxplayers}</p>
    <p><strong>Playing Time:</strong> ${game.playingtime || 'N/A'} min</p>
    ${game.mechanics && game.mechanics.length ? `<p><strong>Mechanics:</strong> ${game.mechanics.slice(0, 3).join(', ')}</p>` : ''}
  `;
  
  // Find similar games (connected by edges)
  const similarGames = edges
    .filter(edge => edge.source === gameId || edge.target === gameId)
    .map(edge => {
      const otherId = edge.source === gameId ? edge.target : edge.source;
      const otherGame = nodes.find(n => n.id === otherId);
      return { game: otherGame, similarity: edge.weight };
    })
    .sort((a, b) => b.similarity - a.similarity);
  
  document.getElementById('neighbors').innerHTML = similarGames.length > 0 
    ? similarGames.map(({ game, similarity }) => `
        <div onclick="showGameDetails('${game.id}')" style="
          padding: 6px 8px; 
          margin: 4px 0; 
          background: #0b1220; 
          border-radius: 6px; 
          cursor: pointer;
          border-left: 2px solid #38bdf8;
        ">
          <strong>${game.name}</strong><br>
          <small style="color: #9ca3af;">Similarity: ${(similarity * 100).toFixed(1)}%</small>
        </div>
      `).join('')
    : '<em>No similar games found</em>';
  
  // Clear search
  document.getElementById('search').value = '';
  document.getElementById('search-results').innerHTML = '';
}

function showGamesList() {
  const { nodes } = window.fallbackData;
  const content = document.getElementById('fallback-content');
  content.innerHTML = `
    <h3>Your Board Game Collection</h3>
    <div style="text-align: left; max-width: 500px; margin: 0 auto;">
      ${nodes.map(game => `
        <div onclick="showGameDetails('${game.id}')" style="
          padding: 8px; 
          margin: 4px 0; 
          background: #111827; 
          border-radius: 6px; 
          border-left: 3px solid #22d3ee;
          cursor: pointer;
        ">
          <strong>${game.name}</strong><br>
          <small style="color: #9ca3af;">
            Rating: ${game.averagerating || 'N/A'} | 
            Weight: ${game.averageweight || 'N/A'} | 
            Players: ${game.minplayers || '?'}-${game.maxplayers || '?'}
          </small>
        </div>
      `).join('')}
    </div>
  `;
}

function showConnectionsGrid() {
  const { nodes, edges } = window.fallbackData;
  const content = document.getElementById('fallback-content');
  
  // Create a map of game names
  const gameNames = {};
  nodes.forEach(n => gameNames[n.id] = n.name);
  
  content.innerHTML = `
    <h3>Game Similarity Connections</h3>
    <div style="text-align: left; max-width: 600px; margin: 0 auto;">
      ${edges.map(edge => `
        <div style="padding: 8px; margin: 4px 0; background: #111827; border-radius: 6px;">
          <div>
            <span onclick="showGameDetails('${edge.source}')" style="
              cursor: pointer; 
              color: #22d3ee; 
              text-decoration: underline;
              font-weight: bold;
            ">${gameNames[edge.source]}</span> 
            ⟷ 
            <span onclick="showGameDetails('${edge.target}')" style="
              cursor: pointer; 
              color: #22d3ee; 
              text-decoration: underline;
              font-weight: bold;
            ">${gameNames[edge.target]}</span>
          </div>
          <small style="color: #9ca3af;">Similarity: ${(edge.weight * 100).toFixed(1)}%</small>
        </div>
      `).join('')}
    </div>
  `;
}