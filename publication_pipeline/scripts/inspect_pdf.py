#!/usr/bin/env python3
"""Run deterministic PDF checks using PyMuPDF only."""
from __future__ import annotations

import argparse
import ast
import json
from pathlib import Path
import re
import sys
from typing import Any, Mapping, Sequence

try:
    from _bootstrap import ensure_reportkit_importable
except ImportError:  # imported as publication_pipeline.scripts.inspect_pdf
    from ._bootstrap import ensure_reportkit_importable

ensure_reportkit_importable()

try:
    import pymupdf as fitz
except ImportError:  # PyMuPDF < 1.26
    try:
        import fitz  # type: ignore
    except ImportError:
        fitz = None  # type: ignore[assignment]

from reportkit.diagnostics import diagnostic_envelope, make_diagnostic  # noqa: E402


SLIDE_METADATA_FIELDS = ("title", "author", "subject", "keywords")
SELECTION_MARKER_PREFIX = "REPORTKIT-SELECTED"
SELECTION_MARKER_FIELDS = (
    "publication_type",
    "requested_theme",
    "theme",
    "renderer",
    "class",
    "template",
    "writer",
    "engine",
    "paper",
    "canvas",
)
_SELECTION_MARKER_FIELD_NAMES = "|".join(re.escape(field) for field in SELECTION_MARKER_FIELDS)
_SELECTION_MARKER_FIELD = re.compile(
    rf"(?P<key>{_SELECTION_MARKER_FIELD_NAMES})=(?P<value>.*?)(?=\s+(?:{_SELECTION_MARKER_FIELD_NAMES})=|$)"
)


def _selection_marker_diagnostic(
    message: str,
    *,
    code: str,
    source: str,
    details: dict[str, object],
) -> dict[str, object]:
    """Create a stable diagnostic for the target-selection PDF gate."""
    return make_diagnostic(
        "configuration_error",
        message,
        code=code,
        source={"file": source},
        remediation="Rebuild the PDF and verify that its resolved target marker matches the requested publication configuration.",
        details=details,
    )


def _selection_marker_source(source: Path | str) -> tuple[str, str]:
    if isinstance(source, Path):
        return str(source), source.read_text(encoding="utf-8", errors="replace")
    return "<inline selection marker>", source


def _parse_selection_marker_line(line: str) -> tuple[dict[str, str] | None, str | None]:
    marker = line.strip()
    if marker == SELECTION_MARKER_PREFIX:
        return None, "marker has no key/value fields"
    if not marker.startswith(SELECTION_MARKER_PREFIX + " "):
        return None, "line does not start with the selection-marker prefix"

    body = marker[len(SELECTION_MARKER_PREFIX):].strip()
    fields: dict[str, str] = {}
    cursor = 0
    for match in _SELECTION_MARKER_FIELD.finditer(body):
        if body[cursor:match.start()].strip():
            return None, f"unrecognised marker content {body[cursor:match.start()].strip()!r}"
        key = match.group("key")
        if key in fields:
            return None, f"marker field {key!r} is repeated"
        value = match.group("value").strip()
        if not value:
            return None, f"marker field {key!r} is empty"
        fields[key] = value
        cursor = match.end()
    if body[cursor:].strip():
        return None, f"unrecognised marker content {body[cursor:].strip()!r}"
    missing = [field for field in SELECTION_MARKER_FIELDS if field not in fields]
    if missing:
        return None, f"marker is missing field(s): {', '.join(missing)}"
    return fields, None


def _selection_value(key: str, value: object) -> object:
    if key == "paper":
        return None if value is None or value == "-" else str(value)
    if key == "canvas":
        if value is None or value == "-":
            return None
        if isinstance(value, Mapping):
            return dict(value)
        try:
            parsed = ast.literal_eval(str(value))
        except (SyntaxError, ValueError):
            raise ValueError("canvas must be '-' or a mapping") from None
        if not isinstance(parsed, dict):
            raise ValueError("canvas must be '-' or a mapping")
        return parsed
    return str(value)


def _canonical_marker_theme(theme: str) -> str:
    """Resolve the registry alias used by the marker's requested theme."""
    try:
        from reportkit.publications import THEMES
    except ImportError:
        return theme
    record = THEMES.get(theme)
    if isinstance(record, Mapping):
        return str(record.get("alias_of") or theme)
    return theme


