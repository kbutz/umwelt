import sqlite3
import json
import os
import glob

DB_PATH = 'data/orchestrator.db'
VAULT_DIR = 'data/vault'

def init_claims_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    # The "Claims Index" Table
    c.execute('''
        CREATE TABLE IF NOT EXISTS claims (
            id INTEGER PRIMARY KEY,
            animal TEXT,
            modality TEXT,
            sub_type TEXT,
            stimulus TEXT,
            min_val REAL,
            max_val REAL,
            unit TEXT,
            FOREIGN KEY(animal) REFERENCES research_queue(animal_name)
        )
    ''')
    conn.commit()
    conn.close()
    print("Claims table initialized.")

def process_file(filepath):
    try:
        with open(filepath, 'r') as f:
            data = json.load(f)
    except Exception as e:
        print(f"Error reading {filepath}: {e}")
        return

    animal_name = data.get('identity', {}).get('common_name')
    if not animal_name:
        # Fallback if common_name is missing, try filename
        animal_name = os.path.basename(filepath).replace('.json', '').replace('_', ' ')

    sensory_modalities = data.get('sensory_modalities', [])

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Optional: Clear existing claims for this animal to avoid duplicates on re-run
    c.execute("DELETE FROM claims WHERE animal = ?", (animal_name,))

    for mod in sensory_modalities:
        modality = mod.get('modality_domain')
        sub_type = mod.get('sub_type')
        stimulus = mod.get('stimulus_type')

        qd = mod.get('quantitative_data')
        min_val = None
        max_val = None
        unit = None

        if qd:
            min_val = qd.get('min')
            max_val = qd.get('max')
            unit = qd.get('unit')

        c.execute('''
            INSERT INTO claims (animal, modality, sub_type, stimulus, min_val, max_val, unit)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (animal_name, modality, sub_type, stimulus, min_val, max_val, unit))

    conn.commit()
    conn.close()
    print(f"Archived claims for {animal_name}")

def run_archivist():
    init_claims_db()
    # Process all JSON files in vault
    files = glob.glob(os.path.join(VAULT_DIR, '*.json'))
    print(f"Found {len(files)} files in vault.")
    for filepath in files:
        process_file(filepath)

if __name__ == "__main__":
    run_archivist()
