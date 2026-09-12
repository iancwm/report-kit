"""Compatibility import for :mod:`reportkit.publication_config`."""
# This module deliberately preserves the legacy import path.
# ruff: noqa: F401,F403
from reportkit.publication_config import *  # noqa: F401,F403
from reportkit.publication_config import main

if __name__ == "__main__":
    raise SystemExit(main())
