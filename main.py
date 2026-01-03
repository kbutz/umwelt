import sqlite3
import os

DB_DIR = 'data'
DB_PATH = os.path.join(DB_DIR, 'orchestrator.db')

def init_db():
    os.makedirs(DB_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS research_queue (
            id INTEGER PRIMARY KEY,
            animal_name TEXT UNIQUE,
            taxonomy_source TEXT,
            priority INTEGER,
            status TEXT DEFAULT 'PENDING',
            attempts INTEGER DEFAULT 0
        )
    ''')
    conn.commit()
    conn.close()
    print(f"Database initialized at {DB_PATH}")

def populate_seed_queue():
    seed_animals = [
        "Bottlenose Dolphin",
        "Great White Shark",
        "Monarch Butterfly",
        "Naked Mole Rat",
        "Human"
    ]

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    for animal in seed_animals:
        try:
            c.execute('''
                INSERT INTO research_queue (animal_name, taxonomy_source, priority, status)
                VALUES (?, ?, ?, ?)
            ''', (animal, "Seed List", 1, "PENDING"))
            print(f"Added to queue: {animal}")
        except sqlite3.IntegrityError:
            print(f"Already in queue: {animal}")

    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    populate_seed_queue()
