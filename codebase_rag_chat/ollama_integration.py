# ollama_integration.py
import requests
from config import DEFAULT_CONFIG  # import inline config

class OllamaClient:
    def __init__(self):
        self.config = DEFAULT_CONFIG
        self.base_url = self.config['ollama']['integration']['base_url']
        self.default_model = self.config['ollama']['integration']['default_model']
    
    def query_codebase(self, question: str, context: str, files: list, template: str = 'file_change'):
        # Boost component files in priority
        react_components = [f for f in files if any(f.endswith(ext) for ext in ['.tsx','.jsx'])]
        hooks = [f for f in files if 'hooks/' in f]
        python_files = [f for f in files if f.endswith('.py')]
        
        prioritized_files = (
            react_components 
            + hooks 
            + python_files 
            + [f for f in files if f not in react_components+hooks+python_files]
        )
        
        # Enhanced prompt template
        prompt = f"""Analyze these files considering:
            - Component hierarchy and prop flows
            - Python service integrations (look for @api routes)
            - Shared state management patterns
            - Type definitions and interfaces
            
            Files by relevance:
            {prioritized_files}
            
            Code Context:
            {context}
            
            Question: {question}
            
            Required analysis format:
            1. Core functionality summary
            2. Key component relationships
            3. Data flow architecture
            4. Language integration points""
        """
        
        response = requests.post(
            f"{self.base_url}/v1/chat/completions",
            json={
                "model": self.default_model,
                "messages": [{
                    "role": "user",
                    "content": prompt
                }],
                "temperature": 0.1
            }
        )
        return response.json()['choices'][0]['message']['content']
