"""Language and script truthfulness contract.

Agent-interface spec §13 and the multi-format plan's D-prime 3 item: every
theme declares which scripts and languages it has actually proven, which
fonts cover each proven script, and which languages are recorded only as PDF
catalog metadata. Renderers declare the text directions they can set. This
module turns those declarations into three things:

* the ``language_support`` records ``reportkit context`` publishes, so an
  agent can pick a compatible theme before it writes anything;
* the pre-compile diagnostics ``reportkit check`` and ``reportkit build``
  emit for a declared ``language``; and
* the tables the generated LaTeX registry carries, so the TeX core applies
  the same rule to hand-written documents (locale typography is loaded only
  for verified languages; RTL is always an error).

Right-to-left text is explicitly unsupported by every renderer. Vietnamese is
metadata-only: the Latin glyphs it needs happen to exist in the LuaLaTeX
Libertinus faces, but no fixture has proven its locale typography, and the
pdfLaTeX default theme cannot typeset it at all.
"""
from __future__ import annotations

from dataclasses import dataclass
import re
from typing import TYPE_CHECKING, Any, Mapping

from .diagnostics import make_diagnostic

if TYPE_CHECKING:  # pragma: no cover - typing only
    from .themes import Theme

# ISO 15924 scripts written right to left. A theme may not claim any of these
# while every renderer declares ``rtl: unsupported``.
RTL_SCRIPTS = frozenset({"Adlm", "Arab", "Hebr", "Mand", "Nkoo", "Rohg", "Samr", "Syrc", "Thaa", "Yezi"})

# BCP 47 primary language subtags whose default script is right to left. A
# declared document language in this set is always rejected rather than
# silently rendered left to right.
RTL_LANGUAGES = frozenset({"ar", "arc", "ckb", "dv", "fa", "he", "iw", "ps", "sd", "syr", "ug", "ur", "yi"})

# Locale-aware typography (hyphenation patterns, captions, quotation and
# spacing conventions) for languages a theme may mark verified. Keys are
# normalized BCP 47 tags; a lookup tries the full tag, then the primary
# subtag. Values are babel language names. A language cannot be declared
# verified unless it has an entry here -- that is the mechanism, not a list
# of what any given theme supports.
#
# Regional English deliberately has no entry of its own: the pinned TeX
# format carries only US English patterns, and babel's british/australian
# locales log "Hyphen rules for 'british' set to \l@english" there.
# Claiming UK hyphenation would be untrue, so en-GB resolves to the same
# american locale through its primary subtag.
LOCALE_TYPOGRAPHY: Mapping[str, str] = {
    "en": "american",
    "en-US": "american",
}

# Declared per renderer in publications.RENDERERS. Every renderer today sets
# left-to-right text only; see the module docstring.
RENDERER_LANGUAGE_SUPPORT: Mapping[str, Any] = {
    "catalog_language": "supported",
    "text_direction": ["ltr"],
    "rtl": "unsupported",
    "locale_typography": {
        "mechanism": "babel",
        "loaded_for": "verified-languages-only",
        "default_language": "en-US",
        "default_loads_package": False,
    },
    "missing_glyph": {
        "strict": "fatal: the TeX engine stops at the first missing glyph (\\tracinglostchars=3)",
        "fallback": "blocking missing_glyph log diagnostic unless allowlisted by the project",
    },
}

LANGUAGE_STATUSES = ("verified", "metadata_only", "rtl_unsupported", "undeclared")

_TAG = re.compile(r"^(?P<primary>[A-Za-z]{2,3})(?P<rest>(?:-[A-Za-z0-9]{1,8})*)$")


def normalize_language_tag(tag: str) -> str:
    """Return a BCP 47 tag with canonical case, or raise ``ValueError``."""
    value = str(tag).strip().replace("_", "-")
    match = _TAG.fullmatch(value)
    if not match:
        raise ValueError(
            f"language {tag!r} is not a BCP 47 tag such as 'en', 'en-GB', or 'vi'"
        )
    parts = [match.group("primary").lower()]
    for subtag in [item for item in match.group("rest").split("-") if item]:
        if len(subtag) == 4 and subtag.isalpha():
            parts.append(subtag.title())
        elif len(subtag) == 2 and subtag.isalpha():
            parts.append(subtag.upper())
        else:
            parts.append(subtag.lower())
    return "-".join(parts)


def primary_subtag(tag: str) -> str:
    return normalize_language_tag(tag).split("-", 1)[0]


def locale_typography_for(tag: str) -> str | None:
    """Return the babel language name for a tag, or ``None``."""
    normalized = normalize_language_tag(tag)
    return LOCALE_TYPOGRAPHY.get(normalized) or LOCALE_TYPOGRAPHY.get(normalized.split("-", 1)[0])


