import sys
from pathlib import Path

# Ensure the root directory and stockup_pulse package are in the Python path
root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir))

from stockup_pulse.api.main import app