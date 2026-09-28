#!/usr/bin/env python3
"""Build a ReportKit publication inside the pinned toolchain container.

Host requirements: Python 3.11+ and the Docker CLI talking to a Linux-container
daemon. Arguments are identical on every host:

    python3 scripts/reportkit_container.py build --image ghcr.io/iancwm/report-kit@sha256:<digest> \\
        --kind pipeline --source-root <publication> --output-root <publication>/output
    py -3 scripts\\reportkit_container.py build ...   (Windows)

The publication is streamed into the container (never bind-mounted), built
without network, and the verified result replaces the output directory only
on success.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))

from rk_container import results, staging  # noqa: E402
from rk_container.docker import Docker, DockerError, RunLimits  # noqa: E402

EXIT_OK, EXIT_CONFIG, EXIT_VALIDATION, EXIT_COMPILE, EXIT_ENVIRONMENT, EXIT_INTERNAL = 0, 2, 3, 4, 5, 70
ENTRYPOINT = ["/opt/reportkit/.venv/bin/python", "/opt/reportkit/toolchain/container_build.py"]
MIB = 1024 * 1024


class LauncherError(Exception):
    def __init__(self, code: str, message: str, exit_code: int) -> None:
        super().__init__(message)
        self.code, self.message, self.exit_code = code, message, exit_code


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="reportkit_container.py", description="Build a ReportKit publication inside the pinned toolchain image")
    sub = parser.add_subparsers(dest="command", required=True)
    build = sub.add_parser("build", help="stage, build, verify and install one publication")
    build.add_argument("--image", required=True, help="toolchain image, normally ghcr.io/iancwm/report-kit@sha256:<digest>")
    build.add_argument("--source-root", required=True)
    build.add_argument("--output-root", required=True)
    build.add_argument("--kind", required=True, choices=("pipeline", "direct-tex"), help="Markdown pipeline from publication.yaml, or one hand-authored .tex entry")
    build.add_argument("--entry", help="direct-tex only: entry .tex path relative to the source root")
    build.add_argument("--engine", choices=("lualatex", "pdflatex"), default="lualatex", help="direct-tex only")
    build.add_argument("--profile", help="pipeline only: publication.yaml profile, for example release")
    build.add_argument("--pages", help="page selection to render, e.g. '1,3-5' (default: every page)")
    build.add_argument("--dpi", type=int, default=110)
    build.add_argument("--allow-unpinned-image", action="store_true", help="development only: accept an image without @sha256 digest")
    build.add_argument("--no-pull", action="store_true")
    build.add_argument("--timeout-seconds", type=int, default=RunLimits.timeout_seconds)
    build.add_argument("--cpus", default=RunLimits.cpus)
    build.add_argument("--memory", default=RunLimits.memory)
    build.add_argument("--max-input-mb", type=int, default=staging.Limits.max_total_bytes // MIB)
    build.add_argument("--max-file-mb", type=int, default=staging.Limits.max_file_bytes // MIB)
    build.add_argument("--max-files", type=int, default=staging.Limits.max_files)
    build.add_argument("--json", action="store_true")
    summary = sub.add_parser("summarize", help="print the cross-host comparison summary of an output directory")
    summary.add_argument("output_root")
    return parser


def _docker() -> Docker:
    return Docker()


def container_command(args: argparse.Namespace) -> list[str]:
    command = [*ENTRYPOINT, "--kind", args.kind, "--dpi", str(args.dpi)]
    if args.kind == "direct-tex":
        command += ["--entry", args.entry, "--engine", args.engine]
    if args.profile:
        command += ["--profile", args.profile]
    if args.pages:
        command += ["--pages", args.pages]
    return command


def _check_arguments(args: argparse.Namespace) -> None:
    if args.kind == "direct-tex" and not args.entry:
        raise LauncherError("RK_ARGS_ENTRY_REQUIRED", "--kind direct-tex needs --entry <file.tex>", EXIT_CONFIG)
    if args.kind == "pipeline" and args.entry:
        raise LauncherError("RK_ARGS_ENTRY_UNEXPECTED", "--entry applies only to --kind direct-tex", EXIT_CONFIG)
    if args.kind == "direct-tex" and args.profile:
        raise LauncherError("RK_ARGS_PROFILE_UNEXPECTED", "--profile applies only to --kind pipeline", EXIT_CONFIG)
    if "@sha256:" not in args.image and not args.allow_unpinned_image:
        raise LauncherError("RK_IMAGE_NOT_PINNED", "pass the image by digest (ghcr.io/iancwm/report-kit@sha256:...), "
                            "or --allow-unpinned-image for a development build", EXIT_CONFIG)
    if not Path(args.source_root).is_dir():
        raise LauncherError("RK_SOURCE_MISSING", f"source root {args.source_root} is not a directory", EXIT_CONFIG)


def run_build(args: argparse.Namespace, docker: Docker | None = None) -> tuple[int, dict]:
    record: dict = {"passed": False, "image": args.image}
    try:
        _check_arguments(args)
        output, failure = results.validate_output_root(Path(args.output_root), Path(args.source_root))
        record.update(output_root=str(output), failure_root=str(failure))
        docker = docker or _docker()
        daemon = docker.daemon()
        if daemon.emulated:
            print(f"WARN: Docker daemon is {daemon.architecture}; running linux/amd64 under emulation (not a supported acceptance platform)", file=sys.stderr)
        image = docker.image(args.image, pull=not args.no_pull)
        record.update(image_digest=image.digest, release_eligible=image.pinned and image.digest is not None)
        limits = staging.Limits(args.max_input_mb * MIB, args.max_file_mb * MIB, args.max_files)
        staged = staging.collect(Path(args.source_root), limits)
        if args.kind == "direct-tex" and args.entry.replace("\\", "/") not in {f.relative for f in staged.files}:
            raise LauncherError("RK_ARGS_ENTRY_MISSING", f"entry {args.entry} is not a staged file under the source root", EXIT_CONFIG)
        if args.entry:
            args.entry = args.entry.replace("\\", "/")
        record["input_manifest_sha256"] = staged.manifest_sha256()
    except LauncherError as exc:
        return exc.exit_code, {**record, "code": exc.code, "message": exc.message}
    except results.ResultError as exc:
        return EXIT_CONFIG, {**record, "code": exc.code, "message": exc.message}
    except DockerError as exc:
        return EXIT_ENVIRONMENT, {**record, "code": exc.code, "message": exc.message}
    except staging.StagingError as exc:
        return EXIT_CONFIG, {**record, "code": exc.problems[0].code, "message": str(exc), "problems": [p.as_dict() for p in exc.problems]}

    env = {"REPORTKIT_IMAGE_REF": args.image, "REPORTKIT_IMAGE_DIGEST": image.digest or "",
           "REPORTKIT_IMAGE_ID": image.image_id, "REPORTKIT_RELEASE_ELIGIBLE": "1" if record["release_eligible"] else "0",
           "HOME": "/work/home"}
    run_limits = RunLimits(cpus=str(args.cpus), memory=args.memory, timeout_seconds=args.timeout_seconds)
    container = incoming = None
    try:
        container = docker.create(image, container_command(args), env, run_limits)
        docker.copy_in(container, lambda stream: staging.write_archive(staged, stream))
        outcome = docker.start(container, args.timeout_seconds)
        incoming = results.incoming_dir(output)
        collect_error = None
        try:
            docker.copy_out(container, "/work/result", lambda stream: results.extract_result(stream, incoming))
        except (DockerError, results.ResultError) as exc:
            collect_error = exc
        if outcome.exit_code == 0 and not outcome.timed_out:
            if collect_error:
                raise collect_error
            manifest = results.verify_result(incoming)
            if manifest.get("status") != "passed":
                raise results.ResultError("RK_RESULT_STATUS", f"container exited 0 but reported status {manifest.get('status')!r}")
            results.install(incoming, output)
            incoming = None
            results.clear_failure(failure)
            return EXIT_OK, {**record, "passed": True, "container_build": manifest}
        code = "RK_CONTAINER_TIMEOUT" if outcome.timed_out else "RK_CONTAINER_FAILED"
        exit_code = EXIT_COMPILE if outcome.timed_out or outcome.exit_code not in (2, 3, 4, 5) else outcome.exit_code
        failure_record = {"code": code, "exit_code": outcome.exit_code, "timed_out": outcome.timed_out,
                          "collect_error": getattr(collect_error, "message", None),
                          "output_tail": outcome.output_tail.decode("utf-8", "replace")}
        if collect_error:
            shutil.rmtree(incoming, ignore_errors=True)
        results.record_failure(failure, None if collect_error else incoming, failure_record)
        incoming = None
        message = f"build failed (exit {outcome.exit_code}); diagnostics in {failure}" if not outcome.timed_out else \
            f"build exceeded {args.timeout_seconds} s and was stopped; diagnostics in {failure}"
        return exit_code, {**record, "code": code, "message": message}
    except results.ResultError as exc:
        return EXIT_VALIDATION, {**record, "code": exc.code, "message": exc.message}
    except DockerError as exc:
        return EXIT_ENVIRONMENT, {**record, "code": exc.code, "message": exc.message}
    except staging.StagingError as exc:
        return EXIT_CONFIG, {**record, "code": exc.problems[0].code, "message": str(exc), "problems": [p.as_dict() for p in exc.problems]}
    finally:
        if container:
            docker.remove(container)
        if incoming is not None:
            shutil.rmtree(incoming, ignore_errors=True)


def summarize(output_root: Path) -> dict:
    manifest = json.loads((Path(output_root) / results.RESULT_MANIFEST).read_text(encoding="utf-8"))
    selection = manifest.get("selection", {})
    return {
        "image_digest": manifest.get("image", {}).get("digest"),
        "release_eligible": manifest.get("release_eligible"),
        "input_manifest_sha256": manifest.get("input_manifest_sha256"),
        "selection": {key: selection.get(key) for key in ("publication_type", "theme", "engine", "paper")},
        "page_count": manifest.get("pdf", {}).get("pages"),
        "inspect_passed": manifest.get("inspect_passed"),
        "pdf_sha256": manifest.get("pdf", {}).get("sha256"),
    }


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "summarize":
        print(json.dumps(summarize(Path(args.output_root)), indent=2, sort_keys=True))
        return EXIT_OK
    try:
        code, record = run_build(args, _docker())
    except KeyboardInterrupt:
        print("interrupted; the build container was removed", file=sys.stderr)
        return 130
    if args.json:
        print(json.dumps(record, indent=2, sort_keys=True, ensure_ascii=False))
    elif code == EXIT_OK:
        print(f"PASS: {record['output_root']} (image {record.get('image_digest') or 'unpinned'})")
        print("  Review every rendered page under render/ before release; a passing build is not an editorial sign-off.")
    else:
        print(f"FAIL [{record.get('code')}]: {record.get('message')}", file=sys.stderr)
        for problem in record.get("problems", [])[:50]:
            print(f"- {problem['path']} [{problem['code']}]: {problem['message']}", file=sys.stderr)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
