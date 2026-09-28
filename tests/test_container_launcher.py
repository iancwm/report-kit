from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path
import sys
import tarfile

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))

import reportkit_container as launcher  # noqa: E402
from rk_container.docker import DaemonInfo, DockerError, ImageInfo, RunOutcome  # noqa: E402

DIGEST = "sha256:" + "d" * 64
IMAGE = f"ghcr.io/iancwm/report-kit@{DIGEST}"


def result_tar(files: dict[str, bytes], status: str = "passed", **extra) -> bytes:
    outputs = [{"path": p, "sha256": hashlib.sha256(d).hexdigest(), "bytes": len(d)} for p, d in files.items()]
    manifest = {"schema": "reportkit-container-build/1", "status": status, "outputs": outputs, **extra}
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w") as archive:
        for name, data in {**files, "container-build.json": json.dumps(manifest).encode()}.items():
            info = tarfile.TarInfo(f"result/{name}")
            info.size = len(data)
            archive.addfile(info, io.BytesIO(data))
    return buffer.getvalue()


class FakeDocker:
    def __init__(self, exit_code=0, result=None, timed_out=False, daemon_error=None, interrupt_on_start=False):
        self.exit_code, self.result, self.timed_out = exit_code, result, timed_out
        self.daemon_error, self.interrupt_on_start = daemon_error, interrupt_on_start
        self.created = self.removed = 0
        self.staged: dict[str, bytes] = {}
        self.command: list[str] = []
        self.env: dict[str, str] = {}

    def daemon(self):
        if self.daemon_error:
            raise self.daemon_error
        return DaemonInfo("linux", "amd64", "27", False)

    def image(self, reference, *, pull):
        return ImageInfo(reference, "sha256:" + "e" * 64, DIGEST if "@" in reference else None, "linux", "amd64")

    def create(self, image, command, env, limits):
        self.created += 1
        self.command, self.env = command, env
        return "cid"

    def copy_in(self, container, write):
        buffer = io.BytesIO()
        write(buffer)
        buffer.seek(0)
        with tarfile.open(fileobj=buffer) as archive:
            self.staged = {m.name: archive.extractfile(m).read() for m in archive.getmembers() if m.isfile()}

    def start(self, container, timeout):
        if self.interrupt_on_start:
            raise KeyboardInterrupt
        return RunOutcome(None if self.timed_out else self.exit_code, self.timed_out, b"tail of output")

    def copy_out(self, container, path, consume):
        if self.result is None:
            raise DockerError("RK_DOCKER_COPY_FAILED", "no result")
        consume(io.BytesIO(self.result))

    def remove(self, container):
        self.removed += 1


def project(tmp_path: Path) -> Path:
    src = tmp_path / "Publication Tëst ü"
    (src / "manuscript").mkdir(parents=True)
    (src / "manuscript" / "01.md").write_bytes(b"# One\r\n")
    (src / "publication.yaml").write_bytes(b"title: T\n")
    return src


def args(src: Path, out: Path, *extra: str):
    return launcher.build_parser().parse_args(["build", "--image", IMAGE, "--source-root", str(src), "--output-root", str(out), "--kind", "pipeline", *extra])


def good_result() -> bytes:
    return result_tar({"doc.pdf": b"%PDF new", "build-report.json": b"{}"},
                      pdf={"path": "doc.pdf", "sha256": hashlib.sha256(b"%PDF new").hexdigest(), "pages": 3},
                      selection={"publication_type": "report", "theme": "default", "engine": "pdflatex", "paper": "a4"},
                      input_manifest_sha256="x", image={"reference": IMAGE, "digest": DIGEST}, inspect_passed=True)


def test_success_installs_verified_output(tmp_path: Path) -> None:
    src, out = project(tmp_path), tmp_path / "out"
    fake = FakeDocker(result=good_result())
    code, record = launcher.run_build(args(src, out), fake)
    assert code == 0 and record["passed"]
    assert (out / "doc.pdf").read_bytes() == b"%PDF new"
    assert fake.removed == 1
    assert fake.staged["source/manuscript/01.md"] == b"# One\r\n"
    assert fake.command[:2] == launcher.ENTRYPOINT and fake.command[2:4] == ["--kind", "pipeline"]
    assert fake.env["REPORTKIT_IMAGE_DIGEST"] == DIGEST
    assert not out.with_name("out.failed").exists()
    assert sorted(p.name for p in tmp_path.iterdir()) == ["Publication Tëst ü", "out"]


def test_failure_keeps_prior_output_and_writes_failure_dir(tmp_path: Path) -> None:
    src, out = project(tmp_path), tmp_path / "out"
    launcher.run_build(args(src, out), FakeDocker(result=good_result()))
    before = (out / "doc.pdf").read_bytes()
    failed = result_tar({"logs/build.log": b"! Undefined control sequence."}, status="failed", failed_step="build")
    code, record = launcher.run_build(args(src, out), FakeDocker(exit_code=4, result=failed))
    assert code == 4 and not record["passed"]
    assert (out / "doc.pdf").read_bytes() == before
    failure = out.with_name("out.failed")
    assert (failure / "logs" / "build.log").is_file()
    assert json.loads((failure / "launcher-failure.json").read_text())["exit_code"] == 4


