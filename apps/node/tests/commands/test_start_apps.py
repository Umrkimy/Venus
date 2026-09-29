from venus_node.commands.start_apps import StartApp, parse_start_apps


def test_parse_start_apps_reads_name_and_app_id():
    raw_json = (
        '[{"Name":"Notepad","AppID":"Microsoft.WindowsNotepad_8wekyb3d8bbwe!App"},'
        '{"Name":"ELDEN RING","AppID":"steam://rungameid/1245620"}]'
    )

    apps = parse_start_apps(raw_json)

    assert apps == [
        StartApp(name="Notepad", app_id="Microsoft.WindowsNotepad_8wekyb3d8bbwe!App"),
        StartApp(name="ELDEN RING", app_id="steam://rungameid/1245620"),
    ]


def test_parse_start_apps_accepts_single_object():
    raw_json = '{"Name":"Notepad","AppID":"Microsoft.WindowsNotepad_8wekyb3d8bbwe!App"}'

    apps = parse_start_apps(raw_json)

    assert apps == [
        StartApp(name="Notepad", app_id="Microsoft.WindowsNotepad_8wekyb3d8bbwe!App"),
    ]


def test_parse_start_apps_returns_empty_for_blank_output():
    assert parse_start_apps("") == []