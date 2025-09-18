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
  // Expect these JSON files to be available at ../data relative to static/
  const nodes = await loadJSON("../data/nodes.json");
  const edges = await loadJSON("../data/edges.json");

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

  // Simple search
  searchInput.addEventListener("input", e => {
    const q = e.target.value.trim().toLowerCase();
    if (!q) { searchResults.innerHTML = ""; return; }
    const matches = cy.nodes().filter(n => (n.data("label") || "").toLowerCase().includes(q)).slice(0, 12);
    searchResults.innerHTML = matches.map(n => `<div data-id="${n.id()}">${n.data("label")}</div>`).join("");
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

  // Optional: try to load static recommendations if you add data/recs.json later
  try {
    const recs = await loadJSON("../data/recs.json"); // expected: { [id]: [{id,name,score,bggUrl}] }
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
  alert("Failed to load data. Make sure ../data/nodes.json and ../data/edges.json exist.");
});