def test_timeout_kills_and_removes_container(tmp_path: Path) -> None:
    src, out = project(tmp_path), tmp_path / "out"
    fake = FakeDocker(timed_out=True, result=None)
    code, record = launcher.run_build(args(src, out, "--timeout-seconds", "5"), fake)
    assert code == 4 and record["code"] == "RK_CONTAINER_TIMEOUT"
    assert fake.removed == 1 and not out.exists()
    assert json.loads((out.with_name("out.failed") / "launcher-failure.json").read_text())["timed_out"] is True


def test_keyboard_interrupt_still_removes_container(tmp_path: Path) -> None:
    src, out = project(tmp_path), tmp_path / "out"
    fake = FakeDocker(interrupt_on_start=True)
    with pytest.raises(KeyboardInterrupt):
        launcher.run_build(args(src, out), fake)
    assert fake.removed == 1
    assert sorted(p.name for p in tmp_path.iterdir()) == ["Publication Tëst ü"]


def test_preflight_failure_happens_before_staging(tmp_path: Path, monkeypatch) -> None:
    src, out = project(tmp_path), tmp_path / "out"
    monkeypatch.setattr(launcher.staging, "collect", lambda *a, **k: pytest.fail("staged before preflight"))
    fake = FakeDocker(daemon_error=DockerError("RK_DOCKER_WINDOWS_CONTAINERS", "switch"))
    code, record = launcher.run_build(args(src, out), fake)
    assert code == 5 and record["code"] == "RK_DOCKER_WINDOWS_CONTAINERS"


def test_staging_problems_stop_before_container_creation(tmp_path: Path) -> None:
    src, out = project(tmp_path), tmp_path / "out"
    (src / "big.bin").write_bytes(b"x" * 2 * 1024 * 1024)
    fake = FakeDocker(result=good_result())
    code, record = launcher.run_build(args(src, out, "--max-file-mb", "1"), fake)
    assert code == 2 and fake.created == 0
    assert record["problems"][0]["code"] == "RK_STAGE_FILE_TOO_LARGE"


def test_unpinned_image_requires_opt_in(tmp_path: Path) -> None:
    src, out = project(tmp_path), tmp_path / "out"
    parsed = launcher.build_parser().parse_args(["build", "--image", "reportkit-local", "--source-root", str(src), "--output-root", str(out), "--kind", "pipeline"])
    code, record = launcher.run_build(parsed, FakeDocker())
    assert code == 2 and record["code"] == "RK_IMAGE_NOT_PINNED"
    parsed.allow_unpinned_image = True
    code, record = launcher.run_build(parsed, FakeDocker(result=good_result()))
    assert code == 0 and record["release_eligible"] is False


def test_direct_tex_requires_existing_entry(tmp_path: Path) -> None:
    src, out = project(tmp_path), tmp_path / "out"
    base = ["build", "--image", IMAGE, "--source-root", str(src), "--output-root", str(out), "--kind", "direct-tex"]
    code, record = launcher.run_build(launcher.build_parser().parse_args(base), FakeDocker())
    assert code == 2 and record["code"] == "RK_ARGS_ENTRY_REQUIRED"
    code, record = launcher.run_build(launcher.build_parser().parse_args([*base, "--entry", "report.tex"]), FakeDocker())
    assert code == 2 and record["code"] == "RK_ARGS_ENTRY_MISSING"


def test_tampered_result_is_not_installed(tmp_path: Path) -> None:
    src, out = project(tmp_path), tmp_path / "out"
    bad = bytearray(good_result())
    bad[bad.index(b"%PDF new")] = ord("X")
    code, record = launcher.run_build(args(src, out), FakeDocker(result=bytes(bad)))
    assert code == 3 and record["code"] == "RK_RESULT_HASH_MISMATCH" and not out.exists()


def test_summarize(tmp_path: Path) -> None:
    src, out = project(tmp_path), tmp_path / "out"
    launcher.run_build(args(src, out), FakeDocker(result=good_result()))
    summary = launcher.summarize(out)
    assert summary["page_count"] == 3 and summary["selection"]["paper"] == "a4" and summary["image_digest"] == DIGEST


def test_main_json_output(tmp_path: Path, capsys, monkeypatch) -> None:
    src, out = project(tmp_path), tmp_path / "out"
    monkeypatch.setattr(launcher, "_docker", lambda: FakeDocker(result=good_result()))
    assert launcher.main(["build", "--image", IMAGE, "--source-root", str(src), "--output-root", str(out), "--kind", "pipeline", "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["passed"] is True
