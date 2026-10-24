"""虚拟键盘：显示 98 版键位、码元和当前应敲的键。"""

from __future__ import annotations

import math

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
gi.require_version("Pango", "1.0")
gi.require_version("PangoCairo", "1.0")

from gi.repository import Gdk, GLib, Gtk, Pango, PangoCairo  # noqa: E402

from ..keymap import KEYMAP, ROWS, ZONE_COLORS  # noqa: E402

KEY_W = 72
KEY_H = 74
GAP = 7
PAD = 6
ROW_OFFSETS = (0, 38, 96)
ACCENT = (0.208, 0.518, 0.894)
SUCCESS = (0.180, 0.760, 0.490)
ERROR = (0.878, 0.106, 0.141)


def _rounded_rect(cr, x: float, y: float, w: float, h: float, r: float) -> None:
    r = min(r, w / 2, h / 2)
    cr.new_sub_path()
    cr.arc(x + w - r, y + r, r, -math.pi / 2, 0)
    cr.arc(x + w - r, y + h - r, r, 0, math.pi / 2)
    cr.arc(x + r, y + h - r, r, math.pi / 2, math.pi)
    cr.arc(x + r, y + r, r, math.pi, 1.5 * math.pi)
    cr.close_path()


class KeyboardView(Gtk.DrawingArea):
    def __init__(self) -> None:
        super().__init__()
        self.set_content_width(10 * KEY_W + 9 * GAP + 2 * PAD)
        self.set_content_height(3 * KEY_H + 2 * GAP + 2 * PAD)
        self.set_draw_func(self._draw)
        self.set_hexpand(True)
        self._expected: str | None = None
        self._flash: dict[str, bool] = {}
        self._flash_token = 0

    def set_expected(self, letter: str | None) -> None:
        if letter == self._expected:
            return
        self._expected = letter
        self.queue_draw()

    def flash(self, letter: str, correct: bool) -> None:
        self._flash[letter] = correct
        self._flash_token += 1
        token = self._flash_token
        self.queue_draw()

        def clear() -> bool:
            if token == self._flash_token:
                self._flash.clear()
                self.queue_draw()
            return False

        GLib.timeout_add(200, clear)

    def reset(self) -> None:
        self._expected = None
        self._flash.clear()
        self.queue_draw()

    # -- 绘制 ---------------------------------------------------------
    def _draw(self, _area: Gtk.DrawingArea, cr, width: int, height: int) -> None:
        board_w = 10 * KEY_W + 9 * GAP + 2 * PAD
        board_h = 3 * KEY_H + 2 * GAP + 2 * PAD
        x0 = max(PAD, (width - board_w) / 2) + PAD
        y0 = max(PAD, (height - board_h) / 2) + PAD
        base = self.get_color()

        for row_index, row in enumerate(ROWS):
            offset = ROW_OFFSETS[row_index]
            for col, letter in enumerate(row):
                x = x0 + offset + col * (KEY_W + GAP)
                y = y0 + row_index * (KEY_H + GAP)
                self._draw_key(cr, x, y, letter, base)

        z_x = x0 + ROW_OFFSETS[2] + 6 * (KEY_W + GAP) + 16
        z_y = y0 + 2 * (KEY_H + GAP)
        self._draw_unused_key(cr, z_x, z_y, "z", base)

    def _draw_key(self, cr, x: float, y: float, letter: str, base: Gdk.RGBA) -> None:
        info = KEYMAP[letter]
        zone_rgb = ZONE_COLORS[info.zone]
        expected = letter == self._expected
        flash = self._flash.get(letter)

        fill_alpha = 0.28 if expected else 0.16
        r, g, b = zone_rgb
        if flash is not None:
            r, g, b = SUCCESS if flash else ERROR
            fill_alpha = 0.42
        cr.set_source_rgba(r, g, b, fill_alpha)
        _rounded_rect(cr, x, y, KEY_W, KEY_H, 10)
        cr.fill()

        if flash is not None:
            border = SUCCESS if flash else ERROR
            cr.set_source_rgba(*border, 0.95)
            line_width = 2.5
        elif expected:
            cr.set_source_rgba(*ACCENT, 1.0)
            line_width = 2.5
        else:
            cr.set_source_rgba(base.red, base.green, base.blue, 0.20)
            line_width = 1.0
        cr.set_line_width(line_width)
        _rounded_rect(cr, x, y, KEY_W, KEY_H, 10)
        cr.stroke()

        # 键位字母与区位号
        self._text(cr, letter.upper(), x + 8, y + 4, 14, base, bold=True)
        self._text(
            cr,
            info.code,
            x + KEY_W - 7,
            y + 7,
            8.5,
            base,
            alpha=0.55,
            right=True,
        )

        # 键名与其余码元
        name_color = ACCENT if expected else (base.red, base.green, base.blue)
        self._text(
            cr,
            info.name,
            x + KEY_W / 2,
            y + 23,
            17,
            name_color,
            bold=True,
            center=True,
        )
        rest = info.radicals[1:]
        if rest:
            half = (len(rest) + 1) // 2
            lines = ("".join(rest[:half]), "".join(rest[half:]))
            for index, line in enumerate(lines):
                if not line:
                    continue
                self._text(
                    cr,
                    line,
                    x + KEY_W / 2,
                    y + 45 + index * 12,
                    9.5,
                    base,
                    alpha=0.72,
                    center=True,
                )

    def _draw_unused_key(
        self, cr, x: float, y: float, letter: str, base: Gdk.RGBA
    ) -> None:
        cr.set_source_rgba(base.red, base.green, base.blue, 0.05)
        _rounded_rect(cr, x, y, KEY_W, KEY_H, 10)
        cr.fill()
        cr.set_source_rgba(base.red, base.green, base.blue, 0.12)
        cr.set_line_width(1.0)
        _rounded_rect(cr, x, y, KEY_W, KEY_H, 10)
        cr.stroke()
        self._text(cr, letter.upper(), x + 8, y + 4, 13, base, alpha=0.3, bold=True)
        self._text(
            cr,
            "未用",
            x + KEY_W / 2,
            y + 32,
            10,
            base,
            alpha=0.35,
            center=True,
        )

    def _text(
        self,
        cr,
        text: str,
        x: float,
        y: float,
        size: float,
        color: Gdk.RGBA | tuple[float, float, float],
        *,
        bold: bool = False,
        alpha: float = 1.0,
        center: bool = False,
        right: bool = False,
    ) -> None:
        layout = self.create_pango_layout(text)
        desc = Pango.FontDescription()
        desc.set_family("Sans")
        desc.set_absolute_size(size * Pango.SCALE)
        if bold:
            desc.set_weight(Pango.Weight.BOLD)
        layout.set_font_description(desc)
        text_w, _text_h = layout.get_pixel_size()
        if center:
            x -= text_w / 2
        elif right:
            x -= text_w
        if isinstance(color, Gdk.RGBA):
            cr.set_source_rgba(color.red, color.green, color.blue, alpha)
        else:
            cr.set_source_rgba(*color, alpha)
        cr.move_to(x, y)
        PangoCairo.show_layout(cr, layout)
