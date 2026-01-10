import json
import sqlite3
import os
import sys
import glob
import wikipediaapi
import requests
from bs4 import BeautifulSoup
from ddgs import DDGS
from src.models import AnimalSensoryData
from pydantic import ValidationError
from src.gemini_adapter import GeminiAdapter
from src.ollama_adapter import OllamaAdapter

DB_PATH = 'data/orchestrator.db'
VAULT_DIR = 'data/vault'

SYSTEM_PROMPT_V4 = """
ROLE: You are an expert Sensory Biologist and Data Curator.
OBJECTIVE: Extract independent sensory claims from the provided text context. You are creating a graph of phenomenology (how the animal experiences the world).

THE 5 GOLDEN RULES:
1. Anti-Anthropocentrism: Do not ignore a sense because it is weak or irrelevant to humans. If an animal senses humidity, magnetic fields, or electrostatic pressure, extract it.
2. Context is King: You must distinguish between what an animal *can* detect vs. what it *uses* for communication.
   - Bad: "Range: 20-20k Hz"
   - Good: "Range: 20-20k Hz (Context: Physiological Limit)"
3. Mechanism Granularity: Distinguish between "having the gene" (Genetic) and "using the organ" (Anatomical).
4. Handling Disputes: If sources disagree (e.g., Magnetoreception in humans), create ONE modality entry but include MULTIPLE items in the 'evidence' list representing the conflict.
5. Null Protocol: If a specific threshold/number is unknown, OMIT the 'quantitative_data' block entirely. Do not guess or output nulls for min/max if the whole object is speculative.

OUTPUT FORMAT:
You must output strictly valid JSON with this EXACT structure:

{
  "identity": {
    "common_name": "Animal Name",
    "scientific_name": "Scientific Name",
    "taxonomy": {"class": "Mammalia", "order": "Cetacea", "family": "Delphinidae"} # class, order and family must be strings
  },
  "sensory_modalities": [
    {
      "modality_domain": "Electroreception", # MUST be one of: 'Mechanoreception', 'Chemoreception', 'Photoreception', 'Electroreception', 'Magnetoreception', 'Thermoreception', or 'Other'
      "sub_type": "Passive Electroreception",
      "stimulus_type": "Electric Field",
      "quantitative_data": {
        "min": 0.005,
        "max": null,
        "unit": "uV/cm",
        "context": "Physiological Threshold"
      },
      "mechanism": {
        "level": "Anatomical", # MUST be one of: 'Anatomical', 'Cellular', 'Neural', 'Genetic', 'Behavioral', 'Physiological', 'Ecological', 'Unspecified', 'Unknown'
        "description": "Ampullae of Lorenzini"
      },
      "evidence": [{
        "source_type": "Review Paper",
        "source_name": "Wikipedia",
        "url": "https://en.wikipedia.org/wiki/Animal_Name",
        "title": "Animal Name - Wikipedia",
        "author": "Wikipedia Contributors",
        "year": 2024,
        "citation": "Wikipedia contributors. (2024). Animal Name. In Wikipedia, The Free Encyclopedia.",
        "note": "From provided context"
      }]
    }
  ],
  "meta": {
    "data_quality_flag": "High_Evidence"
  }
}

IMPORTANT: You MUST use the exact field names and enum values specified.
- "modality_domain" MUST be one of: 'Mechanoreception', 'Chemoreception', 'Photoreception', 'Electroreception', 'Magnetoreception', 'Thermoreception', or 'Other'.
- "mechanism.level" MUST be one of: 'Anatomical', 'Cellular', 'Neural', 'Genetic', 'Behavioral', 'Physiological', 'Ecological', 'Unspecified', 'Unknown'.
- "data_quality_flag" MUST be one of: 'High_Evidence', 'Inferred_Only', 'Contested', or 'Low_Data'.
- "evidence" MUST include accurate source details. Use the provided context metadata to fill these fields.

No markdown. Just pure JSON.
"""

