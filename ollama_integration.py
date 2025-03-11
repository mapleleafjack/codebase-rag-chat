# Add new file: ollama_integration.py
import requests
import yaml

class OllamaClient:
    def __init__(self, config_path="project.yaml"):
        with open(config_path) as f:
            self.config = yaml.safe_load(f)
            
        self.base_url = self.config['ollama']['integration']['base_url']
        self.default_model = self.config['ollama']['integration']['default_model']
    
    
    def query_codebase(self, question: str, context: str, files: list, template: str = 'file_change'):
        if not files:
            return "⚠️ Error: No relevant files found in codebase analysis"
        
        template_config = self.config['ollama']['prompt_templates'].get(template, {})
        
        # Force-include config files in prompt
        config_files = [f for f in files if 'yaml' in f or 'yml' in f]
        prioritized_files = config_files + [f for f in files if f not in config_files]
        
        prompt = f"{template_config.get('system_prompt', '').format(files=prioritized_files)}\n\n"
        prompt += f"Code Context:\n{context}\n\nQuestion: {question}"
        
        # Lower temperature for precise answers
        response = requests.post(
            f"{self.base_url}/v1/chat/completions",
            json={
                "model": self.default_model,
                "messages": [{
                    "role": "user",
                    "content": prompt
                }],
                "temperature": 0.1  # More deterministic
            }
        )
        return response.json()['choices'][0]['message']['content']