def _normalise_expected_selection(key: str, value: object) -> object:
    marker_key = {
        "class_name": "class",
        "pandoc_writer": "writer",
        "canonical_theme": "theme",
        "requested_name": "requested_theme",
    }.get(key, key)
    return _selection_value(marker_key, value)


def inspect_selection_marker(
    source: Path | str,
    *,
    expected_selection: Mapping[str, object] | None = None,
    required: bool = True,
) -> dict:
    """Inspect one ``REPORTKIT-SELECTED`` marker from a build log.

    A marker is normally consumed from the log adjacent to the PDF by
    :func:`inspect`. Passing the marker text directly makes this check useful
    to other gates and keeps the parsing independent of PDF geometry.
    ``expected_selection`` may be a full ``BuildTarget.as_dict()`` result;
    fields not represented in the marker are ignored.
    """
    source_label = str(source) if isinstance(source, Path) else "<inline selection marker>"
    try:
        _, text = _selection_marker_source(source)
    except OSError as exc:
        diagnostic = _selection_marker_diagnostic(
            f"unable to read PDF selection marker source {source}: {exc}",
            code="RK_PDF_SELECTION_MARKER_INPUT",
            source=source_label,
            details={"source": source_label, "error": str(exc)},
        )
        return diagnostic_envelope(
            [diagnostic],
            passed=False,
            selection_marker={"status": "error", "source": source_label, "marker_count": 0, "selection": None},
        )

    marker_lines = [
        (line_number, line.strip())
        for line_number, line in enumerate(text.splitlines(), 1)
        if line.strip() == SELECTION_MARKER_PREFIX or line.strip().startswith(SELECTION_MARKER_PREFIX + " ")
    ]
    marker_summary: dict[str, object] = {
        "source": source_label,
        "marker_count": len(marker_lines),
        "lines": [line_number for line_number, _ in marker_lines],
        "selection": None,
    }
    if not marker_lines:
        if required:
            diagnostic = _selection_marker_diagnostic(
                f"PDF selection marker is missing from {source_label}",
                code="RK_PDF_SELECTION_MARKER_MISSING",
                source=source_label,
                details={"source": source_label, "marker_count": 0},
            )
            return diagnostic_envelope(
                [diagnostic], passed=False,
                selection_marker={**marker_summary, "status": "missing"},
            )
        return diagnostic_envelope([], passed=True, selection_marker={**marker_summary, "status": "not_found"})

    diagnostics: list[dict[str, object]] = []
    if len(marker_lines) != 1:
        diagnostics.append(_selection_marker_diagnostic(
            f"PDF selection marker must occur exactly once in {source_label}; found {len(marker_lines)}",
            code="RK_PDF_SELECTION_MARKER_COUNT",
            source=source_label,
            details={"source": source_label, "marker_count": len(marker_lines), "lines": [line_number for line_number, _ in marker_lines]},
        ))

    line_number, marker_line = marker_lines[0]
    raw_selection, parse_error = _parse_selection_marker_line(marker_line)
    if parse_error:
        diagnostics.append(_selection_marker_diagnostic(
            f"PDF selection marker on line {line_number} is invalid: {parse_error}",
            code="RK_PDF_SELECTION_MARKER_INVALID",
            source=source_label,
            details={"source": source_label, "line": line_number, "marker": marker_line, "error": parse_error},
        ))
        return diagnostic_envelope(
            diagnostics,
            passed=False,
            selection_marker={**marker_summary, "status": "invalid", "line": line_number, "marker": marker_line},
        )

    try:
        selection = {key: _selection_value(key, value) for key, value in raw_selection.items()}
    except ValueError as exc:
        diagnostics.append(_selection_marker_diagnostic(
            f"PDF selection marker on line {line_number} is invalid: {exc}",
            code="RK_PDF_SELECTION_MARKER_INVALID",
            source=source_label,
            details={"source": source_label, "line": line_number, "marker": marker_line, "error": str(exc)},
        ))
        return diagnostic_envelope(
            diagnostics,
            passed=False,
            selection_marker={**marker_summary, "status": "invalid", "line": line_number, "marker": marker_line},
        )

    marker_summary.update({"line": line_number, "marker": marker_line, "selection": selection})
    canonical_requested_theme = _canonical_marker_theme(str(selection["requested_theme"]))
    theme_check = {
        "requested": selection["requested_theme"],
        "canonical_requested": canonical_requested_theme,
        "resolved": selection["theme"],
        "passed": canonical_requested_theme == selection["theme"],
    }
    marker_summary["theme"] = theme_check
    if not theme_check["passed"]:
        diagnostics.append(_selection_marker_diagnostic(
            "PDF selection marker reports default-theme leakage: "
            f"requested theme {selection['requested_theme']!r} resolves as {selection['theme']!r}, "
            f"expected {canonical_requested_theme!r}",
            code="RK_PDF_SELECTION_MARKER_THEME_LEAKAGE",
            source=source_label,
            details={"selection": selection, "theme_check": theme_check},
        ))

    mismatches: dict[str, dict[str, object]] = {}
    for key, expected in (expected_selection or {}).items():
        marker_key = {
            "class_name": "class",
            "pandoc_writer": "writer",
            "canonical_theme": "theme",
            "requested_name": "requested_theme",
        }.get(key, key)
        if marker_key not in selection:
            continue
        expected_value = _normalise_expected_selection(key, expected)
        actual_value = selection[marker_key]
        if expected_value != actual_value:
            mismatches[marker_key] = {"expected": expected_value, "actual": actual_value}
    expected_check = {"provided": bool(expected_selection), "mismatches": mismatches, "passed": not mismatches}
    marker_summary["expected"] = expected_check
    if mismatches:
        diagnostics.append(_selection_marker_diagnostic(
            f"PDF selection marker does not match the expected target: {', '.join(sorted(mismatches))}",
            code="RK_PDF_SELECTION_MARKER_MISMATCH",
            source=source_label,
            details={"mismatches": mismatches, "selection": selection},
        ))

    marker_summary["status"] = "passed" if not diagnostics else "failed"
    return diagnostic_envelope(diagnostics, passed=not diagnostics, selection_marker=marker_summary)


