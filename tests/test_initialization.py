from pathlib import Path
import sys
import tarfile

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "python_scripts"))

from reportkit import initialization  # noqa: E402
from reportkit.initialization import initialize_project  # noqa: E402


def test_initialize_project_scaffolds_without_copying_engine_files(tmp_path: Path) -> None:
    target, created = initialize_project(tmp_path / "publication", REPO)

    assert target == (tmp_path / "publication").resolve()
    assert set(created) == {
        "manuscript/", "fragments/", "assets/", "figures/", "build/", "output/",
        "manuscript/order.txt", "publication.yaml",
    }
    assert (target / "manuscript" / "order.txt").is_file()
    assert (target / "publication.yaml").read_text(encoding="utf-8").startswith("# Publication identity")
    assert not (target / "reportkit_doctor.py").exists()
    assert not (target / "reportkit_viz.py").exists()


def test_initialize_project_is_idempotent_and_preserves_content(tmp_path: Path) -> None:
    target = tmp_path / "publication"
    target.mkdir()
    order = target / "manuscript" / "order.txt"
    order.parent.mkdir()
    order.write_text("01-existing.md\n", encoding="utf-8")

    _, created = initialize_project(target, REPO)

    assert "manuscript/order.txt" not in created
    assert order.read_text(encoding="utf-8") == "01-existing.md\n"


def test_initialize_project_refuses_targets_inside_the_engine_clone(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="inside the ReportKit clone"):
        initialize_project(REPO / "consumer-project", REPO)


def test_install_fonts_rejects_archive_links(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo = tmp_path / "repo"
    font_data = repo / "font_data"
    font_data.mkdir(parents=True)
    bundle = font_data / "reportkit-libertinus-fonts.tar.gz"
    with tarfile.open(bundle, "w:gz") as archive:
        link = tarfile.TarInfo("escape")
        link.type = tarfile.SYMTYPE
        link.linkname = "/tmp/outside"
        archive.addfile(link)

    monkeypatch.setattr(initialization, "_font_files_resolvable", lambda: False)
    monkeypatch.setattr(initialization, "_texmf_local", lambda: tmp_path / "texmf")
    with pytest.raises(ValueError, match="unsupported member"):
        initialization.install_fonts(repo)
