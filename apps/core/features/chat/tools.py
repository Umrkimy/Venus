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
    else:
        raise ValueError(f"Unknown tool: {name}")
