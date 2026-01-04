import requests
import sqlite3
import os

DB_PATH = 'data/orchestrator.db'
GBIF_BACKBONE_KEY = "d7dddbf4-2cf0-4f39-9b2a-bb099caae36c"

def expand_taxonomy(family_name):
    print(f"🔭 Scout looking for: {family_name}")
    # 1. Query GBIF for species in this family, preferring the Backbone Taxonomy
    url = "https://api.gbif.org/v1/species/search"
    params = {
        "q": family_name,
        "rank": "SPECIES",
        "status": "ACCEPTED",
        "datasetKey": GBIF_BACKBONE_KEY,
        "limit": 50
    }
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        print(f"Error querying GBIF: {e}")
        return

    # 2. Extract Names and IDs
    new_animals = []
    for r in data.get('results', []):
        if 'canonicalName' in r and 'key' in r:
            new_animals.append({
                'name': r['canonicalName'],
                'id': r['key']
            })

    if not new_animals:
        print("No species found.")
        return

    # 3. Add to Queue (Ignore Duplicates by GBIF ID)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    count = 0
    for animal in new_animals:
        try:
            c.execute(\"\"\"
                INSERT INTO research_queue (animal_name, gbif_id, taxonomy_source, priority, status, entity_type, entity_id) 
                VALUES (?, ?, ?, ?, ?, ?, ?)
            \"\"\", (animal['name'], animal['id'], f\"GBIF_Expansion_{family_name}\", 5, \"PENDING\", \"species\", str(animal['id'])))
            count += 1
        except sqlite3.IntegrityError:
            pass # Already exists

    conn.commit()
    conn.close()
    print(f"🔭 Scout added {count} new species to the queue from family {family_name}.")

if __name__ == "__main__":
    # Test run
    expand_taxonomy("Delphinidae")
