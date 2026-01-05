import requests
import sqlite3
import os
import json
from src.models import TaxonFamily

DB_PATH = 'data/orchestrator.db'
ANIMALIA_KEY = 1

def get_families_for_order(order_name, limit=10):
# ... (rest of the function stays same)
    """Query GBIF for families within an order, ranked by species count."""
    print(f"🔭 Searching for families in order: {order_name}")
    
    # 1. Resolve order key
    url = "https://api.gbif.org/v1/species/match"
    params = {"name": order_name, "rank": "ORDER", "strict": True}
    resp = requests.get(url, params=params)
    data = resp.json()
    if data.get("matchType") == "NONE":
        print(f"  ⚠ Could not find GBIF match for order: {order_name}")
        return []
    order_key = data.get("usageKey")

    # 2. Get families
    url = "https://api.gbif.org/v1/species/search"
    params = {
        "higherTaxonKey": order_key,
        "rank": "FAMILY",
        "status": "ACCEPTED",
        "limit": 100
    }
    resp = requests.get(url, params=params)
    families = resp.json().get("results", [])
    
    # Sort by species count (numDescendants)
    families.sort(key=lambda x: x.get("numDescendants", 0), reverse=True)
    return families[:limit]

def get_representative_species(family_key, limit=3):
    """Get top N species for a family to use as research context."""
    url = "https://api.gbif.org/v1/species/search"
    params = {
        "higherTaxonKey": family_key,
        "rank": "SPECIES",
        "status": "ACCEPTED",
        "limit": limit
    }
    resp = requests.get(url, params=params)
    return [s.get("canonicalName") for s in resp.json().get("results", []) if "canonicalName" in s]

def enqueue_families(order_name, limit=5):
    families = get_families_for_order(order_name, limit=limit)
    
    conn = sqlite3.connect(DB_PATH, timeout=30)
    c = conn.cursor()
    
    count = 0
    for f in families:
        name = f.get("canonicalName")
        gbif_id = f.get("key")
        
        reps = get_representative_species(gbif_id)
        reps_json = json.dumps(reps)
        
        try:
            c.execute("""
                INSERT INTO family_research_queue (family_name, gbif_id, order_name, representative_species, status, priority)
                VALUES (?, ?, ?, ?, 'PENDING', 5)
            """, (name, gbif_id, order_name, reps_json))
            print(f"  ➕ Enqueued family: {name} (ID: {gbif_id})")
            count += 1
        except sqlite3.IntegrityError:
            print(f"  ⏩ Family already enqueued: {name}")
            
    conn.commit()
    conn.close()
    print(f"🔭 FamilyScout enqueued {count} families from {order_name}.")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Discover and enqueue families for research.")
    parser.add_argument("order", type=str, help="Order name (e.g. Cetacea)")
    parser.add_argument("--limit", type=int, default=5, help="Number of families to enqueue")
    
    args = parser.parse_args()
    enqueue_families(args.order, limit=args.limit)
