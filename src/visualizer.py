import sqlite3
import json

DB_PATH = 'data/orchestrator.db'

def get_graph_summary():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    print("\n📊 --- Umwelt Graph Summary ---")
    
    # 1. Node counts
    c.execute("SELECT type, COUNT(*) FROM nodes GROUP BY type")
    print("\nNodes:")
    for ntype, count in c.fetchall():
        print(f"  {ntype.capitalize()}: {count}")
        
    # 2. Relationship counts
    c.execute("SELECT relationship, COUNT(*) FROM edges GROUP BY relationship")
    print("\nEdges:")
    for rel, count in c.fetchall():
        print(f"  {rel}: {count}")
        
    # 3. Top Senses (Modality popularity)
    c.execute("""
        SELECT target, COUNT(*) as frequency 
        FROM edges 
        WHERE relationship = 'HAS_SENSE' 
        GROUP BY target 
        ORDER BY frequency DESC 
        LIMIT 10
    """)
    print("\nTop 10 Sensory Modalities (across families & species):")
    for modality, freq in c.fetchall():
        clean_name = modality.replace('modality:', '')
        print(f"  {clean_name}: {freq} connections")

    conn.close()

def export_for_gephi():
    """Simple CSV export for Gephi visualization."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    os.makedirs('data/graph_export', exist_ok=True)
    
    # Export Nodes
    c.execute("SELECT id, name, type FROM nodes")
    with open('data/graph_export/nodes.csv', 'w') as f:
        f.write("ID,Label,Type\n")
        for row in c.fetchall():
            f.write(f'"{row[0]}","{row[1]}","{row[2]}"\n')
            
    # Export Edges
    c.execute("SELECT source, target, relationship FROM edges")
    with open('data/graph_export/edges.csv', 'w') as f:
        f.write("Source,Target,Type\n")
        for row in c.fetchall():
            f.write(f'"{row[0]}","{row[1]}","{row[2]}"\n')
            
    conn.close()
    print("\n💾 Graph exported to data/graph_export/nodes.csv and edges.csv")

if __name__ == "__main__":
    import os
    get_graph_summary()
    export_for_gephi()
