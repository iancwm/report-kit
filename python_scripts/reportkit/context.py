"""Build the versioned self-description returned by ``reportkit context``."""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import subprocess
from typing import Any, Iterable

from .config import load_publication_config, resolve_document, resolve_theme
from .diagnostics import make_diagnostic
from .publications import PUBLICATION_TYPES, RENDERERS, THEMES, compatibility_error
from .registry import CALLOUT_ENVIRONMENTS, COMMANDS, LEGACY_CHART_NAMES, PRIMITIVE_KINDS, generate_registry
from .toolchain import toolchain_context
from .version import CONTRACT_VERSION, CONTEXT_SCHEMA_VERSION, DIAGNOSTIC_SCHEMA_VERSION, REPORTKIT_VERSION


def _git(repo_root: Path, *args: str) -> str:
    try:
        result = subprocess.run(["git", "-C", str(repo_root), *args], capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.SubprocessError):
        return "unknown"
    return result.stdout.strip() if result.returncode == 0 and result.stdout.strip() else "unknown"


def _filter_primitives(
    primitives: dict[str, dict[str, Any]],
    *,
    publication_type: str | None,
    theme: str | None,
    kinds: Iterable[str] | None,
) -> dict[str, dict[str, Any]]:
    selected_kinds = set(kinds or PRIMITIVE_KINDS)
    result: dict[str, dict[str, Any]] = {}
    for kind in PRIMITIVE_KINDS:
        if kind not in selected_kinds:
            continue
        result[kind] = {}
        for name, record in primitives[kind].items():
            available = record["available_in"]
            if publication_type and publication_type not in available["publication_types"]:
                continue
            if theme and theme not in available["themes"]:
                continue
            filtered = deepcopy(record)
            filtered_available = filtered["available_in"]
            if publication_type:
                filtered_available["publication_types"] = [publication_type]
                compatible_themes = set(PUBLICATION_TYPES[publication_type]["themes"])
                filtered_available["themes"] = [
                    value for value in filtered_available["themes"] if value in compatible_themes
                ]
            if theme:
                filtered_available["themes"] = [theme]
                compatible_publications = {
                    value for value, publication in PUBLICATION_TYPES.items() if theme in publication["themes"]
                }
                filtered_available["publication_types"] = [
                    value for value in filtered_available["publication_types"] if value in compatible_publications
                ]
            filtered_available["renderers"] = sorted({
                PUBLICATION_TYPES[value]["renderer"]
                for value in filtered_available["publication_types"]
            })
            result[kind][name] = filtered
    return result


