"""
The Agent (LLM + Search).
This module needs to be Class-Based so we can swap out the "Brain" (Ollama vs. OpenAI) without rewriting the logic.
Logic:
1. Fetch: Get job from SQLite (status='PENDING' with highest Priority).
2. Context Assembly: Run 3 distinct DuckDuckGo searches (General, Mechanism, Threshold).
3. Inference: Send 3,000 words of context to the LLM with the Schema v4.0 instructions.
4. Validation: Use Pydantic to ensure the JSON matches the schema.
   - Fail: Increment retry count.
   - Pass: Save to /vault/{animal_name}.json.
"""
# TODO: Implement class-based Researcher.
