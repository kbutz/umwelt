import sqlite3
import re

DB_PATH = 'data/orchestrator.db'

def bulk_enqueue():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    print("🔍 Extracting unique families from species queue...")
    c.execute("SELECT DISTINCT taxonomy_source FROM research_queue WHERE taxonomy_source LIKE 'Sampler%'")
    sources = [r[0] for r in c.fetchall()]
    
    pattern = r"Sampler: (.*?) > (.*?) \("
    
    families_to_enqueue = {}
    for source in sources:
        match = re.search(pattern, source)
        if match:
            order = match.group(1).strip()
            family = match.group(2).strip()
            families_to_enqueue[family] = order

    print(f"📦 Found {len(families_to_enqueue)} families. Enqueuing...")
    
    count = 0
    for family, order in families_to_enqueue.items():
        try:
            # We skip GBIF ID and reps here; Researcher will handle it
            c.execute("""
                INSERT INTO family_research_queue (family_name, order_name, status, priority)
                VALUES (?, ?, 'PENDING', 5)
            """, (family, order))
            count += 1
        except sqlite3.IntegrityError:
            pass # Already exists
            
    conn.commit()
    conn.close()
    print(f"✨ Bulk enqueue complete. Added {count} families to the queue instantly.")

if __name__ == "__main__":
    bulk_enqueue()