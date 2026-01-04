# umwelt

## Architecture

### 1. Epistemic Anchoring
This project uses **GBIF IDs** (Global Biodiversity Information Facility) as the primary anchor for all research. 
- **Stable Identifiers**: Instead of common names, which are ambiguous, research is saved as `{gbif_id}.json`.
- **Alias Resolution**: Common names and synonyms are tracked as aliases within the species record.

### 2. Claim Merging (Epistemic Density)
The system is designed for **append-only accumulation** of knowledge. When an animal is researched:
1.  It checks for an existing record by GBIF ID.
2.  New sensory claims are compared with existing ones.
3.  New evidence is appended to existing claims, increasing the "density" and reliability of the data.
4.  If a new run provides better quantitative data (e.g., specific frequency ranges), the record is updated.

## Setup

1.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

2.  **Configuration:**
    *   This project uses `config.yml` for secrets management.
    *   Copy the sample configuration file:
        ```bash
        cp config_sample.yml config.yml
        ```
    *   Edit `config.yml` and add your `GEMINI_API_KEY`.

3.  **Run:**
    ```bash
    python main.py
    ```
