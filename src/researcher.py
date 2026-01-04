import json
import sqlite3
import os
import wikipediaapi
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
    "taxonomy": {"class": "Mammalia", "order": "Cetacea"} # class and order must be strings
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
        "level": "Anatomical",
        "description": "Ampullae of Lorenzini"
      },
      "evidence": [{
        "source_type": "Review Paper",
        "citation": "Wikipedia article",
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
- "data_quality_flag" MUST be one of: 'High_Evidence', 'Inferred_Only', 'Contested', or 'Low_Data'.

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
        c.execute("SELECT id, animal_name FROM research_queue WHERE status='PENDING' ORDER BY priority ASC LIMIT 1")
        job = c.fetchone()
        conn.close()
        return job

    def update_status(self, job_id, status):
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("UPDATE research_queue SET status=? WHERE id=?", (status, job_id))
        conn.commit()
        conn.close()

    def gather_context(self, animal_name):
        """
        Gather research context from Wikipedia.
        This implements a simple version of the 3-stage search strategy.
        """
        print(f"  📚 Gathering context for {animal_name}...")

        # Try to get the Wikipedia page
        page = self.wiki.page(animal_name)

        if not page.exists():
            print(f"  ⚠️  No Wikipedia page found for {animal_name}")
            return f"No detailed information found for {animal_name}"

        # Extract relevant sections
        context_parts = []

        # Add summary
        if page.summary:
            context_parts.append(f"OVERVIEW:\n{page.summary[:1000]}")

        # Look for sensory-related sections
        sensory_keywords = ['sense', 'sensory', 'hearing', 'vision', 'smell', 'echolocation',
                           'electroreception', 'magnetoreception', 'detection', 'perception']

        # Iterate through sections
        def extract_sections(sections_dict, depth=0):
            if depth > 2:  # Limit recursion depth
                return
            for section in sections_dict:
                # Check if section title contains sensory keywords
                if any(keyword in section.title.lower() for keyword in sensory_keywords):
                    context_parts.append(f"\nSECTION - {section.title}:\n{section.text[:800]}")
                # Recurse into subsections
                if section.sections:
                    extract_sections(section.sections, depth + 1)

        extract_sections(page.sections)

        # If we found sensory sections, limit total length
        if len(context_parts) > 1:
            context = "\n\n".join(context_parts[:4])  # Max 4 sections
        else:
            # Fallback: use full text (truncated)
            context = f"OVERVIEW:\n{page.text[:3000]}"

        print(f"  ✓ Gathered {len(context)} characters of context")
        return context

    def research_animal(self, animal_name: str, context_text: str):
        """
        1. Constructs the prompt.
        2. Calls the Local LLM.
        3. Validates output with Pydantic.
        """
        raw_json = self.adapter.research_animal(animal_name, context_text, SYSTEM_PROMPT_V4)

        if not raw_json:
            return None

        try:
            data_dict = json.loads(raw_json)
            
            # Post-process to fix common LLM errors
            processed_dict = self.post_process_data(data_dict)
            
            validated_data = AnimalSensoryData(**processed_dict)

            return validated_data.model_dump_json(indent=2)

        except json.JSONDecodeError:
            print(f"❌ Failed to parse JSON for {animal_name}")
            return None
        except ValidationError as e:
            print(f"❌ Pydantic Validation Failed for {animal_name}:")
            print(e.json())
            return None
        except Exception as e:
            print(f"❌ LLM Error: {e}")
            return None

    def post_process_data(self, data_dict):
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
        
        # Correct data_quality_flag
        if data_dict.get("meta", {}).get("data_quality_flag") == "Low_Evidence":
            data_dict["meta"]["data_quality_flag"] = "Low_Data"

        # Correct taxonomy fields
        if "identity" in data_dict and "taxonomy" in data_dict["identity"]:
            if "class" in data_dict["identity"]["taxonomy"]:
                data_dict["identity"]["taxonomy"]["class"] = str(data_dict["identity"]["taxonomy"]["class"])
            if "order" in data_dict["identity"]["taxonomy"]:
                data_dict["identity"]["taxonomy"]["order"] = str(data_dict["identity"]["taxonomy"]["order"])

        return data_dict

    def save_to_vault(self, animal_name, json_data):
        filename = f"{animal_name.replace(' ', '_')}.json"
        filepath = os.path.join(VAULT_DIR, filename)
        with open(filepath, 'w') as f:
            f.write(json_data)
        print(f"Saved research to {filepath}")

    def run(self):
        job = self.get_job()
        if not job:
            print("No pending jobs.")
            return

        job_id, animal_name = job
        self.update_status(job_id, "PROCESSING")

        try:
            context = self.gather_context(animal_name)
            result_json = self.research_animal(animal_name, context)

            if result_json:
                self.save_to_vault(animal_name, result_json)
                self.update_status(job_id, "COMPLETED")
            else:
                self.update_status(job_id, "FAILED")
        except Exception as e:
            print(f"Job failed: {e}")
            self.update_status(job_id, "FAILED")

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run the researcher with a specific adapter.")
    parser.add_argument("--adapter", type=str, default="gemini", help="The adapter to use (gemini or ollama)")
    args = parser.parse_args()

    agent = Researcher(adapter=args.adapter)
    agent.run()
