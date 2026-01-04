from google import genai
from src.config import GEMINI_API_KEY
import os

class GeminiAdapter:
    def __init__(self, model_name="gemini-2.0-flash"):
        self.model_name = model_name
        self.client = genai.Client(api_key=GEMINI_API_KEY)

    def research_animal(self, animal_name: str, context_text: str, system_prompt: str):
        """
        1. Constructs the prompt.
        2. Calls the Gemini API.
        3. Returns the raw JSON response.
        """
        print(f"🧠 Gemini Adapter analyzing: {animal_name}...")

        # Construct the User Prompt
        user_prompt = f"""
        {system_prompt}

        ANIMAL: {animal_name}

        CONTEXT DATA:
        {context_text}

        INSTRUCTIONS:
        Based strictly on the context above, generate the JSON for {animal_name}.
        """

        try:
            # Call Gemini API
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=[user_prompt]
            )

            raw_json = response.text

            # Basic cleanup (sometimes LLMs add ```json ... ```)
            if "```json" in raw_json:
                raw_json = raw_json.split("```json")[1].split("```")[0]
            elif "```" in raw_json:
                raw_json = raw_json.split("```")[1].split("```")[0]
            
            return raw_json

        except Exception as e:
            print(f"❌ Gemini API Error: {e}")
            return None
