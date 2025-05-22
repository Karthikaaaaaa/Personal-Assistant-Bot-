from config.settings import load_config
import google.generativeai as genai

class LLMService:
    def __init__(self):
        config = load_config()
        self.model = genai.GenerativeModel(config["model_name"])

    def generate_response(self, prompt):
        try:
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            raise Exception(f"LLM Error: {e}")