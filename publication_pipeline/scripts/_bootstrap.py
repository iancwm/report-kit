"""Import bootstrap for direct execution of pipeline scripts."""
from __future__ import annotations

from pathlib import Path
import sys


def ensure_reportkit_importable() -> None:
    """Make the clone's ``python_scripts`` directory importable once."""
    try:
        import reportkit  # noqa: F401
        return
    except ModuleNotFoundError as exc:
        if exc.name != "reportkit":
            raise
    repo_root = Path(__file__).resolve().parents[2]
    python_root = repo_root / "python_scripts"
    if str(python_root) not in sys.path:
        sys.path.insert(0, str(python_root))
