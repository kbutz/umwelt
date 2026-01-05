import sqlite3
import json
import os

DB_PATH = 'data/orchestrator.db'
OUTPUT_FILE = 'web_of_senses.html'

def generate_html():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Fetch ALL nodes
    c.execute("SELECT id, name, type FROM nodes")
    nodes = [{"id": r[0], "name": r[1], "type": r[2]} for r in c.fetchall()]
    
    # Fetch ALL edges
    c.execute("SELECT source, target, relationship FROM edges")
    links = [{"source": r[0], "target": r[1], "rel": r[2]} for r in c.fetchall()]
    
    graph_data = {"nodes": nodes, "links": links}
    
    html_template = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Umwelt: Web of Senses</title>
    <script src="https://d3js.org/d3.v7.min.js"></script>
    <style>
        body {{ margin: 0; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #0a0a0a; color: #eee; overflow: hidden; }}
        svg {{ background: #0a0a0a; }}
        .controls {{ position: absolute; top: 20px; left: 20px; background: rgba(15,15,15,0.95); padding: 20px; border-radius: 12px; border: 1px solid #444; pointer-events: auto; z-index: 100; box-shadow: 0 8px 32px rgba(0,0,0,0.8); width: 250px; }}
        .legend-item {{ display: flex; align-items: center; margin-bottom: 8px; font-size: 0.9em; }}
        .color-box {{ width: 14px; height: 14px; margin-right: 10px; border-radius: 50%; }}
        .node-label {{ pointer-events: none; font-size: 10px; fill: #aaa; opacity: 0.8; }}
        .modality-label {{ pointer-events: none; font-size: 18px; font-weight: bold; fill: #fff; text-shadow: 0 0 10px #000; }}
        line {{ stroke: #444; stroke-opacity: 0.2; transition: stroke-opacity 0.3s, stroke 0.3s; }}
        circle {{ stroke: #000; stroke-width: 1px; transition: r 0.3s, opacity 0.3s; }}
        
        /* Highlight Classes */
        .dimmed {{ opacity: 0.1 !important; }}
        .highlighted-node {{ stroke: #fff !important; stroke-width: 3px !important; opacity: 1 !important; }}
        .highlighted-link {{ stroke: #00d4ff !important; stroke-opacity: 0.8 !important; stroke-width: 2px !important; }}
        
        #details {{ margin-top: 15px; padding-top: 15px; border-top: 1px solid #333; min-height: 60px; color: #00d4ff; font-size: 0.95em; line-height: 1.4; }}
        .hint {{ font-size: 0.75em; opacity: 0.5; margin-top: 10px; font-style: italic; }}
    </style>
</head>
<body>
    <div class="controls">
        <h2 style="margin-top:0; color: #00d4ff; letter-spacing: 1px;">UMWELT</h2>
        <div class="legend-item"><div class="color-box" style="background: #ff4444;"></div> <b>Modality</b></div>
        <div class="legend-item"><div class="color-box" style="background: #44ff44;"></div> Order</div>
        <div class="legend-item"><div class="color-box" style="background: #4444ff;"></div> Family</div>
        <div class="legend-item"><div class="color-box" style="background: #ffaa00;"></div> Species</div>
        
        <div id="details">Click a node to focus its connections</div>
        <div class="hint">Click background to reset view</div>
    </div>
    <svg id="viz"></svg>

    <script>
        const data = {json.dumps(graph_data)};
        const width = window.innerWidth;
        const height = window.innerHeight;
        
        const colorMap = {{
            'modality': '#ff4444',
            'order': '#44ff44',
            'family': '#4444ff',
            'species': '#ffaa00'
        }};

        const svg = d3.select("#viz")
            .attr("width", width)
            .attr("height", height);

        const container = svg.append("g");

        // Background click to reset
        svg.on("click", (event) => {{
            if (event.target.tagName === 'svg') resetFocus();
        }});

        // Zoom setup
        const zoom = d3.zoom()
            .scaleExtent([0.01, 8])
            .on("zoom", (event) => container.attr("transform", event.transform));
        
        svg.call(zoom);

        const simulation = d3.forceSimulation(data.nodes)
            .force("link", d3.forceLink(data.links).id(d => d.id).distance(120).strength(0.2))
            .force("charge", d3.forceManyBody().strength(-300))
            .force("center", d3.forceCenter(width / 2, height / 2))
            .force("collision", d3.forceCollide().radius(d => d.type === 'modality' ? 50 : 25));

        const link = container.append("g")
            .selectAll("line")
            .data(data.links)
            .join("line");

        const node = container.append("g")
            .selectAll("g")
            .data(data.nodes)
            .join("g")
            .attr("cursor", "pointer")
            .call(d3.drag()
                .on("start", dragstarted)
                .on("drag", dragged)
                .on("end", dragended));

        node.append("circle")
            .attr("r", d => d.type === 'modality' ? 18 : 8)
            .attr("fill", d => colorMap[d.type] || '#ccc');

        node.append("text")
            .filter(d => d.type === 'modality')
            .attr("dy", -25)
            .attr("text-anchor", "middle")
            .attr("class", "modality-label")
            .text(d => d.name);

        node.on("click", (event, d) => {{
            event.stopPropagation();
            focusOnNode(d);
        }});

        simulation.on("tick", () => {{
            link
                .attr("x1", d => d.source.x)
                .attr("y1", d => d.source.y)
                .attr("x2", d => d.target.x)
                .attr("y2", d => d.target.y);

            node.attr("transform", d => `translate(${{d.x}},${{d.y}})`);
        }});

        function focusOnNode(focusD) {{
            // Find neighbors
            const neighbors = new Set();
            neighbors.add(focusD.id);
            
            data.links.forEach(l => {{
                if (l.source.id === focusD.id) neighbors.add(l.target.id);
                if (l.target.id === focusD.id) neighbors.add(l.source.id);
            }});

            // Dim others
            node.selectAll("circle").classed("dimmed", n => !neighbors.has(n.id));
            node.selectAll("circle").classed("highlighted-node", n => n.id === focusD.id);
            node.selectAll("text").classed("dimmed", n => !neighbors.has(n.id) && n.type !== 'modality');
            
            link.classed("dimmed", l => l.source.id !== focusD.id && l.target.id !== focusD.id);
            link.classed("highlighted-link", l => l.source.id === focusD.id || l.target.id === focusD.id);

            d3.select("#details").html(`
                <span style="font-size: 0.8em; opacity: 0.7;">${{focusD.type.toUpperCase()}}</span><br>
                <span style="font-size: 1.2em; color: #fff;">${{focusD.name}}</span><br>
                <span style="font-size: 0.8em; color: #44ff44;">Connections: ${{neighbors.size - 1}}</span>
            `);
        }}

        function resetFocus() {{
            node.selectAll("circle").classed("dimmed", false).classed("highlighted-node", false);
            node.selectAll("text").classed("dimmed", false);
            link.classed("dimmed", false).classed("highlighted-link", false);
            d3.select("#details").text("Click a node to focus its connections");
        }}

        function dragstarted(event) {{
            if (!event.active) simulation.alphaTarget(0.3).restart();
            event.subject.fx = event.subject.x;
            event.subject.fy = event.subject.y;
        }}

        function dragged(event) {{
            event.subject.fx = event.x;
            event.subject.fy = event.y;
        }}

        function dragended(event) {{
            if (!event.active) simulation.alphaTarget(0);
            event.subject.fx = null;
            event.subject.fy = null;
        }}
    </script>
</body>
</html>
    """
    
    with open(OUTPUT_FILE, 'w') as f:
        f.write(html_template)
    
    print(f"✨ Interactive Focus-Graph generated: {OUTPUT_FILE}")
    conn.close()

if __name__ == "__main__":
    generate_html()
