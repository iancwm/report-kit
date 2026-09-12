"""Compatibility import for :mod:`reportkit.license_metadata`."""
# This module deliberately preserves the legacy import path.
# ruff: noqa: F401,F403
from reportkit.license_metadata import *  # noqa: F401,F403
from reportkit.license_metadata import main

if __name__ == "__main__":
    raise SystemExit(main())
