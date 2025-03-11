import argparse
from .main import CodebaseRAGAssistant

def main():
    parser = argparse.ArgumentParser(description="Codebase RAG Assistant")
    parser.add_argument('command', choices=['analyze', 'query'], 
                      help="Action to perform: analyze or query")
    parser.add_argument('-c', '--config', default="project.yaml",
                      help="Path to configuration file")
    parser.add_argument('-o', '--output', default="output",
                      help="Output directory for reports")
    
    args = parser.parse_args()
    
    assistant = CodebaseRAGAssistant()
    

    if args.command == "analyze":
        print("🚀 Starting codebase analysis...")
        try:
            results = assistant.run_analysis()
            kb_collection = assistant.setup_knowledge_base(results['semantics'])
            print("\n✅ Analysis complete! Database ready in output/chroma_db")
        except Exception as e:
            print(f"\n❌ Analysis failed: {str(e)}")
            raise

    elif args.command == "query":
        print("\n💬 Starting query interface...")
        try:
            # Attempt to load existing knowledge base
            kb_collection = assistant.setup_knowledge_base()
            assistant.query_interface(kb_collection)
        except Exception as e:
            print(f"\n❌ Query failed: {str(e)}")
            print("First run: codebase-rag analyze")

if __name__ == "__main__":
    main()