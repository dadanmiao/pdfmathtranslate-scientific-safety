"""Locate the persistent application and assets without user-specific paths."""
import os
from pathlib import Path
import sys

APP = Path(os.environ.get("PDF2ZH_APP_DIR", str(Path.home() / "Documents/Codex/DevTools/apps/PDFMathTranslate/2.9.0-safety-v1/pdf2zh")))
PACKAGES = APP / "site-packages"
if not PACKAGES.is_dir():
    raise RuntimeError("Install PDFMathTranslate or set PDF2ZH_APP_DIR to its pdf2zh directory.")
sys.path.insert(0, str(PACKAGES))
os.environ["PYTHONPATH"] = str(PACKAGES)
OUTPUT = Path(os.environ.get("PDF2ZH_TEST_OUTPUT", str(Path(__file__).resolve().parents[1] / "artifacts")))
OUTPUT.mkdir(parents=True, exist_ok=True)


def font_path(name):
    from babeldoc.assets.assets import get_font_and_metadata
    return Path(get_font_and_metadata(name)[0])
