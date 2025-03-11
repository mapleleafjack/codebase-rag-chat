# main.py
import importlib
import json
import time
import yaml
import markdown2
import chromadb
import requests
from pathlib import Path
from typing import Dict, Any
from codebase_rag_chat.analysis_modules import (
    CodeStructureParser,
    DependencyMapper,
    SemanticAnalyzer
)

class CodebaseRAGAssistant:
    def __init__(self, config_path: str = None):
        # Use package resources as fallback
        if not config_path or not Path(config_path).exists():
            config_path = str(importlib.resources.files('codebase_rag_chat') / 'project.yaml')
        
        with open(config_path) as f:
            self.config = yaml.safe_load(f)
        
        # Initialize core components
        self.parser = CodeStructureParser(config_path)
        self.dep_mapper = DependencyMapper(config_path)
        self.semantic_analyzer = SemanticAnalyzer(self.config)
        
        # Setup output directory
        self.output_dir = Path("output")
        self.output_dir.mkdir(exist_ok=True)

    def run_analysis(self) -> dict[str, Any]:
        """Execute complete analysis workflow"""
        results = {}
        start_time = time.time()

        # Phase 1: Directory structure analysis
        results['structure'] = self.parser.analyze_directory()
        end_time = time.time()

        print("✅ Directory structure analysis complete in {:.2f}s".format(end_time - start_time))
        
        start_time = end_time
        # Phase 2: Dependency mapping
        results['dependencies'] = self.dep_mapper.build_dependency_graph()

        end_time = time.time()

        print("✅ Dependency mapping complete in {:.2f}s".format(end_time - start_time))
        
        start_time = end_time
        # Phase 3: Semantic analysis
        results['semantics'] = self._analyze_code_semantics(results['structure'])
        end_time = time.time()
        print("✅ Semantic analysis complete in {:.2f}s".format(end_time - start_time))
        
        return results

    def _analyze_code_semantics(self, structure: Dict) -> Dict:
        """Process code files for semantic understanding"""
        semantics = {}
        
        for module in structure.get('modules', []):
            file_path = module['file']
            # Expand to analyze key config files
            if any(file_path.endswith(ext) for ext in ['.py', '.yaml', '.yml', '.md']):
                with open(file_path) as f:
                    code = f.read()
                    analysis = self.semantic_analyzer.analyze_code_semantics(code)
                    if analysis:  # Only store valid analyses
                        semantics[file_path] = analysis
        return semantics

    def generate_reports(self, results: Dict) -> None:
        """Generate output reports in all configured formats"""
        # Architectural overview
        self._generate_architectural_report(results)
        
        # Dependency visualization
        if self.config['output']['visualization']['dependency_graph']:
            self._generate_dependency_graph(results['dependencies'])
            
        print(f"📊 Reports generated in {self.output_dir}")

    def _generate_architectural_report(self, results: Dict) -> None:
        """Generate multi-format architectural report"""
        report_data = {
            "project_stats": {
                "total_files": sum(results['structure']['file_types'].values()),
                "file_types": results['structure']['file_types'],
                "entry_points": results['structure']['entry_points']
            },
            "dependency_stats": {
                "total_dependencies": sum(len(v) for v in results['dependencies'].values() 
                                       if isinstance(v, (list, dict)))
            }
        }

        # YAML format
        with open(self.output_dir/'architectural_overview.yaml', 'w') as f:
            yaml.dump(report_data, f, sort_keys=False)
            
        # JSON format
        with open(self.output_dir/'architectural_overview.json', 'w') as f:
            json.dump(report_data, f, indent=2)
            
        # Markdown format
        md_content = f"""
        # Architectural Overview Report
        
        ## Project Statistics
        - Total Files: {report_data['project_stats']['total_files']}
        - File Types: {', '.join(report_data['project_stats']['file_types'].keys())}
        
        ## Dependencies
        - Total Dependencies: {report_data['dependency_stats']['total_dependencies']}
        """
        with open(self.output_dir/'architectural_overview.md', 'w') as f:
            f.write(markdown2.markdown(md_content))

    def _generate_dependency_graph(self, dependencies: Dict) -> None:
        """Generate visual dependency graph using Graphviz"""
        try:
            from graphviz import Digraph
        except ImportError:
            print("⚠️ Graphviz not installed, skipping dependency graph")
            return

        dot = Digraph(comment='Project Dependencies')
        
        # Add nodes and edges
        for lang, deps in dependencies.items():
            if lang == 'code_imports':
                for file, imports in deps.items():
                    dot.node(file, shape='box')
                    for imp in imports:
                        dot.edge(file, imp)
            else:
                dot.node(lang, shape='ellipse')
                for dep in deps:
                    dot.edge(lang, dep)
        
        dot.render(self.output_dir/'dependency_graph.gv', view=False)
        print(f"📈 Dependency graph saved to {self.output_dir/'dependency_graph.gv.pdf'}")

    def setup_knowledge_base(self, semantic_results: Dict = None) -> chromadb.Collection:
        try:
            print("🔧 Setting up knowledge base...")
            client = chromadb.PersistentClient(
                path=str(self.output_dir/'chroma_db')
            )

            if semantic_results:

                print("📦 Creating/loading collection for code embeddings")
                collection = client.get_or_create_collection(
                    name="code_embeddings",
                    metadata={"hnsw:space": "cosine"}
                )

                print("🔍 Batch processing embeddings...")
                # Prepare batch data
                batch_size = 100
                embeddings = []
                documents = []
                metadatas = []
                ids = []
                
                total_processed = 0
                print(f"🔍 Processing {len(semantic_results)} files...")

                for i, (file_path, analysis) in enumerate(semantic_results.items()):
                    if i % 10 == 0:  # Update every 10 files
                        print(f"⏳ Processed {i}/{len(semantic_results)} files...", end='\r')

                    for chunk, embedding in analysis.items():
                        if embedding and len(embedding) > 0:
                            embeddings.append(embedding)
                            documents.append(chunk)
                            metadatas.append({"file_path": file_path})
                            ids.append(f"{file_path}-{hash(chunk)}")
                            total_processed += 1

                            # Add in batches
                            if len(embeddings) >= batch_size:
                                collection.add(
                                    embeddings=embeddings,
                                    documents=documents,
                                    metadatas=metadatas,
                                    ids=ids
                                )
                                print(f"📦 Added batch of {len(embeddings)} embeddings")
                                # Reset batch buffers
                                embeddings = []
                                documents = []
                                metadatas = []
                                ids = []

                # Add any remaining items
                if embeddings:
                    collection.add(
                        embeddings=embeddings,
                        documents=documents,
                        metadatas=metadatas,
                        ids=ids
                    )
                    print(f"📦 Added final batch of {len(embeddings)} embeddings")

                print(f"✅ Successfully stored {total_processed} embeddings in total")
            else:
                try:
                    return client.get_collection("code_embeddings")
                except ValueError:
                    raise RuntimeError("No existing knowledge base - run analysis first")
            return collection

        except Exception as e:
            print(f"🚨 Knowledge base error: {str(e)}")
            raise

    def query_interface(self, collection: chromadb.Collection = None):

        if not collection:
            collection = self.setup_knowledge_base()

        from codebase_rag_chat.ollama_integration import OllamaClient
        ollama = OllamaClient()
        print("\n💬 Codebase Query Interface (type 'exit' to quit)")

        while True:
            query = input("\nQuestion: ")
            if query.lower() == 'exit':
                break

            # -- 1. Embed the user query via the same Ollama model used for code chunks --
            embed_url = f"{self.config['ollama']['integration']['base_url']}/api/embed"
            embed_model = self.config['rag']['knowledge_base']['embedding_model']

            try:
                embed_resp = requests.post(
                    embed_url,
                    json={
                        "model": embed_model,
                        "input": query
                    }
                )
                embed_resp.raise_for_status()
                # This should be the same 1024-dimensional vector that was used for code
                query_embedding = embed_resp.json()['embeddings'][0]
            except Exception as e:
                print(f"Error embedding query: {str(e)}")
                continue

            # -- 2. Query the collection using our manually generated embedding --
            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=8,  # Increased from 5
                include=['documents', 'metadatas']
            )
            metadatas = results['metadatas'][0]

            # Enhanced file prioritization
            file_counts = {}
            for md in metadatas:
                fp = md['file_path']
                file_counts[fp] = file_counts.get(fp, 0) + 1

            # Extract and deduplicate files
            seen_files = set()
            unique_files = []
            for md in metadatas:
                if (fp := md['file_path']) not in seen_files:
                    seen_files.add(fp)
                    unique_files.append(fp)

                # Sort files by relevance frequency
            unique_files = sorted(file_counts.keys(), 
                                key=lambda x: file_counts[x], 
                                reverse=True)[:5]  # Show top 5 files

            print(f"🔍 Found {len(unique_files)} relevant files: {unique_files}")

            context = "Relevant code snippets:\n" + "\n".join([
                f"From {md['file_path']}:\n{doc}" 
                for md, doc in zip(metadatas, results['documents'][0])
            ])
            
            # Then pass both query & context to Ollama’s chat API
            response = ollama.query_codebase(
                query,
                context=context,
                files=unique_files,
                template='file_change'
            )
            print(f"\nAssistant Response:\n{'-'*40}\n{response}\n{'-'*40}")


def main():
    assistant = CodebaseRAGAssistant()
    
    # Run full analysis pipeline
    print("🚀 Starting codebase analysis...")

    analysis_results = assistant.run_analysis()

    print("\n✅ Analysis complete!")

    
    # Generate formatted reports

    print("📊 Generating reports...")
    assistant.generate_reports(analysis_results)
    print("✅ Reports generated!")
    # Initialize RAG knowledge base

    print("🔧 Setting up knowledge base...")
    kb_collection = assistant.setup_knowledge_base(analysis_results['semantics'])
    print("✅ Knowledge base setup complete!")

    print("\n💬 Starting query interface...")
    # Start interactive query interface
    assistant.query_interface(kb_collection)

if __name__ == "__main__":
    main()