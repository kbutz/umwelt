import sqlite3
import json
import os

DB_NAME = 'data/sensory_graph.db'

def init_db():
    if os.path.exists(DB_NAME):
        os.remove(DB_NAME)

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # Create table
    # We store the main structured data in JSON columns.
    # We extract common_name and scientific_name for easier standard SQL querying.
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS animals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        common_name TEXT NOT NULL,
        scientific_name TEXT,
        taxonomy JSON,
        sensory_modalities JSON,
        meta JSON,
        raw_data JSON
    )
    ''')

    conn.commit()
    conn.close()
    print(f"Initialized {DB_NAME}")

if __name__ == "__main__":
    init_db()
