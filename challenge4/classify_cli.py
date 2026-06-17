# Python 3.12
"""User-facing CLI entry point.

Usage:
    python challenge4/classify_cli.py --text "email me at a@b.com"
    echo "secret stuff" | python challenge4/classify_cli.py
A thin wrapper that puts challenge4/ on sys.path, then delegates to classifier.cli.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from classifier.cli import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
