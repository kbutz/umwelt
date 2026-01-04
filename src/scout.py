import requests
import sqlite3
import os

DB_PATH = 'data/orchestrator.db'
GBIF_BACKBONE_KEY = "d7dddbf4-2cf0-4f39-9b2a-bb099caae36c"

def get_family_key(family_name):
    """Matches a family name to its canonical GBIF backbone key."""
    url = "https://api.gbif.org/v1/species/match"
    params = {
        "name": family_name,
        "rank": "FAMILY",
        "strict": True
    }
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        if data.get("matchType") == "NONE":
            print(f"  ⚠ Could not find canonical GBIF match for family: {family_name}")
            return None
        return data.get("usageKey")
    except Exception as e:
        print(f"  ❌ Error matching family name: {e}")
        return None

def expand_taxonomy(family_name, limit=50, offset=0):
    print(f"🔭 Scout looking for members of family: {family_name} (limit={limit}, offset={offset})")
    
    # 1. Resolve canonical Family Key
    family_key = get_family_key(family_name)
    if not family_key:
        return

    # 2. Query GBIF for species UNDER this family key
    url = "https://api.gbif.org/v1/species/search"
    params = {
        "higherTaxonKey": family_key,
        "rank": "SPECIES",
        "status": "ACCEPTED",
        "datasetKey": GBIF_BACKBONE_KEY,
        "limit": limit,
        "offset": offset
    }
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        print(f"Error querying GBIF: {e}")
        return

    # 3. Extract Names and IDs
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

    # 4. Add to Queue (Ignore Duplicates by GBIF ID)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    count = 0
    for animal in new_animals:
        try:
            c.execute("""
                INSERT INTO research_queue (animal_name, gbif_id, taxonomy_source, priority, status, entity_type, entity_id) 
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (animal['name'], animal['id'], f"GBIF_Expansion_{family_name}", 5, "PENDING", "species", str(animal['id'])))
            count += 1
        except sqlite3.IntegrityError:
            pass # Already exists

    conn.commit()
    conn.close()
    print(f"🔭 Scout added {count} new species to the queue from family {family_name}.")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Scout species for a given family.")
    parser.add_argument("family", type=str, help="The biological family name (e.g., Felidae)")
    parser.add_argument("--limit", type=int, default=50, help="Number of results to fetch")
    parser.add_argument("--offset", type=int, default=0, help="Pagination offset")
    
    args = parser.parse_args()
    expand_taxonomy(args.family, limit=args.limit, offset=args.offset)
