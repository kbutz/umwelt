import requests
import sqlite3
import os
import wikipediaapi

DB_PATH = 'data/orchestrator.db'
ANIMALIA_KEY = 1
WIKI_USER_AGENT = "UmweltProject/1.0 (https://github.com/your-repo-here; contact@example.com)"

class TaxonomySampler:
    def __init__(self, families_per_order=5):
        self.families_per_order = families_per_order
        self.wiki = wikipediaapi.Wikipedia(user_agent=WIKI_USER_AGENT, language='en')
        self.conn = sqlite3.connect(DB_PATH)

    def has_wiki(self, name):
        """Quick check if a Wikipedia page exists."""
        try:
            return self.wiki.page(name).exists()
        except:
            return False

    def get_all_orders(self):
        print("📡 Fetching orders in Animalia...")
        url = "https://api.gbif.org/v1/species/search"
        params = {
            "higherTaxonKey": ANIMALIA_KEY,
            "rank": "ORDER",
            "status": "ACCEPTED",
            "limit": 1000
        }
        resp = requests.get(url, params=params)
        resp.raise_for_status()
        # Filter out extinct/fossil orders
        return [o for o in resp.json().get("results", []) if not o.get("extinct")]

    def score_families(self, order_key):
        """Fetches families and scores them by richness and documentation."""
        url = "https://api.gbif.org/v1/species/search"
        params = {
            "higherTaxonKey": order_key,
            "rank": "FAMILY",
            "status": "ACCEPTED",
            "limit": 50 
        }
        resp = requests.get(url, params=params)
        families = resp.json().get("results", [])
        
        scored = []
        for f in families:
            name = f.get("canonicalName")
            # Heuristic Score:
            # 1. log10 of species count (richness)
            # 2. +5 points for having a Wikipedia page
            richness = f.get("numDescendants", 1)
            wiki_bonus = 5 if self.has_wiki(name) else 0
            score = (richness ** 0.5) + wiki_bonus # Using sqrt to avoid extreme skew
            
            scored.append({
                "name": name,
                "key": f.get("key"),
                "score": score,
                "reason": f"Richness: {richness}, Wiki: {bool(wiki_bonus)}"
            })
            
        scored.sort(key=lambda x: x['score'], reverse=True)
        return scored[:self.families_per_order]

    def pick_best_species(self, family_key, family_name):
        """Picks a species that is likely to have good research data."""
        url = "https://api.gbif.org/v1/species/search"
        params = {
            "higherTaxonKey": family_key,
            "rank": "SPECIES",
            "status": "ACCEPTED",
            "limit": 20 # Look at top 20
        }
        resp = requests.get(url, params=params)
        species_list = resp.json().get("results", [])
        
        # Priority: Species with a Wikipedia page
        for s in species_list:
            name = s.get("canonicalName")
            if self.has_wiki(name):
                return s, "Wiki-confirmed"
        
        # Fallback: Just the most common one in GBIF
        if species_list:
            return species_list[0], "GBIF-default"
        
        return None, None

    def run(self, limit_orders=None):
        orders = self.get_all_orders()
        if limit_orders:
            orders = orders[:limit_orders]
        
        print(f"✅ Sampling {len(orders)} orders...")
        
        c = self.conn.cursor()
        total_added = 0
        
        for order in orders:
            order_name = order.get("canonicalName")
            print(f"\n🌿 Order: {order_name}")
            
            top_families = self.score_families(order.get("key"))
            if not top_families:
                print(f"  ⚠️ No families found for order {order_name}")
                continue

            for f in top_families:
                species, pick_method = self.pick_best_species(f['key'], f['name'])
                if species:
                    sci_name = species.get("scientificName")
                    canon_name = species.get("canonicalName")
                    gbif_id = species.get("key")
                    
                    reason = f"Sampler: {order_name} > {f['name']} ({f['reason']}, Pick: {pick_method})"
                    
                    try:
                        c.execute("""
                            INSERT INTO research_queue (animal_name, gbif_id, taxonomy_source, priority, status, entity_type, entity_id) 
                            VALUES (?, ?, ?, ?, ?, ?, ?)
                        """, (canon_name, gbif_id, reason, 10, "PENDING", "species", str(gbif_id)))
                        print(f"  ➕ {canon_name} ({f['name']})")
                        total_added += 1
                    except sqlite3.IntegrityError:
                        print(f"  ⏩ Already in queue: {canon_name} ({f['name']})")
                else:
                    print(f"  ⚠️ No species found for family: {f['name']}")

        self.conn.commit()
        print(f"\n✨ Sampler finished. Added {total_added} species.")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Sample families and species across Animalia.")
    parser.add_argument("--limit", type=int, default=None, help="Limit the number of orders to process (for testing)")
    parser.add_argument("--families", type=int, default=3, help="Number of families to sample per order")
    args = parser.parse_args()

    sampler = TaxonomySampler(families_per_order=args.families)
    sampler.run(limit_orders=args.limit)
