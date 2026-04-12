from pathlib import Path

from repo_analyzer.file_filter import FileFilter


def test_file_filter_excludes_model_artifacts(tmp_path: Path):
    (tmp_path / "src").mkdir(parents=True, exist_ok=True)
    (tmp_path / "src" / "main.py").write_text("print('ok')\n", encoding="utf-8")
    (tmp_path / "src" / "weights.pth").write_bytes(b"binary")

    file_filter = FileFilter()
    selected = file_filter.filter_files(tmp_path)
    selected_rel = {p.relative_to(tmp_path).as_posix() for p in selected}

    assert "src/main.py" in selected_rel
    assert "src/weights.pth" not in selected_rel


def test_file_filter_applies_optimistic_cap(tmp_path: Path):
    (tmp_path / "src").mkdir(parents=True, exist_ok=True)
    (tmp_path / "README.md").write_text("readme\n", encoding="utf-8")
    (tmp_path / "requirements.txt").write_text("pytest\n", encoding="utf-8")

    for idx in range(10):
        (tmp_path / "src" / f"module_{idx}.py").write_text(f"x = {idx}\n", encoding="utf-8")

    file_filter = FileFilter()
    file_filter.MAX_SELECTED_FILES = 4
    selected = file_filter.filter_files(tmp_path)
    selected_rel = {p.relative_to(tmp_path).as_posix() for p in selected}

    assert len(selected) == 4
    assert "requirements.txt" in selected_rel
    assert "README.md" in selected_rel
