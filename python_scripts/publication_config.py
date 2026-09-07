#!/usr/bin/env python3
"""Read a consumer project's small, dependency-free publication.yaml.

Publication identity belongs to the publication, not to ReportKit. This reads
the flat ``key: value`` subset that `metadata/licenses.yml` already uses, so no
YAML dependency enters the engine. ReportKit vNext replaces this with a
validated schema; keep it deliberately minimal until then.
"""
from __future__ import annotations

from pathlib import Path
import re

CONFIG_NAME = "publication.yaml"

REQUIRED = ("title",)

# Every key a publication may declare. Anything else is a typo, and silently
# ignoring it would strand a title the author believed they had set.
KNOWN = (
    "title",
    "subtitle",
    "author",
    "version",
    "left_header",
    "footer",
    "subject",
    "keywords",
    "disclaimer",
    "project_url",
)


def load_publication_config(path: Path) -> dict[str, str]:
    """Parse publication.yaml. Returns {} when the file is absent."""
    if not path.is_file():
        return {}
    values: dict[str, str] = {}
    for line_number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            raise ValueError(f"{path}:{line_number}: expected key: value")
        key, value = line.split(":", 1)
        key, value = key.strip(), value.strip().strip("'\"")
        if not key:
            raise ValueError(f"{path}:{line_number}: empty key")
        if key not in KNOWN:
            raise ValueError(f"{path}:{line_number}: unknown key {key!r}; known keys: {', '.join(KNOWN)}")
        if not value:
            continue
        values[key] = value
    return values


def slugify(value: str) -> str:
    """Filename-safe slug for the output PDF, derived from the title."""
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "publication"


def resolve_identity(config: dict[str, str], overrides: dict[str, str | None], source_root: Path) -> dict[str, str]:
    """Merge publication.yaml with CLI/environment overrides.

    Overrides win, so a release build can stamp a version without editing the
    project's config. Everything unset falls back to a value derived from the
    title rather than to a hard-coded project identity.
    """
    values = dict(config)
    for key, value in overrides.items():
        if value:
            values[key] = value

    missing = [key for key in REQUIRED if not values.get(key)]
    if missing:
        raise ValueError(
            f"missing publication identity: {', '.join(missing)}. "
            f"Set it in {source_root / CONFIG_NAME} or pass --{missing[0]}."
        )

    title = values["title"]
    values.setdefault("subtitle", title)
    values.setdefault("author", "")
    values.setdefault("version", "draft")
    values.setdefault("left_header", f"REPORTKIT / {title.upper()}")
    values.setdefault("footer", title)
    values.setdefault("subject", "")
    values.setdefault("keywords", "")
    values.setdefault("disclaimer", "")
    values.setdefault("project_url", "")
    values["slug"] = slugify(title)
    return values


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Validate a publication.yaml file.")
    parser.add_argument("path", type=Path, nargs="?", default=Path(CONFIG_NAME))
    args = parser.parse_args()
    try:
        config = load_publication_config(args.path)
        if not config:
            print(f"FAIL: no publication config at {args.path}")
            return 1
        identity = resolve_identity(config, {}, args.path.parent)
    except (OSError, ValueError) as exc:
        print(f"FAIL: {exc}")
        return 1
    print(f"PASS: {identity['title']} ({identity['slug']}) version {identity['version']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
