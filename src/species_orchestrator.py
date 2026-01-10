import time
import sys
import os

# Ensure the root directory is in the path so we can import from src
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.researcher import Researcher

SLEEP_BETWEEN_JOBS = 6 # Seconds

class SpeciesOrchestrator:
    def __init__(self, adapter="gemini"):
        self.researcher = Researcher(adapter=adapter)

    def run_loop(self):
        print("🚀 Species Orchestrator starting...")
        while True:
            # researcher.run() now returns True if it processed a job (even if failed), False if no jobs
            if self.researcher.run():
                print(f"Waiting {SLEEP_BETWEEN_JOBS}s to stay under rate limits...")
                time.sleep(SLEEP_BETWEEN_JOBS)
            else:
                print("📭 No pending species research jobs. Waiting 60s...")
                time.sleep(60)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Run the species researcher loop.")
    parser.add_argument("--adapter", type=str, default="gemini", help="The adapter to use (gemini or ollama)")
    args = parser.parse_args()

    orchestrator = SpeciesOrchestrator(adapter=args.adapter)
    orchestrator.run_loop()
