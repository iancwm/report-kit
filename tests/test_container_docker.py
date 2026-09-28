from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))

from rk_container.docker import Docker, DockerError, RunLimits  # noqa: E402

DIGEST = "sha256:" + "a" * 64
PINNED = f"ghcr.io/iancwm/report-kit@{DIGEST}"


class FakeCli:
    """Scripted `docker` responses keyed by the first argument(s)."""

    def __init__(self, responses: dict[tuple[str, ...], list[subprocess.CompletedProcess | BaseException]]) -> None:
        self.responses = responses
        self.calls: list[list[str]] = []

    def __call__(self, argv, **kwargs):
        assert isinstance(argv, list) and "shell" not in kwargs
        self.calls.append(argv)
        for key, queue in self.responses.items():
            if tuple(argv[1:1 + len(key)]) == key:
                item = queue.pop(0) if len(queue) > 1 else queue[0]
                if isinstance(item, BaseException):
                    raise item
                return item
        raise AssertionError(f"unexpected docker call {argv}")


def ok(stdout: str | bytes = b"", rc: int = 0, stderr: bytes = b"") -> subprocess.CompletedProcess:
    return subprocess.CompletedProcess([], rc, stdout.encode() if isinstance(stdout, str) else stdout, stderr)


def version(os_name="linux", arch="amd64") -> subprocess.CompletedProcess:
    return ok(json.dumps({"Client": {}, "Server": {"Os": os_name, "Arch": arch, "Version": "27.0"}}))


def inspect(os_name="linux", arch="amd64", digests=(f"ghcr.io/iancwm/report-kit@{DIGEST}",)) -> subprocess.CompletedProcess:
    return ok(json.dumps({"Id": "sha256:" + "b" * 64, "Os": os_name, "Architecture": arch, "RepoDigests": list(digests)}))


def test_missing_cli() -> None:
    with pytest.raises(DockerError) as exc:
        Docker(run=FakeCli({("version",): [FileNotFoundError()]})).daemon()
    assert exc.value.code == "RK_DOCKER_MISSING"


def test_daemon_unavailable() -> None:
    cli = FakeCli({("version",): [ok(json.dumps({"Client": {}}), rc=1, stderr=b"Cannot connect to the Docker daemon")]})
    with pytest.raises(DockerError) as exc:
        Docker(run=cli).daemon()
    assert exc.value.code == "RK_DOCKER_DAEMON_UNAVAILABLE"
    assert "Cannot connect" in exc.value.message


def test_windows_container_mode_is_actionable() -> None:
    with pytest.raises(DockerError) as exc:
        Docker(run=FakeCli({("version",): [version(os_name="windows")]})).daemon()
    assert exc.value.code == "RK_DOCKER_WINDOWS_CONTAINERS"
    assert "Switch to Linux containers" in exc.value.message


def test_arm_daemon_is_marked_emulated() -> None:
    info = Docker(run=FakeCli({("version",): [version(arch="arm64")]})).daemon()
    assert info.emulated is True


def test_pinned_image_is_pulled_when_absent_and_digest_verified() -> None:
    cli = FakeCli({("image", "inspect"): [ok(rc=1), inspect()], ("pull",): [ok()]})
    info = Docker(run=cli).image(PINNED, pull=True)
    assert info.digest == DIGEST and info.pinned
    assert ["docker", "pull", "--platform", "linux/amd64", PINNED] in cli.calls


def test_unavailable_image() -> None:
    cli = FakeCli({("image", "inspect"): [ok(rc=1)], ("pull",): [ok(rc=1, stderr=b"manifest unknown")]})
    with pytest.raises(DockerError) as exc:
        Docker(run=cli).image(PINNED, pull=True)
    assert exc.value.code == "RK_DOCKER_IMAGE_UNAVAILABLE"
    assert "manifest unknown" in exc.value.message


def test_no_pull_reports_unavailable_without_pulling() -> None:
    cli = FakeCli({("image", "inspect"): [ok(rc=1)]})
    with pytest.raises(DockerError) as exc:
        Docker(run=cli).image(PINNED, pull=False)
    assert exc.value.code == "RK_DOCKER_IMAGE_UNAVAILABLE"
    assert not any(c[1] == "pull" for c in cli.calls)


def test_wrong_architecture_image() -> None:
    cli = FakeCli({("image", "inspect"): [inspect(arch="arm64")]})
    with pytest.raises(DockerError) as exc:
        Docker(run=cli).image(PINNED, pull=False)
    assert exc.value.code == "RK_DOCKER_IMAGE_PLATFORM"


def test_digest_mismatch() -> None:
    cli = FakeCli({("image", "inspect"): [inspect(digests=("ghcr.io/iancwm/report-kit@sha256:" + "c" * 64,))]})
    with pytest.raises(DockerError) as exc:
        Docker(run=cli).image(PINNED, pull=False)
    assert exc.value.code == "RK_DOCKER_DIGEST_MISMATCH"


def test_local_unpinned_image_has_no_digest() -> None:
    info = Docker(run=FakeCli({("image", "inspect"): [inspect(digests=())]})).image("reportkit-local", pull=False)
    assert info.digest is None and not info.pinned


def test_create_is_isolated_and_runs_the_inspected_image_id() -> None:
    cli = FakeCli({("create",): [ok("cid123\n")]})
    image = Docker(run=FakeCli({("image", "inspect"): [inspect()]})).image(PINNED, pull=False)
    cid = Docker(run=cli).create(image, ["/opt/py", "/opt/entry.py", "--kind", "pipeline"], {"B": "2", "A": "1"}, RunLimits())
    argv = cli.calls[0]
    assert cid == "cid123"
    for flag in (["--network", "none"], ["--user", "10001:10001"], ["--cap-drop", "ALL"], ["--platform", "linux/amd64"],
                 ["--security-opt", "no-new-privileges"], ["--memory", "6g"], ["--memory-swap", "6g"], ["--cpus", "4"],
                 ["--entrypoint", "/opt/py"], ["--env", "A=1"]):
        assert any(argv[i:i + 2] == flag for i in range(len(argv))), flag
    assert not any(a.startswith(("-v", "--volume", "--mount")) for a in argv)
    assert argv[-4:] == ["sha256:" + "b" * 64, "/opt/entry.py", "--kind", "pipeline"]


def test_start_timeout_kills_container() -> None:
    cli = FakeCli({("start",): [subprocess.TimeoutExpired(["docker"], 5, output=b"partial")], ("kill",): [ok()]})
    outcome = Docker(run=cli).start("cid", timeout=5)
    assert outcome.timed_out and outcome.exit_code is None
    assert ["docker", "kill", "cid"] in cli.calls


def test_start_reports_exit_code_and_bounded_tail() -> None:
    cli = FakeCli({("start",): [ok(b"x" * 200_000, rc=4)]})
    outcome = Docker(run=cli).start("cid", timeout=5)
    assert outcome.exit_code == 4 and len(outcome.output_tail) == 64 * 1024


def test_remove_never_raises() -> None:
    Docker(run=FakeCli({("rm",): [FileNotFoundError()]})).remove("cid")