class Researcher:
    def __init__(self, adapter="gemini"):
        if adapter == "gemini":
            self.adapter = GeminiAdapter()
        elif adapter == "ollama":
            self.adapter = OllamaAdapter()
        else:
            raise ValueError("Invalid adapter specified")
        self.wiki = wikipediaapi.Wikipedia('UmweltProject/1.0', 'en')

    def get_job(self):
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT id, animal_name, gbif_id FROM research_queue WHERE status='PENDING' ORDER BY priority ASC LIMIT 1")
        job = c.fetchone()
        conn.close()
        return job

    def update_status(self, job_id, status, error_log=None):
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        if error_log:
            c.execute("UPDATE research_queue SET status=?, error_log=? WHERE id=?", (status, str(error_log), job_id))
        else:
            c.execute("UPDATE research_queue SET status=? WHERE id=?", (status, job_id))
        conn.commit()
        conn.close()

    def search_web(self, query, max_results=3):
        """
        Performs a DuckDuckGo search.
        """
        print(f"  🔍 Searching: {query}")
        results = []
        try:
            with DDGS() as ddgs:
                search_gen = ddgs.text(query, max_results=max_results)
                if search_gen:
                    for r in search_gen:
                        results.append(r)
        except Exception as e:
            print(f"  ⚠ Search failed for '{query}': {e}")
        return results

    def fetch_page_content(self, url, timeout=10):
        """
        Fetches and extracts main text from a URL.
        """
        print(f"  🌐 Fetching content from: {url}")
        try:
            headers = {'User-Agent': 'Mozilla/5.0 (compatible; UmweltBot/1.0; +http://umwelt-project.org)'}
            resp = requests.get(url, headers=headers, timeout=timeout)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.content, 'html.parser')
                
                # Remove unwanted elements
                for script in soup(["script", "style", "nav", "footer", "header", "aside"]):
                    script.extract()
                
                text = soup.get_text()
                
                # Clean up whitespace
                lines = (line.strip() for line in text.splitlines())
                chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
                text = '\n'.join(chunk for chunk in chunks if chunk)
                
                # Limit content length to avoid token explosion
                return text[:6000] 
            else:
                print(f"  ⚠ HTTP Error {resp.status_code} for {url}")
        except Exception as e:
            print(f"  ⚠ Failed to fetch {url}: {e}")
        return None

    def gather_context(self, animal_name, gbif_id=None):
        """
        Gather research context from Wikipedia, GBIF, and Web Search.
        """
        context_parts = []
        source_urls = []

        # 1. GBIF Context (if ID is available)
        if gbif_id:
            print(f"  🧬 Fetching GBIF data for ID: {gbif_id}...")
            gbif_url = f"https://api.gbif.org/v1/species/{gbif_id}"
            try:
                resp = requests.get(gbif_url)
                if resp.status_code == 200:
                    data = resp.json()
                    gbif_context = f"GBIF TAXONOMY:\n"
                    gbif_context += f"Scientific Name: {data.get('scientificName')}\n"
                    gbif_context += f"Kingdom: {data.get('kingdom')}\n"
                    gbif_context += f"Phylum: {data.get('phylum')}\n"
                    gbif_context += f"Class: {data.get('class')}\n"
                    gbif_context += f"Order: {data.get('order')}\n"
                    gbif_context += f"Family: {data.get('family')}\n"
                    gbif_context += f"Genus: {data.get('genus')}\n"
                    context_parts.append(gbif_context)
                    source_urls.append(f"https://www.gbif.org/species/{gbif_id}")
            except Exception as e:
                print(f"  ⚠ Failed to fetch GBIF data: {e}")

        # 2. Wikipedia Context (Solid base)
        print(f"  📚 Gathering Wikipedia context for {animal_name}...")
        page = self.wiki.page(animal_name)
        if page.exists():
            if page.summary:
                context_parts.append(f"WIKIPEDIA OVERVIEW:\n{page.summary[:1500]}")
            
            # Extract sensory sections
            sensory_keywords = ['sense', 'sensory', 'hearing', 'vision', 'smell', 'echolocation',
                               'electroreception', 'magnetoreception', 'detection', 'perception']
            
            def extract_sections(sections_dict, depth=0):
                if depth > 2: return
                for section in sections_dict:
                    if any(keyword in section.title.lower() for keyword in sensory_keywords):
                        context_parts.append(f"\nWIKIPEDIA SECTION - {section.title}:\n{section.text[:1000]}")
                    if section.sections:
                        extract_sections(section.sections, depth + 1)

            extract_sections(page.sections)
            source_urls.append(page.fullurl)
        else:
            print(f"  ⚠️  No Wikipedia page found for {animal_name}")

        # 3. Web Search Strategy (The "Real Search")
        print(f"  🕸️  Executing 3-Stage Search Strategy for {animal_name}...")
        
        # Strategy A: Broad Sweep
        broad_query = f"{animal_name} sensory biology umwelt review"
        broad_results = self.search_web(broad_query, max_results=2)
        
        # Fetch content from the top broad result
        if broad_results:
            top_url = broad_results[0]['href']
            print(f"    👉 Drilling down into top result: {top_url}")
            page_content = self.fetch_page_content(top_url)
            if page_content:
                context_parts.append(f"WEB ARTICLE ({top_url}):\n{page_content}")
                source_urls.append(top_url)
            
            for res in broad_results:
                context_parts.append(f"SEARCH SNIPPET: {res['title']}\n{res['body']}\nURL: {res['href']}")

        # Strategy B: Targeted Drill-Down (General sensory terms)
        target_query = f"{animal_name} vision hearing smell mechanoreception mechanisms"
        target_results = self.search_web(target_query, max_results=2)
        for res in target_results:
            context_parts.append(f"SEARCH SNIPPET (Targeted): {res['title']}\n{res['body']}\nURL: {res['href']}")
            if res['href'] not in source_urls:
                source_urls.append(res['href'])

        # Strategy C: Threshold Hunt (Quantitative data)
        threshold_query = f"{animal_name} sensory threshold sensitivity audiogram range"
        threshold_results = self.search_web(threshold_query, max_results=2)
        for res in threshold_results:
            context_parts.append(f"SEARCH SNIPPET (Quantitative): {res['title']}\n{res['body']}\nURL: {res['href']}")
            if res['href'] not in source_urls:
                source_urls.append(res['href'])

        # Combine contexts
        context = "\n\n".join(context_parts)
        primary_url = source_urls[0] if source_urls else None

        print(f"  ✓ Gathered {len(context)} characters of context from {len(source_urls)} sources")
        return context, primary_url

    def research_animal(self, animal_name: str, context_text: str, source_url: str = None):
        """
        1. Constructs the prompt.
        2. Calls the Local LLM.
        3. Validates output with Pydantic.
        """
        augmented_prompt = SYSTEM_PROMPT_V4
        if source_url:
            augmented_prompt += f"\n\nCONTEXT SOURCE URL: {source_url}"

        raw_json = self.adapter.research_animal(animal_name, context_text, augmented_prompt)

        if not raw_json:
            return None, "Adapter returned empty response"

        try:
            data_dict = json.loads(raw_json)
            
            # Post-process to fix common LLM errors
            processed_dict = self.post_process_data(data_dict, animal_name, source_url)
            
            validated_data = AnimalSensoryData(**processed_dict)

            return validated_data.model_dump_json(indent=2, by_alias=True), None

        except json.JSONDecodeError:
            err = f"❌ Failed to parse JSON for {animal_name}"
            print(err)
            return None, err
        except ValidationError as e:
            err = f"❌ Pydantic Validation Failed for {animal_name}: {e.json()}"
            print(err)
            return None, err
        except Exception as e:
            err = f"❌ LLM Error: {e}"
            print(err)
            return None, err

    def post_process_data(self, data_dict, animal_name, source_url):
        """
        Corrects common, predictable LLM output errors before validation.
        """
        # Correct modality_domain
        for modality in data_dict.get("sensory_modalities", []):
            if modality.get("modality_domain") == "Vision":
                modality["modality_domain"] = "Photoreception"
            if modality.get("modality_domain") == "Hearing":
                modality["modality_domain"] = "Mechanoreception"
            if modality.get("modality_domain") == "Smell" or modality.get("modality_domain") == "Taste":
                modality["modality_domain"] = "Chemoreception"

            # Correct mechanism.level
            if "mechanism" in modality and isinstance(modality["mechanism"], dict):
                level = modality["mechanism"].get("level")
                if level == "Inferred":
                    modality["mechanism"]["level"] = "Unknown"

            # Fix citation placeholder if LLM didn't replace it
            for ev in modality.get("evidence", []):
                if "Animal Name" in ev.get("citation", ""):
                    ev["citation"] = ev["citation"].replace("Animal Name", animal_name)
                if not ev.get("url") and source_url:
                    ev["url"] = source_url
        
        # Correct data_quality_flag
        if data_dict.get("meta", {}).get("data_quality_flag") == "Low_Evidence":
            data_dict["meta"]["data_quality_flag"] = "Low_Data"

        # Correct taxonomy fields
        if "identity" not in data_dict:
            data_dict["identity"] = {}
        if "taxonomy" not in data_dict["identity"]:
            data_dict["identity"]["taxonomy"] = {}
        
        # Ensure common_name and scientific_name exist
        if not data_dict["identity"].get("common_name"):
            data_dict["identity"]["common_name"] = animal_name
        if not data_dict["identity"].get("scientific_name"):
            data_dict["identity"]["scientific_name"] = animal_name

        if "class" in data_dict["identity"]["taxonomy"]:
            data_dict["identity"]["taxonomy"]["class"] = str(data_dict["identity"]["taxonomy"]["class"])
        else:
            data_dict["identity"]["taxonomy"]["class"] = "Unknown"
            
        if "order" in data_dict["identity"]["taxonomy"]:
            data_dict["identity"]["taxonomy"]["order"] = str(data_dict["identity"]["taxonomy"]["order"])
        else:
            data_dict["identity"]["taxonomy"]["order"] = "Unknown"

        if "family" in data_dict["identity"]["taxonomy"]:
            data_dict["identity"]["taxonomy"]["family"] = str(data_dict["identity"]["taxonomy"]["family"])
        else:
            data_dict["identity"]["taxonomy"]["family"] = "Unknown"

        return data_dict

    def save_to_vault(self, animal_name, gbif_id, new_json_data):
        """
        Anchors data by GBIF ID and merges new claims into existing records.
        """
        new_data = json.loads(new_json_data)
        scientific_name = new_data.get('identity', {}).get('scientific_name', animal_name)
        
        # New Naming Convention: GBIF_ID_Scientific_Name.json (no whitespace)
        if gbif_id:
            filename = f"{gbif_id}_{scientific_name.replace(' ', '_')}.json"
        else:
            filename = f"{animal_name.replace(' ', '_')}.json"
            
        filepath = os.path.join(VAULT_DIR, filename)
        
        if os.path.exists(filepath):
            print(f"  📂 Existing record found for {scientific_name} ({filename}). Merging claims...")
            with open(filepath, 'r') as f:
                existing_data = json.load(f)
            
            # 1. Update Identity / Aliases
            if animal_name not in existing_data['identity'].get('aliases', []):
                if 'aliases' not in existing_data['identity']:
                    existing_data['identity']['aliases'] = []
                if animal_name != existing_data['identity']['common_name'] and animal_name != existing_data['identity']['scientific_name']:
                    existing_data['identity']['aliases'].append(animal_name)
            
            # 2. Merge Modalities
            existing_modalities = existing_data.get('sensory_modalities', [])
            for new_mod in new_data.get('sensory_modalities', []):
                # Look for matching modality/subtype
                match = next((m for m in existing_modalities 
                             if m['modality_domain'] == new_mod['modality_domain'] 
                             and m['sub_type'] == new_mod['sub_type']), None)
                
                if match:
                    # Append evidence to existing modality
                    # Check for duplicate citations before appending
                    existing_citations = [e.get('citation') for e in match.get('evidence', [])]
                    for ev in new_mod.get('evidence', []):
                        if ev.get('citation') not in existing_citations:
                            match['evidence'].append(ev)
                    
                    # Update quantitative data if the new one is 'better' (has more fields)
                    if not match.get('quantitative_data') and new_mod.get('quantitative_data'):
                        match['quantitative_data'] = new_mod['quantitative_data']
                else:
                    # New modality, just add it
                    existing_modalities.append(new_mod)
            
            existing_data['sensory_modalities'] = existing_modalities
            final_data = existing_data
        else:
            # Check for old naming convention if scientific name match fails
            # This handles cases where we renamed manually but didn't update the logic yet
            old_pattern = os.path.join(VAULT_DIR, f"{gbif_id} - *.json")
            old_matches = glob.glob(old_pattern)
            if old_matches:
                filepath = old_matches[0]
                print(f"  📂 Existing record found (old format) for {scientific_name} ({os.path.basename(filepath)}). Merging...")
                # ... same merge logic could go here, but for now we just rename then merge
            
            final_data = new_data
            if gbif_id:
                final_data['identity']['gbif_id'] = gbif_id

        with open(filepath, 'w') as f:
            json.dump(final_data, f, indent=2)
        print(f"✓ Saved/Merged research to {filepath}")

    def is_already_researched(self, gbif_id):
        """Checks if a file for this GBIF ID already exists in the vault (any format)."""
        if not gbif_id:
            return False
        # Match both new and old formats
        patterns = [
            os.path.join(VAULT_DIR, f"{gbif_id}_*.json"),
            os.path.join(VAULT_DIR, f"{gbif_id} - *.json")
        ]
        for pattern in patterns:
            if glob.glob(pattern):
                return True
        return False

    def run(self):
        job = self.get_job()
        if not job:
            print("No pending jobs.")
            return False

        job_id, animal_name, gbif_id = job
        
        # Skip if already researched
        if self.is_already_researched(gbif_id):
            print(f"⏩ Skipping {animal_name} (GBIF ID: {gbif_id}) - already in vault.")
            self.update_status(job_id, "COMPLETED")
            return True

        self.update_status(job_id, "PROCESSING")

        try:
            context, source_url = self.gather_context(animal_name, gbif_id=gbif_id)
            result_json, error = self.research_animal(animal_name, context, source_url)

            if result_json:
                self.save_to_vault(animal_name, gbif_id, result_json)
                self.update_status(job_id, "COMPLETED")
            else:
                self.update_status(job_id, "FAILED", error_log=error)
                print(f"❌ Job aborted for {animal_name}. Error logged to DB.")
                # sys.exit(1) # Abort the process
        except Exception as e:
            print(f"Job failed: {e}")
            import traceback
            traceback.print_exc()
            self.update_status(job_id, "FAILED", error_log=str(e))
            # sys.exit(1) # Abort the process
        
        return True

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run the researcher with a specific adapter.")
    parser.add_argument("--adapter", type=str, default="gemini", help="The adapter to use (gemini or ollama)")
    args = parser.parse_args()

    agent = Researcher(adapter=args.adapter)
    agent.run()
