import os
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw

from venus_node.app.autostart_windows import background_python

NODE_DIRECTORY = Path(__file__).resolve().parent.parent.parent
ROSE_DARK = (159, 18, 57, 255)  # Tailwind rose-800
ROSE = (225, 29, 72, 255)  # rose-600, the web theme's crimson (D-44)
WHITE = (255, 255, 255, 255)


def venus_icon(size: int, square: bool = False) -> Image.Image:
    """The Venus app icon: a white V on a crimson tile. square: no rounded corners (phones round it)."""
    big = 1024
    image = Image.new("RGBA", (big, big), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    tile = (0, 0, big, big)
    # Top-to-bottom crimson, a little darker at the bottom.
    span = tile[3] - tile[1]
    gradient = Image.new("RGBA", (big, big))
    gradient_draw = ImageDraw.Draw(gradient)
    for y in range(big):
        share = min(max((y - tile[1]) / span, 0), 1)
        colour = tuple(round(a + (b - a) * share) for a, b in zip(ROSE, ROSE_DARK))
        gradient_draw.line([(0, y), (big, y)], fill=colour)
    mask = Image.new("L", (big, big), 0)
    ImageDraw.Draw(mask).rounded_rectangle(tile, radius=0 if square else int(span * 0.23), fill=255)
    image.paste(gradient, (0, 0), mask)
    # The V: two strokes meeting at the bottom.
    left, right = tile[0] + span * 0.27, tile[0] + span * 0.73
    top, bottom = tile[1] + span * 0.27, tile[1] + span * 0.75
    middle = (left + right) / 2
    stroke = span * 0.11
    draw.polygon(
        [
            (left - stroke / 2, top), (left + stroke / 2, top), (middle, bottom - stroke * 1.25),
            (right - stroke / 2, top), (right + stroke / 2, top), (middle + stroke * 0.55, bottom),
            (middle - stroke * 0.55, bottom),
        ],
        fill=WHITE,
    )
    return image.resize((size, size), Image.LANCZOS)


def write_icon(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    venus_icon(256).save(path, sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    return path


SHORTCUT_SCRIPT = """
$shell = New-Object -ComObject WScript.Shell
foreach ($folder in @([Environment]::GetFolderPath('Desktop'), [Environment]::GetFolderPath('Programs'))) {
    $link = $shell.CreateShortcut((Join-Path $folder 'Venus.lnk'))
    $link.TargetPath = $env:VENUS_TARGET
    $link.Arguments = 'venus.pyw'
    $link.WorkingDirectory = $env:VENUS_FOLDER
    $link.IconLocation = $env:VENUS_ICON
    $link.Description = 'Start Venus'
    $link.Save()
}
"""


def create_shortcuts(node_directory: Path = NODE_DIRECTORY) -> None:
    """A "Venus" icon on the desktop and in the Start menu that starts everything."""
    if sys.platform != "win32":
        print("Shortcuts are made on Windows only. On Linux use start-venus.sh.")
        return
    icon = write_icon(node_directory / "data" / "venus.ico")
    # Paths go in as environment variables, so spaces and quotes can't break the script.
    env = {
        **os.environ,
        "VENUS_TARGET": str(background_python()),
        "VENUS_FOLDER": str(node_directory),
        "VENUS_ICON": str(icon),
    }
    subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", SHORTCUT_SCRIPT],
        env=env,
        check=True,
    )
    print("Added Venus to the desktop and the Start menu.")


if __name__ == "__main__":
    create_shortcuts()
