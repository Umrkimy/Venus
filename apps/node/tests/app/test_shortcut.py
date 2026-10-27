from PIL import Image

from venus_node.app.shortcut import venus_icon, write_icon


def test_icon_is_a_crimson_tile_with_a_white_v():
    icon = venus_icon(256)

    assert icon.size == (256, 256)
    # Rounded corner: see-through. Middle top: crimson. Where the V's strokes meet: white.
    assert icon.getpixel((2, 2))[3] == 0
    red, green, blue, alpha = icon.getpixel((128, 30))
    assert alpha == 255 and red > 150 and green < 60
    assert icon.getpixel((128, 175)) == (255, 255, 255, 255)


def test_square_icon_has_no_see_through_corners():
    assert venus_icon(180, square=True).getpixel((0, 0))[3] == 255


def test_write_icon_saves_every_windows_size(tmp_path):
    path = write_icon(tmp_path / "data" / "venus.ico")

    with Image.open(path) as saved:
        assert (16, 16) in saved.info["sizes"]
        assert (256, 256) in saved.info["sizes"]
