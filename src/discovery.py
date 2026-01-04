import requests
import sqlite3
import os
import json

DB_PATH = 'data/orchestrator.db'
ANIMALIA_KEY = 1

def get_all_orders():
    """Fetches all accepted orders under Animalia."""
    print("📡 Fetching all orders in Animalia...")
    url = "https://api.gbif.org/v1/species/search"
    params = {
        "higherTaxonKey": ANIMALIA_KEY,
        "rank": "ORDER",
        "status": "ACCEPTED",
        "limit": 1000  # We know there are ~644
    }
    response = requests.get(url, params=params)
    response.raise_for_status()
    data = response.json()
    return data.get("results", [])

def get_top_families_for_order(order_key, limit=10):
    """Fetches top families for a given order, ranked by number of descendants."""
    url = "https://api.gbif.org/v1/species/search"
    params = {
        "higherTaxonKey": order_key,
        "rank": "FAMILY",
        "status": "ACCEPTED",
        "limit": 100 # Fetch a pool to sort
    }
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        families = data.get("results", [])
        # Sort by numDescendants descending
        families.sort(key=lambda x: x.get("numDescendants", 0), reverse=True)
        return families[:limit]
    except Exception as e:
        print(f"  ❌ Error fetching families for order {order_key}: {e}")
        return []

def get_representative_species(family_key):
    """Fetches the most 'prominent' species for a family."""
    url = "https://api.gbif.org/v1/species/search"
    params = {
        "higherTaxonKey": family_key,
        "rank": "SPECIES",
        "status": "ACCEPTED",
        "limit": 1
    }
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        results = data.get("results", [])
        if results:
            return results[0]
    except Exception as e:
        print(f"  ❌ Error fetching species for family {family_key}: {e}")
    return None

def main(sample_only=True):
    orders = get_all_orders()
    print(f"✅ Found {len(orders)} orders.")
    
    if sample_only:
        orders = orders[:5] # Just look at first 5 for now
        print(f"🧪 Running in SAMPLE MODE (first {len(orders)} orders).")

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    total_added = 0
    for order in orders:
        order_name = order.get("canonicalName")
        order_key = order.get("key")
        print(f"\n🌿 Processing Order: {order_name} ({order_key})")
        
        families = get_top_families_for_order(order_key)
        print(f"  Found {len(families)} families.")
        
        for family in families:
            family_name = family.get("canonicalName")
            family_key = family.get("key")
            
            species = get_representative_species(family_key)
            if species:
                sci_name = species.get("scientificName")
                canon_name = species.get("canonicalName")
                gbif_id = species.get("key")
                
                try:
                    c.execute("""
                        INSERT INTO research_queue (animal_name, gbif_id, taxonomy_source, priority, status, entity_type, entity_id) 
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (canon_name, gbif_id, f"Discovery_Order_{order_name}", 10, "PENDING", "species", str(gbif_id)))
                    print(f"    ➕ Added: {canon_name} (Family: {family_name})")
                    total_added += 1
                except sqlite3.IntegrityError:
                    print(f"    ⏩ Already in queue: {canon_name}")
            else:
                print(f"    ⚠️ No representative species found for family: {family_name}")

    conn.commit()
    conn.close()
    print(f"\n✨ Discovery complete. Added {total_added} new items to the research queue.")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--full", action="store_true", help="Run for all orders (default is sample of 5)")
    args = parser.parse_args()
    
    main(sample_only=not args.full)