def _pdf_string(value: object) -> str:
    """Return a comparison-friendly value from PyMuPDF's PDF-string form."""
    text = "" if value is None else str(value).strip()
    if len(text) >= 2 and text[0] == "(" and text[-1] == ")":
        return text[1:-1]
    if len(text) >= 2 and text[0] == "<" and text[-1] == ">":
        try:
            return bytes.fromhex(text[1:-1]).decode("utf-8", errors="replace")
        except ValueError:
            return text[1:-1]
    return text.removeprefix("/")


def _catalog_language(doc: Any) -> str | None:
    """Read the catalog's ``/Lang`` key, including compressed catalog objects."""
    catalog = getattr(doc, "pdf_catalog", None)
    xref_get_key = getattr(doc, "xref_get_key", None)
    if catalog is None or xref_get_key is None:
        return None
    catalog_xref = catalog()
    if not catalog_xref:
        return None
    value = xref_get_key(catalog_xref, "Lang")
    if not value or len(value) < 2 or value[0] in {"null", "none"}:
        return None
    return _pdf_string(value[1]) or None


def _decode_actual_text(value: bytes) -> str:
    """Decode the PDF string used as a diagram's ``/ActualText`` value."""
    if value.startswith(b"\xfe\xff"):
        return value[2:].decode("utf-16-be", errors="replace")
    return value.decode("utf-8", errors="replace")


def _read_actual_text_string(stream: bytes, opening: int) -> tuple[bytes | None, int]:
    """Read a PDF literal or hexadecimal string beginning at ``opening``."""
    if stream[opening] == ord("<"):
        closing = stream.find(b">", opening + 1)
        if closing < 0:
            return None, len(stream)
        encoded = re.sub(rb"\s+", b"", stream[opening + 1:closing])
        if len(encoded) % 2:
            encoded += b"0"
        try:
            return bytes.fromhex(encoded.decode("ascii")), closing + 1
        except (UnicodeDecodeError, ValueError):
            return None, closing + 1

    # PDF literal strings may contain balanced parentheses and use the usual
    # backslash, octal, and line-continuation escapes. The slide renderer emits
    # plain literals for ordinary descriptions and hexadecimal strings when a
    # description contains parentheses.
    depth = 1
    value = bytearray()
    cursor = opening + 1
    escapes = {ord("n"): 10, ord("r"): 13, ord("t"): 9, ord("b"): 8, ord("f"): 12}
    while cursor < len(stream):
        character = stream[cursor]
        if character == ord("\\"):
            cursor += 1
            if cursor >= len(stream):
                return None, cursor
            escaped = stream[cursor]
            if escaped in escapes:
                value.append(escapes[escaped])
            elif escaped in b"\\()":
                value.append(escaped)
            elif escaped in b"\r\n":
                if escaped == ord("\r") and cursor + 1 < len(stream) and stream[cursor + 1] == ord("\n"):
                    cursor += 1
            elif ord("0") <= escaped <= ord("7"):
                octal = bytearray([escaped])
                while len(octal) < 3 and cursor + 1 < len(stream) and ord("0") <= stream[cursor + 1] <= ord("7"):
                    cursor += 1
                    octal.append(stream[cursor])
                value.append(int(octal, 8))
            else:
                value.append(escaped)
        elif character == ord("("):
            depth += 1
            value.append(character)
        elif character == ord(")"):
            depth -= 1
            if depth == 0:
                return bytes(value), cursor + 1
            value.append(character)
        else:
            value.append(character)
        cursor += 1
    return None, cursor


