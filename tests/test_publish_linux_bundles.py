"""Pin publish.yml Linux Tauri bundles: .deb stays, AppImage is additive."""

from pathlib import Path

PUBLISH = Path(__file__).resolve().parent.parent / ".github" / "workflows" / "publish.yml"


def test_linux_bundles_deb_and_appimage() -> None:
    text = PUBLISH.read_text(encoding="utf-8")
    assert "--bundles deb,appimage" in text
    assert "deb/*_amd64.deb" in text
    assert "appimage/*_amd64.AppImage" in text
    assert "APPIMAGE_EXTRACT_AND_RUN" in text
    assert "NO_STRIP" in text
    # .deb path must not be replaced by appimage-only
    assert "--bundles appimage" not in text.replace("--bundles deb,appimage", "")