@dataclass(frozen=True)
class LanguageResolution:
    """How one declared document language resolves against one theme."""

    tag: str
    primary: str
    theme: str
    status: str
    locale_typography: str | None

    def as_dict(self) -> dict[str, Any]:
        return {
            "tag": self.tag, "primary": self.primary, "theme": self.theme,
            "status": self.status, "locale_typography": self.locale_typography,
        }


def resolve_language(tag: str, theme: str | "Theme") -> LanguageResolution:
    """Resolve a declared language against a theme's script coverage."""
    from .themes import get_theme

    record = get_theme(theme) if isinstance(theme, str) else theme
    coverage = record.script_coverage
    normalized = normalize_language_tag(tag)
    primary = normalized.split("-", 1)[0]
    if primary in RTL_LANGUAGES:
        status = "rtl_unsupported"
    elif primary in coverage.verified_languages:
        status = "verified"
    elif primary in coverage.metadata_only_languages:
        status = "metadata_only"
    else:
        status = "undeclared"
    return LanguageResolution(
        tag=normalized, primary=primary, theme=record.name, status=status,
        locale_typography=locale_typography_for(normalized) if status == "verified" else None,
    )


def language_diagnostics(language: Any, theme: str, *, font_policy: str = "fallback") -> list[dict[str, Any]]:
    """Return pre-compile diagnostics for a publication's declared language.

    An omitted language keeps the historical en-US catalog default and emits
    nothing. RTL and malformed tags are always errors; an undeclared language
    is an error only under ``font_policy: strict``.
    """
    if language in (None, ""):
        return []
    primitive = "publication.language"
    docs = "#/selection/language_support"
    try:
        resolution = resolve_language(str(language), theme)
    except ValueError as exc:
        return [make_diagnostic("configuration_error", str(exc), code="RK_LANGUAGE_TAG_INVALID", primitive=primitive, docs=docs)]
    details = resolution.as_dict()
    if resolution.status == "rtl_unsupported":
        return [make_diagnostic(
            "configuration_error",
            f"language {resolution.tag!r} is written right to left; RTL is explicitly unsupported by every ReportKit renderer and theme",
            code="RK_LANGUAGE_RTL_UNSUPPORTED", primitive=primitive, docs=docs, details=details,
            remediation="Remove the RTL language declaration; ReportKit does not typeset right-to-left text.",
        )]
    if resolution.status == "metadata_only":
        return [make_diagnostic(
            "configuration_error",
            f"language {resolution.tag!r} is metadata-only for theme {resolution.theme!r}: it sets the PDF catalog language, but no locale typography (hyphenation, quotation, spacing) is loaded",
            code="RK_LANGUAGE_METADATA_ONLY", severity="warning", primitive=primitive, docs=docs, details=details,
            remediation="Review hyphenation and punctuation by eye, or use a theme that verifies this language.",
        )]
    if resolution.status == "undeclared":
        strict = str(font_policy) == "strict"
        return [make_diagnostic(
            "configuration_error",
            f"language {resolution.tag!r} is not declared by theme {resolution.theme!r}"
            + ("; theme.font_policy: strict refuses undeclared languages" if strict else "; only the PDF catalog language will be set"),
            code="RK_LANGUAGE_UNSUPPORTED" if strict else "RK_LANGUAGE_UNDECLARED",
            severity="error" if strict else "warning", primitive=primitive, docs=docs, details=details,
            candidates=sorted(get_theme_language_candidates(theme)),
            remediation="Choose a language the theme verifies (see reportkit context --slice selection), or use theme.font_policy: fallback.",
        )]
    return []


def get_theme_language_candidates(theme: str) -> set[str]:
    from .themes import get_theme

    coverage = get_theme(theme).script_coverage
    return set(coverage.verified_languages) | set(coverage.metadata_only_languages)


def theme_language_support(theme: "Theme") -> dict[str, Any]:
    """Return the JSON-friendly ``language_support`` record for one theme.

    ``verified``/``metadata_only``/``scripts``/``rtl`` keep the v1.x shape;
    ``scripts.font_stacks`` and ``locale_typography`` are additive.
    """
    coverage = theme.script_coverage
    return {
        "verified": list(coverage.verified_languages),
        "metadata_only": list(coverage.metadata_only_languages),
        "scripts": {
            "verified": list(coverage.verified),
            "metadata_only": list(coverage.metadata_only),
            "font_stacks": {
                script: {role: list(getattr(stack, role)) for role in ("body", "heading", "mono")}
                for script, stack in sorted(coverage.font_stacks.items())
            },
        },
        "rtl": coverage.rtl,
        "locale_typography": {
            tag: babel for tag, babel in sorted(LOCALE_TYPOGRAPHY.items())
            if tag.split("-", 1)[0] in coverage.verified_languages
        },
    }


