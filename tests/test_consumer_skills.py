"""Consumer skills are copied into a project on init and materialize."""

from pathlib import Path

from python_scripts.reportkit.materialize import CONSUMER_SKILLS, materialize_skills

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_consumer_skills_exist_with_frontmatter():
    for name in CONSUMER_SKILLS:
        text = (REPO_ROOT / "skills" / name / "SKILL.md").read_text(encoding="utf-8")
        assert text.startswith("---\nname: ")
        assert "description:" in text.split("---")[1]


def test_materialize_skills_copies_and_is_idempotent(tmp_path):
    for _ in range(2):
        assert materialize_skills(tmp_path, REPO_ROOT) == list(CONSUMER_SKILLS)
    for name in CONSUMER_SKILLS:
        assert (tmp_path / ".reportkit" / "skills" / name / "SKILL.md").is_file()


def test_skills_name_no_specific_publication():
    text = (REPO_ROOT / "skills" / "review-triage" / "SKILL.md").read_text(encoding="utf-8").lower()
    assert "toan" not in text and "grok" not in text
