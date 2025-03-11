# analysis_modules/code_structure_parser.py
import os
import ast
import magic
from pathlib import Path
from typing import Dict, List, Any
from config import DEFAULT_CONFIG
import re

class CodeStructureParser:
    def __init__(self):
        self.config = DEFAULT_CONFIG
        self.ignore_dirs = set(self.config['analysis']['code_parsing']['directory_structure']['ignore'])
        self.entry_points = self.config['analysis']['code_parsing']['entry_points']
        self.max_size = self.parse_size(self.config['analysis']['code_parsing']['file_analysis']['max_size'])
        
    def parse_size(self, size_str: str) -> int:
        units = {"B": 1, "KB": 10**3, "MB": 10**6}
        number, unit = size_str[:-2], size_str[-2:]
        return int(float(number) * units[unit])

    def analyze_directory(self, root_dir: str = ".") -> Dict[str, Any]:
        structure = {
            "modules": [],
            "entry_points": [],
            "file_types": {},
            "project_size": 0
        }
        for root, dirs, files in os.walk(root_dir):
            dirs[:] = [d for d in dirs if d not in self.ignore_dirs]
            for file in files:
                file_path = Path(root) / file
                if file_path.is_symlink():
                    continue
                file_size = file_path.stat().st_size
                if file_size > self.max_size:
                    continue
                structure["project_size"] += file_size
                if file in self.entry_points:
                    structure["entry_points"].append(str(file_path))
                mime = magic.from_file(str(file_path), mime=True)
                structure["file_types"].setdefault(mime, 0)
                structure["file_types"][mime] += 1
                if file_path.suffix in [".py", ".js", ".jsx", ".ts", ".tsx"]:
                    structure["modules"].append({
                        "file": str(file_path),
                        "language": file_path.suffix[1:],
                        "size": file_size
                    })
        return structure

    def parse_python_file(self, file_path: Path) -> Dict[str, Any]:
        with open(file_path, "r", encoding="utf-8") as f:
            try:
                tree = ast.parse(f.read())
            except:
                return {"file": str(file_path), "error": "parse_error"}
        return {
            "file": str(file_path),
            "classes": [self._parse_class(node) for node in ast.walk(tree) if isinstance(node, ast.ClassDef)],
            "functions": [self._parse_function(node) for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)],
            "imports": self._collect_imports(tree)
        }

    def _parse_class(self, node: ast.ClassDef) -> Dict[str, Any]:
        return {
            "name": node.name,
            "methods": [n.name for n in node.body if isinstance(n, ast.FunctionDef)],
            "line_start": node.lineno,
            "docstring": ast.get_docstring(node) or ""
        }

    def _parse_function(self, node: ast.FunctionDef) -> Dict[str, Any]:
        return {
            "name": node.name,
            "parameters": [a.arg for a in node.args.args],
            "returns": ast.unparse(node.returns) if node.returns else None,
            "line_start": node.lineno,
            "docstring": ast.get_docstring(node) or ""
        }

    def _collect_imports(self, tree: ast.AST) -> List[str]:
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                imports.extend(f"{module}.{alias.name}" if module else alias.name for alias in node.names)
        return imports
