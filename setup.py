from pathlib import Path
from setuptools import setup, find_packages

here = Path(__file__).parent
readme = (here / "README.md").read_text(encoding="utf-8") if (here / "README.md").exists() else ""

setup(
    name="travel_planner",
    version="0.1.0",
    description="LangGraph agent that researches, plans, writes and illustrates travel plan for user.",
    long_description=readme,
    long_description_content_type="text/markdown",
    author="Pramod Khavare",
    url="https://github.com/pramodkhavare/TripPlanner",
    # package_dir={"": "src"},
    # packages=find_packages(where="src"),
    packages=find_packages(include=["src", "src.*"]),
    python_requires=">=3.10",
    install_requires=[
        # "langgraph", 
    ],
    extras_require={
        "dev": ["pytest", "ipykernel"],
    },
    entry_points={
        "console_scripts": [
            "travelplanner=src.Travel_Planner.cli:main",
        ],
    },
)