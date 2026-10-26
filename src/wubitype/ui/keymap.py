"""键位图查看窗口：缩放、全屏和键盘操作。"""

from __future__ import annotations

from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
gi.require_version("GdkPixbuf", "2.0")

from gi.repository import Gdk, GdkPixbuf, GLib, Gtk  # noqa: E402

MIN_SCALE = 0.15
MAX_SCALE = 1.5
ZOOM_STEP = 1.25


class KeymapWindow(Gtk.Window):
    def __init__(
        self,
        parent: Gtk.Window,
        image_path: Path,
        title: str,
    ) -> None:
        super().__init__(transient_for=parent, modal=True, title=title)
        self.image_path = Path(image_path)
        self.set_default_size(1100, 760)

        info = GdkPixbuf.Pixbuf.get_file_info(str(self.image_path))
        if info[0] is None:
            raise ValueError(f"无法读取键位图：{self.image_path}")
        self._image_width = max(1, int(info[1]))
        self._image_height = max(1, int(info[2]))
        self._scale = 1.0
        self._fit_mode = True

        header = Gtk.HeaderBar()
        header.set_show_title_buttons(True)
        self.set_titlebar(header)

        zoom_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        zoom_out = Gtk.Button(label="−")
        zoom_out.set_tooltip_text("缩小（-）")
        zoom_out.add_css_class("flat")
        zoom_out.connect("clicked", lambda _b: self._zoom_by(1 / ZOOM_STEP))
        zoom_box.append(zoom_out)

        self.zoom_label = Gtk.Label(label="100%")
        self.zoom_label.set_width_chars(5)
        self.zoom_label.add_css_class("meta")
        zoom_box.append(self.zoom_label)

        zoom_in = Gtk.Button(label="+")
        zoom_in.set_tooltip_text("放大（+）")
        zoom_in.add_css_class("flat")
        zoom_in.connect("clicked", lambda _b: self._zoom_by(ZOOM_STEP))
        zoom_box.append(zoom_in)

        fit = Gtk.Button(label="适应")
        fit.set_tooltip_text("适应窗口（0）")
        fit.add_css_class("flat")
        fit.connect("clicked", lambda _b: self._fit())
        zoom_box.append(fit)

        actual = Gtk.Button(label="1:1")
        actual.set_tooltip_text("实际大小（1）")
        actual.add_css_class("flat")
        actual.connect("clicked", lambda _b: self._zoom_to(1.0))
        zoom_box.append(actual)
        header.pack_start(zoom_box)

        self.scroller = Gtk.ScrolledWindow()
        self.scroller.set_policy(
            Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC
        )
        self.scroller.set_overlay_scrolling(False)
        self.scroller.set_hexpand(True)
        self.scroller.set_vexpand(True)

        self.picture = Gtk.Picture()
        self.picture.set_can_shrink(False)
        self.picture.set_content_fit(Gtk.ContentFit.CONTAIN)
        self.picture.set_halign(Gtk.Align.CENTER)
        self.picture.set_valign(Gtk.Align.CENTER)
        self.scroller.set_child(self.picture)
        self.set_child(self.scroller)

        controller = Gtk.EventControllerKey()
        controller.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        controller.connect("key-pressed", self._on_key_pressed)
        self.add_controller(controller)

        GLib.idle_add(self._initial_fit)

    def _initial_fit(self) -> bool:
        self._fit()
        return False

    def _fit(self) -> None:
        self._fit_mode = True
        width = self.get_width() or 1100
        height = self.get_height() or 760
        available_w = max(320, width - 48)
        available_h = max(320, height - 100)
        scale = min(
            available_w / self._image_width,
            available_h / self._image_height,
            1.0,
        )
        self._apply_scale(scale)

    def _zoom_by(self, factor: float) -> None:
        self._fit_mode = False
        self._apply_scale(self._scale * factor)

    def _zoom_to(self, scale: float) -> None:
        self._fit_mode = False
        self._apply_scale(scale)

    def _apply_scale(self, scale: float) -> None:
        scale = max(MIN_SCALE, min(MAX_SCALE, scale))
        width = max(1, int(self._image_width * scale))
        height = max(1, int(self._image_height * scale))
        try:
            pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(
                str(self.image_path), width, height, True
            )
        except GLib.Error:
            return
        if pixbuf is None:
            return
        texture = Gdk.Texture.new_for_pixbuf(pixbuf)
        self.picture.set_paintable(texture)
        self.picture.set_size_request(
            pixbuf.get_width(), pixbuf.get_height()
        )
        self._scale = scale
        self.zoom_label.set_label(f"{round(scale * 100)}%")

    def _scroll(self, dx: int, dy: int) -> None:
        h = self.scroller.get_hadjustment()
        v = self.scroller.get_vadjustment()
        if dx:
            h.set_value(max(0, h.get_value() + dx))
        if dy:
            v.set_value(max(0, v.get_value() + dy))

    def _on_key_pressed(self, _controller, keyval, _keycode, state) -> bool:
        control = bool(state & Gdk.ModifierType.CONTROL_MASK)
        if keyval == Gdk.KEY_Escape or (
            control and Gdk.keyval_to_lower(keyval) == Gdk.KEY_w
        ):
            self.close()
            return True
        if keyval == Gdk.KEY_F11:
            if self.is_fullscreen():
                self.unfullscreen()
            else:
                self.fullscreen()
            if self._fit_mode:
                GLib.timeout_add(120, lambda: (self._fit(), False)[1])
            return True
        if keyval in (Gdk.KEY_plus, Gdk.KEY_equal, Gdk.KEY_KP_Add):
            self._zoom_by(ZOOM_STEP)
            return True
        if keyval in (Gdk.KEY_minus, Gdk.KEY_KP_Subtract):
            self._zoom_by(1 / ZOOM_STEP)
            return True
        if keyval in (Gdk.KEY_0, Gdk.KEY_KP_0):
            self._fit()
            return True
        if keyval in (Gdk.KEY_1, Gdk.KEY_KP_1):
            self._zoom_to(1.0)
            return True
        if keyval in (Gdk.KEY_Left, Gdk.KEY_KP_Left):
            self._scroll(-60, 0)
            return True
        if keyval in (Gdk.KEY_Right, Gdk.KEY_KP_Right):
            self._scroll(60, 0)
            return True
        if keyval in (Gdk.KEY_Up, Gdk.KEY_KP_Up):
            self._scroll(0, -60)
            return True
        if keyval in (Gdk.KEY_Down, Gdk.KEY_KP_Down):
            self._scroll(0, 60)
            return True
        return False
