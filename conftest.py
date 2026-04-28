"""Root conftest for Shadertoy→AGSL converter tests."""
import sys
from pathlib import Path

# Ensure project root is on sys.path so `rules` and `converter` are importable.
_root = Path(__file__).resolve().parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))
