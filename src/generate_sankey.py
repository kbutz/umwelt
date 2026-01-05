import sqlite3
import json
import os

DB_PATH = 'data/orchestrator.db'
OUTPUT_FILE = 'sensory_flow.html'

def generate_sankey_html():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # We'll build nodes and links for: Order -> Family -> Modality
    nodes = []
    links = []
    node_map = {} # name -> index

    def get_node(name, ntype):
        key = f"{ntype}:{name}"
        if key not in node_map:
            node_map[key] = len(nodes)
            nodes.append({"name": name, "type": ntype})
        return node_map[key]

    # 1. Fetch Top 20 Orders
    c.execute("""
        SELECT name, id FROM nodes 
        WHERE type = 'order' 
        LIMIT 20
    """)
    orders = c.fetchall()
    
    for o_name, o_id in orders:
        o_idx = get_node(o_name, 'order')
        
        # 2. Get Families for this order
        c.execute("""
            SELECT f.name, f.id FROM nodes f
            JOIN edges e ON f.id = e.source AND e.relationship = 'MEMBER_OF'
            WHERE e.target = ?
        """, (o_id,))
        families = c.fetchall()
        
        for f_name, f_id in families:
            f_idx = get_node(f_name, 'family')
            links.append({"source": o_idx, "target": f_idx, "value": 1})
            
            # 3. Get Senses for this family
            c.execute("""
                SELECT m.name FROM nodes m
                JOIN edges e ON m.id = e.target AND e.relationship = 'HAS_SENSE'
                WHERE e.source = ?
            """, (f_id,))
            senses = c.fetchall()
            for (s_name,) in senses:
                s_idx = get_node(s_name, 'modality')
                links.append({"source": f_idx, "target": s_idx, "value": 1})

    data_json = json.dumps({"nodes": nodes, "links": links})
    
    html_template = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Umwelt: Sensory Flow</title>
    <script src="https://d3js.org/d3.v7.min.js"></script>
    <script src="https://unpkg.com/d3-sankey@0.12.3/dist/d3-sankey.min.js"></script>
    <style>
        body {{ margin: 0; font-family: sans-serif; background: #0f0f0f; color: #eee; }}
        .node rect {{ fill-opacity: 0.9; shape-rendering: crispEdges; stroke-width: 0; }}
        .node text {{ fill: #fff; font-size: 10px; pointer-events: none; }}
        .link {{ fill: none; stroke: #444; stroke-opacity: 0.2; }}
        .link:hover {{ stroke-opacity: 0.5; }}
        h1 {{ text-align: center; color: #00d4ff; }}
    </style>
</head>
<body>
    <h1>Sensory Flow: Order → Family → Sense</h1>
    <div id="chart"></div>

    <script>
        const data = {data_json};
        const width = window.innerWidth;
        const height = 2000; // Large height for readability

        const svg = d3.select("#chart").append("svg")
            .attr("width", width)
            .attr("height", height)
            .append("g")
            .attr("transform", "translate(20,20)");

        const sankey = d3.sankey()
            .nodeWidth(15)
            .nodePadding(10)
            .extent([[0, 0], [width - 40, height - 40]]);

        const {{nodes, links}} = sankey(data);

        const colorMap = {{
            'order': '#44ff44',
            'family': '#4444ff',
            'modality': '#ff4444'
        }};

        svg.append("g")
            .selectAll("rect")
            .data(nodes)
            .join("rect")
            .attr("x", d => d.x0)
            .attr("y", d => d.y0)
            .attr("height", d => d.y1 - d.y0)
            .attr("width", d => d.x1 - d.x0)
            .attr("fill", d => colorMap[d.type] || "#ccc")
            .append("title").text(d => d.name);

        svg.append("g")
            .attr("fill", "none")
            .selectAll("path")
            .data(links)
            .join("path")
            .attr("d", d3.sankeyLinkHorizontal())
            .attr("stroke", "#555")
            .attr("stroke-width", d => Math.max(1, d.width))
            .attr("class", "link");

        svg.append("g")
            .selectAll("text")
            .data(nodes)
            .join("text")
            .attr("x", d => d.x0 < width / 2 ? d.x1 + 6 : d.x0 - 6)
            .attr("y", d => (d.y1 + d.y0) / 2)
            .attr("dy", "0.35em")
            .attr("text-anchor", d => d.x0 < width / 2 ? "start" : "end")
            .text(d => d.name);
    </script>
</body>
</html>
    """
    with open(OUTPUT_FILE, 'w') as f:
        f.write(html_template)
    print(f"✨ Sensory Flow (Sankey) generated: {OUTPUT_FILE}")
    conn.close()

if __name__ == "__main__":
    generate_sankey_html()
