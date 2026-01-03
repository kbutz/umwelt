# Technical Architecture: Engineering Blueprint

This is the engineering blueprint. We will move from a "Script" to a System using a modular Micro-Services Architecture (even if running on one machine).

This separates the "Brain" (finding animals), the "Hands" (researching them), and the "Memory" (storing the graph).

## 1. High-Level Architecture Diagram

This architecture has three independent loops running in parallel:

- **The Scout (Discovery Loop)**: Finds new animals to research (via Taxonomy APIs).
- **The Researcher (Worker Loop)**: Takes an animal, performs the "Deep Search," and extracts claims.
- **The Archivist (Storage Loop)**: Validates JSON, saves to the Vault, and updates the Graph.

## 2. The Core Components

### A. The State Database (orchestrator.db)

We need a robust queue to manage thousands of animals. We will use SQLite but treat it like a message broker.

**Table: research_queue**

| Column | Type | Purpose |
| :--- | :--- | :--- |
| id | INT | Primary Key |
| animal_name | TEXT | Unique Identifier |
| taxonomy_source | TEXT | e.g., "Seed List", "GBIF_Expansion" |
| priority | INT | 1 (High/Seed) to 10 (Low/Random) |
| status | TEXT | PENDING, PROCESSING, COMPLETED, FAILED |
| attempts | INT | Retry counter |

### B. The Directory Structure

Set up your project folder like this to keep "Claims" separate from "Code":

```
/web_of_senses
│
├── /data
│   ├── orchestrator.db      # The State DB
│   ├── /vault               # RAW JSON files (One file per animal)
│   └── /graph_export        # Cleaned Gephi/Neo4j files
│
├── /src
│   ├── scout.py             # The Taxonomy Walker (Finds animals)
│   ├── researcher.py        # The Agent (LLM + Search)
│   ├── archivist.py         # Validator & Graph Builder
│   └── config.py            # API Keys & Prompts
│
└── main.py                  # The Controller (runs the loops)
```

## 3. The "Scout" (Automated Discovery)

How do we grow the list automatically?

We should not ask the LLM to "guess" new animals (it repeats common ones). Instead, we use the GBIF API (Global Biodiversity Information Facility) or Wikidata to "walk the tree."

**Logic**:

1. **Input**: A target family (e.g., Delphinidae - Dolphins).
2. **Action**: Fetch top 50 species by "Observation Count" (ensures we research animals that actually have data).
3. **Output**: Add to research_queue with priority=5.

**Code Snippet (src/scout.py)**:

```python
import requests
import sqlite3

def expand_taxonomy(family_name, db_path):
    # 1. Query GBIF for species in this family
    url = "https://api.gbif.org/v1/species/search"
    params = {
        "q": family_name,
        "rank": "SPECIES",
        "status": "ACCEPTED",
        "limit": 20
    }
    response = requests.get(url, params=params).json()

    # 2. Extract Names
    new_animals = [r['canonicalName'] for r in response['results'] if 'canonicalName' in r]

    # 3. Add to Queue (Ignore Duplicates)
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    for animal in new_animals:
        try:
            c.execute("INSERT INTO research_queue (animal_name, priority) VALUES (?, ?)",
                      (animal, 5))
            print(f"🔭 Scout found: {animal}")
        except sqlite3.IntegrityError:
            pass # Already exists
    conn.commit()
    conn.close()
```

## 4. The "Researcher" (The Agent)

This is where the "System Prompt" and "Schema" live.

**Technical Requirement**: This module needs to be Class-Based so we can swap out the "Brain" (Ollama vs. OpenAI) without rewriting the logic.

**Logic**:

1. **Fetch**: Get job from SQLite (status='PENDING' with highest Priority).
2. **Context Assembly**: Run 3 distinct DuckDuckGo searches (General, Mechanism, Threshold).
3. **Inference**: Send 3,000 words of context to the LLM with the Schema v4.0 instructions.
4. **Validation**: Use Pydantic to ensure the JSON matches the schema.
   - **Fail**: Increment retry count.
   - **Pass**: Save to `/vault/{animal_name}.json`.

## 5. The "Archivist" (Storage & Linking)

We don't want to query thousands of JSON files to find "Who has Echolocation?" We need a secondary index.

**Logic**: Whenever a JSON file is saved to `/vault`, the Archivist runs:

1. **Load**: Read the JSON.
2. **Flatten**: Extract every object in `sensory_modalities`.
3. **Index**: Insert into a "Claims Table" in SQLite (or Neo4j) for instant querying.

**The "Claims Index" Table**:

| animal | modality | sub_type | stimulus | min_val | max_val | unit |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| Bat | Acoustic | Echolocation | Pressure | 20 | 120 | kHz |
| Dolphin | Acoustic | Echolocation | Pressure | 150 | 180 | kHz |

This allows you to instantly run SQL queries like:
```sql
SELECT * FROM claims WHERE sub_type = 'Echolocation'
```

## 6. Execution Strategy (How to Build)

### Phase 1: The Skeleton (Day 1)

1. Create the folders and `orchestrator.db`.
2. Write a simple `main.py` that manually inserts the Seed List (Dolphin, Shark, Mole, etc.) into the DB.
3. Verify the database viewer works.

### Phase 2: The Agent (Day 2)

1. Build `researcher.py`. Connect it to Ollama.
2. Run the Seed List.
3. **Crucial Step**: Manually inspect the JSON outputs in `/vault`. Are the units correct? Is the evidence cited? Tune the prompt.

### Phase 3: The Automation (Day 3)

1. Enable `scout.py`.
2. Set it to target "Chiroptera" (Bats) and "Cetacea" (Whales).
3. Watch the queue grow from 10 to 100 automatically.
4. Let the Researcher run overnight.

### Phase 4: The Interface (Day 4)

1. Build `archivist.py`.
2. Run a script to generate a Gephi graph file from the finished data.
3. Visualize your first "Cluster".

## Next Step

Would you like the SQL Setup Script (to create the tables) or the Pydantic Validator Code (to ensure the LLM output is perfect) first?
