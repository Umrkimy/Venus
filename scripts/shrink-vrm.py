"""Make a VRM model smaller: big textures down to 1024 px.

    python scripts/shrink-vrm.py <original.vrm> <smaller.vrm> [--keep NAME ...]

A VRM is a glTF binary (.glb): a JSON part saying what is where, then one
block of bytes holding meshes and images. This resizes the images, packs the
bytes again and fixes the "where" numbers. Textures named in --keep (part of
the name, e.g. "eyes") stay as they are. Needs Pillow (pip install pillow).
"""

import argparse
import io
import json
import struct
from pathlib import Path

from PIL import Image

MAX_SIZE = 1024
JSON_CHUNK = 0x4E4F534A  # "JSON"
BIN_CHUNK = 0x004E4942  # "BIN\0"


def pad(data: bytes, filler: bytes) -> bytes:
    # glTF wants every block to start on a multiple of 4 bytes.
    return data + filler * (-len(data) % 4)


def read_glb(path: Path) -> tuple[dict, bytes]:
    data = path.read_bytes()
    json_length = struct.unpack_from("<I", data, 12)[0]
    gltf = json.loads(data[20 : 20 + json_length])
    bin_start = 20 + json_length + 8
    bin_length = struct.unpack_from("<I", data, 20 + json_length)[0]
    return gltf, data[bin_start : bin_start + bin_length]


def write_glb(path: Path, gltf: dict, binary: bytes) -> None:
    text = pad(json.dumps(gltf, separators=(",", ":")).encode(), b" ")
    binary = pad(binary, b"\0")
    total = 12 + 8 + len(text) + 8 + len(binary)
    path.write_bytes(
        struct.pack("<III", 0x46546C67, 2, total)  # "glTF", version 2
        + struct.pack("<II", len(text), JSON_CHUNK)
        + text
        + struct.pack("<II", len(binary), BIN_CHUNK)
        + binary
    )


def shrink_image(data: bytes) -> bytes:
    image = Image.open(io.BytesIO(data))
    if max(image.size) <= MAX_SIZE:
        return data
    image.thumbnail((MAX_SIZE, MAX_SIZE), Image.Resampling.LANCZOS)
    out = io.BytesIO()
    image.save(out, format="PNG", optimize=True)
    return out.getvalue()


def shrink(source: Path, target: Path, keep: list[str]) -> None:
    gltf, binary = read_glb(source)
    views = gltf["bufferViews"]
    chunks = [binary[v.get("byteOffset", 0) : v.get("byteOffset", 0) + v["byteLength"]] for v in views]

    for image in gltf.get("images", []):
        name = image.get("name", "")
        if "bufferView" not in image or any(word.lower() in name.lower() for word in keep):
            continue
        index = image["bufferView"]
        before = len(chunks[index])
        chunks[index] = shrink_image(chunks[index])
        print(f"{name}: {before / 1e6:.2f} MB -> {len(chunks[index]) / 1e6:.2f} MB")

    # Lay the pieces end to end again, each at a new offset.
    packed = b""
    for view, chunk in zip(views, chunks):
        packed = pad(packed, b"\0")
        view["byteOffset"] = len(packed)
        view["byteLength"] = len(chunk)
        packed += chunk
    gltf["buffers"][0]["byteLength"] = len(pad(packed, b"\0"))
    write_glb(target, gltf, packed)
    print(f"{source.stat().st_size / 1e6:.1f} MB -> {target.stat().st_size / 1e6:.1f} MB")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("source", type=Path)
    parser.add_argument("target", type=Path)
    parser.add_argument("--keep", nargs="*", default=[], help="texture names to leave alone")
    arguments = parser.parse_args()
    shrink(arguments.source, arguments.target, arguments.keep)
