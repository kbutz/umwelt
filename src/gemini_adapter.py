import time
import random
from google import genai
from src.config import GEMINI_API_KEY
import os

class GeminiAdapter:
    def __init__(self, model_name="gemini-2.0-flash"):
        self.model_name = model_name
        self.client = genai.Client(api_key=GEMINI_API_KEY)

    def research_animal(self, animal_name: str, context_text: str, system_prompt: str, max_retries=5):
        """
        1. Constructs the prompt.
        2. Calls the Gemini API with retry logic.
        3. Returns the raw JSON response.
        """
        print(f"🧠 Gemini Adapter analyzing: {animal_name}...")

        user_prompt = f"""
        {system_prompt}

        ANIMAL: {animal_name}

        CONTEXT DATA:
        {context_text}

        INSTRUCTIONS:
        Based strictly on the context above, generate the JSON for {animal_name}.
        """

        retries = 0
        while retries <= max_retries:
            try:
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=[user_prompt]
                )

                raw_json = response.text

                # Basic cleanup
                if "```json" in raw_json:
                    raw_json = raw_json.split("```json")[1].split("```")[0]
                elif "```" in raw_json:
                    raw_json = raw_json.split("```")[1].split("```")[0]
                
                return raw_json

            except Exception as e:
                # Check for rate limit error (429)
                if "429" in str(e) or "Too Many Requests" in str(e):
                    wait_time = (2 ** retries) + random.random()
                    print(f"  ⚠ Rate limit hit (429). Retrying in {wait_time:.2f}s... (Attempt {retries + 1}/{max_retries})")
                    time.sleep(wait_time)
                    retries += 1
                else:
                    print(f"  ❌ Gemini API Error: {e}")
                    return None
        
        print(f"  ❌ Max retries exceeded for {animal_name}")
        return None
