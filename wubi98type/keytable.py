"""从键位总图中截取单个键位的图形。"""

from __future__ import annotations

import os
from pathlib import Path

import gi

gi.require_version("Gdk", "4.0")
gi.require_version("GdkPixbuf", "2.0")

from gi.repository import Gdk, GdkPixbuf, GLib  # noqa: E402

#: wubi98-table.png 中 25 个键位图形的像素范围 ``(x, y, width, height)``。
KEY_BOXES: dict[str, tuple[int, int, int, int]] = {
    # 第一行：Q W E R T Y U I O P
    "q": (36, 52, 313, 384),
    "w": (379, 52, 313, 384),
    "e": (722, 52, 313, 384),
    "r": (1065, 52, 313, 384),
    "t": (1408, 52, 313, 384),
    "y": (1750, 52, 314, 384),
    "u": (2094, 52, 313, 384),
    "i": (2436, 52, 313, 384),
    "o": (2779, 52, 313, 384),
    "p": (3122, 52, 313, 384),
    # 第二行：A S D F G H J K L
    "a": (189, 466, 314, 384),
    "s": (533, 466, 313, 384),
    "d": (876, 466, 313, 384),
    "f": (1220, 466, 313, 384),
    "g": (1564, 466, 313, 384),
    "h": (1907, 466, 313, 384),
    "j": (2251, 466, 313, 384),
    "k": (2595, 466, 313, 384),
    "l": (2938, 466, 313, 384),
    # 第三行：X C V B N M
    "x": (716, 881, 313, 384),
    "c": (1060, 881, 313, 384),
    "v": (1404, 881, 313, 384),
    "b": (1748, 881, 313, 384),
    "n": (2092, 881, 314, 384),
    "m": (2437, 881, 313, 384),
}

TABLE_SIZE = (3478, 1858)


def find_table_image() -> Path | None:
    """按与词库相同的思路寻找 wubi98-table.png。"""
    candidates: list[Path] = []
    explicit = os.environ.get("WUBI98TYPE_TABLE")
    if explicit:
        candidates.append(Path(explicit).expanduser())
    data_dir = os.environ.get("WUBI98TYPE_DATA")
    if data_dir:
        candidates.append(Path(data_dir).expanduser() / "wubi98-table.png")
    package_dir = Path(__file__).resolve().parent
    candidates.extend(
        (
            Path.cwd() / "wubi98-table.png",
            package_dir.parent / "wubi98-table.png",
            package_dir / "wubi98-table.png",
            Path.home() / ".local/share/wubi98type/wubi98-table.png",
        )
    )
    return next((path for path in candidates if path.is_file()), None)


class KeyTableImages:
    """按需裁剪并缓存键位图，避免每次切换按键都读盘。"""

    def __init__(self, path: Path | None = None) -> None:
        self.path = path or find_table_image()
        self._pixbuf: GdkPixbuf.Pixbuf | None = None
        self._textures: dict[tuple[str, tuple[int, int] | None], Gdk.Texture] = {}
        self._failed = self.path is None

    def texture(
        self,
        letter: str | None,
        size: tuple[int, int] | None = None,
    ) -> Gdk.Texture | None:
        if not letter or self._failed:
            return None
        letter = letter.lower()
        box = KEY_BOXES.get(letter)
        if box is None:
            return None
        cache_key = (letter, size)
        cached = self._textures.get(cache_key)
        if cached is not None:
            return cached
        if self._pixbuf is None:
            try:
                self._pixbuf = GdkPixbuf.Pixbuf.new_from_file(str(self.path))
            except (GLib.Error, OSError):
                self._failed = True
                return None
        x, y, width, height = box
        try:
            cropped = self._pixbuf.new_subpixbuf(x, y, width, height)
        except (GLib.Error, ValueError):
            return None
        if size is not None and (width, height) != size:
            cropped = cropped.scale_simple(
                size[0], size[1], GdkPixbuf.InterpType.HYPER
            )
            if cropped is None:
                return None
        texture = Gdk.Texture.new_for_pixbuf(cropped)
        self._textures[cache_key] = texture
        return texture