def _page_actual_text_values(doc: Any, page: Any) -> list[str]:
    """Read decompressed ``/ActualText`` values from one page's content streams."""
    get_contents = getattr(page, "get_contents", None)
    xref_stream = getattr(doc, "xref_stream", None)
    if get_contents is None or xref_stream is None:
        return []
    values: list[str] = []
    for xref in get_contents() or []:
        stream = xref_stream(xref)
        if isinstance(stream, str):
            stream = stream.encode("latin-1", errors="replace")
        stream_bytes = bytes(stream)
        for marker in re.finditer(rb"/ActualText\s*(?P<opening>[<(])", stream_bytes):
            raw_value, _ = _read_actual_text_string(stream_bytes, marker.end() - 1)
            values.append("" if raw_value is None else _decode_actual_text(raw_value))
    return values


def _page_actual_text_count(doc: Any, page: Any) -> int:
    """Count decompressed ``/ActualText`` spans in one page's content streams."""
    return len(_page_actual_text_values(doc, page))


def _meaningful_links(doc: Any) -> list[dict[str, object]]:
    """Return external links whose annotation rectangle contains visible text."""
    links: list[dict[str, object]] = []
    rect_factory = getattr(fitz, "Rect", None)
    for page_number, page in enumerate(doc, 1):
        for link in page.get_links():
            uri = str(link.get("uri") or "").strip()
            if not uri:
                continue
            text = ""
            link_rect = link.get("from")
            if rect_factory is not None and link_rect is not None:
                try:
                    text = " ".join(str(page.get_text("text", clip=rect_factory(link_rect))).split())
                except (TypeError, ValueError, RuntimeError):
                    text = ""
            links.append({"page": page_number, "uri": uri, "text": text})
    return links


def _append_accessibility_diagnostic(
    diagnostics: list[dict[str, object]],
    message: str,
    *,
    code: str,
    details: dict[str, object],
    source: str,
) -> None:
    diagnostics.append(make_diagnostic(
        "pdf_accessibility", message, code=code, source={"file": source}, details=details,
    ))


