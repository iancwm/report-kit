"""Host-neutral scripted driver for the ReportKit reasoning loop.

The oracle uses only the stable CLI surface and the frozen ``LOOP_STEPS``
table. It makes no model or browser calls, so its transcript is reproducible
in CI and can be compared with transcripts from future model-backed drivers.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from typing import Any, Protocol, Sequence

from reportkit.loop import LOOP_STEPS
from reportkit.publications import PUBLICATION_TYPES
from reportkit.registry import COMMAND_CONTRACT


REPO_ROOT = Path(__file__).resolve().parents[2]
CLI = REPO_ROOT / "reportkit"


@dataclass(frozen=True)
class CommandResult:
    """The host-neutral result of one CLI invocation."""

    argv: tuple[str, ...]
    returncode: int
    stdout: str = ""
    stderr: str = ""

    def json(self) -> dict[str, Any]:
        """Parse a JSON CLI response, returning an empty object if absent."""
        try:
            value = json.loads(self.stdout)
        except json.JSONDecodeError:
            return {}
        return value if isinstance(value, dict) else {}


class CommandRunner(Protocol):
    """Minimal interface used to run ReportKit commands in a consumer dir."""

    def run(self, argv: Sequence[str], *, cwd: Path) -> CommandResult:
        """Run ``argv`` with ``cwd`` as its working directory."""


class SubprocessCommandRunner:
    """Run the repository-local CLI without assuming a shell or host UI."""

    def run(self, argv: Sequence[str], *, cwd: Path) -> CommandResult:
        command = (sys.executable, str(CLI), *map(str, argv))
        env = os.environ.copy()
        python_path = str(REPO_ROOT / "python_scripts")
        if env.get("PYTHONPATH"):
            python_path += os.pathsep + env["PYTHONPATH"]
        env["PYTHONPATH"] = python_path
        completed = subprocess.run(
            command,
            cwd=cwd,
            env=env,
            capture_output=True,
            text=True,
            check=False,
            timeout=300,
        )
        return CommandResult(
            argv=tuple(command),
            returncode=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
        )


@dataclass(frozen=True)
class TranscriptEvent:
    """One loop action and, when applicable, its CLI response."""

    step: str
    command: tuple[str, ...] = ()
    returncode: int = 0
    stdout: str = ""
    stderr: str = ""

    def json(self) -> dict[str, Any]:
        try:
            value = json.loads(self.stdout)
        except json.JSONDecodeError:
            return {}
        return value if isinstance(value, dict) else {}


@dataclass(frozen=True)
class Transcript:
    """Portable record of a driver's response to one user prompt."""

    prompt: str
    workdir: Path
    events: tuple[TranscriptEvent, ...]
    target: dict[str, str] | None = None

    @property
    def succeeded(self) -> bool:
        return all(event.returncode == 0 for event in self.events)

    def event(self, step: str) -> TranscriptEvent:
        """Return the last event with ``step`` or raise ``KeyError``."""
        for item in reversed(self.events):
            if item.step == step:
                return item
        raise KeyError(f"transcript has no {step!r} event")

    def summary(self) -> str:
        """Render compact failure context suitable for an assertion message."""
        lines = [f"prompt: {self.prompt}", f"workdir: {self.workdir}"]
        for event in self.events:
            rendered = " ".join(event.command)
            lines.append(f"{event.step} (exit {event.returncode}): {rendered}")
            if event.stderr.strip():
                lines.append(event.stderr.strip()[-1600:])
            elif event.stdout.strip() and event.returncode:
                lines.append(event.stdout.strip()[-1600:])
        return "\n".join(lines)


class AgentDriver(Protocol):
    """Adapter surface implemented by scripted and future model drivers."""

    def run(self, prompt: str, workdir: Path) -> Transcript:
        """Process one request in ``workdir`` and return its transcript."""


@dataclass(frozen=True)
class ScenarioTarget:
    publication_type: str
    theme: str
    title: str
    author: str
    reference: str | None = None

    def as_selection(self) -> dict[str, str]:
        return {"publication_type": self.publication_type, "theme": self.theme}


_SCENARIOS = (
    (
        re.compile(r"magazine[- ]style feature", re.IGNORECASE),
        ScenarioTarget(
            "feature-article", "editorial", "How a city learned to count its rivers",
            "ReportKit oracle fixture", str(REPO_ROOT / "latex_templates/examples/editorial-feature/report.tex"),
        ),
    ),
    (
        re.compile(r"\bdecision brief\b.*\bCFO\b", re.IGNORECASE),
        ScenarioTarget(
            "executive-brief",
            str(PUBLICATION_TYPES["executive-brief"]["default_target"]["theme"]),
            "Consolidate the two regional dispatch platforms",
            "Harborline Operations Strategy Office",
        ),
    ),
    (
        re.compile(r"\bconsulting deck\b", re.IGNORECASE),
        ScenarioTarget(
            "presentation", "executive", "Turn fragmented data into decision velocity",
            "ReportKit oracle fixture",
        ),
    ),
)

