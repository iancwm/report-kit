#!/usr/bin/env python3
"""Cross-host acceptance gate for the ReportKit container workflow.

Run the same command on Windows (Docker Desktop, Linux containers) and on
Linux, then compare the two summaries:

    python3 scripts/cross_host_gate.py run --image ghcr.io/iancwm/report-kit@sha256:<d> --work-dir <dir> --summary linux.json
    py -3 scripts\\cross_host_gate.py run --image ... --summary windows.json
    python3 scripts/cross_host_gate.py compare linux.json windows.json

Fixture bytes come from Git blobs, never from the checkout, so a CRLF
checkout still stages identical bytes.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tarfile

sys.path.insert(0, str(Path(__file__).resolve().parent))

import reportkit_container as launcher  # noqa: E402
from rk_container import results, staging  # noqa: E402

REPO = Path(__file__).resolve().parents[1]
SCHEMA = "reportkit-cross-host-gate/1"
WORK_NAME = "Publication Tëst ü"
FIXTURES = {
    "markdown": {"path": "publication_pipeline/example_publication", "kind": "pipeline", "entry": None},
    "editorial": {"path": "latex_templates/examples/editorial-feature", "kind": "direct-tex", "entry": "report.tex"},
}
REQUIRED_CHECKS = (
    "doctor", "build-markdown", "build-editorial", "crlf-bytes-preserved", "unicode-collision-rejected",
    "path-safety-symlink", "path-safety-dotdot-result", "failure-atomicity",
)
COMPARED_FIXTURE_KEYS = ("input_manifest_sha256", "selection", "page_count", "inspect_passed")


def materialize(commit: str, repo_path: str, destination: Path) -> None:
    listing = subprocess.run(["git", "ls-tree", "-r", "-z", "--full-tree", commit, "--", repo_path],
                             cwd=REPO, capture_output=True, check=True).stdout
    for record in filter(None, listing.split(b"\0")):
        meta, name = record.split(b"\t", 1)
        blob = meta.split()[2].decode()
        relative = Path(name.decode("utf-8")).relative_to(repo_path)
        if relative.parts[0] in ("build",):
            continue
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(subprocess.run(["git", "cat-file", "blob", blob], cwd=REPO, capture_output=True, check=True).stdout)


def _build(image: str, allow_unpinned: bool, source: Path, output: Path, kind: str, entry: str | None) -> tuple[int, dict]:
    argv = ["build", "--image", image, "--source-root", str(source), "--output-root", str(output), "--kind", kind]
    argv += ["--entry", entry] if entry else []
    argv += ["--allow-unpinned-image"] if allow_unpinned else []
    return launcher.run_build(launcher.build_parser().parse_args(argv))


def _tree_digest(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        digest.update(path.relative_to(root).as_posix().encode() + b"\0" + path.read_bytes())
    return digest.hexdigest()


def check_result_dotdot(work: Path) -> tuple[str, str]:
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w") as archive:
        info = tarfile.TarInfo("result/../escaped.txt")
        info.size = 1
        archive.addfile(info, io.BytesIO(b"x"))
    buffer.seek(0)
    destination = work / "dotdot" / "in"
    destination.mkdir(parents=True, exist_ok=True)
    try:
        results.extract_result(buffer, destination)
    except results.ResultError as exc:
        escaped = (destination.parent / "escaped.txt").exists()
        return ("failed", "entry escaped") if escaped else ("passed", exc.code)
    return "failed", "a ../ result entry was accepted"


def _expect_rejection(source: Path, code: str) -> tuple[str, str]:
    try:
        staging.collect(source)
    except staging.StagingError as exc:
        codes = {p.code for p in exc.problems}
        return ("passed", code) if code in codes else ("failed", f"rejected with {sorted(codes)}")
    return "failed", "accepted"


def run(args: argparse.Namespace) -> dict:
    work = Path(args.work_dir) / WORK_NAME
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)
    checks: list[dict] = []
    fixtures: dict[str, dict] = {}

    def record(name: str, status: str, detail: str = "") -> None:
        checks.append({"name": name, "status": status, "detail": detail})

    if args.fresh:
        subprocess.run(["docker", "image", "rm", "--force", args.image], capture_output=True)
    record("host-has-no-lualatex", "passed" if shutil.which("lualatex") is None else "failed", shutil.which("lualatex") or "")
    doctor = subprocess.run(["docker", "run", "--rm", "--network", "none", "--platform", "linux/amd64", args.image,
                             "doctor", "--require", "pinned-toolchain", "--json"], capture_output=True)
    record("doctor", "passed" if doctor.returncode == 0 else "failed", doctor.stdout.decode("utf-8", "replace")[-2000:])

    for name, fixture in FIXTURES.items():
        source = work / f"{name} source"
        materialize(args.commit, fixture["path"], source)
        code, outcome = _build(args.image, args.allow_unpinned_image, source, work / f"{name} output", fixture["kind"], fixture["entry"])
        record(f"build-{name}", "passed" if code == 0 else "failed", outcome.get("message", ""))
        if code == 0:
            fixtures[name] = launcher.summarize(work / f"{name} output")

    crlf = work / "markdown-crlf source"
    materialize(args.commit, FIXTURES["markdown"]["path"], crlf)
    for md in crlf.rglob("*.md"):
        md.write_bytes(md.read_bytes().replace(b"\r\n", b"\n").replace(b"\n", b"\r\n"))
    expected = staging.collect(crlf).manifest_sha256()
    code, outcome = _build(args.image, args.allow_unpinned_image, crlf, work / "markdown-crlf output", "pipeline", None)
    staged_hash = launcher.summarize(work / "markdown-crlf output")["input_manifest_sha256"] if code == 0 else None
    record("crlf-bytes-preserved", "passed" if code == 0 and staged_hash == expected else "failed", f"exit {code}; {outcome.get('message', '')}")
    if code == 0:
        fixtures["markdown-crlf"] = launcher.summarize(work / "markdown-crlf output")

    unicode_dir = work / "unicode-collision"
    unicode_dir.mkdir()
    (unicode_dir / "caf\u00e9.md").write_bytes(b"1")
    (unicode_dir / "cafe\u0301.md").write_bytes(b"2")
    if len(list(unicode_dir.iterdir())) == 2:
        record("unicode-collision-rejected", *_expect_rejection(unicode_dir, "RK_STAGE_PATH_COLLISION"))
    else:
        record("unicode-collision-rejected", "failed", "filesystem normalized the names; run the gate on a non-normalizing filesystem")

    case_dir = work / "case-collision"
    case_dir.mkdir()
    (case_dir / "Chapter.md").write_bytes(b"1")
    (case_dir / "chapter.md").write_bytes(b"2")
    if len(list(case_dir.iterdir())) == 2:
        record("case-collision-rejected", *_expect_rejection(case_dir, "RK_STAGE_PATH_COLLISION"))
    else:
        record("case-collision-rejected", "not-applicable", "case-insensitive filesystem cannot hold both names")

    link_dir = work / "symlink"
    link_dir.mkdir()
    (work / "outside.txt").write_bytes(b"outside")
    try:
        (link_dir / "link.md").symlink_to(work / "outside.txt")
        record("path-safety-symlink", *_expect_rejection(link_dir, "RK_STAGE_SYMLINK"))
    except OSError as exc:
        record("path-safety-symlink", "failed", f"cannot create a symlink ({exc}); enable Windows Developer Mode and rerun")

    if os.name == "nt":
        import _winapi
        junction_dir = work / "junction"
        junction_dir.mkdir()
        (work / "outside-dir").mkdir()
        _winapi.CreateJunction(str(work / "outside-dir"), str(junction_dir / "j"))
        record("path-safety-junction", *_expect_rejection(junction_dir, "RK_STAGE_REPARSE_POINT"))

    record("path-safety-dotdot-result", *check_result_dotdot(work))

    good_output = work / "editorial output"
    if good_output.is_dir():
        before = _tree_digest(good_output)
        broken = work / "editorial-broken source"
        materialize(args.commit, FIXTURES["editorial"]["path"], broken)
        tex = broken / "report.tex"
        tex.write_bytes(tex.read_bytes().replace(b"\\end{document}", b"\\ReportKitGateUndefinedMacro\n\\end{document}"))
        code, _ = _build(args.image, args.allow_unpinned_image, broken, good_output, "direct-tex", "report.tex")
        failure = good_output.with_name(good_output.name + ".failed")
        ok = code != 0 and _tree_digest(good_output) == before and (failure / "launcher-failure.json").is_file() and any((failure / "logs").glob("*.log"))
        record("failure-atomicity", "passed" if ok else "failed", f"exit {code}")
    else:
        record("failure-atomicity", "failed", "editorial fixture did not build")

    digests = {s.get("image_digest") for s in fixtures.values()}
    required_ok = all(any(c["name"] == n and c["status"] == "passed" for c in checks) for n in REQUIRED_CHECKS)
    return {
        "schema": SCHEMA,
        "host": {"system": platform.system(), "release": platform.release(), "python": platform.python_version(), "machine": platform.machine()},
        "image": {"reference": args.image, "digest": digests.pop() if len(digests) == 1 else None},
        "fixtures": fixtures, "checks": checks,
        "passed": required_ok and not any(c["status"] == "failed" for c in checks),
    }


def compare_summaries(a: dict, b: dict) -> list[str]:
    diffs = []
    if a["image"].get("digest") != b["image"].get("digest") or not a["image"].get("digest"):
        diffs.append(f"image digest differs or is missing: {a['image'].get('digest')} vs {b['image'].get('digest')}")
    for name in sorted(set(a["fixtures"]) | set(b["fixtures"])):
        left, right = a["fixtures"].get(name), b["fixtures"].get(name)
        if left is None or right is None:
            diffs.append(f"fixture {name} missing on one host")
            continue
        for key in COMPARED_FIXTURE_KEYS:
            if left.get(key) != right.get(key):
                diffs.append(f"fixture {name} {key}: {left.get(key)!r} vs {right.get(key)!r}")
    for label, summary in (("first", a), ("second", b)):
        statuses = {c["name"]: c["status"] for c in summary["checks"]}
        for name in REQUIRED_CHECKS:
            if statuses.get(name) != "passed":
                diffs.append(f"{label} summary: required check {name} is {statuses.get(name, 'missing')}")
    return diffs


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    run_parser = sub.add_parser("run")
    run_parser.add_argument("--image", required=True)
    run_parser.add_argument("--allow-unpinned-image", action="store_true")
    run_parser.add_argument("--work-dir", required=True)
    run_parser.add_argument("--summary", required=True)
    run_parser.add_argument("--fresh", action="store_true", help="remove the local image first so the gate pulls it")
    run_parser.add_argument("--commit", default="HEAD")
    compare_parser = sub.add_parser("compare")
    compare_parser.add_argument("first")
    compare_parser.add_argument("second")
    args = parser.parse_args(argv)
    if args.command == "compare":
        diffs = compare_summaries(*(json.loads(Path(p).read_text(encoding="utf-8")) for p in (args.first, args.second)))
        print("\n".join(diffs) or "equivalent")
        return 3 if diffs else 0
    result = run(args)
    Path(args.summary).write_text(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    for check in result["checks"]:
        print(f"{check['status'].upper():15} {check['name']}")
    return 0 if result["passed"] else 3


if __name__ == "__main__":
    raise SystemExit(main())