def inspect_slide_accessibility(
    path: Path,
    *,
    expected_metadata: Mapping[str, str | None] | None = None,
    expected_language: str = "en-US",
    minimum_bookmarks: int = 1,
    expected_bookmark_titles: Sequence[str] | None = None,
    minimum_meaningful_links: int = 1,
    expected_actual_text: int = 1,
    expected_actual_text_values: Sequence[str] | None = None,
    tagged_pdf_status: str = "unsupported",
    tagged_pdf_reason: str | None = None,
    selection_log: Path | None = None,
    expected_selection: Mapping[str, object] | None = None,
    require_selection_marker: bool = False,
) -> dict:
    """Inspect the shipped, non-tagged slide accessibility contract.

    This intentionally verifies the features ReportKit currently claims for
    slides. Tagged PDF is reported as a declared capability; this inspector
    does not infer tagging support from a successful TeX compilation.
    """
    if fitz is None:
        raise ModuleNotFoundError("PyMuPDF is not installed")
    result = inspect(
        path,
        selection_log=selection_log,
        expected_selection=expected_selection,
        require_selection_marker=require_selection_marker,
    )
    diagnostics = list(result["diagnostics"])
    metadata = dict(result.get("metadata") or {})
    expected = dict(expected_metadata or {})
    metadata_checks: dict[str, dict[str, object]] = {}
    for field in SLIDE_METADATA_FIELDS:
        actual = str(metadata.get(field) or "").strip()
        wanted = expected.get(field)
        passed = bool(actual) and (wanted is None or actual == str(wanted).strip())
        metadata_checks[field] = {"expected": wanted, "actual": actual, "passed": passed}
        if not passed:
            expectation = f" {wanted!r}" if wanted is not None else " a non-empty value"
            _append_accessibility_diagnostic(
                diagnostics,
                f"slide PDF metadata {field!r} must contain{expectation}; got {actual!r}",
                code=f"RK_PDF_ACCESSIBILITY_METADATA_{field.upper()}",
                details={"field": field, "expected": wanted, "actual": actual},
                source=str(path),
            )

    language = _catalog_language(doc := fitz.open(path))
    language_passed = language == expected_language
    if not language_passed:
        _append_accessibility_diagnostic(
            diagnostics,
            f"slide PDF catalog language must be {expected_language!r}; got {language!r}",
            code="RK_PDF_ACCESSIBILITY_CATALOG_LANGUAGE",
            details={"expected": expected_language, "actual": language},
            source=str(path),
        )

    toc = doc.get_toc(simple=True)
    bookmark_titles = [str(item[1]) for item in toc if len(item) > 1]
    expected_titles = list(expected_bookmark_titles) if expected_bookmark_titles is not None else None
    bookmark_titles_passed = expected_titles is None or bookmark_titles == expected_titles
    bookmarks_passed = len(toc) >= minimum_bookmarks and bookmark_titles_passed
    if not bookmarks_passed:
        _append_accessibility_diagnostic(
            diagnostics,
            f"slide PDF outline must contain at least {minimum_bookmarks} entries and the expected titles; got {bookmark_titles!r}",
            code="RK_PDF_ACCESSIBILITY_BOOKMARKS",
            details={"minimum": minimum_bookmarks, "actual": len(toc), "expected_titles": expected_titles, "actual_titles": bookmark_titles},
            source=str(path),
        )

    links = _meaningful_links(doc)
    meaningful_links = [link for link in links if link["text"]]
    links_passed = len(meaningful_links) >= minimum_meaningful_links
    if not links_passed:
        _append_accessibility_diagnostic(
            diagnostics,
            f"slide PDF must contain at least {minimum_meaningful_links} meaningful external link annotations; got {len(meaningful_links)}",
            code="RK_PDF_ACCESSIBILITY_LINKS",
            details={"minimum": minimum_meaningful_links, "external": len(links), "meaningful": len(meaningful_links)},
            source=str(path),
        )

    actual_text_values_by_page = {
        page_number: _page_actual_text_values(doc, page)
        for page_number, page in enumerate(doc, 1)
    }
    actual_text_by_page = {
        page_number: len(page_values)
        for page_number, page_values in actual_text_values_by_page.items()
    }
    actual_text_values = [value for page_values in actual_text_values_by_page.values() for value in page_values]
    actual_text_count = len(actual_text_values)
    expected_values = list(expected_actual_text_values) if expected_actual_text_values is not None else None
    actual_text_values_passed = (
        all(value.strip() for value in actual_text_values)
        and (expected_values is None or actual_text_values == expected_values)
    )
    actual_text_passed = actual_text_count == expected_actual_text and actual_text_values_passed
    if not actual_text_passed:
        _append_accessibility_diagnostic(
            diagnostics,
            f"slide PDF must contain exactly {expected_actual_text} non-empty diagram ActualText alternatives with the expected values; got {actual_text_values!r}",
            code="RK_PDF_ACCESSIBILITY_ACTUAL_TEXT",
            details={"expected": expected_actual_text, "expected_values": expected_values, "actual": actual_text_count, "actual_values": actual_text_values, "pages": actual_text_by_page},
            source=str(path),
        )

    tagged_status_passed = tagged_pdf_status == "unsupported" and bool(tagged_pdf_reason)
    if not tagged_status_passed:
        _append_accessibility_diagnostic(
            diagnostics,
            "slide tagged-PDF capability must remain explicitly declared as unsupported with a reason",
            code="RK_PDF_ACCESSIBILITY_TAGGED_STATUS",
            details={"status": tagged_pdf_status, "reason": tagged_pdf_reason},
            source=str(path),
        )

    doc.close()
    result.update({
        "diagnostics": diagnostics,
        "issues": diagnostics,
        "errors": [item["message"] for item in diagnostics if item.get("severity") == "error"],
        "passed": result["passed"] and not any(item.get("severity") == "error" for item in diagnostics),
        "slide_accessibility": {
            "metadata": metadata_checks,
            "catalog_language": {"expected": expected_language, "actual": language, "passed": language_passed},
            "bookmarks": {"minimum": minimum_bookmarks, "count": len(toc), "items": toc, "expected_titles": expected_titles, "titles": bookmark_titles, "passed": bookmarks_passed},
            "links": {"minimum_meaningful": minimum_meaningful_links, "external": links, "meaningful": meaningful_links, "passed": links_passed},
            "diagram_actual_text": {"expected": expected_actual_text, "expected_values": expected_values, "count": actual_text_count, "values": actual_text_values, "pages": actual_text_by_page, "passed": actual_text_passed},
            "tagged_pdf": {"status": tagged_pdf_status, "reason": tagged_pdf_reason, "verified": tagged_status_passed},
        },
    })
    return result


