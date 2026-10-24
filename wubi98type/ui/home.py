"""首页：选择练习模式、范围、题量与提示。"""

from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")

from gi.repository import Gtk  # noqa: E402

from ..config import Config  # noqa: E402
from ..data import CHAR_SCOPES, PHRASE_SCOPES  # noqa: E402
from ..keymap import MNEMONICS, MNEMONIC_ROWS  # noqa: E402
from .widgets import card, dropdown, label  # noqa: E402

MODE_LABELS = ("单字练习", "词组练习", "混合练习")
MODE_IDS = ("char", "phrase", "mixed")
HINT_LABELS = ("显示完整编码", "逐码提示（推荐）", "关闭提示")
HINT_IDS = ("full", "next", "none")


class HomeView(Gtk.ScrolledWindow):
    def __init__(self, config: Config, on_start) -> None:
        super().__init__()
        self.config = config
        self.on_start = on_start
        self._updating = False
        self._scope_ids: list[str] = []
        self._scope_options: tuple[tuple[str, str], ...] = CHAR_SCOPES

        self.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.set_vexpand(True)

        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        outer.set_halign(Gtk.Align.CENTER)
        outer.set_size_request(760, -1)
        outer.set_margin_top(34)
        outer.set_margin_bottom(34)
        outer.set_margin_start(28)
        outer.set_margin_end(28)
        self.set_child(outer)

        heading = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        title = label("五笔 98 打字练习", "title-xl")
        title.set_xalign(0)
        subtitle = label(
            "按 98 版码元规则出题，边打边记键位。选择范围后即可开始。",
            "subtitle",
        )
        subtitle.set_xalign(0)
        subtitle.set_wrap(True)
        heading.append(title)
        heading.append(subtitle)
        outer.append(heading)

        form = card(spacing=18)
        grid = Gtk.Grid(column_spacing=24, row_spacing=14)
        grid.set_hexpand(True)
        form.append(grid)

        row = 0
        grid.attach(self._field_label("练习模式"), 0, row, 1, 1)
        self.mode_dd = dropdown(list(MODE_LABELS), MODE_IDS.index(config.mode))
        self.mode_dd.set_hexpand(True)
        self.mode_dd.connect("notify::selected", self._on_mode_changed)
        grid.attach(self.mode_dd, 1, row, 1, 1)

        row += 1
        grid.attach(self._field_label("练习范围"), 0, row, 1, 1)
        self.scope_dd = dropdown([])
        self.scope_dd.set_hexpand(True)
        self.scope_dd.connect("notify::selected", self._on_scope_changed)
        grid.attach(self.scope_dd, 1, row, 1, 1)
        self._rebuild_scope()

        row += 1
        grid.attach(self._field_label("每组题数"), 0, row, 1, 1)
        adjustment = Gtk.Adjustment(
            value=config.count, lower=1, upper=500, step_increment=5, page_increment=25
        )
        self.count_spin = Gtk.SpinButton(adjustment=adjustment, climb_rate=1, digits=0)
        self.count_spin.set_hexpand(False)
        self.count_spin.set_halign(Gtk.Align.START)
        self.count_spin.set_size_request(120, -1)
        self.count_spin.connect("value-changed", self._on_count_changed)
        grid.attach(self.count_spin, 1, row, 1, 1)

        row += 1
        grid.attach(self._field_label("编码提示"), 0, row, 1, 1)
        self.hint_dd = dropdown(list(HINT_LABELS), HINT_IDS.index(config.hint))
        self.hint_dd.set_hexpand(True)
        self.hint_dd.connect("notify::selected", self._on_hint_changed)
        grid.attach(self.hint_dd, 1, row, 1, 1)

        row += 1
        grid.attach(self._field_label("扩展字库"), 0, row, 1, 1)
        extended_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        self.extended_switch = Gtk.Switch(active=config.extended)
        self.extended_switch.set_halign(Gtk.Align.START)
        self.extended_switch.connect("notify::active", self._on_extended_changed)
        extended_hint = label("包含扩展 A/B 区生僻字（使用 large 码表）", "hint")
        extended_box.append(self.extended_switch)
        extended_box.append(extended_hint)
        grid.attach(extended_box, 1, row, 1, 1)

        outer.append(form)

        self.start_button = Gtk.Button(label="开始练习")
        self.start_button.add_css_class("suggested-action")
        self.start_button.add_css_class("start-button")
        self.start_button.set_halign(Gtk.Align.FILL)
        self.start_button.connect("clicked", lambda _button: self.on_start())
        outer.append(self.start_button)

        best_card = card(spacing=4)
        best_title = label("最佳记录", "stat-label")
        best_title.set_xalign(0)
        self.best_label = label("", "best-value")
        self.best_label.set_xalign(0)
        self.best_note = label("按练习模式分别保存", "hint")
        self.best_note.set_xalign(0)
        best_card.append(best_title)
        best_card.append(self.best_label)
        best_card.append(self.best_note)
        outer.append(best_card)

        mnemonic_card = card(spacing=8)
        mnemonic_header = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL, spacing=8
        )
        mnemonic_title = label("字根助记口诀", "card-title")
        mnemonic_title.set_xalign(0)
        mnemonic_title.set_hexpand(True)
        mnemonic_header.append(mnemonic_title)
        mnemonic_note = label("按横、竖、撇、捺、折五区排列", "hint")
        mnemonic_header.append(mnemonic_note)
        mnemonic_card.append(mnemonic_header)

        mnemonic_grid = Gtk.Grid(column_spacing=12, row_spacing=6)
        for row_index, (zone, letters) in enumerate(MNEMONIC_ROWS):
            zone_label = label(zone, "zone-label")
            zone_label.set_xalign(0)
            zone_label.set_valign(Gtk.Align.CENTER)
            mnemonic_grid.attach(zone_label, 0, row_index, 1, 1)
            for column, letter in enumerate(letters):
                cell = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
                key_label = label(letter.upper(), "mnemonic-key")
                key_label.set_valign(Gtk.Align.CENTER)
                text_label = label(MNEMONICS[letter], "mnemonic-text")
                text_label.set_xalign(0)
                text_label.set_valign(Gtk.Align.CENTER)
                cell.append(key_label)
                cell.append(text_label)
                mnemonic_grid.attach(cell, column + 1, row_index, 1, 1)
        mnemonic_card.append(mnemonic_grid)
        outer.append(mnemonic_card)

        tips = label(
            "快捷键：Tab 跳过 · Backspace 退格 · Esc 结束本组",
            "hint",
        )
        tips.set_xalign(0.5)
        outer.append(tips)

        self.refresh_best()

    @staticmethod
    def _field_label(text: str) -> Gtk.Label:
        widget = label(text, "field-label")
        widget.set_xalign(0)
        widget.set_valign(Gtk.Align.CENTER)
        return widget

    # -- 事件 ---------------------------------------------------------
    def _on_mode_changed(self, drop: Gtk.DropDown, _pspec) -> None:
        if self._updating:
            return
        self.config.mode = MODE_IDS[drop.get_selected()]
        self._rebuild_scope()
        self.refresh_best()

    def _rebuild_scope(self) -> None:
        self._updating = True
        phrase = self.config.mode == "phrase"
        options = PHRASE_SCOPES if phrase else CHAR_SCOPES
        self._scope_options = options
        self._scope_ids = [scope_id for _label, scope_id in options]
        self.scope_dd.set_model(
            Gtk.StringList.new([scope_label for scope_label, _sid in options])
        )
        target = (
            self.config.phrase_scope if phrase else self.config.char_scope
        )
        if target not in self._scope_ids:
            target = self._scope_ids[0]
        self.scope_dd.set_selected(self._scope_ids.index(target))
        self._updating = False

    def _on_scope_changed(self, drop: Gtk.DropDown, _pspec) -> None:
        if self._updating:
            return
        selected = drop.get_selected()
        if not (0 <= selected < len(self._scope_ids)):
            return
        scope_id = self._scope_ids[selected]
        if self.config.mode == "phrase":
            self.config.phrase_scope = scope_id
        else:
            self.config.char_scope = scope_id

    def _on_count_changed(self, spin: Gtk.SpinButton) -> None:
        if not self._updating:
            self.config.count = spin.get_value_as_int()

    def _on_hint_changed(self, drop: Gtk.DropDown, _pspec) -> None:
        if self._updating:
            return
        self.config.hint = HINT_IDS[drop.get_selected()]

    def _on_extended_changed(self, switch: Gtk.Switch, _pspec) -> None:
        if not self._updating:
            self.config.extended = switch.get_active()

    # -- 对外 ---------------------------------------------------------
    def sync_config(self) -> None:
        """从控件读回配置，避免因信号顺序漏掉改动。"""
        self.config.mode = MODE_IDS[self.mode_dd.get_selected()]
        selected = self.scope_dd.get_selected()
        if 0 <= selected < len(self._scope_ids):
            scope_id = self._scope_ids[selected]
            if self.config.mode == "phrase":
                self.config.phrase_scope = scope_id
            else:
                self.config.char_scope = scope_id
        self.config.count = self.count_spin.get_value_as_int()
        self.config.hint = HINT_IDS[self.hint_dd.get_selected()]
        self.config.extended = self.extended_switch.get_active()

    def refresh_best(self) -> None:
        best = self.config.best_for(self.config.mode)
        if not best:
            self.best_label.set_label("还没有记录，先来一组吧")
            return
        speed = float(best.get("speed", 0))
        accuracy = float(best.get("accuracy", 0))
        self.best_label.set_label(f"{speed:.0f} 字/分 · {accuracy:.1f}% 准确率")

    def scope_caption(self) -> str:
        selected = self.scope_dd.get_selected()
        if 0 <= selected < len(self._scope_options):
            return self._scope_options[selected][0]
        return "全部"
