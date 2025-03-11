# analysis_modules/dependency_mapper.py
import json
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List
from config import DEFAULT_CONFIG
import ast
import re

class DependencyMapper:
    def __init__(self):
        self.config = DEFAULT_CONFIG
        self.supported_languages = self.config['system']['supported_languages']
        
    def build_dependency_graph(self, root_dir: str = ".") -> Dict[str, List[str]]:
        graph = {}
        root_path = Path(root_dir)
        for file in root_path.glob("**/*"):
            if not file.is_file() or file.stat().st_size == 0:
                continue
            try:
                if file.name == "requirements.txt":
                    graph.setdefault("python", []).extend(self._parse_requirements(file))
                elif file.name == "package.json":
                    pkg = self._parse_package_json(file)
                    graph.setdefault("javascript", []).extend(pkg["dependencies"] + pkg["devDependencies"])
                elif file.name == "pom.xml":
                    graph.setdefault("java", []).extend(self._parse_pom_xml(file))
            except Exception as e:
                print(f"⚠️ Error processing {file}: {str(e)}")
                continue
        code_deps = self._map_code_dependencies(root_path)
        graph.update(code_deps)
        return graph

    def _parse_requirements(self, file_path: Path) -> List[str]:
        deps = []
        with open(file_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    deps.append(line.split("==")[0])
        return deps

    def _parse_package_json(self, file_path: Path) -> Dict[str, List[str]]:
        with open(file_path) as f:
            data = json.load(f)
        return {
            "dependencies": list(data.get("dependencies", {}).keys()),
            "devDependencies": list(data.get("devDependencies", {}).keys())
        }

    def _parse_pom_xml(self, file_path: Path) -> List[str]:
        try:
            if file_path.stat().st_size == 0:
                return []
            tree = ET.parse(file_path)
            root = tree.getroot()
            ns = {'mvn': 'http://maven.apache.org/POM/4.0.0'}
            deps = []
            for dep in root.findall('.//mvn:dependency', ns):
                group = dep.find('mvn:groupId', ns)
                artifact = dep.find('mvn:artifactId', ns)
                if group is not None and artifact is not None:
                    deps.append(f"{group.text}:{artifact.text}")
            return deps
        except ET.ParseError:
            print(f"⚠️ Invalid/malformed XML in {file_path}")
            return []

    def _map_code_dependencies(self, root_path: Path) -> Dict[str, List[str]]:
        deps = {}
        for file in root_path.glob("**/*.{js,jsx,ts,tsx}"):  
            with open(file) as f:
                content = f.read()
                imports = self._parse_javascript_imports(content)
            deps[str(file)] = imports
        
        for file in root_path.glob("**/*.py"):
            with open(file) as f:
                try:
                    content = f.read()
                    if not content:
                        continue
                    tree = ast.parse(content)
                except:
                    continue
            imports = []
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    imports.extend(alias.name for alias in node.names)
                elif isinstance(node, ast.ImportFrom):
                    module = node.module or ""
                    imports.extend(f"{module}.{alias.name}" if module else alias.name for alias in node.names)
            deps[str(file)] = imports
        return {"code_imports": deps}

    def _parse_javascript_imports(self, content: str) -> List[str]:
        """Improved React component detection with prop types"""
        imports = []
        
        # 1. Find component definitions with props
        component_pattern = re.compile(
            r"(export\s+(default\s+)?(function|const)\s+([A-Z]\w+)\s*\(\{([^}]*)\}\)\s*=>)",
            re.MULTILINE
        )
        
        # 2. Detect styled-components
        styled_pattern = re.compile(r"styled\.(\w+)\`")
        
        # 3. Find context providers/consumers
        context_pattern = re.compile(r"createContext<([^>]+)>\(\)")
        
        matches = component_pattern.findall(content)
        styled_matches = styled_pattern.findall(content)
        context_matches = context_pattern.findall(content)
        
        # Add component props to dependencies
        for match in matches:
            imports.append(f"Component:{match[3]} Props:[{match[4].strip()}]")
            
        # Add styled components
        imports.extend(f"Styled:{comp}" for comp in styled_matches)
        
        # Add context types
        imports.extend(f"ContextType:{ctx}" for ctx in context_matches)
        
        return imports