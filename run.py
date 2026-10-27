"""OpenLDAC Launcher.

Runs the OpenLDAC application with proper path resolution.
"""

from __future__ import annotations
import os
import sys
from pathlib import Path

# Ensure package root is in sys.path
root_dir = Path(__file__).resolve().parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from src.app import OpenLDACController
from src.gui.main_window import MainWindow

def main() -> None:
    controller = OpenLDACController()
    controller.initialize()
    
    app = MainWindow(controller)
    app.mainloop()

if __name__ == "__main__":
    main()
