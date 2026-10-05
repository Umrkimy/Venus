import sys

from venus_node.app.single import ask_to_quit


def main() -> None:
    """Ask the Venus tray app to quit cleanly (its icon goes away too)."""
    if ask_to_quit():
        print("Asked Venus to quit.")
    else:
        print("Venus isn't running.")
        sys.exit(1)


if __name__ == "__main__":
    main()
