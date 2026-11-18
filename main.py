"""
Main Entrypoint for JXL Batch Converter.
Launches the Graphical User Interface (GUI) by default, or the CLI if arguments are supplied.
"""

import sys


def main():
    # If no arguments or explicitly --gui, start GUI
    if len(sys.argv) == 1 or (len(sys.argv) == 2 and sys.argv[1] == "--gui"):
        from src.gui import launch_gui
        launch_gui()
    else:
        from src.cli import run_cli
        # Filter out --cli flag if passed
        args = [arg for arg in sys.argv[1:] if arg != "--cli"]
        run_cli(args)


if __name__ == "__main__":
    main()
