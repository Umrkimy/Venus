TOOLS: list[dict] = [
    {
        "type": "function",
        "name": "open_app",
        "description": "Open an installed app on the owner's PC.",
        "parameters": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "App name, e.g. Spotify",
                }
            },
            "required": ["name"],
        },
    },
    {
        "type": "function",
        "name": "open_link",
        "description": "Open a website link in the owner's browser.",
        "parameters": {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "Website URL to open",
                }
            },
            "required": ["url"],
        },
    },
    {
        "type": "function",
        "name": "open_project",
        "description": "Open a project folder on the owner's PC.",
        "parameters": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Project name",
                }
            },
            "required": ["name"],
        },
    },
    {
        "type": "function",
        "name": "search_site",
        "description": "Search a specific website for the given words.",
        "parameters": {
            "type": "object",
            "properties": {
                "site": {
                    "type": "string",
                    "description": "Website to search, e.g. youtube",
                },
                "words": {
                    "type": "string",
                    "description": "Words to search for",
                },
            },
            "required": ["site", "words"],
        },
    },
    {
        "type": "function",
        "name": "control_home",
        "description": (
            "Control the owner's home: lights, plugs, the TV's volume, waking "
            "another PC, or this PC's volume and lock."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "device": {
                    "type": "string",
                    "description": "Device name from the home devices list, \"tv\", or \"pc\" for this PC",
                },
                "action": {
                    "type": "string",
                    "enum": [
                        "on", "off", "brightness", "color", "volume_up", "volume_down",
                        "volume_set", "mute", "unmute", "wake", "lock",
                    ],
                },
                "value": {
                    "type": "integer",
                    "description": "Brightness or volume from 0 to 100, only for brightness and volume_set",
                },
                "color": {
                    "type": "string",
                    "description": "Only for color: a color name like red or a hex like #ff8800",
                },
            },
            "required": ["device", "action"],
        },
    },
    {
        "type": "function",
        "name": "save_memory",
        "description": (
            "Remember a fact about the owner for future chats, when they "
            "tell you something about themselves or ask you to remember it."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "fact": {
                    "type": "string",
                    "description": "One short sentence, e.g. Owner likes lo-fi music",
                }
            },
            "required": ["fact"],
        },
    },
]


def tool_to_command(name: str, arguments: dict) -> str:
    """Turn Luna's tool choice into the text the rule parser understands."""
    if name == "open_app":
        return f"open {arguments['name']}"
    elif name == "open_link":
        return f"open {arguments['url']}"
    elif name == "open_project":
        return f"open project {arguments['name']}"
    elif name == "search_site":
        return f"{arguments['site']} {arguments['words']}"
    elif name == "control_home":
        return home_sentence(arguments)
    else:
        raise ValueError(f"Unknown tool: {name}")


def home_sentence(arguments: dict) -> str:
    """control_home as the sentence the home rules understand."""
    device = str(arguments["device"]).strip()
    action = arguments["action"]
    value = arguments.get("value")
    if action in ("on", "off"):
        return f"turn {action} {device}"
    if action == "brightness":
        return f"set {device} to {value}%"
    if action == "color":
        return f"set {device} to {arguments.get('color', '')}"
    if action in ("volume_up", "volume_down"):
        return f"{device} volume {action.removeprefix('volume_')}"
    if action == "volume_set":
        return f"set {device} volume to {value}"
    if action == "wake":
        return f"wake {device}"
    if action == "lock":
        return "lock pc"
    return f"{action} {device}"
