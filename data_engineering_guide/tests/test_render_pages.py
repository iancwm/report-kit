from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

try:
    import pymupdf as fitz
except ImportError:  # pragma: no cover - the locked guide venv supplies this in CI
    try:
        import fitz  # type: ignore
    except ImportError:
        fitz = None  # type: ignore


@unittest.skipUnless(fitz is not None, "PyMuPDF is required for renderer integration tests")
class RenderPagesTests(unittest.TestCase):
    def test_rerender_removes_stale_page_images(self) -> None:
        renderer = Path(__file__).resolve().parents[1] / "scripts" / "render_pdf_pages.py"
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            pdf = root / "fixture.pdf"
            pages = root / "pages"
            pages.mkdir()
            (pages / "page-99.png").write_bytes(b"stale")
            manifest_path = root / "manifest.json"

            document = fitz.open()
            document.new_page(width=100, height=100)
            document.save(pdf)
            document.close()

            result = subprocess.run(
                [sys.executable, str(renderer), str(pdf), str(pages), "--manifest", str(manifest_path)],
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertFalse((pages / "page-99.png").exists())
            self.assertTrue((pages / "page-01.png").is_file())
            self.assertTrue((pages / "index.html").is_file())
            self.assertEqual(json.loads(manifest_path.read_text(encoding="utf-8"))["page_count"], 1)


if __name__ == "__main__":
    unittest.main()
