import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")

from gi.repository import Gtk  # noqa: E402


def label(text: str = "", css: str | None = None, **kwargs) -> Gtk.Label:
    widget = Gtk.Label(label=text, **kwargs)
    if css:
        widget.add_css_class(css)
    return widget


def card(child: Gtk.Widget | None = None, *, spacing: int = 12) -> Gtk.Box:
    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=spacing)
    box.add_css_class("card")
    if child is not None:
        box.append(child)
    return box


def stat_block(caption: str) -> tuple[Gtk.Box, Gtk.Label]:
    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1)
    box.set_hexpand(True)
    box.set_halign(Gtk.Align.CENTER)
    value = label("—", "stat-value")
    value.set_xalign(0.5)
    caption_label = label(caption, "stat-label")
    caption_label.set_xalign(0.5)
    box.append(value)
    box.append(caption_label)
    return box, value


def dropdown(labels: list[str], selected: int = 0) -> Gtk.DropDown:
    widget = Gtk.DropDown.new_from_strings(labels)
    widget.set_selected(selected)
    return widget


def separator() -> Gtk.Separator:
    separator = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
    separator.add_css_class("spacer-line")
    return separator
