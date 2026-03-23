import sys
from pathlib import Path

# Ensure the backend directory is on sys.path so that `app` is importable
# when pytest is invoked from the backend/ directory (e.g., `cd backend && pytest tests/`).
sys.path.insert(0, str(Path(__file__).resolve().parent))
