import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BACKEND = ROOT / "backend"

if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

# Production model lives on Hugging Face.
os.environ.setdefault(
    "HF_MODEL_ID",
    "praveen9052/contractiq-clause-classifier"
)

from main import app
