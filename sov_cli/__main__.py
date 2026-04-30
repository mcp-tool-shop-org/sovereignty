"""Allow running as `python -m sov_cli` (used by PyInstaller)."""

from sov_cli.main import app

if __name__ == "__main__":
    app()
