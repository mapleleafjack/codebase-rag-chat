# config.py

DEFAULT_CONFIG = {
    "ollama": {
        "integration": {
            "base_url": "http://localhost:11434",
            "default_model": "phi4"
        },
        "prompt_templates": {
            "file_change": {
                "system_prompt": (
                    "You are a code change analyst working with THESE EXACT FILES:\n"
                    "{files}\n\n"
                    "ALWAYS:\n"
                    "1. Reference specific file paths from the list above\n"
                    "2. Cite line numbers when possible\n"
                    "3. Show actual code examples from context\n"
                    "4. Consider config files first (look for .yaml/.yml)\n\n"
                    "NEVER:\n"
                    "- Invent new file paths\n"
                    "- Suggest generic examples\n"
                    "- Mention files not in the list"
                )
            }
        }
    },
    "rag": {
        "knowledge_base": {
            "embedding_model": "nomic-embed-text",
            "indexing_strategy": {
                "chunk_size": 1024,   # Updated chunk size
                "overlap": 128        # Updated overlap
            }
        },
        "query_processing": {
            "context_window": 4096,
            "temperature": 0.3,
            "max_tokens": 1024
        }
    },
    "analysis": {
        "code_parsing": {
            "entry_points": ["package.json", "requirements.txt", "pom.xml"],
            "directory_structure": {
                "ignore": ["node_modules", ".git", "venv"]
            },
            "file_analysis": {
                "max_size": "1MB",
                "sample_rate": 0.2
            }
        }
    },
    "system": {
        "supported_languages": ["python"]
    },
    "output": {
        "visualization": {
            "dependency_graph": True
        }
    }
}