_CONTINUE_PROMPT = re.compile(r"^\s*continue the publication in\s+(.+?)\s*$", re.IGNORECASE)


class OracleDriver:
    """Replay the canonical loop with fixed target choices and CLI actions.

    ``stop_after="AUTHOR"`` is used by the context-reset scenario to simulate
    an agent process ending after its authored files are on disk. A new driver
    then receives only the continuation prompt and must reload the target.
    """

    def __init__(self, runner: CommandRunner | None = None, *, stop_after: str | None = None) -> None:
        self.runner = runner or SubprocessCommandRunner()
        self.stop_after = stop_after

    def run(self, prompt: str, workdir: Path) -> Transcript:
        root = Path(workdir).expanduser().resolve()
        root.mkdir(parents=True, exist_ok=True)
        events: list[TranscriptEvent] = []
        continuation = _CONTINUE_PROMPT.fullmatch(prompt)
        if continuation:
            requested_root = Path(continuation.group(1)).expanduser().resolve()
            if requested_root != root:
                raise ValueError("continuation path must match the supplied workdir")
            target = self._rehydrate(root, events)
            if target is None:
                return Transcript(prompt, root, tuple(events))
            return self._resume(prompt, root, target, events)

        target = self._target_for_prompt(prompt)
        for step in LOOP_STEPS:
            if step.name == "SELECT":
                result = self._invoke(
                    "SELECT", ["context", "--source-root", str(root), "--slice", "quickstart", "--json"], root, events,
                )
            elif step.name == "LOCK":
                args = [
                    "target", "set", "--source-root", str(root),
                    "--publication-type", target.publication_type,
                    "--theme", target.theme,
                    "--source-mode", "tex",
                    "--request", prompt,
                    "--decided-by", "agent-inferred",
                ]
                if target.reference:
                    args.extend(["--reference", target.reference])
                args.append("--json")
                result = self._invoke("LOCK", args, root, events)
            elif step.name == "SCAFFOLD":
                # LOCK already wrote the target and intent. Plain init creates
                # the starter tree without replacing the verbatim request.
                result = self._invoke("SCAFFOLD", ["init", str(root), "--json"], root, events)
            elif step.name == "AUTHOR":
                result = self._invoke(
                    "AUTHOR", ["context", "--source-root", str(root), "--slice", "primitives", "--json"], root, events,
                )
                if result.returncode == 0:
                    self._author(root, target)
                    events.append(TranscriptEvent("AUTHOR_FILES"))
            elif step.name == "CHECK":
                result = self._invoke("CHECK", ["check", "--source-root", str(root), "--json"], root, events)
            elif step.name == "BUILD":
                result = self._invoke(
                    "BUILD",
                    ["build", "--source-root", str(root), "--title", target.title, "--author", target.author, "--json"],
                    root,
                    events,
                )
            elif step.name == "REVIEW":
                result = self._invoke(
                    "REVIEW", ["review", "--source-root", str(root), "--visual-review", "unavailable", "--json"], root, events,
                )
            elif step.name == "DELIVER":
                result = self._invoke("DELIVER", ["status", "--source-root", str(root), "--json"], root, events)
            else:
                raise RuntimeError(f"unsupported ReportKit loop step {step.name!r}")

            if result.returncode != 0:
                break
            if self.stop_after == step.name:
                break

        return Transcript(prompt, root, tuple(events), target.as_selection())

    def _resume(
        self,
        prompt: str,
        root: Path,
        target: dict[str, str],
        events: list[TranscriptEvent],
    ) -> Transcript:
        """Continue from the persisted AUTHOR artefacts with a fresh driver."""
        result = self._invoke(
            "AUTHOR_CONTEXT", ["context", "--source-root", str(root), "--slice", "primitives", "--json"], root, events,
        )
        if result.returncode != 0:
            return Transcript(prompt, root, tuple(events), target)
        title, author = self._identity_for(target["publication_type"])
        for step in LOOP_STEPS:
            if step.name not in {"CHECK", "BUILD", "REVIEW", "DELIVER"}:
                continue
            if step.name == "CHECK":
                result = self._invoke("CHECK", ["check", "--source-root", str(root), "--json"], root, events)
            elif step.name == "BUILD":
                result = self._invoke(
                    "BUILD", ["build", "--source-root", str(root), "--title", title, "--author", author, "--json"],
                    root,
                    events,
                )
            elif step.name == "REVIEW":
                result = self._invoke(
                    "REVIEW", ["review", "--source-root", str(root), "--visual-review", "unavailable", "--json"], root, events,
                )
            else:
                result = self._invoke("DELIVER", ["status", "--source-root", str(root), "--json"], root, events)
            if result.returncode != 0:
                break
        return Transcript(prompt, root, tuple(events), target)

    def _rehydrate(self, root: Path, events: list[TranscriptEvent]) -> dict[str, str] | None:
        result = self._invoke("REHYDRATE", ["target", "show", "--source-root", str(root), "--json"], root, events)
        if result.returncode != 0:
            return None
        record = result.json().get("target_state")
        if not isinstance(record, dict):
            return None
        publication_type = record.get("publication_type")
        theme = record.get("theme")
        source_mode = record.get("source_mode")
        if not all(isinstance(value, str) and value for value in (publication_type, theme, source_mode)):
            return None
        intent_path = root / ".reportkit" / "intent.json"
        try:
            intent = json.loads(intent_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        if not isinstance(intent, dict):
            return None
        if any(
            intent.get(key) != record.get(key)
            for key in ("publication_type", "theme", "source_mode")
        ):
            return None
        return {"publication_type": publication_type, "theme": theme, "source_mode": source_mode}

    def _invoke(self, step: str, argv: Sequence[str], root: Path, events: list[TranscriptEvent]) -> CommandResult:
        if not argv or argv[0] not in COMMAND_CONTRACT:
            raise ValueError(f"oracle loop step {step!r} uses an uncontracted CLI command: {argv!r}")
        result = self.runner.run(argv, cwd=root)
        events.append(TranscriptEvent(step, result.argv, result.returncode, result.stdout, result.stderr))
        return result

    @staticmethod
    def _target_for_prompt(prompt: str) -> ScenarioTarget:
        for pattern, target in _SCENARIOS:
            if pattern.search(prompt):
                return target
        raise ValueError(f"oracle has no deterministic scenario for prompt: {prompt!r}")

    @staticmethod
    def _identity_for(publication_type: str) -> tuple[str, str]:
        for _, target in _SCENARIOS:
            if target.publication_type == publication_type:
                return target.title, target.author
        raise ValueError(f"oracle has no identity fixture for {publication_type!r}")

    @staticmethod
    def _author(root: Path, target: ScenarioTarget) -> None:
        if target.publication_type == "feature-article":
            source = (REPO_ROOT / "latex_templates/examples/feature_article_acceptance_test.tex").read_text(encoding="utf-8")
            brief = {
                "visual_reference": "ReportKit editorial feature acceptance fixture",
                "required": ["dropcap"],
            }
        elif target.publication_type == "executive-brief":
            example = REPO_ROOT / "latex_templates/examples/executive-brief"
            source = (example / "report.tex").read_text(encoding="utf-8")
            body = (example / "brief.tex").read_text(encoding="utf-8")
            source = source.replace(r"\input{brief.tex}", body)
            brief = {
                "publication_type": "executive-brief",
                "visual_reference": "ReportKit executive brief canonical example",
            }
        elif target.publication_type == "presentation":
            source = OracleDriver._presentation_source()
            brief = {
                "publication_type": "presentation",
                "visual_reference": "ReportKit executive presentation canonical example",
            }
        else:
            raise ValueError(f"oracle has no authoring fixture for {target.publication_type!r}")
        (root / "report.tex").write_text(source, encoding="utf-8")
        (root / "composition-brief.json").write_text(json.dumps(brief, indent=2) + "\n", encoding="utf-8")

    @staticmethod
    def _presentation_source() -> str:
        slides = [
            r"\begin{frame}[plain]\begin{titleslide}\end{titleslide}\end{frame}",
            r"\begin{frame}\begin{evidenceslide}{Governed decisions improve operating performance.}"
            r"The fictional case supports a ten-slide consulting narrative.\end{evidenceslide}\end{frame}",
        ]
        slides.extend(
            rf"\begin{{frame}}{{Consulting slide {index}}}"
            rf"The team aligns evidence, ownership, timing, and measurable outcomes in step {index}."
            rf"\end{{frame}}"
            for index in range(3, 11)
        )
        return "\n".join([
            r"\documentclass[theme=executive,publication-type=presentation]{reportkit-slides}",
            r"\title{Turn fragmented data into decision velocity}",
            r"\subtitle{A fictional consulting decision deck}",
            r"\author{ReportKit oracle fixture}",
            r"\date{}",
            r"\begin{document}",
            *slides,
            r"\end{document}",
        ]) + "\n"
