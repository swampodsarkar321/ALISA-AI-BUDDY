"""ALISA command entry: `alisa` / `alisa --version`."""

import sys


def main(argv=None):
    args = list(argv) if argv is not None else sys.argv[1:]
    if "--version" in args or "-V" in args:
        try:
            from importlib.metadata import version
            print("ALISA", version("alisa-assistant"))
        except Exception:
            print("ALISA (dev)")
        return 0
    if "--help" in args or "-h" in args:
        print("ALISA — AI Desktop Assistant\n\nUsage:\n"
              "  alisa            Launch the dashboard\n"
              "  alisa --version  Show version")
        return 0
    from .gui import main as run_gui
    run_gui()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
