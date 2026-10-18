"""Default-suite self-test for the scripted, host-neutral loop harness."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Sequence

from agent_evals.harness import CommandResult, CommandRunner, OracleDriver
from reportkit.loop import LOOP_STEPS


class RecordingRunner(CommandRunner):
    """Small fake CLI boundary; no model, subprocess, or TeX is required."""

    def __init__(self) -> None:
        self.calls: list[tuple[tuple[str, ...], Path]] = []
        self.selection: dict[str, str] = {}

    def run(self, argv: Sequence[str], *, cwd: Path) -> CommandResult:
        command = tuple(map(str, argv))
        self.calls.append((command, cwd))
        action = command[0]
        if action == "target":
            self.selection = {
                "publication_type": command[command.index("--publication-type") + 1],
                "theme": command[command.index("--theme") + 1],
            }
            payload = {"passed": True}
        elif action == "check":
            payload = {"passed": True, "composition": {"passed": True, "diagnostics": []}}
        elif action == "build":
            build = cwd / "build" / "combined"
            build.mkdir(parents=True, exist_ok=True)
            (build / "build-report.json").write_text(
                json.dumps({"selection": self.selection}), encoding="utf-8",
            )
            payload = {"passed": True}
        else:
            payload = {"passed": True}
        return CommandResult(command, 0, json.dumps(payload))


def test_oracle_is_deterministic_and_replays_the_frozen_loop(tmp_path: Path) -> None:
    runner = RecordingRunner()
    workdir = tmp_path / "publication"
    prompt = "Write a magazine-style feature about X, like this reference."

    transcript = OracleDriver(runner).run(prompt, workdir)

    assert transcript.succeeded, transcript.summary()
    loop_events = [event.step for event in transcript.events if event.step in {step.name for step in LOOP_STEPS}]
    assert loop_events == [step.name for step in LOOP_STEPS]
    assert transcript.target == {"publication_type": "feature-article", "theme": "editorial"}
    assert transcript.event("CHECK").json()["composition"]["passed"] is True
    assert all(cwd == workdir.resolve() for _, cwd in runner.calls)
    assert (workdir / "report.tex").is_file()
    assert json.loads((workdir / "composition-brief.json").read_text(encoding="utf-8"))["required"] == ["dropcap"]
    report = json.loads((workdir / "build" / "combined" / "build-report.json").read_text(encoding="utf-8"))
    assert report["selection"] == transcript.target
