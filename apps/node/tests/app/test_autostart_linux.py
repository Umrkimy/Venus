from pathlib import Path, PurePosixPath

from venus_node.app import autostart_linux as autostart

# Plain files, so these run on Windows too.


def test_autostart_dir_follows_xdg_config_home():
    assert autostart.autostart_dir({"XDG_CONFIG_HOME": "/home/me/.cfg"}) == Path("/home/me/.cfg/autostart")


def test_launch_command_quotes_paths_and_starts_hidden():
    command = autostart.launch_command(
        PurePosixPath("/home/me/My Venus/python"), PurePosixPath("/home/me/My Venus/venus.pyw")
    )

    assert command == '"/home/me/My Venus/python" "/home/me/My Venus/venus.pyw" --hidden'


def test_quote_escapes_what_the_desktop_spec_says():
    assert autostart.quote('a"b`c$d\\e') == '"a\\"b\\`c\\$d\\\\e"'


def test_enable_writes_a_desktop_file_and_disable_removes_it(tmp_path: Path):
    key = str(tmp_path / "autostart" / "venus.desktop")
    assert autostart.is_enabled(key) is False

    autostart.enable('"python" "venus.pyw" --hidden', key)

    text = Path(key).read_text(encoding="utf-8")
    assert "Exec=\"python\" \"venus.pyw\" --hidden\n" in text
    assert "Type=Application\n" in text
    assert autostart.is_enabled(key) is True

    autostart.disable(key)

    assert autostart.is_enabled(key) is False
    autostart.disable(key)  # Already off is fine.


def test_switched_off_in_the_desktop_settings_counts_as_off(tmp_path: Path):
    key = tmp_path / "venus.desktop"
    key.write_text("[Desktop Entry]\nName=Venus\nHidden=true\n", encoding="utf-8")

    assert autostart.is_enabled(str(key)) is False
