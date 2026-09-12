#!/usr/bin/env python3
"""Build a callout/diagram/chart document using only emitted context data."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]

# Direct execution places only scripts/ on sys.path; add the clone root so the
# importable publication_pipeline package can load the shared bootstrap.
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from publication_pipeline.scripts._bootstrap import ensure_reportkit_importable

ensure_reportkit_importable()

from publication_pipeline.scripts.publication_build import run_limited
from reportkit.diagnostics import diagnostic_envelope, inspect_log, make_diagnostic


def acceptance_source(context: dict, chart_file: str = "contract-chart.pdf") -> str:
    primitives = context["capabilities"]["primitives"]
    body = "\n\n".join([
        *(record["example"] for record in primitives["callout"].values()),
        *(record["example"] for record in primitives["figure"].values()),
        f"\\begin{{figure}}[htbp]\n\\centering\n\\includegraphics[width=.72\\linewidth]{{{chart_file}}}\n"
        "\\caption{Contract-generated chart.}\\source{Contract acceptance data.}\n\\end{figure}",
    ])
    return context["capabilities"]["authoring"]["document_template"].replace("{{body}}", body)


def run_acceptance(output: Path) -> tuple[int, dict]:
    context_proc = subprocess.run(
        [str(ROOT / "reportkit"), "context", "--publication-type", "technical-report", "--theme", "default",
         "--kind", "callout", "--kind", "figure", "--kind", "chart", "--json"],
        capture_output=True, text=True,
    )
    if context_proc.returncode:
        return context_proc.returncode, json.loads(context_proc.stdout)
    context = json.loads(context_proc.stdout)
    output.mkdir(parents=True, exist_ok=True)

    try:
        for name, record in context["capabilities"]["primitives"]["chart"].items():
            namespace: dict[str, object] = {}
            exec(context["capabilities"]["authoring"]["chart_prelude"], namespace)
            exec(record["example"], namespace)
            if name == "bar_chart":
                namespace["output_path"] = output / "contract-chart"
                exec(context["capabilities"]["authoring"]["chart_export"], namespace)
            namespace["rkv"].plt.close(namespace.get("fig"))
    except (ImportError, ModuleNotFoundError) as exc:
        diagnostic = make_diagnostic("environment_error", f"chart acceptance dependency unavailable: {exc}", code="RK_ACCEPTANCE_CHART_ENVIRONMENT")
        return 5, diagnostic_envelope([diagnostic], passed=False)
    except Exception as exc:
        diagnostic = make_diagnostic("contract_drift", f"chart contract example failed: {exc}", code="RK_ACCEPTANCE_CHART_EXAMPLE")
        return 3, diagnostic_envelope([diagnostic], passed=False)

    tex = output / "report.tex"
    tex.write_text(acceptance_source(context), encoding="utf-8")
    engine = shutil.which("pdflatex")
    if not engine:
        diagnostic = make_diagnostic("environment_error", "pdflatex is required for contract acceptance", code="RK_ACCEPTANCE_TEX_MISSING")
        return 5, diagnostic_envelope([diagnostic], passed=False, source=str(tex))
    env = {
        **os.environ,
        "TEXINPUTS": f"{output}:{ROOT / 'latex_templates'}//:",
        "openin_any": "p",
        "openout_any": "p",
        "SOURCE_DATE_EPOCH": "1",
        "FORCE_SOURCE_DATE": "1",
        "TZ": "UTC",
    }
    logs: list[str] = []
    try:
        for _ in range(2):
            result = run_limited(
                [engine, "-file-line-error", "-interaction=nonstopmode", "-halt-on-error", tex.name],
                cwd=output, timeout=120, memory_limit_mb=2048, capture_output=True, text=True, env=env,
            )
            logs.append((result.stdout or "") + "\n" + (result.stderr or ""))
            if result.returncode:
                memory_failure = result.returncode < 0 or result.returncode in {134, 137} or "memory" in logs[-1].lower()
                diagnostic = make_diagnostic(
                    "compile_memory" if memory_failure else "compile_failure",
                    f"contract document failed with status {result.returncode}",
                    code="RK_ACCEPTANCE_MEMORY" if memory_failure else "RK_ACCEPTANCE_TEX_FAILURE",
                )
                return 4, diagnostic_envelope([diagnostic], passed=False, source=str(tex), log=logs[-1][-4000:])
    except subprocess.TimeoutExpired:
        diagnostic = make_diagnostic("compile_timeout", "contract acceptance exceeded 120 seconds", code="RK_ACCEPTANCE_TIMEOUT")
        return 4, diagnostic_envelope([diagnostic], passed=False, source=str(tex))
    except (OSError, RuntimeError) as exc:
        diagnostic = make_diagnostic(
            "environment_error", f"contract acceptance cannot enforce its build environment: {exc}",
            code="RK_ACCEPTANCE_ENVIRONMENT",
        )
        return 5, diagnostic_envelope([diagnostic], passed=False, source=str(tex))
    diagnostics = inspect_log("\n".join(logs))["diagnostics"]
    if any(item.get("blocking") for item in diagnostics):
        return 3, diagnostic_envelope(diagnostics, passed=False, source=str(tex))
    pdf = output / "report.pdf"
    if not pdf.is_file():
        diagnostic = make_diagnostic("compile_failure", "contract acceptance produced no PDF", code="RK_ACCEPTANCE_PDF_MISSING")
        return 4, diagnostic_envelope([diagnostic], passed=False, source=str(tex))
    return 0, diagnostic_envelope(diagnostics, passed=True, source=str(tex), pdf=str(pdf))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    if args.output_dir:
        code, payload = run_acceptance(Path(args.output_dir).resolve())
    else:
        with tempfile.TemporaryDirectory(prefix="reportkit-contract-") as temp_dir:
            code, payload = run_acceptance(Path(temp_dir))
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    elif code == 0:
        print("PASS: context-only callout/diagram/chart acceptance")
    else:
        for diagnostic in payload["diagnostics"]:
            print(f"FAIL [{diagnostic['code']}]: {diagnostic['message']}", file=sys.stderr)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
