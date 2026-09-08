from pathlib import Path

from python_scripts.reportkit.registry import generate_registry, skill_inventory


def test_registry_matches_skill_inventories() -> None:
    root = Path(__file__).resolve().parents[1]
    registry = generate_registry(root)
    documented = skill_inventory(root / "SKILL.md")
    assert set(registry["components"]["figures"]) == documented["figures"]
    callouts = set(registry["components"]["callouts"]["names"])
    assert callouts == documented["callouts"]
