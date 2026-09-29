"""Target-aware composition audits (agent reasoning loop spec §4.7).

The brief declares observable roles and manual review items. The audit checks
source composition and target grammar; it does not claim that the rendered
pages look good or that their evidence is true.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path
import re
import tempfile
from typing import Any

from .diagnostics import diagnostic_envelope, make_diagnostic
from .editorial_audit import MANUAL_REVIEW as FEATURE_MANUAL_REVIEW
from .editorial_audit import audit_editorial_source
from .registry import generate_registry
from .target import TargetState

BRIEF_NAMES = ("composition-brief.json", "editorial-brief.json")


@dataclass(frozen=True)
class RoleRegistry:
    required_roles: tuple[str, ...] = ()
    role_patterns: dict[str, str] = field(default_factory=dict)
    manual_review: tuple[str, ...] = ()
    local_style_forbidden: tuple[str, ...] = ()


_FEATURE_PATTERNS = {
    "openingvisual": r"\\begin\{openingvisual\}",
    "dropcap": r"\\dropcap\s*\{",
    "featurecolumns": r"\\begin\{featurecolumns\}",
    "pullquote": r"\\pullquote\s*\{",
    "featuresidebar": r"\\begin\{featuresidebar\}",
    "featureexhibit": r"\\begin\{featureexhibit\}",
    "graphic-exhibit": r"\\includegraphics\b|\\begin\{diagram\}",
    "full-width-exhibit": r"\\begin\{featureexhibit\}\[span=full\]",
}
_EQUITY_PATTERNS = {
    "researchfrontpage": r"\\begin\{researchfrontpage\}",
    "ratingstrip": r"\\begin\{ratingstrip\}",
    "whatschanged": r"\\begin\{whatschanged\}",
    "exhibit": r"\\begin\{exhibit\}",
    "financialtable": r"\\begin\{financialtable\}",
    "scenario-cases": r"\\begin\{scenariocases\}",
}
_BRIEF_PATTERNS = {
    "briefheader": r"\\begin\{briefheader\}",
    "decisionpoint": r"\\begin\{decisionpoint\}",
    "exhibit": r"\\begin\{exhibit\}",
    "briefactions": r"\\begin\{briefactions\}",
    "briefsources": r"\\begin\{briefsources\}",
}
_PRESENTATION_PATTERNS = {
    "titleslide": r"\\begin\{titleslide\}",
    "assertionslide": r"\\begin\{assertionslide\}",
    "evidenceslide": r"\\begin\{evidenceslide\}",
    "sectiondivider": r"\\begin\{sectiondivider\}",
    "closingslide": r"\\begin\{closingslide\}",
    "dense-layout mix": r"\\begin\{(?:fullvisual|visualtext|chartslide|tableslide|messageslide)\}",
}
_BOOK_PATTERNS = {
    "bookdetails": r"\\begin\{bookdetails\}",
    "bookpart": r"\\bookpart\s*\{",
    "bookappendix": r"\\bookappendix\b",
    "bookreferences": r"\\begin\{bookreferences\}",
}
_DEFAULT_LOCAL_STYLE = (
    r"\\(?:fontsize|vspace|hspace|definecolor)\b",
    r"\\begin\{minipage\}",
    r"\\color\s*\{",
)
ROLE_REGISTRIES: dict[str, RoleRegistry] = {
    "technical-report": RoleRegistry(
        manual_review=("Review the rendered pages for hierarchy, legibility, and evidence placement.",),
    ),
    "equity-research": RoleRegistry(
        required_roles=("researchfrontpage", "ratingstrip", "whatschanged", "exhibit", "financialtable"),
        role_patterns=_EQUITY_PATTERNS,
        manual_review=(
            "Reconcile every displayed estimate, valuation, and scenario with its cited source.",
            "Confirm rating, price target, risks, and disclosures remain legible in the rendered pages.",
        ),
    ),
    "executive-brief": RoleRegistry(
        required_roles=("briefheader", "decisionpoint", "exhibit", "briefactions", "briefsources"),
        role_patterns=_BRIEF_PATTERNS,
        manual_review=(
            "Confirm the decision and requested approval are clear on the first page.",
            "Check that every action has an owner or timing and every exhibit names its source.",
        ),
    ),
    "feature-article": RoleRegistry(
        required_roles=("openingvisual", "dropcap", "featurecolumns", "pullquote", "featuresidebar", "graphic-exhibit", "full-width-exhibit"),
        role_patterns=_FEATURE_PATTERNS,
        manual_review=FEATURE_MANUAL_REVIEW,
    ),
    "book": RoleRegistry(
        required_roles=("bookdetails", "bookpart", "bookappendix", "bookreferences"),
        role_patterns=_BOOK_PATTERNS,
        manual_review=(
            "Check front matter, part starts, appendices, references, and running furniture across the full book.",
            "Confirm cross-references and page breaks remain correct in the rendered PDF.",
        ),
    ),
    "presentation": RoleRegistry(
        required_roles=("titleslide", "evidenceslide", "dense-layout mix"),
        role_patterns=_PRESENTATION_PATTERNS,
        manual_review=(
            "Review each slide at presentation size for readable text and one clear assertion.",
            "Confirm evidence is legible and the closing slide states the requested action.",
        ),
    ),
}


def _read_brief(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("composition brief must be a JSON object")
    return value


def find_brief(source_root: Path, state: TargetState) -> Path | None:
    """Resolve the intent-linked composition brief, then its canonical names."""
    root = Path(source_root).resolve()
    intent = state.intent or {}
    configured = intent.get("composition_brief") if isinstance(intent, dict) else None
    candidates = ([root / str(configured)] if configured else []) + [root / name for name in BRIEF_NAMES]
    for candidate in candidates:
        try:
            resolved = candidate.resolve()
            if (resolved == root or root in resolved.parents) and resolved.is_file():
                return resolved
        except OSError:
            continue
    return None


def _uncomment(source: str) -> str:
    return "\n".join(re.split(r"(?<!\\)%", line, maxsplit=1)[0] for line in source.splitlines())


def _expand_tex_inputs(tex: Path, state: TargetState) -> str:
    """Include local ``\\input``/``\\include`` files for source-level audits."""
    main = Path(tex).resolve()
    project_root = Path(state.source_root).resolve() if state.source_root is not None else main.parent
    allowed_roots = (project_root, main.parent)
    input_pattern = re.compile(r"\\(?:input|include)\s*\{([^{}]+)\}")
    visited: set[Path] = set()

    def read(path: Path) -> str:
        resolved = path.resolve()
        if resolved in visited or not any(resolved == root or root in resolved.parents for root in allowed_roots):
            return ""
        visited.add(resolved)
        try:
            source = _uncomment(resolved.read_text(encoding="utf-8"))
        except (OSError, UnicodeError):
            return ""

        def replace(match: re.Match[str]) -> str:
            requested = match.group(1).strip()
            if not requested or "\\" in requested:
                return match.group(0)
            relative = Path(requested)
            candidates = [resolved.parent / relative, project_root / relative]
            if not relative.suffix:
                candidates = [candidate.with_suffix(".tex") for candidate in candidates] + candidates
            child = next((candidate for candidate in candidates if candidate.is_file()), None)
            return read(child) if child is not None else match.group(0)

        return input_pattern.sub(replace, source)

    return read(main)


def _generic_inventory(source: str, patterns: dict[str, str]) -> dict[str, int]:
    body = _uncomment(source)
    return {role: len(re.findall(pattern, body, flags=re.S)) for role, pattern in patterns.items()}


def _used_off_target(source: str, publication_type: str) -> list[tuple[str, str]]:
    """Return used LaTeX primitives whose declared role rejects this target."""
    from .primitive_targets import role_for

    body = _uncomment(source)
    registry = generate_registry(strict=False)
    findings: list[tuple[str, str]] = []
    inventories = {kind: set(entries) for kind, entries in registry["primitives"].items()}
    # \\maketitle belongs to the base class rather than a source-adjacent
    # style contract, but it still has a reviewed target role.
    inventories.setdefault("command", set()).add("maketitle")
    for kind, entries in inventories.items():
        if kind == "chart":
            continue
        for name in sorted(entries):
            command = re.search(r"\\" + re.escape(name) + r"(?![A-Za-z@])", body)
            environment = re.search(r"\\begin\s*\{" + re.escape(name) + r"\}", body)
            if not command and not environment:
                continue
            role = role_for(name, kind, publication_type)
            if role in {"discouraged", "absent"}:
                findings.append((name, role))
    return findings


def _universal_diagnostics(source: str, tex: Path, brief: dict[str, Any], state: TargetState) -> list[dict[str, Any]]:
    diagnostics: list[dict[str, Any]] = []
    strict = brief.get("strict") is True
    for primitive, role in _used_off_target(source, state.publication_type):
        diagnostics.append(make_diagnostic(
            "off_target",
            f"Primitive {primitive!r} is {role} for structure={state.publication_type} look={state.theme}.",
            code="RK_PRIMITIVE_OFF_TARGET", severity="error" if strict else "warning",
            source={"file": str(tex), "line": None}, primitive=primitive,
            remediation=(
                f"Replace {primitive!r} with a primitive listed by `reportkit context --slice primitives` "
                f"for structure={state.publication_type}; this brief is strict."
                if strict else
                f"Review {primitive!r}; use only primitives listed by `reportkit context --slice primitives` "
                f"for structure={state.publication_type}."
            ),
        ))
    body = source.split(r"\begin{document}", 1)[-1]
    forbidden = next((pattern for pattern in _DEFAULT_LOCAL_STYLE if re.search(pattern, body)), None)
    if forbidden:
        diagnostics.append(make_diagnostic(
            "off_target", f"Local styling command {re.search(forbidden, body).group()} bypasses the target theme.",
            code="RK_LOCAL_STYLE", severity="error", source={"file": str(tex), "line": None},
            remediation="Remove the local styling command and use the declared theme's primitives; rerun `reportkit check`.",
        ))
    if not isinstance(brief.get("visual_reference"), str) or not str(brief.get("visual_reference", "")).strip():
        diagnostics.append(make_diagnostic(
            "publication_validation", "Composition brief has no visual_reference.",
            code="RK_COMPOSITION_REFERENCE_MISSING", severity="warning",
            source={"file": str(tex), "line": None}, primitive="composition-brief.visual_reference",
            remediation="Set `visual_reference` in composition-brief.json or record that no visual reference was supplied.",
        ))
    return diagnostics


def audit_source(tex: Path, brief: Path | None, state: TargetState) -> dict[str, Any]:
    """Audit direct TeX or generated TeX against the selected target brief."""
    if brief is None:
        return diagnostic_envelope(
            [], passed=True, source=str(tex), brief=None, publication_type=state.publication_type,
            inventory={}, manual_review_required=False, manual_review=[],
        )
    try:
        source = Path(tex).read_text(encoding="utf-8")
        request = _read_brief(Path(brief))
    except (OSError, UnicodeError, ValueError, json.JSONDecodeError) as exc:
        diagnostic = make_diagnostic(
            "configuration_error", f"cannot read composition source or brief: {exc}",
            code="RK_COMPOSITION_BRIEF_INVALID", source={"file": str(brief)},
        )
        return diagnostic_envelope(
            [diagnostic], passed=False, source=str(tex), brief=str(brief),
            publication_type=state.publication_type, inventory={},
        )
    expanded_source = _expand_tex_inputs(Path(tex), state)
    record = ROLE_REGISTRIES.get(state.publication_type, RoleRegistry())
    if not str(request.get("visual_reference", "")).strip() and isinstance(state.intent, dict):
        intent_reference = state.intent.get("visual_reference")
        if isinstance(intent_reference, str) and intent_reference.strip():
            request["visual_reference"] = intent_reference
    required = request.get("required", list(record.required_roles))
    if not isinstance(required, list) or any(not isinstance(role, str) for role in required):
        diagnostic = make_diagnostic(
            "configuration_error", "composition brief `required` must be a list of role names.",
            code="RK_COMPOSITION_BRIEF_INVALID", source={"file": str(brief)},
        )
        return diagnostic_envelope([diagnostic], passed=False, source=str(tex), brief=str(brief), inventory={})
    requested_manual_review = request.get("manual_review", list(record.manual_review))
    if not isinstance(requested_manual_review, list) or any(not isinstance(item, str) for item in requested_manual_review):
        diagnostic = make_diagnostic(
            "configuration_error", "composition brief `manual_review` must be a list of strings.",
            code="RK_COMPOSITION_BRIEF_INVALID", source={"file": str(brief)},
        )
        return diagnostic_envelope([diagnostic], passed=False, source=str(tex), brief=str(brief), inventory={})

    # Keep the existing editorial audit's detailed ratio, exhibit, section, and
    # local-style checks, while presenting the generalized brief name/API.
    if state.publication_type == "feature-article":
        compatible_brief = dict(request)
        compatible_brief.setdefault("required", required)
        compatible_brief.setdefault("visual_reference", "")
        if not str(compatible_brief.get("visual_reference", "")).strip():
            compatible_brief["visual_reference"] = "(not supplied)"
            # The legacy audit accepts a path; use a unique system temporary
            # directory so concurrent checks never touch the consumer brief.
            with tempfile.TemporaryDirectory(prefix="reportkit-composition-") as temp_dir:
                temp_brief = Path(temp_dir) / "editorial-brief.json"
                temp_brief.write_text(json.dumps(compatible_brief), encoding="utf-8")
                result = audit_editorial_source(Path(tex), temp_brief, source_text=expanded_source)
        else:
            result = audit_editorial_source(Path(tex), Path(brief), source_text=expanded_source)
        diagnostics = list(result.get("diagnostics", []))
        inventory = dict(result.get("inventory", {}))
        manual_review = list(requested_manual_review)
        details = {
            key: value for key, value in result.items()
            if key not in {
                "passed", "diagnostics", "source", "brief", "inventory", "visual_reference",
                "manual_review", "manual_review_required", "schema_version",
            }
        }
    else:
        patterns = record.role_patterns
        inventory = _generic_inventory(expanded_source, patterns)
        diagnostics = []
        unknown = sorted(set(required) - set(patterns))
        if unknown:
            diagnostics.append(make_diagnostic(
                "configuration_error", f"Unknown composition roles for {state.publication_type}: {', '.join(unknown)}.",
                code="RK_COMPOSITION_BRIEF_INVALID", source={"file": str(brief)}, candidates=sorted(patterns),
            ))
        for role in required:
            if role in patterns and inventory.get(role, 0) == 0:
                diagnostics.append(make_diagnostic(
                    "publication_validation", f"Composition brief requires {role}, but the source has none.",
                    code="RK_COMPOSITION_ROLE_MISSING", source={"file": str(tex), "line": None}, primitive=role,
                    remediation=f"Add a target-native {role} role where the publication's evidence and structure call for it, or revise the brief with a documented reason.",
                ))
        manual_review = list(requested_manual_review)
        details = {}

    diagnostics.extend(_universal_diagnostics(expanded_source, Path(tex), request, state))
    return diagnostic_envelope(
        diagnostics, source=str(tex), brief=str(brief), publication_type=state.publication_type,
        inventory=inventory, manual_review_required=bool(manual_review), manual_review=manual_review,
        visual_reference=request.get("visual_reference"), **details,
    )
