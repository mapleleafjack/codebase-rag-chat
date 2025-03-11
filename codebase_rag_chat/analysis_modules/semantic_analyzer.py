# analysis_modules/semantic_analyzer.py
import os
from typing import Dict, List
from dotenv import load_dotenv
import requests
import re

load_dotenv()

class SemanticAnalyzer:
    def __init__(self, config: dict):
        self.config = config
        self.api_key = os.getenv("DEEPSEEK_API_KEY")
        self.chunk_size = self.config['rag']['knowledge_base']['indexing_strategy']['chunk_size']
        self.overlap = self.config['rag']['knowledge_base']['indexing_strategy']['overlap']
        
    def analyze_code_semantics(self, code: str) -> Dict[str, List[float]]:
        chunks = self._chunk_code(code)
        return self._generate_embeddings(chunks)
    
    def _chunk_python(self, code: str) -> List[str]:
        lines = code.split('\n')
        chunks = []
        current_chunk: List[str] = []
        current_length = 0
        for line in lines:
            line_length = len(line.split())
            if current_length + line_length > self.chunk_size:
                chunks.append('\n'.join(current_chunk))
                current_chunk = current_chunk[-self.overlap:]
                current_length = sum(len(line.split()) for line in current_chunk)
            current_chunk.append(line)
            current_length += line_length
        if current_chunk:
            chunks.append('\n'.join(current_chunk))
        return chunks


    def _chunk_code(self, code: str) -> List[str]:
        # Handle JSX/TSX components
        if any(code.startswith(s) for s in ['import React', 'export function', 'export const']):
            return self._chunk_react_components(code)
        
        # Handle Python classes/functions
        if 'def ' in code or 'class ' in code:
            return self._chunk_python(code)
        
        # Default chunking
        return self._chunk_python(code)

    def _chunk_react_components(self, code: str) -> List[str]:
        """Split code into component boundaries"""
        chunks = []
        current_chunk: List[str] = []
        in_component = False
        
        for line in code.split('\n'):
            if re.match(r'export (default )?(function|const) [A-Z]', line):
                if current_chunk:
                    chunks.append('\n'.join(current_chunk))
                current_chunk = [line]
                in_component = True
            elif in_component and line.strip() == '}':
                current_chunk.append(line)
                chunks.append('\n'.join(current_chunk))
                current_chunk = []
                in_component = False
            elif in_component:
                current_chunk.append(line)
        
        return chunks

    def _generate_embeddings(self, chunks: List[str]) -> Dict[str, List[float]]:
        embeddings = {}
        for chunk in chunks:
            try:
                response = requests.post(
                    f"{self.config['ollama']['integration']['base_url']}/api/embed",
                    json={
                        "model": self.config['rag']['knowledge_base']['embedding_model'],
                        "input": f"CODE CHUNK:\n{chunk}\nIMPORTANT NOTES:This code exists in the actual codebase files."
                    }
                )
                response.raise_for_status()
                embeddings[chunk] = response.json()['embeddings'][0]
            except Exception as e:
                print(f"Embedding error in chunk '{chunk[:30]}...': {str(e)}")
                embeddings[chunk] = []
        return embeddings
