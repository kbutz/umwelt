import json
import ollama
import sqlite3
import os
from src.models import AnimalSensoryData
from pydantic import ValidationError

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
You must output strictly valid JSON adhering to the Pydantic schema provided below.
No markdown formatting. No conversational filler.
"""

class Researcher:
    def __init__(self, model_name="llama3"):
        self.model_name = model_name

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
        # Mock context gathering as search is not implemented yet
        # Returning a placeholder string as requested
        return f"""
        Research context for {animal_name}:
        The {animal_name} is known for its specialized sensory systems.
        Studies show it has a hearing range of 20 Hz to 20 kHz.
        It uses echolocation in some contexts.
        Mechanism involves the cochlea.
        """

    def research_animal(self, animal_name: str, context_text: str):
        """
        1. Constructs the prompt.
        2. Calls the Local LLM.
        3. Validates output with Pydantic.
        """
        print(f"🧠 Researcher analyzing: {animal_name}...")

        # Construct the User Prompt
        user_prompt = f"""
        ANIMAL: {animal_name}

        CONTEXT DATA:
        {context_text}

        INSTRUCTIONS:
        Based strictly on the context above, generate the JSON for {animal_name}.
        """

        try:
            # Call Ollama
            response = ollama.chat(model=self.model_name, messages=[
                {'role': 'system', 'content': SYSTEM_PROMPT_V4},
                {'role': 'user', 'content': user_prompt},
            ])

            raw_json = response['message']['content']

            # Basic cleanup (sometimes LLMs add ```json ... ```)
            if "```json" in raw_json:
                raw_json = raw_json.split("```json")[1].split("```")[0]
            elif "```" in raw_json:
                raw_json = raw_json.split("```")[1].split("```")[0]

            # Parse and Validate
            data_dict = json.loads(raw_json)
            validated_data = AnimalSensoryData(**data_dict)

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
    agent = Researcher()
    agent.run()
