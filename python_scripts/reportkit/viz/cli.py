"""Command-line entry point for ReportKit visualization utilities."""
from .core import _cli


def main() -> None:
    """Run the visualization demo or theme consistency check."""
    _cli()


if __name__ == "__main__":
    main()
