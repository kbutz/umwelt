# First Production Run - Implementation Guide

## POC Status: ✅ FUNCTIONAL

All three microservices (Scout, Researcher, Archivist) are implemented and tested with seed data. The core claims-based architecture is working end-to-end.

## Current Test Results

**Seed Animals Processed:** 5
- Bottlenose Dolphin (3 claims)
- Great White Shark (3 claims)
- Monarch Butterfly (2 claims)
- Naked Mole Rat (2 claims)
- Human (2 claims)

**Total Claims Indexed:** 12

**Claims by Modality Domain:**
- Mechanoreception: 3
- Photoreception: 2
- Magnetoreception: 2
- Electroreception: 2
- Thermoreception: 1
- Chemoreception: 1
- Nociception: 1

## Recommended First Production Run

### Goal
Validate LLM extraction quality with real web search before scaling to hundreds of animals.

### Prerequisites

1. **Fix File Path Inconsistency**
   - Update `src/db_init.py` to create database in `data/sensory_graph.db` (not root)
   - Update `src/populate_seed_data.py` to use `data/sensory_graph.db`
   - Ensure all scripts reference consistent paths

2. **Implement Real Search** (in `researcher.py`)
   - Replace mock `gather_context()` with actual web search
   - Implement 3-stage search strategy:
     - **Broad Sweep**: `"{animal} sensory biology umwelt review"`
     - **Targeted Drill-Down**: `"{animal} {modality} mechanism anatomical"`
     - **Threshold Hunt**: `"{animal} {modality} threshold audiogram sensitivity"`
   - Options:
     - DuckDuckGo API (recommended)
     - Wikipedia API + Wikidata SPARQL
     - Custom web scraping

3. **Test LLM Connection**
   - Verify Ollama is running: `ollama list`
   - Test with a model: `ollama run llama3`
   - Update `researcher.py` model name if needed

### Step-by-Step Execution

#### Step 1: Expand One Family (Scout Test)

```bash
# Expand Delphinidae (dolphin family) - should add ~20-50 species
python3 src/scout.py
```

**Expected Output:**
```
🔭 Scout looking for: Delphinidae
🔭 Scout added 23 new species to the queue from family Delphinidae.
```

**Verify:**
```bash
sqlite3 data/orchestrator.db "SELECT COUNT(*) FROM research_queue WHERE taxonomy_source LIKE 'GBIF_Expansion%';"
```

#### Step 2: Run Researcher on 3-5 Animals

```bash
# Process first pending job
python3 src/researcher.py

# Repeat 2-4 more times to process additional animals
python3 src/researcher.py
python3 src/researcher.py
```

**Expected Output:**
```
🧠 Researcher analyzing: Tursiops truncatus...
Saved research to data/vault/Tursiops_truncatus.json
```

**Check Status:**
```bash
sqlite3 data/orchestrator.db "SELECT animal_name, status FROM research_queue WHERE status='COMPLETED';"
```

#### Step 3: Manual Quality Inspection

**Critical Step:** Don't scale until you verify quality!

```bash
# List all vault files
ls -lh data/vault/

# Inspect one JSON file
cat data/vault/[newest_file].json | python3 -m json.tool
```

**Quality Checklist:**
- [ ] Evidence citations are real (not hallucinated)
- [ ] Quantitative data has proper units (Hz, nm, uV/cm)
- [ ] Context field distinguishes measurement types
- [ ] Mechanism descriptions are anatomically accurate
- [ ] No "null" values for entire quantitative_data blocks (should be omitted)
- [ ] Data quality flag is appropriate

**If quality is poor:**
- Tune `SYSTEM_PROMPT_V4` in `researcher.py`
- Add more context to searches
- Try a different LLM model

#### Step 4: Run Archivist and Analyze

```bash
# Index all claims
python3 src/archivist.py

# Run post-processing
python3 src/claim_linker.py
```

**Expected Output:**
```
Claims table initialized.
Found 8 files in vault.
Archived claims for [animals...]

Claim Density Report:
[Species list with claim counts]
```

#### Step 5: Query for Patterns

Test the "Web of Senses" concept with SQL queries:

