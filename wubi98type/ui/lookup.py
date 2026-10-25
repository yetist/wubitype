"""编码反查窗口：输入编码，列出对应的单字与词组。"""

from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")

from gi.repository import Gdk, GLib, Gtk  # noqa: E402

from ..lookup import LookupItem, ReverseLookup, clean_code  # noqa: E402
from .widgets import label  # noqa: E402

DISPLAY_LIMIT = 150


class LookupDialog(Gtk.Window):
    def __init__(self, parent: Gtk.Window, lookup: ReverseLookup) -> None:
        super().__init__(transient_for=parent, modal=True, title="编码反查")
        self.lookup = lookup
        self._updating = False

        self.set_default_size(760, 640)
        self.set_size_request(560, 420)

        header = Gtk.HeaderBar()
        header.set_show_title_buttons(True)
        self.set_titlebar(header)

        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        outer.set_margin_top(16)
        outer.set_margin_bottom(16)
        outer.set_margin_start(20)
        outer.set_margin_end(20)
        self.set_child(outer)

        description = label(
            "输入 1–4 位五笔编码（a–y），支持简码、全码和词组。"
            "精确匹配显示在前，其余为同前缀编码。",
            "hint",
        )
        description.set_xalign(0)
        description.set_wrap(True)
        outer.append(description)

        search_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        self.search = Gtk.SearchEntry()
        self.search.set_placeholder_text("输入编码，如 trng、khk、a")
        self.search.set_hexpand(True)
        self.search.connect("changed", self._on_search_changed)
        search_row.append(self.search)

        self.phrase_switch = Gtk.Switch(active=True)
        self.phrase_switch.set_valign(Gtk.Align.CENTER)
        self.phrase_switch.connect("notify::active", self._on_filter_changed)
        phrase_label = label("包含词组", "hint")
        phrase_label.set_valign(Gtk.Align.CENTER)
        search_row.append(self.phrase_switch)
        search_row.append(phrase_label)
        outer.append(search_row)

        self.status = label("输入编码开始查询", "hint")
        self.status.set_xalign(0)
        outer.append(self.status)

        self.listbox = Gtk.ListBox()
        self.listbox.add_css_class("lookup-list")
        self.listbox.set_selection_mode(Gtk.SelectionMode.NONE)
        scroller = Gtk.ScrolledWindow()
        scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroller.set_overlay_scrolling(False)
        scroller.set_vexpand(True)
        scroller.add_css_class("lookup-scroller")
        scroller.set_child(self.listbox)
        outer.append(scroller)

        footer = label("点击结果可复制汉字", "hint")
        footer.set_xalign(0.5)
        outer.append(footer)

        key_controller = Gtk.EventControllerKey()
        key_controller.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        key_controller.connect("key-pressed", self._on_key_pressed)
        self.add_controller(key_controller)

        GLib.idle_add(self.search.grab_focus)

    def _on_key_pressed(self, _controller, keyval, _keycode, _state) -> bool:
        if keyval == Gdk.KEY_Escape:
            self.close()
            return True
        return False

    def _on_search_changed(self, _entry: Gtk.SearchEntry) -> None:
        if self._updating:
            return
        raw = self.search.get_text()
        cleaned = clean_code(raw)
        if cleaned != raw:
            self._updating = True
            self.search.set_text(cleaned)
            self._updating = False
        self._search(cleaned)

    def _on_filter_changed(self, _switch: Gtk.Switch, _pspec) -> None:
        self._search(clean_code(self.search.get_text()))

    def _search(self, query: str) -> None:
        if not query:
            self._clear_rows()
            self.status.set_label("输入编码开始查询")
            return

        result = self.lookup.search(
            query,
            include_phrases=self.phrase_switch.get_active(),
            limit=DISPLAY_LIMIT,
        )
        self._clear_rows()
        if result.total == 0:
            self.status.set_label(f"未找到编码「{query.upper()}」对应的字词")
            return

        exact_note = f"精确 {result.exact_total} 条"
        prefix_note = f"前缀 {result.prefix_total} 条"
        parts = []
        if result.exact_total:
            parts.append(exact_note)
        if result.prefix_total:
            parts.append(prefix_note)
        if result.truncated:
            parts.append(f"仅显示前 {DISPLAY_LIMIT} 条")
        self.status.set_label(" · ".join(parts))

        if result.exact:
            self._add_section("精确匹配")
            for item in result.exact:
                self._add_item(item)
        if result.prefix:
            self._add_section("同前缀编码")
            for item in result.prefix:
                self._add_item(item)

    def _clear_rows(self) -> None:
        while (child := self.listbox.get_first_child()) is not None:
            self.listbox.remove(child)

    def _add_section(self, text: str) -> None:
        row = Gtk.ListBoxRow()
        row.set_activatable(False)
        row.set_selectable(False)
        row.add_css_class("lookup-section-row")
        section = label(text, "lookup-section")
        section.set_xalign(0)
        section.set_margin_top(10)
        section.set_margin_bottom(2)
        section.set_margin_start(10)
        row.set_child(section)
        self.listbox.append(row)

    def _add_item(self, item: LookupItem) -> None:
        row = Gtk.ListBoxRow()
        row.set_activatable(True)
        row.set_tooltip_text("点击复制汉字")
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        box.set_margin_top(5)
        box.set_margin_bottom(5)
        box.set_margin_start(10)
        box.set_margin_end(10)

        code = label(item.code.upper(), "lookup-code")
        code.set_size_request(64, -1)
        word = label(item.text, "lookup-word")
        kind = label(item.kind_label, "lookup-kind")
        spacer = Gtk.Box()
        spacer.set_hexpand(True)
        copy_hint = label("点击复制", "lookup-copy")
        for widget in (code, word, kind, spacer, copy_hint):
            box.append(widget)
        row.set_child(box)
        row.connect("activate", self._on_row_activated, item)
        self.listbox.append(row)

    def _on_row_activated(self, _row: Gtk.ListBoxRow, item: LookupItem) -> None:
        self.get_clipboard().set(item.text)
        self.status.set_label(f"已复制「{item.text}」 {item.code.upper()}")
