"""
Smart Transit
AI-Powered Multimodal Journey Planner

Project Structure Generator

AI Lab - Transit BD
"""

from pathlib import Path


# ============================================================
# PROJECT CONFIGURATION
# ============================================================

PROJECT_NAME = "Smart Transit"
PROJECT_VERSION = "0.1.0"

ROOT_DIR = Path(__file__).resolve().parent


# ============================================================
# FOLDER STRUCTURE
# ============================================================

FOLDERS = [
    "notebooks",

    "src",
    "src/api",
    "src/algorithms",
    "src/graph",
    "src/utils",

    "data",
    "data/raw",
    "data/processed",

    "tests",
]


# ============================================================
# FILE STRUCTURE
# ============================================================

FILES = [
    "src/__init__.py",

    "src/api/__init__.py",
    "src/api/geocoding.py",
    "src/api/routing.py",

    "src/algorithms/__init__.py",
    "src/algorithms/dijkstra.py",
    "src/algorithms/astar.py",
    "src/algorithms/multicriteria.py",
    "src/algorithms/eta.py",

    "src/graph/__init__.py",
    "src/graph/graph_builder.py",

    "src/utils/__init__.py",
    "src/utils/distance.py",

    "tests/__init__.py",

    "requirements.txt",
]


# ============================================================
# CREATE FOLDERS
# ============================================================

def create_folders():
    """Create all required project directories."""

    for folder in FOLDERS:
        path = ROOT_DIR / folder
        path.mkdir(parents=True, exist_ok=True)

        print(f"[DIR]  {folder}")


# ============================================================
# CREATE FILES
# ============================================================

def create_files():
    """Create empty project files if they do not already exist."""

    for file in FILES:
        path = ROOT_DIR / file

        if not path.exists():
            path.touch()
            print(f"[FILE] {file}")
        else:
            print(f"[SKIP] {file} already exists")


# ============================================================
# MAIN
# ============================================================

def main():
    print("=" * 60)
    print(f"{PROJECT_NAME} - Project Setup")
    print("=" * 60)

    print("\nCreating folders...\n")
    create_folders()

    print("\nCreating files...\n")
    create_files()

    print("\n" + "=" * 60)
    print("Project structure created successfully.")
    print("=" * 60)


if __name__ == "__main__":
    main()