def _selection_log_for_pdf(path: Path) -> Path | None:
    """Find the build log conventionally paired with a compiled PDF."""
    candidates = (path.with_suffix(".log"), path.with_name("publication.log"))
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return None


def inspect(
    path: Path,
    *,
    selection_log: Path | None = None,
    expected_selection: Mapping[str, object] | None = None,
    require_selection_marker: bool = False,
) -> dict:
    """Inspect a PDF and consume a nearby resolved-target marker when present.

    Existing standalone PDF inspection remains valid without a build log. A
    marker found in the adjacent log is always checked; callers can require a
    marker explicitly with ``require_selection_marker`` or ``selection_log``.
    """
    if fitz is None:
        raise ModuleNotFoundError("PyMuPDF is not installed")
    doc = fitz.open(path)
    outside: list[dict[str, object]] = []
    near_margin: list[dict[str, object]] = []
    blank_pages: list[int] = []
    dimensions: list[dict[str, object]] = []
    fonts: dict[str, dict[str, object]] = {}
    margin = 4.0
    for page_number, page in enumerate(doc, 1):
        media = page.rect
        dimensions.append({"page": page_number, "width": round(media.width, 3), "height": round(media.height, 3)})
        words = page.get_text("words")
        images = page.get_images(full=True)
        drawings = page.get_drawings()
        if not words and not images and not drawings:
            blank_pages.append(page_number)
        for font in page.get_fonts(full=True):
            font_key = str(font[3] or font[4] or font[0])
            fonts.setdefault(font_key, {"name": font_key, "pages": []})["pages"].append(page_number)
        for word in words:
            x0, y0, x1, y1, text = word[:5]
            if x0 < media.x0 - 0.5 or y0 < media.y0 - 0.5 or x1 > media.x1 + 0.5 or y1 > media.y1 + 0.5:
                outside.append({"page": page_number, "text": text, "bbox": [x0, y0, x1, y1], "media_box": [media.x0, media.y0, media.x1, media.y1]})
            elif x0 < media.x0 + margin or y0 < media.y0 + margin or x1 > media.x1 - margin or y1 > media.y1 - margin:
                near_margin.append({"page": page_number, "text": text, "bbox": [x0, y0, x1, y1], "margin_pt": margin})
    toc = doc.get_toc(simple=True)
    diagnostics = [make_diagnostic(
        "pdf_geometry", f"content {item['text']!r} lies outside the page media box",
        code="RK_PDF_OUTSIDE_MEDIA_BOX", source={"file": str(path)},
        details={"page": item["page"], "bbox": item["bbox"], "media_box": item["media_box"]},
    ) for item in outside]
    diagnostics.extend(make_diagnostic(
        "blank_page", f"page {page} is blank", code="RK_PDF_BLANK_PAGE",
        source={"file": str(path)}, details={"page": page},
    ) for page in blank_pages)
    marker_required = require_selection_marker or expected_selection is not None
    marker_log = selection_log or _selection_log_for_pdf(path)
    if marker_log is None and marker_required:
        marker_log = path.with_name("publication.log")
    if marker_log is None:
        marker_result = diagnostic_envelope(
            [],
            passed=True,
            selection_marker={
                "status": "not_checked",
                "source": None,
                "marker_count": 0,
                "selection": None,
            },
        )
    else:
        marker_result = inspect_selection_marker(
            marker_log,
            expected_selection=expected_selection,
            required=selection_log is not None or marker_required,
        )
        diagnostics.extend(marker_result["diagnostics"])
    return diagnostic_envelope(
        diagnostics,
        passed=not outside and not blank_pages and len(doc) > 0 and marker_result["passed"],
        page_count=len(doc),
        outside_media_box=outside,
        near_margin_content=near_margin,
        blank_pages=blank_pages,
        page_dimensions=dimensions,
        bookmarks={"count": len(toc), "items": toc},
        fonts=sorted(fonts.values(), key=lambda item: str(item["name"])),
        metadata=doc.metadata,
        link_count=sum(len(page.get_links()) for page in doc),
        selection_marker=marker_result["selection_marker"],
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pdf", type=Path)
    parser.add_argument("--json", dest="json_path", type=Path)
    parser.add_argument("--selection-log", type=Path, help="read the resolved-target marker from this build log")
    parser.add_argument("--require-selection-marker", action="store_true", help="fail if the paired build log has no resolved-target marker")
    parser.add_argument("--slide-accessibility", action="store_true", help="also enforce the declared slide accessibility contract")
    parser.add_argument("--expected-title")
    parser.add_argument("--expected-author")
    parser.add_argument("--expected-subject")
    parser.add_argument("--expected-keywords")
    parser.add_argument("--expected-language", default="en-US")
    parser.add_argument("--minimum-bookmarks", type=int, default=1)
    parser.add_argument("--expected-bookmark-title", action="append")
    parser.add_argument("--minimum-meaningful-links", type=int, default=1)
    parser.add_argument("--expected-actual-text", type=int, default=1)
    parser.add_argument("--expected-actual-text-value", action="append")
    parser.add_argument("--tagged-pdf-status", choices=("supported", "unsupported"), default="unsupported")
    parser.add_argument("--tagged-pdf-reason", default="")
    args = parser.parse_args()
    try:
        if args.slide_accessibility:
            result = inspect_slide_accessibility(
                args.pdf,
                expected_metadata={
                    "title": args.expected_title,
                    "author": args.expected_author,
                    "subject": args.expected_subject,
                    "keywords": args.expected_keywords,
                },
                expected_language=args.expected_language,
                minimum_bookmarks=args.minimum_bookmarks,
                expected_bookmark_titles=args.expected_bookmark_title,
                minimum_meaningful_links=args.minimum_meaningful_links,
                expected_actual_text=args.expected_actual_text,
                expected_actual_text_values=args.expected_actual_text_value,
                tagged_pdf_status=args.tagged_pdf_status,
                tagged_pdf_reason=args.tagged_pdf_reason or None,
                selection_log=args.selection_log,
                require_selection_marker=args.require_selection_marker,
            )
        else:
            result = inspect(
                args.pdf,
                selection_log=args.selection_log,
                require_selection_marker=args.require_selection_marker,
            )
    except ModuleNotFoundError as exc:
        result = diagnostic_envelope([
            make_diagnostic("environment_error", f"PDF inspection requires PyMuPDF: {exc}", code="RK_PYMUPDF_MISSING")
        ], passed=False)
        if args.json_path:
            args.json_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(f"FAIL: PDF inspection requires PyMuPDF: {exc}", file=sys.stderr)
        return 5
    except Exception as exc:
        result = diagnostic_envelope([
            make_diagnostic("pdf_geometry", f"PDF inspection failed: {exc}", code="RK_PDF_INSPECTION")
        ], passed=False)
        if args.json_path:
            args.json_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(f"FAIL: PDF inspection failed: {exc}", file=sys.stderr)
        return 3
    if args.json_path:
        args.json_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if not result["passed"]:
        if args.slide_accessibility:
            failures = [item["message"] for item in result["diagnostics"] if item.get("severity") == "error"]
            print(f"FAIL: slide accessibility inspection: {'; '.join(failures)}", file=sys.stderr)
        elif result.get("selection_marker", {}).get("status") in {"failed", "missing", "invalid", "error"}:
            failures = [item["message"] for item in result["diagnostics"] if item.get("severity") == "error"]
            print(f"FAIL: PDF selection inspection: {'; '.join(failures)}", file=sys.stderr)
        else:
            print(f"FAIL: {len(result['outside_media_box'])} glyph boxes fall outside the media box; {len(result['blank_pages'])} blank pages", file=sys.stderr)
        return 3
    profile = " + slide accessibility" if args.slide_accessibility else ""
    print(f"PASS: PDF inspection{profile} ({result['page_count']} pages, {result['link_count']} links)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
