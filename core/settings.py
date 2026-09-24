from pathlib import Path
import os


BASE_DIR = Path(__file__).resolve().parent.parent

MANIFESTS_DIR = BASE_DIR / "manifests"

INPUTS_DIR = BASE_DIR / "inputs"

OUTPUTS_DIR = BASE_DIR / "outputs"

LOGS_DIR = BASE_DIR / "logs"

STORAGE_DIR = BASE_DIR / "storage"

DATABASE_PATH = STORAGE_DIR / "mello.db"

STORAGE_BACKEND = os.getenv("STORAGE_BACKEND", "local").strip().lower()