# Source Code Documentation

This directory contains the core scripts for the **Web of Senses** project. These scripts handle database initialization, data population, post-processing, and auditing.

## Setup and Usage

To set up the project locally, follow these steps in order. All commands should be run from the root directory of the repository (or the `src` directory, but the instructions below assume the root).

### 1. Initialize the Database

Run `db_init.py` to create the SQLite database schema. This will create a file named `sensory_graph.db`.

```bash
python src/db_init.py
```

**What it does:**
- Creates a new SQLite database `sensory_graph.db`.
- Defines the `animals` table with columns for taxonomy, sensory modalities, and metadata.
- **Note:** If the database file already exists, it will be deleted and recreated.

### 2. Populate Seed Data

Run `populate_seed_data.py` to insert initial species data into the database.

```bash
python src/populate_seed_data.py
```

**What it does:**
- Reads a hardcoded list of seed data (including Bottlenose Dolphin, Great White Shark, Monarch Butterfly, Naked Mole Rat, and Human).
- Inserts this data into the `animals` table.

### 3. Post-Processing and Claim Linking

Run `claim_linker.py` to normalize data units and analyze claim density.

```bash
python src/claim_linker.py
```

**What it does:**
- **Unit Normalization:** Converts units in `quantitative_data` to base units (e.g., kHz to Hz, mm to nm).
- **Claim Density Report:** prints a report showing the number of sensory claims per species.
- **Bias Check:** Warns if there is a significant imbalance in the number of claims between species (e.g., > 5x ratio).

### 4. Audit Data

Run `audit_shark.py` to verify specific data points.

```bash
python src/audit_shark.py
```

**What it does:**
- Fetches the Great White Shark record from the database.
- Verifies that "Electric Field" stimulus and "Ampullae of Lorenzini" mechanism are present.
- Prints "AUDIT PASSED" if the data is correct.

## File Descriptions

- **`db_init.py`**: Database schema creation script.
- **`populate_seed_data.py`**: ETL script to load initial JSON data into SQLite.
- **`claim_linker.py`**: Post-processing script for unit normalization and metadata analysis.
- **`audit_shark.py`**: A specialized test script to validate specific entries in the knowledge graph.
