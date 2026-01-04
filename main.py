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
    # Anchored Seed List (Scientific Name, Common Name, GBIF ID)
    seed_animals = [
        ("Tursiops truncatus", "Bottlenose Dolphin", 2440502),
        ("Carcharodon carcharias", "Great White Shark", 2420712),
        ("Danaus plexippus", "Monarch Butterfly", 5133088)
    ]

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    for sci_name, common_name, gbif_id in seed_animals:
        try:
            c.execute('''
                INSERT INTO research_queue (animal_name, gbif_id, taxonomy_source, priority, status, entity_type, entity_id)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (sci_name, gbif_id, "Seed List", 1, "PENDING", "species", str(gbif_id)))
            print(f"Added to queue: {common_name} ({sci_name})")
        except sqlite3.IntegrityError:
            print(f"Already in queue: {sci_name}")

    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    populate_seed_queue()
