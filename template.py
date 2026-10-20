# template.py  —  run once from the project root:  python template.py
from pathlib import Path

PACKAGE = "Travel_Planner"

files = [
    # package
    f"src/__init__.py",
    f"src/{PACKAGE}/__init__.py",
    f"src/{PACKAGE}/config.py",
    f"src/{PACKAGE}/state.py",
    f"src/{PACKAGE}/schemas.py",
    f"src/{PACKAGE}/prompts.py",
    f"src/{PACKAGE}/utils.py",
    f"src/{PACKAGE}/graph.py",
    f"src/{PACKAGE}/cli.py",
    # tools
    f"src/{PACKAGE}/tools/__init__.py",
    f"src/{PACKAGE}/tools/flight_tool.py",
    f"src/{PACKAGE}/tools/tavily_tool.py", 
    # nodes
    f"src/{PACKAGE}/nodes/__init__.py", 
    # other
    "notebooks/experiments.ipynb",
    "tests/__init__.py",
    "tests/test_utils.py",
    "tests/test_schemas.py",
    "output/.gitkeep",
    ".env",
    ".env.example",
    ".gitignore",
    "requirements.txt",
    "setup.py",
    "README.md",
    "app.py" ,
    "backend.py" ,
    f"templates/index.html" ,
    f"static/script.js",
    f"static/style.css"

]

# starter content for a few files (others are created empty)
content = {
    ".env.example": "GOOGLE_API_KEY=\nTAVILY_API_KEY=\nCF_ACCOUNT_ID=\nCF_API_TOKEN=\n",
    ".gitignore": ".env\n.venv/\n__pycache__/\n*.pyc\noutput/*\n!output/.gitkeep\n"
                  ".ipynb_checkpoints/\n*.egg-info/\n",
    "requirements.txt": "-e .[dev]\n",
    "notebooks/experiments.ipynb": '{"cells": [], "metadata": {}, "nbformat": 4, "nbformat_minor": 5}\n',
    "README.md": "# Agentic Travel Planner\n",
}

for f in files:
    path = Path(f)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.stat().st_size > 0:
        print(f"skip (exists): {path}")       # never overwrite your code
        continue
    path.write_text(content.get(f, ""), encoding="utf-8")
    print(f"created: {path}")