def language_compatibility(theme_support: Mapping[str, Any], renderer_support: Mapping[str, Any]) -> dict[str, Any]:
    """Combine a theme's and a renderer's declarations for one build target."""
    rtl = "unsupported" if "unsupported" in {theme_support.get("rtl"), renderer_support.get("rtl")} else str(theme_support.get("rtl"))
    return {
        **{key: value for key, value in theme_support.items() if key != "rtl"},
        "rtl": rtl,
        "text_direction": list(renderer_support.get("text_direction", ["ltr"])),
        "missing_glyph": dict(renderer_support.get("missing_glyph", {})),
    }


def validate_script_coverage(theme: "Theme") -> list[str]:
    """Return language/script contract violations for one theme.

    Messages name the exact ``ScriptCoverageTokens`` field to declare, so a
    new theme module fails with an instruction rather than a guess.
    """
    coverage = theme.script_coverage
    errors: list[str] = []
    verified = set(coverage.verified)
    metadata_only = set(coverage.metadata_only)
    if not verified:
        errors.append("script_coverage.verified must name at least one ISO 15924 script, e.g. ('Latn',)")
    if verified & metadata_only:
        errors.append(f"script_coverage scripts cannot be both verified and metadata_only: {sorted(verified & metadata_only)}")
    for script in sorted(verified | metadata_only):
        if not re.fullmatch(r"[A-Z][a-z]{3}", script):
            errors.append(f"script_coverage script {script!r} is not an ISO 15924 code such as 'Latn'")
    rtl_claims = sorted((verified | metadata_only) & RTL_SCRIPTS)
    if rtl_claims:
        errors.append(f"script_coverage cannot claim right-to-left scripts {rtl_claims}; RTL is unsupported")
    if coverage.rtl != "unsupported":
        errors.append("script_coverage.rtl must be 'unsupported'; no ReportKit renderer sets right-to-left text")
    for script in sorted(verified):
        stack = coverage.font_stacks.get(script)
        if stack is None:
            errors.append(
                f"script_coverage.font_stacks must declare a ScriptFontStack(body=..., heading=..., mono=...) for verified script {script!r}"
            )
            continue
        for role in ("body", "heading", "mono"):
            families = getattr(stack, role)
            if not families or any(not str(family).strip() for family in families):
                errors.append(f"script_coverage.font_stacks[{script!r}].{role} must list at least one font family")
    for script in sorted(set(coverage.font_stacks) - verified - metadata_only):
        errors.append(f"script_coverage.font_stacks declares {script!r}, which is neither verified nor metadata_only")
    verified_languages = set(coverage.verified_languages)
    metadata_languages = set(coverage.metadata_only_languages)
    if not verified_languages:
        errors.append("script_coverage.verified_languages must name at least one BCP 47 primary subtag, e.g. ('en',)")
    if verified_languages & metadata_languages:
        errors.append(
            f"script_coverage languages cannot be both verified and metadata_only: {sorted(verified_languages & metadata_languages)}"
        )
    for language in sorted(verified_languages | metadata_languages):
        if not re.fullmatch(r"[a-z]{2,3}", language):
            errors.append(f"script_coverage language {language!r} must be a lower-case BCP 47 primary subtag such as 'en'")
    rtl_languages = sorted((verified_languages | metadata_languages) & RTL_LANGUAGES)
    if rtl_languages:
        errors.append(f"script_coverage cannot declare right-to-left languages {rtl_languages}; RTL is unsupported")
    for language in sorted(verified_languages):
        if language not in LOCALE_TYPOGRAPHY:
            errors.append(
                f"script_coverage.verified_languages declares {language!r}, but reportkit.languages.LOCALE_TYPOGRAPHY has no locale typography for it"
            )
    return errors


def render_latex_language_tables(themes: Mapping[str, Mapping[str, Any]]) -> list[str]:
    """Return generated TeX lines for the LaTeX core's language resolution."""
    def csdef(name: str, value: str) -> str:
        return rf"\expandafter\def\csname {name}\endcsname{{{value}}}"

    lines = [csdef(f"RKRTLLanguage@{language}", "1") for language in sorted(RTL_LANGUAGES)]
    lines.extend(csdef(f"RKLocaleBabel@{tag}", babel) for tag, babel in sorted(LOCALE_TYPOGRAPHY.items()))
    for name, record in sorted(themes.items()):
        support = record["language_support"]
        for language in support["verified"]:
            lines.append(csdef(f"RKThemeLanguage@{name}@{language}", "verified"))
        for language in support["metadata_only"]:
            lines.append(csdef(f"RKThemeLanguage@{name}@{language}", "metadata-only"))
        lines.append(csdef(f"RKThemeScripts@{name}", ",".join(support["scripts"]["verified"])))
    return lines


__all__ = [
    "LANGUAGE_STATUSES", "LOCALE_TYPOGRAPHY", "LanguageResolution", "RENDERER_LANGUAGE_SUPPORT",
    "RTL_LANGUAGES", "RTL_SCRIPTS", "language_compatibility", "language_diagnostics",
    "locale_typography_for", "normalize_language_tag", "primary_subtag", "render_latex_language_tables",
    "resolve_language", "theme_language_support", "validate_script_coverage",
]
