"""编码查询窗口：编码反查与汉字查码。"""

from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")

from gi.repository import Gdk, GLib, Gtk  # noqa: E402

from ..encoding import Segment, WordIndex  # noqa: E402
from ..lookup import LookupItem, ReverseLookup, clean_code  # noqa: E402
from .widgets import label  # noqa: E402

DISPLAY_LIMIT = 150


class LookupDialog(Gtk.Window):
    def __init__(
        self,
        parent: Gtk.Window,
        lookup: ReverseLookup,
        words: WordIndex,
    ) -> None:
        super().__init__(transient_for=parent, modal=True, title="编码查询")
        self.lookup = lookup
        self.words = words
        self.set_title(f"编码查询 · {lookup.scheme.short_label}")
        self._updating = False
        self._minimal_code = ""
        self._full_code = ""
        self._nav_rows: list[tuple[Gtk.ListBoxRow, object]] = []
        self._nav_index: int | None = None

        self.set_default_size(800, 700)
        self.set_size_request(600, 460)

        header = Gtk.HeaderBar()
        header.set_show_title_buttons(True)
        self.set_titlebar(header)

        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        outer.set_margin_top(14)
        outer.set_margin_bottom(14)
        outer.set_margin_start(20)
        outer.set_margin_end(20)
        self.set_child(outer)

        self.stack = Gtk.Stack(
            transition_type=Gtk.StackTransitionType.CROSSFADE,
            transition_duration=120,
        )
        self.stack.set_vexpand(True)
        self.stack.connect("notify::visible-child", self._on_page_changed)
        switcher = Gtk.StackSwitcher(stack=self.stack)
        switcher.set_halign(Gtk.Align.CENTER)
        outer.append(switcher)
        outer.append(self.stack)

        self.stack.add_titled(self._build_encode_page(), "encode", "汉字查码")
        self.stack.add_titled(self._build_reverse_page(), "reverse", "编码反查")

        key_controller = Gtk.EventControllerKey()
        key_controller.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        key_controller.connect("key-pressed", self._on_key_pressed)
        self.add_controller(key_controller)

        GLib.idle_add(self._focus_current)

    # -- 页面 ---------------------------------------------------------
    def _build_reverse_page(self) -> Gtk.Widget:
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)

        description = label(
            "输入 1–4 位五笔编码（a–y），支持简码、全码和词组。"
            "精确匹配显示在前，其余为同前缀编码。",
            "hint",
        )
        description.set_xalign(0)
        description.set_wrap(True)
        page.append(description)

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
        page.append(search_row)

        self.status = label("输入编码开始查询", "hint")
        self.status.set_xalign(0)
        page.append(self.status)

        self.listbox = Gtk.ListBox()
        self.listbox.add_css_class("lookup-list")
        self.listbox.set_selection_mode(Gtk.SelectionMode.NONE)
        scroller = Gtk.ScrolledWindow()
        scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroller.set_overlay_scrolling(False)
        scroller.set_vexpand(True)
        scroller.add_css_class("lookup-scroller")
        scroller.set_child(self.listbox)
        page.append(scroller)
        self.reverse_scroller = scroller

        footer = label("点击结果可复制汉字", "hint")
        footer.set_xalign(0.5)
        page.append(footer)
        return page

    def _build_encode_page(self) -> Gtk.Widget:
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)

        description = label(
            "输入汉字、词组或句子（可用输入法输入或粘贴），"
            "按最长词组优先切分，并分别给出最少击键编码与全码。",
            "hint",
        )
        description.set_xalign(0)
        description.set_wrap(True)
        page.append(description)

        self.encode_search = Gtk.SearchEntry()
        self.encode_search.set_placeholder_text(
            "输入汉字、词组或句子，如 中国、计算机、我爱北京天安门"
        )
        self.encode_search.set_hexpand(True)
        self.encode_search.connect("changed", self._on_encode_changed)
        page.append(self.encode_search)

        self.encode_status = label("输入汉字或句子开始查码", "hint")
        self.encode_status.set_xalign(0)
        page.append(self.encode_status)

        self.encode_summary = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL, spacing=4
        )
        self.encode_summary.add_css_class("encode-summary")
        self.encode_summary.set_visible(False)

        self.minimal_caption = label("最少击键", "stat-label")
        self.minimal_caption.set_xalign(0)
        self.minimal_code_label = label("—", "encode-total-code")
        self.minimal_code_label.set_xalign(0)
        self.minimal_code_label.set_selectable(True)
        self.minimal_code_label.set_wrap(True)
        minimal_row = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL, spacing=10
        )
        minimal_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1)
        minimal_box.set_hexpand(True)
        minimal_box.append(self.minimal_caption)
        minimal_box.append(self.minimal_code_label)
        minimal_row.append(minimal_box)
        self.minimal_copy = Gtk.Button(label="复制")
        self.minimal_copy.add_css_class("flat")
        self.minimal_copy.set_valign(Gtk.Align.CENTER)
        self.minimal_copy.connect("clicked", lambda _b: self._copy_minimal())
        minimal_row.append(self.minimal_copy)
        self.encode_summary.append(minimal_row)

        self.full_caption = label("全码", "stat-label")
        self.full_caption.set_xalign(0)
        self.full_code_label = label("—", "encode-total-code-dim")
        self.full_code_label.set_xalign(0)
        self.full_code_label.set_selectable(True)
        self.full_code_label.set_wrap(True)
        full_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        full_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1)
        full_box.set_hexpand(True)
        full_box.append(self.full_caption)
        full_box.append(self.full_code_label)
        full_row.append(full_box)
        self.full_copy = Gtk.Button(label="复制")
        self.full_copy.add_css_class("flat")
        self.full_copy.set_valign(Gtk.Align.CENTER)
        self.full_copy.connect("clicked", lambda _b: self._copy_full())
        full_row.append(self.full_copy)
        self.encode_summary.append(full_row)
        self.full_row = full_row
        page.append(self.encode_summary)

        self.encode_list = Gtk.ListBox()
        self.encode_list.add_css_class("lookup-list")
        self.encode_list.set_selection_mode(Gtk.SelectionMode.NONE)
        scroller = Gtk.ScrolledWindow()
        scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroller.set_overlay_scrolling(False)
        scroller.set_vexpand(True)
        scroller.add_css_class("lookup-scroller")
        scroller.set_child(self.encode_list)
        page.append(scroller)
        self.encode_scroller = scroller

        self.encode_feedback = label("点击结果可复制编码", "hint")
        self.encode_feedback.set_xalign(0.5)
        page.append(self.encode_feedback)
        return page

    # -- 通用 ---------------------------------------------------------
    def _on_key_pressed(self, _controller, keyval, _keycode, state) -> bool:
        control = bool(state & Gdk.ModifierType.CONTROL_MASK)
        lowered = Gdk.keyval_to_lower(keyval)

        if control and lowered == Gdk.KEY_1:
            self.stack.set_visible_child_name("encode")
            self._focus_current()
            return True
        if control and lowered == Gdk.KEY_2:
            self.stack.set_visible_child_name("reverse")
            self._focus_current()
            return True
        if control and lowered == Gdk.KEY_l:
            self._focus_current()
            return True
        if keyval == Gdk.KEY_Escape:
            self.close()
            return True
        if keyval in (Gdk.KEY_Up, Gdk.KEY_KP_Up):
            return self._move_nav(-1)
        if keyval in (Gdk.KEY_Down, Gdk.KEY_KP_Down):
            return self._move_nav(1)
        if keyval in (Gdk.KEY_Return, Gdk.KEY_KP_Enter) or (
            control and lowered == Gdk.KEY_c
        ):
            if self._nav_index is not None:
                self._activate_nav()
                return True
        return False

    def _on_page_changed(self, _stack, _pspec) -> None:
        page = self.stack.get_visible_child_name()
        if page == "reverse" and hasattr(self, "search"):
            self._search(clean_code(self.search.get_text()))
        elif page == "encode" and hasattr(self, "encode_search"):
            self._on_encode_changed(self.encode_search)
        GLib.idle_add(self._focus_current)

    def _focus_current(self) -> bool:
        if self.stack.get_visible_child_name() == "encode":
            self.encode_search.grab_focus()
        else:
            self.search.grab_focus()
        return False

    def _reset_nav(self) -> None:
        for row, _action in self._nav_rows:
            row.remove_css_class("lookup-selected")
        self._nav_rows.clear()
        self._nav_index = None

    def _move_nav(self, delta: int) -> bool:
        if not self._nav_rows:
            return False
        if self._nav_index is None:
            index = 0 if delta > 0 else len(self._nav_rows) - 1
        else:
            index = max(
                0,
                min(len(self._nav_rows) - 1, self._nav_index + delta),
            )
        if index == self._nav_index:
            return True
        if self._nav_index is not None:
            self._nav_rows[self._nav_index][0].remove_css_class(
                "lookup-selected"
            )
        self._nav_index = index
        row = self._nav_rows[index][0]
        row.add_css_class("lookup-selected")
        self._ensure_row_visible(row)
        return True

    def _activate_nav(self) -> None:
        if self._nav_index is None:
            return
        _row, action = self._nav_rows[self._nav_index]
        action()

    def _ensure_row_visible(self, row: Gtk.ListBoxRow) -> None:
        scroller = (
            self.encode_scroller
            if self.stack.get_visible_child_name() == "encode"
            else self.reverse_scroller
        )
        adjustment = scroller.get_vadjustment()
        allocation = row.get_allocation()
        top = adjustment.get_value()
        bottom = top + adjustment.get_page_size()
        if allocation.y < top:
            adjustment.set_value(allocation.y)
        elif allocation.y + allocation.height > bottom:
            adjustment.set_value(
                allocation.y + allocation.height - adjustment.get_page_size()
            )

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

    # -- 编码反查 -----------------------------------------------------
    def _search(self, query: str) -> None:
        self._reset_nav()
        if not query:
            self._clear_rows(self.listbox)
            self.status.set_label("输入编码开始查询")
            return

        result = self.lookup.search(
            query,
            include_phrases=self.phrase_switch.get_active(),
            limit=DISPLAY_LIMIT,
        )
        self._clear_rows(self.listbox)
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
            self._add_section(self.listbox, "精确匹配")
            for item in result.exact:
                self._add_reverse_item(item)
        if result.prefix:
            self._add_section(self.listbox, "同前缀编码")
            for item in result.prefix:
                self._add_reverse_item(item)

    def _add_reverse_item(self, item: LookupItem) -> None:
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
        row.connect("activate", self._on_reverse_row_activated, item)
        self.listbox.append(row)
        self._nav_rows.append(
            (
                row,
                lambda row=row, item=item: self._on_reverse_row_activated(
                    row, item
                ),
            )
        )

    def _on_reverse_row_activated(
        self, _row: Gtk.ListBoxRow, item: LookupItem
    ) -> None:
        self.get_clipboard().set(item.text)
        self.status.set_label(f"已复制「{item.text}」 {item.code.upper()}")

    # -- 汉字查码 -----------------------------------------------------
    def _on_encode_changed(self, _entry: Gtk.SearchEntry) -> None:
        self._reset_nav()
        text = self.encode_search.get_text().strip()
        self._clear_rows(self.encode_list)
        if not text:
            self.encode_status.set_label("输入汉字或句子开始查码")
            self.encode_summary.set_visible(False)
            self.encode_feedback.set_label("点击结果可复制编码")
            return

        result = self.words.encode(text)
        self._minimal_code = result.minimal_code
        self._full_code = result.full_code
        self.encode_summary.set_visible(bool(result.segments))
        self.minimal_code_label.set_label(result.minimal_code_spaced or "—")
        self.full_code_label.set_label(result.full_code_spaced or "—")
        self.full_row.set_visible(
            bool(result.segments)
            and result.minimal_code != result.full_code
        )

        notes = [f"共 {len(result.segments)} 段", f"{result.char_count} 字"]
        if result.missing:
            notes.append(f"未识别 {len(result.missing)} 字")
        self.encode_status.set_label(" · ".join(notes))
        if not result.segments:
            self.encode_feedback.set_label("没有可编码的汉字")
            return

        self.encode_feedback.set_label("点击结果可复制编码")
        for segment in result.segments:
            self._add_encode_item(segment)
        if result.missing:
            warning = label(
                "未识别：" + "".join(result.missing), "feedback-bad"
            )
            warning.set_xalign(0)
            warning.set_margin_top(6)
            warning_row = Gtk.ListBoxRow()
            warning_row.set_activatable(False)
            warning_row.set_selectable(False)
            warning_row.set_child(warning)
            self.encode_list.append(warning_row)

    def _add_encode_item(self, segment: Segment) -> None:
        row = Gtk.ListBoxRow()
        row.set_activatable(True)
        row.set_tooltip_text("点击复制编码")
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        box.set_margin_top(5)
        box.set_margin_bottom(5)
        box.set_margin_start(10)
        box.set_margin_end(10)

        word = label(segment.text, "lookup-word")
        kind = label(segment.kind_label, "lookup-kind")

        code_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        code = label(segment.code.upper(), "lookup-code")
        code.set_xalign(0)
        code_box.append(code)
        if segment.full_code != segment.code:
            full = label(
                f"全码 {segment.full_code.upper()}", "encode-full-code"
            )
            full.set_xalign(0)
            code_box.append(full)

        spacer = Gtk.Box()
        spacer.set_hexpand(True)
        copy_hint = label("点击复制", "lookup-copy")
        for widget in (word, kind, spacer, code_box, copy_hint):
            box.append(widget)
        row.set_child(box)
        row.connect("activate", self._on_encode_row_activated, segment)
        self.encode_list.append(row)
        self._nav_rows.append(
            (
                row,
                lambda row=row, segment=segment: self._on_encode_row_activated(
                    row, segment
                ),
            )
        )

    def _on_encode_row_activated(
        self, _row: Gtk.ListBoxRow, segment: Segment
    ) -> None:
        self.get_clipboard().set(segment.code)
        self.encode_feedback.set_label(
            f"已复制「{segment.text}」的编码：{segment.code.upper()}"
        )

    def _copy_minimal(self) -> None:
        self._copy_code(self._minimal_code)

    def _copy_full(self) -> None:
        self._copy_code(self._full_code)

    def _copy_code(self, code: str) -> None:
        if not code:
            return
        self.get_clipboard().set(code)
        self.encode_feedback.set_label("已复制编码")

    # -- 列表辅助 -----------------------------------------------------
    @staticmethod
    def _clear_rows(listbox: Gtk.ListBox) -> None:
        while (child := listbox.get_first_child()) is not None:
            listbox.remove(child)

    def _add_section(self, listbox: Gtk.ListBox, text: str) -> None:
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
        listbox.append(row)
