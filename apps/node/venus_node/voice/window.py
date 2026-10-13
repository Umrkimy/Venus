from venus_node.commands.pc import IS_WINDOWS


def orb_window():
    """The orb window class for this OS. Imported late: it needs a real desktop."""
    if IS_WINDOWS:
        from venus_node.voice.circle import Circle
    else:
        from venus_node.voice.circle_linux import Circle
    return Circle
