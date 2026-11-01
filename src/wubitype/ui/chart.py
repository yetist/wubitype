"""速度曲线：用折线展示最近若干组练习的打字速度。"""

from __future__ import annotations

import math
from typing import Sequence

import cairo
import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
gi.require_version("Pango", "1.0")
gi.require_version("PangoCairo", "1.0")

from gi.repository import Gdk, Gtk, Pango, PangoCairo  # noqa: E402

ACCENT = (0.208, 0.518, 0.894)
PAD_X = 12.0
PAD_TOP = 18.0
PAD_BOTTOM = 12.0
DOT_R = 3.0
LAST_DOT_R = 4.5
LINE_W = 2.2


class SpeedCurve(Gtk.DrawingArea):
    def __init__(self) -> None:
        super().__init__()
        self.set_content_width(600)
        self.set_content_height(140)
        self.set_hexpand(True)
        self.set_draw_func(self._draw)
        self._points: list[float] = []

    def set_points(self, values: Sequence[float]) -> None:
        self._points = [max(0.0, float(value)) for value in values]
        self.queue_draw()

    # -- 绘制 ---------------------------------------------------------
    def _draw(
        self,
        _area: Gtk.DrawingArea,
        cr: cairo.Context,
        width: int,
        height: int,
    ) -> None:
        base = self.get_color()
        points = self._points
        if not points:
            self._text(
                cr,
                "暂无历史成绩，完成一组练习后这里会出现速度曲线",
                width / 2,
                height / 2,
                12,
                base,
                alpha=0.55,
                center=True,
                middle=True,
            )
            return

        count = len(points)
        left, right = PAD_X, width - PAD_X
        bottom = height - PAD_BOTTOM
        plot_h = max(1.0, bottom - PAD_TOP)

        lo, hi = min(points), max(points)
        if hi - lo < 1e-6:
            # 所有速度相同：给上下各留一格余量，让曲线落在中间
            margin = max(hi * 0.15, 1.0)
            lo, hi = lo - margin, hi + margin
        span = hi - lo

        xs: list[float] = []
        ys: list[float] = []
        for index, value in enumerate(points):
            if count == 1:
                x = (left + right) / 2
            else:
                x = left + (right - left) * index / (count - 1)
            ratio = (value - lo) / span
            y = PAD_TOP + (1.0 - ratio) * plot_h
            xs.append(x)
            ys.append(y)

        # 底线
        cr.set_source_rgba(base.red, base.green, base.blue, 0.15)
        cr.set_line_width(1.0)
        cr.move_to(left, bottom)
        cr.line_to(right, bottom)
        cr.stroke()

        # 曲线下方淡色填充
        cr.set_source_rgba(*ACCENT, 0.10)
        cr.move_to(xs[0], ys[0])
        for x, y in zip(xs[1:], ys[1:]):
            cr.line_to(x, y)
        cr.line_to(xs[-1], bottom)
        cr.line_to(xs[0], bottom)
        cr.close_path()
        cr.fill()

        # 折线
        cr.set_source_rgba(*ACCENT, 0.95)
        cr.set_line_width(LINE_W)
        cr.set_line_join(cairo.LineJoin.ROUND)
        cr.set_line_cap(cairo.LineCap.ROUND)
        cr.move_to(xs[0], ys[0])
        for x, y in zip(xs[1:], ys[1:]):
            cr.line_to(x, y)
        cr.stroke()

        # 数据点
        for index, (x, y) in enumerate(zip(xs, ys)):
            last = index == count - 1
            cr.set_source_rgba(*ACCENT, 1.0)
            cr.arc(x, y, LAST_DOT_R if last else DOT_R, 0, 2 * math.pi)
            cr.fill()

    def _text(
        self,
        cr,
        text: str,
        x: float,
        y: float,
        size: float,
        color: Gdk.RGBA | tuple[float, float, float],
        *,
        alpha: float = 1.0,
        center: bool = False,
        middle: bool = False,
    ) -> None:
        layout = self.create_pango_layout(text)
        desc = Pango.FontDescription()
        desc.set_family("Sans")
        desc.set_absolute_size(size * Pango.SCALE)
        layout.set_font_description(desc)
        text_w, _text_h = layout.get_pixel_size()
        if center:
            x -= text_w / 2
        if middle:
            y -= text_h / 2
        if isinstance(color, Gdk.RGBA):
            cr.set_source_rgba(color.red, color.green, color.blue, alpha)
        else:
            cr.set_source_rgba(*color, alpha)
        cr.move_to(x, y)
        PangoCairo.show_layout(cr, layout)
