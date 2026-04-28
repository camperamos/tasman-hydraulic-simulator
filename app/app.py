import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
APP_DIR = Path(__file__).resolve().parent

sys.path.insert(0, str(ROOT_DIR))
sys.path.insert(0, str(APP_DIR))

from ui import render_ui

if __name__ == "__main__":
    render_ui()