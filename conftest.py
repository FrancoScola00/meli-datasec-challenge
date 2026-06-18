# Python 3.12
"""Pytest path setup.

Puts the repository root and ``challenge4/`` on ``sys.path`` so tests can import
the root-level solution modules (``solution_minesweeper``, ``solution_best_in_genre``)
and the Challenge 4 ``classifier`` package without an installable layout.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).parent
for _path in (ROOT, ROOT / "challenge4"):
    _p = str(_path)
    if _p not in sys.path:
        sys.path.insert(0, _p)
