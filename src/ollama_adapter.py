import ollama
import json

class OllamaAdapter:
    def __init__(self, model_name="llama3.2"):
        self.model_name = model_name

    def research_animal(self, animal_name: str, context_text: str, system_prompt: str):
        """
        1. Constructs the prompt.
        2. Calls the Local LLM.
        3. Validates output with Pydantic.
        """
        print(f"🧠 Ollama Adapter analyzing: {animal_name}...")

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
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': user_prompt},
            ])

            raw_json = response['message']['content']

            # Basic cleanup (sometimes LLMs add ```json ... ```)
            if "```json" in raw_json:
                raw_json = raw_json.split("```json")[1].split("```")[0]
            elif "```" in raw_json:
                raw_json = raw_json.split("```")[1].split("```")[0]
            
            return raw_json

        except Exception as e:
            print(f"❌ Ollama Error: {e}")
            return None
