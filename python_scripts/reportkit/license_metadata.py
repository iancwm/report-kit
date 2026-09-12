"""Validate ReportKit's small, dependency-free licence metadata file."""
from __future__ import annotations

from pathlib import Path
import re
from urllib.parse import urlparse

REQUIRED = ("software_license", "content_license", "content_license_url")
# This validator complements reportkit.latex.tex_escape_url; URLs are
# rejected here rather than escaped because malformed percent escapes and
# URL delimiters need to remain visible to the URL parser.
INVALID_URL_LATEX_RE = re.compile(r"[\\{}$^~_]")
INVALID_PERCENT_ESCAPE_RE = re.compile(r"%(?![0-9A-Fa-f]{2})")


def validate_license_metadata(values: dict[str, str], source: Path | str = "licence metadata") -> dict[str, str]:
    """Validate global or resolved publication license metadata."""
    missing = [key for key in REQUIRED if not values.get(key)]
    if missing:
        raise ValueError(f"{source}: missing required fields: {', '.join(missing)}")
    url = values["content_license_url"]
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.netloc:
        raise ValueError(f"{source}: content_license_url must be an HTTPS URL")
    if INVALID_URL_LATEX_RE.search(url):
        raise ValueError(
            f"{source}: content_license_url contains LaTeX-special characters; "
            "percent-encode them in the URL"
        )
    if INVALID_PERCENT_ESCAPE_RE.search(url):
        raise ValueError(f"{source}: content_license_url contains an invalid percent escape")
    return values


def load_license_metadata(path: Path) -> dict[str, str]:
    """Load and validate the repository's simple ``key: value`` licence file."""
    if not path.is_file():
        raise ValueError(f"licence metadata is missing: {path}")
    values: dict[str, str] = {}
    for line_number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            raise ValueError(f"{path}:{line_number}: expected key: value")
        key, value = line.split(":", 1)
        key, value = key.strip(), value.strip().strip("'\"")
        if not key or not value:
            raise ValueError(f"{path}:{line_number}: keys and values cannot be empty")
        values[key] = value
    return validate_license_metadata(values, path)


def rights_notice(metadata: dict[str, str]) -> str:
    """Return the standard publication-content rights notice."""
    return (
        "Original prose and diagrams in this publication are licensed under "
        f"{metadata['content_license']} ({metadata['content_license_url']}). "
        "Code examples and third-party assets retain their separate licences."
    )


def main() -> int:
    """Validate a licence metadata file from the command line."""
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path, nargs="?", default=Path("metadata/licenses.yml"))
    args = parser.parse_args()
    try:
        values = load_license_metadata(args.path)
    except (OSError, ValueError) as exc:
        print(f"FAIL: {exc}")
        return 1
    print("PASS: licence metadata", values["content_license"], values["content_license_url"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