def build_context(
    repo_root: Path | None = None,
    source_root: Path | None = None,
    profile: str | None = None,
    *,
    publication_type: str | None = None,
    theme: str | None = None,
    kinds: Iterable[str] | None = None,
) -> dict[str, Any]:
    repo_root = (repo_root or Path(__file__).resolve().parents[2]).resolve()
    source_root = (source_root or repo_root / "publication_pipeline" / "example_publication").resolve()
    config = load_publication_config(source_root / "publication.yaml")
    document = resolve_document(config, profile)
    selected_publication = str(document.get("publication_type", "technical-report"))
    selected_theme = str(document.get("theme", "default"))
    for value, known, label in (
        (selected_publication, PUBLICATION_TYPES, "publication type"),
        (selected_theme, THEMES, "theme"),
        (publication_type, PUBLICATION_TYPES, "publication type"),
        (theme, THEMES, "theme"),
    ):
        if value is not None and value not in known:
            raise ValueError(f"unknown {label} {value!r}; known values: {', '.join(known)}")
    conflict = compatibility_error(selected_publication, selected_theme)
    if conflict:
        raise ValueError(conflict)
    if publication_type and theme:
        filter_conflict = compatibility_error(publication_type, theme)
        if filter_conflict:
            raise ValueError(filter_conflict)
    effective_publication = publication_type
    if effective_publication is None and theme is not None:
        effective_publication = next(
            name for name, record in PUBLICATION_TYPES.items() if theme in record["themes"]
        )
    effective_publication = effective_publication or selected_publication
    effective_theme = theme or (
        PUBLICATION_TYPES[effective_publication]["themes"][0]
        if publication_type is not None
        else selected_theme
    )
    resolved_conflict = compatibility_error(effective_publication, effective_theme)
    if resolved_conflict:
        raise ValueError(resolved_conflict)
    selected_kinds = list(kinds or PRIMITIVE_KINDS)
    unknown_kinds = sorted(set(selected_kinds) - set(PRIMITIVE_KINDS))
    if unknown_kinds:
        raise ValueError(f"unknown primitive kind {unknown_kinds[0]!r}; known values: {', '.join(PRIMITIVE_KINDS)}")

    registry = generate_registry(repo_root, strict=True)
    revision = _git(repo_root, "describe", "--tags", "--always")
    class_version = registry["class_version"]
    primitives = _filter_primitives(
        registry["primitives"], publication_type=publication_type, theme=theme, kinds=selected_kinds,
    )
    diagnostics: list[dict[str, Any]] = []
    if revision != "unknown" and class_version != "unknown" and not revision.endswith(class_version):
        diagnostics.append(make_diagnostic(
            "contract_version",
            f"git ref {revision} does not end with class version {class_version}",
            code="RK_VERSION_PARITY", severity="warning", docs="#/reportkit_version",
            remediation="Tag the release with the ReportKit version or use a checkout whose class metadata matches its revision.",
        ))
    explicit_selection = publication_type is not None or theme is not None
    effective_engine = (
        THEMES[effective_theme]["required_engine"]
        if explicit_selection
        else document.get("engine", THEMES[effective_theme]["required_engine"])
    )
    effective_paper = (
        PUBLICATION_TYPES[effective_publication]["paper"]
        if explicit_selection
        else document.get("paper", PUBLICATION_TYPES[effective_publication]["paper"])
    )
    document_options = f"theme={effective_theme},publication-type={effective_publication}"
    result: dict[str, Any] = {
        "schema_version": CONTEXT_SCHEMA_VERSION,
        "passed": True,
        "diagnostics": diagnostics,
        "issues": diagnostics,
        "errors": [],
        "contract_version": CONTRACT_VERSION,
        "reportkit_version": REPORTKIT_VERSION,
        "revision": revision,
        "selection": {
            "engine": effective_engine,
            "theme": effective_theme,
            "publication_type": effective_publication,
            "renderer": PUBLICATION_TYPES[effective_publication]["renderer"],
            "paper": effective_paper,
            "profile": profile or "draft",
        },
        "filters": {"publication_type": publication_type, "theme": theme, "kinds": selected_kinds},
        "capabilities": {
            "publication_types": deepcopy(PUBLICATION_TYPES),
            "themes": deepcopy(THEMES),
            "renderers": deepcopy(RENDERERS),
            "primitives": primitives,
            "authoring": {
                "mode": "trusted-latex",
                "document_template": (
                    f"\\documentclass[{document_options}]{{reportkit}}\n"
                    "\\title{Contract acceptance}\n\\author{ReportKit}\n"
                    "\\begin{document}\n\\maketitle\n{{body}}\n\\end{document}\n"
                ),
                "chart_prelude": (
                    "import pandas as pd\nimport numpy as np\nimport reportkit_viz as rkv\n"
                    f"rkv.apply_theme({effective_theme!r})"
                ),
                "chart_export": "rkv.save_figure(fig, output_path)",
                "markdown_raw_tex": "disabled",
                "trusted_escape_hatches": ["direct .tex", "fragments/*.tex"],
            },
        },
        "commands": dict(COMMANDS),
        "command_contract": deepcopy(registry["command_contract"]),
        "schemas": {
            "context": {"version": CONTEXT_SCHEMA_VERSION, "id": "urn:reportkit:schema:context:1.0.0"},
            "diagnostic": {"version": DIAGNOSTIC_SCHEMA_VERSION, "id": "urn:reportkit:schema:diagnostic:1.0.0"},
        },
        "toolchain": toolchain_context(repo_root),
        "deprecated_fields": ["version", "class_version", "document", "theme_config", "components", "commands", "command_strings"],
        # v1.x compatibility fields.
        "version": revision,
        "class_version": class_version,
        "document": {
            "engine": document.get("engine", "pdflatex"), "theme": selected_theme,
            "publication_type": selected_publication, "paper": document.get("paper", "a4"),
        },
        "theme_config": {
            "font_family": resolve_theme(config, profile).get("font_family", "Google Sans"),
            "font_path": resolve_theme(config, profile).get("font_path", ""),
            "font_policy": resolve_theme(config, profile).get("font_policy", "fallback"),
        },
        "components": {
            "figures": sorted(primitives.get("figure", {})),
            "callouts": sorted(name for name in primitives.get("callout", {}) if name in CALLOUT_ENVIRONMENTS and name not in {"evidence", "limitation", "tip"}),
            "callout_aliases": {name: target for name, target in {"evidence": "evidencenote", "limitation": "limitationnote", "tip": "tipnote"}.items() if name in primitives.get("callout", {})},
            "charts": sorted(name for name in primitives.get("chart", {}) if name in LEGACY_CHART_NAMES),
        },
        "command_strings": dict(COMMANDS),
    }
    if diagnostics:
        result["version_warning"] = f"git ref {revision} does not end with class version {class_version}"
    return result
