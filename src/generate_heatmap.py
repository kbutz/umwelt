import sqlite3
import json
import os

DB_PATH = 'data/orchestrator.db'
OUTPUT_FILE = 'sensory_heatmap.html'

def generate_heatmap_html():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # 1. Get Top 40 Orders (filtering out noise like 'Unknown')
    noise = ('Unknown', 'Not Available', 'Not specified in context', 'Unspecified', 'None', 'NULL')
    placeholders = ','.join(['?'] * len(noise))
    
    c.execute(f"""
        SELECT n.name, COUNT(*) as count 
        FROM nodes n
        JOIN edges e ON n.id = e.target
        WHERE n.type = 'order' 
          AND e.relationship = 'MEMBER_OF'
          AND n.name NOT IN ({placeholders})
        GROUP BY n.name 
        ORDER BY count DESC 
        LIMIT 40
    """, noise)
    orders = [r[0] for r in c.fetchall()]
    
    # 2. Get All Modalities and sort by global frequency
    c.execute("""
        SELECT target, COUNT(*) as freq 
        FROM edges 
        WHERE relationship = 'HAS_SENSE' 
        GROUP BY target 
        ORDER BY freq DESC
    """)
    modalities = [r[0].replace('modality:', '') for r in c.fetchall()]
    
    # 3. Calculate "Sensation Density" per order
    matrix = []
    for order in orders:
        row = {"order": order}
        for mod in modalities:
            c.execute("""
                SELECT COUNT(DISTINCT f.id)
                FROM nodes o
                JOIN edges e1 ON o.id = e1.target AND e1.relationship = 'MEMBER_OF'
                JOIN nodes f ON e1.source = f.id
                JOIN edges e2 ON f.id = e2.source AND e2.relationship = 'HAS_SENSE'
                JOIN nodes m ON e2.target = m.id
                WHERE o.name = ? AND m.name = ?
            """, (order, mod))
            count = c.fetchone()[0]
            row[mod] = count
        matrix.append(row)

    data_json = json.dumps({"orders": orders, "modalities": modalities, "matrix": matrix})
    
    html_template = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Umwelt: Sensory Heatmap</title>
    <script src="https://d3js.org/d3.v7.min.js"></script>
    <style>
        body {{ margin: 0; font-family: sans-serif; background: #0a0a0a; color: #eee; display: flex; flex-direction: column; align-items: center; }}
        .chart-container {{ margin-top: 50px; margin-bottom: 50px; }}
        .cell {{ cursor: crosshair; }}
        .cell:hover {{ stroke: #fff; stroke-width: 2px; }}
        .axis text {{ font-size: 11px; fill: #aaa; }}
        .tooltip {{ position: absolute; background: rgba(0,0,0,0.9); padding: 12px; border-radius: 8px; pointer-events: none; opacity: 0; border: 1px solid #00d4ff; box-shadow: 0 4px 10px rgba(0,0,0,0.5); z-index: 1000; font-size: 0.9em; line-height: 1.4; }}
        h1 {{ color: #00d4ff; margin-top: 30px; letter-spacing: 1px; }}
        .legend {{ display: flex; margin-top: 20px; font-size: 0.8em; color: #888; }}
        .legend-item {{ margin: 0 10px; }}
    </style>
</head>
<body>
    <h1>Sensory Density by Order</h1>
    <p style="opacity: 0.7; font-size: 0.9em;">Intensity represents number of families in the order possessing the sense.</p>
    
    <div class="tooltip" id="tooltip"></div>
    <div class="chart-container" id="heatmap"></div>

    <script>
        const data = {data_json};
        
        const margin = {{top: 150, right: 50, bottom: 50, left: 180}};
        const width = Math.max(800, data.modalities.length * 40) - margin.left - margin.right;
        const height = (data.orders.length * 22) + margin.top + margin.bottom;

        const svg = d3.select("#heatmap")
            .append("svg")
            .attr("width", width + margin.left + margin.right)
            .attr("height", height)
            .append("g")
            .attr("transform", `translate(${{margin.left}},${{margin.top}})`);

        const x = d3.scaleBand()
            .range([0, width])
            .domain(data.modalities)
            .padding(0.05);

        svg.append("g")
            .attr("class", "axis")
            .call(d3.axisTop(x))
            .selectAll("text")
            .attr("transform", "rotate(-45)")
            .style("text-anchor", "start")
            .style("font-weight", d => ['Mechanoreception', 'Chemoreception', 'Photoreception'].includes(d) ? 'bold' : 'normal');

        const y = d3.scaleBand()
            .range([0, height - margin.top - margin.bottom])
            .domain(data.orders)
            .padding(0.05);

        svg.append("g")
            .attr("class", "axis")
            .call(d3.axisLeft(y));

        const colorScale = d3.scaleSequential()
            .interpolator(d3.interpolateTurbo)
            .domain([0, d3.max(data.matrix, d => d3.max(data.modalities, m => d[m]))]);

        data.matrix.forEach(row => {{
            data.modalities.forEach(mod => {{
                const val = row[mod];
                svg.append("rect")
                    .attr("x", x(mod))
                    .attr("y", y(row.order))
                    .attr("width", x.bandwidth())
                    .attr("height", y.bandwidth())
                    .attr("fill", val === 0 ? "#111" : colorScale(val))
                    .attr("class", "cell")
                    .on("mouseover", (event) => {{
                        d3.select("#tooltip")
                            .style("opacity", 1)
                            .html(`<b>Order:</b> ${{row.order}}<br><b>Sense:</b> ${{mod}}<br><b>Family Count:</b> ${{val}}`)
                            .style("left", (event.pageX + 15) + "px")
                            .style("top", (event.pageY - 15) + "px");
                    }})
                    .on("mousemove", (event) => {{
                        d3.select("#tooltip")
                            .style("left", (event.pageX + 15) + "px")
                            .style("top", (event.pageY - 15) + "px");
                    }})
                    .on("mouseout", () => d3.select("#tooltip").style("opacity", 0));
            }});
        }});
    </script>
</body>
</html>
    """
    
    with open(OUTPUT_FILE, 'w') as f:
        f.write(html_template)
    print(f"✨ Improved Sensory Heatmap generated: {OUTPUT_FILE}")
    conn.close()

if __name__ == "__main__":
    generate_heatmap_html()