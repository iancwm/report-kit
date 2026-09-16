#!/usr/bin/env python3
"""Run deterministic PDF checks using PyMuPDF only."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
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


def _page_actual_text_count(doc: Any, page: Any) -> int:
    """Count decompressed ``/ActualText`` spans in one page's content streams."""
    get_contents = getattr(page, "get_contents", None)
    xref_stream = getattr(doc, "xref_stream", None)
    if get_contents is None or xref_stream is None:
        return 0
    count = 0
    for xref in get_contents() or []:
        stream = xref_stream(xref)
        if isinstance(stream, str):
            stream = stream.encode("latin-1", errors="replace")
        count += bytes(stream).count(b"/ActualText")
    return count


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
    tagged_pdf_status: str = "unsupported",
    tagged_pdf_reason: str | None = None,
) -> dict:
    """Inspect the shipped, non-tagged slide accessibility contract.

    This intentionally verifies the features ReportKit currently claims for
    slides. Tagged PDF is reported as a declared capability; this inspector
    does not infer tagging support from a successful TeX compilation.
    """
    if fitz is None:
        raise ModuleNotFoundError("PyMuPDF is not installed")
    result = inspect(path)
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

    actual_text_by_page = {
        page_number: _page_actual_text_count(doc, page)
        for page_number, page in enumerate(doc, 1)
    }
    actual_text_count = sum(actual_text_by_page.values())
    actual_text_passed = actual_text_count == expected_actual_text
    if not actual_text_passed:
        _append_accessibility_diagnostic(
            diagnostics,
            f"slide PDF must contain exactly {expected_actual_text} diagram ActualText alternatives; got {actual_text_count}",
            code="RK_PDF_ACCESSIBILITY_ACTUAL_TEXT",
            details={"expected": expected_actual_text, "actual": actual_text_count, "pages": actual_text_by_page},
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
            "diagram_actual_text": {"expected": expected_actual_text, "count": actual_text_count, "pages": actual_text_by_page, "passed": actual_text_passed},
            "tagged_pdf": {"status": tagged_pdf_status, "reason": tagged_pdf_reason, "verified": tagged_status_passed},
        },
    })
    return result


def inspect(path: Path) -> dict:
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
    return diagnostic_envelope(
        diagnostics,
        passed=not outside and not blank_pages and len(doc) > 0,
        page_count=len(doc),
        outside_media_box=outside,
        near_margin_content=near_margin,
        blank_pages=blank_pages,
        page_dimensions=dimensions,
        bookmarks={"count": len(toc), "items": toc},
        fonts=sorted(fonts.values(), key=lambda item: str(item["name"])),
        metadata=doc.metadata,
        link_count=sum(len(page.get_links()) for page in doc),
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pdf", type=Path)
    parser.add_argument("--json", dest="json_path", type=Path)
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
                tagged_pdf_status=args.tagged_pdf_status,
                tagged_pdf_reason=args.tagged_pdf_reason or None,
            )
        else:
            result = inspect(args.pdf)
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
        else:
            print(f"FAIL: {len(result['outside_media_box'])} glyph boxes fall outside the media box; {len(result['blank_pages'])} blank pages", file=sys.stderr)
        return 3
    profile = " + slide accessibility" if args.slide_accessibility else ""
    print(f"PASS: PDF inspection{profile} ({result['page_count']} pages, {result['link_count']} links)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
