import sqlite3
import os

DB_PATH = 'data/orchestrator.db'

def init_family_db(drop=False):
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=30)
    c = conn.cursor()
    
    if drop:
        c.execute("DROP TABLE IF EXISTS family_research_queue")
    
    # Create family_research_queue table
    c.execute('''
        CREATE TABLE IF NOT EXISTS family_research_queue (
            family_name TEXT PRIMARY KEY,
            gbif_id INTEGER,
            order_name TEXT,
            representative_species TEXT,
            status TEXT CHECK(status IN ('PENDING', 'PROCESSING', 'COMPLETED', 'FAILED')) DEFAULT 'PENDING',
            priority INTEGER DEFAULT 5,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()
    print(f"Family research queue initialized in {DB_PATH}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--drop", action="store_true")
    args = parser.parse_args()
    init_family_db(drop=args.drop)
