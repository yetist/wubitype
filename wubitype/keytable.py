"""从键位总图中截取单个键位的图形。"""

from __future__ import annotations

import os
from pathlib import Path

import gi

gi.require_version("Gdk", "4.0")
gi.require_version("GdkPixbuf", "2.0")

from gi.repository import Gdk, GdkPixbuf, GLib  # noqa: E402

from .schemes import get_scheme  # noqa: E402

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
KEY_BOXES_98 = KEY_BOXES
TABLE_SIZE_98 = TABLE_SIZE

#: wubi86-table.png 中 25 个键位图形的像素范围（含边框留白）。
KEY_BOXES_86: dict[str, tuple[int, int, int, int]] = {
    # 第一行：Q W E R T Y U I O P
    "q": (172, 277, 200, 244),
    "w": (392, 277, 200, 244),
    "e": (612, 277, 200, 244),
    "r": (828, 277, 200, 244),
    "t": (1048, 277, 200, 244),
    "y": (1316, 281, 196, 240),
    "u": (1532, 281, 200, 240),
    "i": (1752, 281, 200, 240),
    "o": (1972, 281, 200, 240),
    "p": (2192, 281, 200, 240),
    # 第二行：A S D F G H J K L
    "a": (264, 589, 200, 244),
    "s": (484, 589, 196, 244),
    "d": (704, 589, 196, 244),
    "f": (920, 589, 200, 244),
    "g": (1140, 589, 200, 244),
    "h": (1404, 589, 200, 244),
    "j": (1624, 589, 200, 244),
    "k": (1844, 589, 200, 244),
    "l": (2064, 589, 200, 244),
    # 第三行：X C V B N M
    "x": (584, 897, 196, 244),
    "c": (800, 897, 200, 244),
    "v": (1020, 897, 200, 244),
    "b": (1240, 897, 200, 244),
    "n": (1460, 897, 196, 244),
    "m": (1724, 897, 200, 244),
}
TABLE_SIZE_86 = (2560, 1743)

KEY_BOXES_BY_VERSION = {"98": KEY_BOXES_98, "86": KEY_BOXES_86}
TABLE_SIZE_BY_VERSION = {"98": TABLE_SIZE_98, "86": TABLE_SIZE_86}


def find_table_image(version: str = "98") -> Path | None:
    """按与词库相同的思路寻找对应版本的键位图。"""
    scheme = get_scheme(version)
    candidates: list[Path] = []
    explicit = os.environ.get("WUBITYPE_TABLE") or os.environ.get(
        "WUBI98TYPE_TABLE"
    )
    if explicit:
        candidates.append(Path(explicit).expanduser())
    data_dir = os.environ.get("WUBITYPE_DATA") or os.environ.get(
        "WUBI98TYPE_DATA"
    )
    if data_dir:
        candidates.append(Path(data_dir).expanduser() / scheme.table_image)
    package_dir = Path(__file__).resolve().parent
    candidates.extend(
        (
            Path.cwd() / scheme.table_image,
            package_dir.parent / scheme.table_image,
            package_dir / scheme.table_image,
            Path.home() / ".local/share/wubitype" / scheme.table_image,
            Path.home() / ".local/share/wubi98type" / scheme.table_image,
        )
    )
    return next((path for path in candidates if path.is_file()), None)


class KeyTableImages:
    """按需裁剪并缓存键位图，避免每次切换按键都读盘。"""

    def __init__(
        self,
        path: Path | None = None,
        *,
        version: str = "98",
    ) -> None:
        self.version = get_scheme(version).id
        self.path = path or find_table_image(self.version)
        self._boxes = KEY_BOXES_BY_VERSION[self.version]
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
        box = self._boxes.get(letter)
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