```bash
sqlite3 data/orchestrator.db << 'EOF'
.headers on
.mode column

-- Find all animals with echolocation
SELECT 'Echolocators:' as category;
SELECT animal, sub_type, min_val, max_val, unit
FROM claims
WHERE sub_type LIKE '%Echolocation%';

-- Find overlapping hearing ranges
SELECT 'Hearing Ranges (Hz):' as category;
SELECT animal, min_val, max_val
FROM claims
WHERE sub_type LIKE '%Hearing%' AND unit = 'Hz'
ORDER BY min_val;

-- Find animals with electroreception
SELECT 'Electroreceptors:' as category;
SELECT animal, sub_type, stimulus
FROM claims
WHERE modality = 'Electroreception';

-- Check claim density
SELECT 'Claims per Animal:' as category;
SELECT animal, COUNT(*) as claim_count
FROM claims
GROUP BY animal
ORDER BY claim_count DESC;
EOF
```

#### Step 6: Review and Iterate

Based on the results:

**If successful:**
- Scale to 20-50 animals
- Add more families (Chiroptera - bats, Cetacea - whales)
- Run overnight processing

**If issues found:**
- Review and fix search quality
- Adjust LLM prompt
- Add more validation rules
- Process 5 more animals and re-evaluate

### Scale-Up Strategy (After Validation)

Once you've validated quality with 5-10 animals:

1. **Expand Multiple Families:**
   ```bash
   # Bats (known for echolocation)
   python3 -c "from src.scout import expand_taxonomy; expand_taxonomy('Chiroptera')"

   # Whales (infrasound + ultrasound)
   python3 -c "from src.scout import expand_taxonomy; expand_taxonomy('Cetacea')"

   # Sharks (electroreception)
   python3 -c "from src.scout import expand_taxonomy; expand_taxonomy('Selachimorpha')"
   ```

2. **Run Batch Processing:**
   ```bash
   # Process 10 animals in a loop
   for i in {1..10}; do
     python3 src/researcher.py
     sleep 5  # Rate limiting
   done
   ```

3. **Monitor Progress:**
   ```bash
   watch -n 30 'sqlite3 data/orchestrator.db "SELECT status, COUNT(*) FROM research_queue GROUP BY status;"'
   ```

4. **Archive Regularly:**
   ```bash
   python3 src/archivist.py
   python3 src/claim_linker.py
   ```

### Success Metrics

After the first production run, you should have:

- ✅ **8-10 animals** with complete sensory profiles
- ✅ **20-40 claims** indexed and queryable
- ✅ **Evidence citations** for all claims
- ✅ **Multiple modality domains** represented (not just vision/hearing)
- ✅ **Quantitative ranges** for at least 50% of claims
- ✅ **No claim density imbalance** > 5x ratio
- ✅ **Query results** showing sensory overlaps between species

### Known Issues to Monitor

1. **LLM Hallucination:** Watch for made-up citations or unrealistic values
2. **Unit Confusion:** Verify kHz vs Hz, nm vs μm conversions
3. **Overfitting:** Ensure diverse modalities, not just human-centric senses
4. **Context Collapse:** LLM should distinguish "can detect" vs "uses for communication"
5. **Evidence Quality:** Prefer "Behavioral Audiogram" over "Genetic Inference"

### Troubleshooting

**Problem:** Researcher fails with Pydantic validation error
- **Solution:** Check JSON output structure, update system prompt for clarity

**Problem:** Scout finds no species
- **Solution:** Try different family names, check GBIF API status

**Problem:** Claim density heavily imbalanced
- **Solution:** LLM may be over-extracting for familiar animals, tune prompt for consistency

**Problem:** Database locked errors
- **Solution:** Add retry logic, ensure only one process writes at a time

### Next Steps After First Run

1. **Visualization Layer**
   - Export claims to Gephi format
   - Create force-directed graph
   - Identify clusters (echolocators, magnetoreceptors, etc.)

2. **Advanced Queries**
   - Find sensory overlaps by frequency range
   - Identify animals with unique modality combinations
   - Calculate "sensory distance" between species

3. **Web Interface**
   - Build simple query UI
   - Display animal profiles
   - Interactive graph exploration

4. **Continuous Integration**
   - Schedule periodic Scout runs
   - Auto-process new animals
   - Daily claim_linker reports

---

## Summary

This first production run is designed to validate the entire pipeline with a small, manageable dataset. Focus on **quality over quantity**—don't scale until you're confident the LLM is extracting accurate, well-cited sensory data that follows the v4.0 schema principles.

Once validated, the system can scale to hundreds or thousands of animals with minimal oversight.
