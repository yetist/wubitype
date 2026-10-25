"""应用入口。"""

from __future__ import annotations

import sys
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")

from gi.repository import Gdk, Gio, GLib, Gtk  # noqa: E402

from . import APP_ID  # noqa: E402
from .config import load_config, save_config  # noqa: E402
from .ui.window import MainWindow  # noqa: E402


class Application(Gtk.Application):
    def __init__(self) -> None:
        super().__init__(
            application_id=APP_ID,
            flags=Gio.ApplicationFlags.DEFAULT_FLAGS,
        )
        self.config = load_config()

    def do_startup(self) -> None:
        Gtk.Application.do_startup(self)
        GLib.set_application_name("五笔打字通")
        Gtk.Window.set_default_icon_name("input-keyboard")

        css_file = Path(__file__).with_name("style.css")
        if css_file.is_file():
            provider = Gtk.CssProvider()
            provider.load_from_path(str(css_file))
            display = Gdk.Display.get_default()
            if display is not None:
                Gtk.StyleContext.add_provider_for_display(
                    display,
                    provider,
                    Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
                )

    def do_activate(self) -> None:
        window = self.props.active_window
        if window is None:
            window = MainWindow(application=self, config=self.config)
        window.present()

    def do_shutdown(self) -> None:
        save_config(self.config)
        Gtk.Application.do_shutdown(self)


def main(argv: list[str] | None = None) -> int:
    app = Application()
    return app.run(argv if argv is not None else sys.argv)


if __name__ == "__main__":
    raise SystemExit(main())
