"""
Validator & Graph Builder.
Logic: Whenever a JSON file is saved to /vault, the Archivist runs:
1. Load: Read the JSON.
2. Flatten: Extract every object in sensory_modalities.
3. Index: Insert into a "Claims Table" in SQLite (or Neo4j) for instant querying.
"""
# TODO: Implement Archivist logic.
