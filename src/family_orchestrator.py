import sqlite3
import json
import time
import os
from src.family_researcher import FamilyResearcher
from src.family_aggregator import FamilyAggregator

DB_PATH = 'data/orchestrator.db'
SLEEP_BETWEEN_JOBS = 4 # Seconds, to stay under 15 RPM (60/15 = 4)

class FamilyOrchestrator:
    def __init__(self):
        self.researcher = FamilyResearcher()
        self.aggregator = FamilyAggregator()

    def get_next_job(self):
        conn = sqlite3.connect(DB_PATH, timeout=30)
        c = conn.cursor()
        c.execute("""
            SELECT family_name, gbif_id, order_name, representative_species 
            FROM family_research_queue 
            WHERE status = 'PENDING' 
            ORDER BY priority DESC 
            LIMIT 1
        """)
        job = c.fetchone()
        conn.close()
        return job

    def update_status(self, family_name, status):
        conn = sqlite3.connect(DB_PATH, timeout=30)
        c = conn.cursor()
        c.execute("UPDATE family_research_queue SET status = ? WHERE family_name = ?", (status, family_name))
        conn.commit()
        conn.close()

    def run_once(self):
        job = self.get_next_job()
        if not job:
            return False

        family_name, gbif_id, order_name, reps_json = job
        reps = json.loads(reps_json) if reps_json else []
        
        self.update_status(family_name, 'PROCESSING')
        
        try:
            profile = self.researcher.research_family(family_name, gbif_id, order_name, reps)
            if profile:
                self.aggregator.save_profile(profile)
                self.update_status(family_name, 'COMPLETED')
                print(f"✅ Completed research for {family_name}")
            else:
                self.update_status(family_name, 'FAILED')
                print(f"❌ Research failed for {family_name}")
        except Exception as e:
            self.update_status(family_name, 'FAILED')
            print(f"💥 Error processing {family_name}: {e}")
            
        return True

    def run_loop(self):
        print("🚀 Family Orchestrator starting...")
        while True:
            if self.run_once():
                print(f"Waiting {SLEEP_BETWEEN_JOBS}s to stay under rate limits...")
                time.sleep(SLEEP_BETWEEN_JOBS)
            else:
                print("📭 No pending family research jobs. Waiting 60s...")
                time.sleep(60)

if __name__ == "__main__":
    orchestrator = FamilyOrchestrator()
    orchestrator.run_loop()
