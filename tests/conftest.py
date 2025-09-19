import os
import sys

# Ensure the repository root is importable so tests can import the package
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# Avoid Qt backend selection during non-GUI tests
os.environ.setdefault("MPLBACKEND", "Agg")
