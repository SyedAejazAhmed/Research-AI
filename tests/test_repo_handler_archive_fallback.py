import io
import zipfile
from pathlib import Path

from repo_analyzer.repo_handler import RepoHandler


class _FakeResponse:
    def __init__(self, payload: bytes):
        self._buffer = io.BytesIO(payload)

    def read(self, size: int = -1) -> bytes:
        return self._buffer.read(size)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def _make_zip_bytes(root_name: str, files: dict[str, str]) -> bytes:
    data = io.BytesIO()
    with zipfile.ZipFile(data, "w", zipfile.ZIP_DEFLATED) as zf:
        for rel_path, content in files.items():
            zf.writestr(f"{root_name}/{rel_path}", content)
    return data.getvalue()


def test_download_archive_replaces_partial_clone(monkeypatch, tmp_path: Path):
    repo_name = "AI-Based-Underwater-Image-Enhancement-System-for-Increased-Maritime-Security"
    archive_root = f"{repo_name}-main"
    archive_payload = _make_zip_bytes(archive_root, {"README.md": "hello"})

    handler = RepoHandler()
    handler._temp_dir = tmp_path
    handler._repo_path = tmp_path / repo_name

    # Simulate a timed-out git clone leaving a partial directory behind.
    handler._repo_path.mkdir(parents=True, exist_ok=True)
    (handler._repo_path / "partial.txt").write_text("stale", encoding="utf-8")

    monkeypatch.setattr(handler, "_candidate_branches", lambda owner, repo: ("main",))

    def _fake_urlopen(request, timeout=0):
        return _FakeResponse(archive_payload)

    monkeypatch.setattr("urllib.request.urlopen", _fake_urlopen)

    handler._download_archive(
        repo_url="https://github.com/SyedAejazAhmed/AI-Based-Underwater-Image-Enhancement-System-for-Increased-Maritime-Security",
        repo_name=repo_name,
        timeout=5,
    )

    assert handler._repo_path.exists()
    assert (handler._repo_path / "README.md").exists()
    assert not (handler._repo_path / "partial.txt").exists()


def test_extract_archive_uses_archive_top_level_dir(tmp_path: Path):
    repo_name = "AI-Based-Underwater-Image-Enhancement-System-for-Increased-Maritime-Security"
    archive_root = f"{repo_name}-main"
    archive_file = tmp_path / "repo_main.zip"
    extract_dir = tmp_path / "extract"

    with zipfile.ZipFile(archive_file, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(f"{archive_root}/src/app.py", "print('ok')\n")

    # Simulate unrelated stale directory that previously confused extraction root selection.
    stale_dir = tmp_path / repo_name
    stale_dir.mkdir(parents=True, exist_ok=True)

    handler = RepoHandler()
    extracted_root = handler._extract_archive(archive_file, extract_dir)

    assert extracted_root.name == archive_root
    assert (extracted_root / "src" / "app.py").exists()
