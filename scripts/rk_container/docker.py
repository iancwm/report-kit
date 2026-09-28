"""Docker CLI adapter for the ReportKit container launcher (stdlib only).

Every call is an argument list. No shell, no path interpolation.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
import subprocess
from typing import BinaryIO, Callable

from .staging import BUILD_GID, BUILD_UID

PLATFORM = "linux/amd64"
OUTPUT_TAIL_BYTES = 64 * 1024


class DockerError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True)
class DaemonInfo:
    os: str
    architecture: str
    version: str
    emulated: bool


@dataclass(frozen=True)
class ImageInfo:
    reference: str
    image_id: str
    digest: str | None
    os: str
    architecture: str

    @property
    def pinned(self) -> bool:
        return "@sha256:" in self.reference


@dataclass(frozen=True)
class RunLimits:
    cpus: str = "4"
    memory: str = "6g"
    pids: int = 1024
    timeout_seconds: int = 1800


@dataclass(frozen=True)
class RunOutcome:
    exit_code: int | None
    timed_out: bool
    output_tail: bytes


def _last_line(data: bytes | None) -> str:
    lines = (data or b"").decode("utf-8", "replace").strip().splitlines()
    return lines[-1] if lines else "no error output"


def _repository(reference: str) -> str:
    if "@" in reference:
        return reference.split("@", 1)[0]
    head, _, tail = reference.rpartition("/")
    name = tail.split(":", 1)[0]
    return f"{head}/{name}" if head else name


class Docker:
    def __init__(self, executable: str = "docker", run: Callable = subprocess.run, popen: Callable = subprocess.Popen) -> None:
        self.executable = executable
        self._runner = run
        self._popen = popen

    def _run(self, args: list[str], *, timeout: float = 120) -> subprocess.CompletedProcess:
        try:
            return self._runner([self.executable, *args], capture_output=True, timeout=timeout)
        except FileNotFoundError:
            raise DockerError("RK_DOCKER_MISSING", "the Docker CLI was not found on PATH; install Docker Desktop (Windows) or Docker Engine (Linux)") from None
        except subprocess.TimeoutExpired:
            raise DockerError("RK_DOCKER_TIMEOUT", f"`docker {args[0]}` did not finish within {timeout:.0f} seconds") from None

    def daemon(self) -> DaemonInfo:
        proc = self._run(["version", "--format", "{{json .}}"], timeout=30)
        try:
            data = json.loads(proc.stdout.decode("utf-8", "replace") or "{}")
        except json.JSONDecodeError:
            data = {}
        server = data.get("Server") if isinstance(data, dict) else None
        if proc.returncode != 0 or not server:
            raise DockerError("RK_DOCKER_DAEMON_UNAVAILABLE",
                              f"the Docker daemon is not reachable; start Docker Desktop or the docker service and retry ({_last_line(proc.stderr)})")
        os_name, arch = server.get("Os", ""), server.get("Arch", "")
        if os_name != "linux":
            raise DockerError("RK_DOCKER_WINDOWS_CONTAINERS",
                              f"Docker is running {os_name or 'non-Linux'} containers; ReportKit needs Linux containers. "
                              "In Docker Desktop choose 'Switch to Linux containers...' and retry")
        return DaemonInfo(os_name, arch, server.get("Version", ""), emulated=arch not in ("amd64", "x86_64"))

    def _inspect(self, reference: str) -> ImageInfo | None:
        proc = self._run(["image", "inspect", "--format", "{{json .}}", reference], timeout=60)
        if proc.returncode != 0:
            return None
        data = json.loads(proc.stdout)
        digests = [d for d in data.get("RepoDigests") or [] if "@" in d]
        wanted = reference.split("@", 1)[1] if "@" in reference else None
        if wanted:
            if not any(d.split("@", 1)[1] == wanted for d in digests):
                raise DockerError("RK_DOCKER_DIGEST_MISMATCH", f"local image for {reference} does not carry digest {wanted}")
            digest = wanted
        else:
            repo = _repository(reference)
            digest = next((d.split("@", 1)[1] for d in digests if d.split("@", 1)[0] == repo), None)
        return ImageInfo(reference, data.get("Id", ""), digest, data.get("Os", ""), data.get("Architecture", ""))

    def image(self, reference: str, *, pull: bool) -> ImageInfo:
        info = self._inspect(reference)
        if info is None and pull:
            proc = self._run(["pull", "--platform", PLATFORM, reference], timeout=3600)
            if proc.returncode != 0:
                raise DockerError("RK_DOCKER_IMAGE_UNAVAILABLE", f"could not pull {reference}: {_last_line(proc.stderr)}")
            info = self._inspect(reference)
        if info is None:
            raise DockerError("RK_DOCKER_IMAGE_UNAVAILABLE", f"image {reference} is not available locally" + ("" if pull else " and --no-pull was given"))
        if (info.os, info.architecture) != ("linux", "amd64"):
            raise DockerError("RK_DOCKER_IMAGE_PLATFORM", f"image {reference} is {info.os}/{info.architecture}; ReportKit v1 images are linux/amd64 only")
        return info

    def create(self, image: ImageInfo, command: list[str], env: dict[str, str], limits: RunLimits) -> str:
        args = ["create", "--platform", PLATFORM, "--network", "none", "--user", f"{BUILD_UID}:{BUILD_GID}",
                "--cpus", limits.cpus, "--memory", limits.memory, "--memory-swap", limits.memory,
                "--pids-limit", str(limits.pids), "--cap-drop", "ALL", "--security-opt", "no-new-privileges",
                "--workdir", "/work", "--entrypoint", command[0]]
        for key, value in sorted(env.items()):
            args += ["--env", f"{key}={value}"]
        args += [image.image_id or image.reference, *command[1:]]
        proc = self._run(args, timeout=120)
        if proc.returncode != 0:
            raise DockerError("RK_DOCKER_CREATE_FAILED", f"could not create the build container: {_last_line(proc.stderr)}")
        return proc.stdout.decode().strip()

    def copy_in(self, container: str, write: Callable[[BinaryIO], None]) -> None:
        try:
            proc = self._popen([self.executable, "cp", "--archive", "-", f"{container}:/work"],
                               stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        except FileNotFoundError:
            raise DockerError("RK_DOCKER_MISSING", "the Docker CLI was not found on PATH") from None
        try:
            write(proc.stdin)
            proc.stdin.close()
        except BrokenPipeError:
            pass
        except BaseException:
            proc.kill()
            proc.wait()
            raise
        stderr = proc.stderr.read()
        if proc.wait(timeout=600) != 0:
            raise DockerError("RK_DOCKER_COPY_FAILED", f"staging into the container failed: {_last_line(stderr)}")

    def start(self, container: str, timeout: int) -> RunOutcome:
        try:
            proc = self._runner([self.executable, "start", "--attach", container], capture_output=True, timeout=timeout)
        except FileNotFoundError:
            raise DockerError("RK_DOCKER_MISSING", "the Docker CLI was not found on PATH") from None
        except subprocess.TimeoutExpired as exc:
            try:
                self._run(["kill", container], timeout=60)
            except DockerError:
                pass
            return RunOutcome(None, True, ((exc.output or b"") + (exc.stderr or b""))[-OUTPUT_TAIL_BYTES:])
        return RunOutcome(proc.returncode, False, ((proc.stdout or b"") + (proc.stderr or b""))[-OUTPUT_TAIL_BYTES:])

    def copy_out(self, container: str, path: str, consume: Callable[[BinaryIO], None]) -> None:
        proc = self._popen([self.executable, "cp", f"{container}:{path}", "-"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        try:
            consume(proc.stdout)
        except BaseException:
            proc.kill()
            proc.wait()
            raise
        proc.stdout.close()
        stderr = proc.stderr.read()
        if proc.wait(timeout=600) != 0:
            raise DockerError("RK_DOCKER_COPY_FAILED", f"collecting {path} failed: {_last_line(stderr)}")

    def remove(self, container: str) -> None:
        try:
            self._run(["rm", "--force", "--volumes", container], timeout=120)
        except DockerError:
            pass
