from setuptools import setup, find_packages

setup(
    name="codebase-rag-chat",
    version="0.1",
    packages=find_packages(include=['codebase_rag_chat', 'analysis_modules*']),
    include_package_data=True,
    install_requires=[
        'requests>=2.31.0',
        'PyYAML>=6.0.1',
        'markdown2>=2.4.10',
        'jsonschema>=4.21.1',
        'astunparse>=1.6.3',
        'tqdm>=4.66.2',
        'chromadb>=0.4.24',
        'ollama>=0.1.6',
        'python-magic>=0.4.27',
        'graphviz>=0.20.1',
    ],
    entry_points={
        'console_scripts': [
            'codebase-rag = codebase_rag_chat.cli:main',
        ],
    },
    package_data={
        'codebase_rag_chat': ['*.yaml', '*.yml'],
    },
    python_requires='>=3.8',
)