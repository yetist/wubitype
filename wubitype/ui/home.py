"""首页：选择练习模式、范围、题量与提示。"""

from __future__ import annotations

from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")

from gi.repository import Gio, GLib, Gtk  # noqa: E402

from ..config import Config  # noqa: E402
from ..data import CHAR_SCOPES, PHRASE_SCOPES, is_hanzi  # noqa: E402
from ..keymap import MNEMONIC_ROWS  # noqa: E402
from ..passage import read_text_file  # noqa: E402
from ..poems import POEMS  # noqa: E402
from ..schemes import VERSION_IDS, VERSION_LABELS, get_scheme  # noqa: E402
from .widgets import card, dropdown, label  # noqa: E402

MODE_LABELS = ("单字练习", "词组练习", "混合练习", "键位专项", "文稿跟打")
MODE_IDS = ("char", "phrase", "mixed", "keys", "text")
HINT_LABELS = ("显示完整编码", "逐码提示（推荐）", "关闭提示")
HINT_IDS = ("full", "next", "none")
TEXT_CUSTOM_ID = "custom"
TEXT_SCOPE_OPTIONS: tuple[tuple[str, str], ...] = tuple(
    (poem.label, f"poem-{poem.number:02d}") for poem in POEMS
) + (("自定义文本文件…", TEXT_CUSTOM_ID),)


class HomeView(Gtk.ScrolledWindow):
    def __init__(self, config: Config, on_start) -> None:
        super().__init__()
        self.config = config
        self.on_start = on_start
        self._updating = False
        self._scope_ids: list[str] = []
        self._scope_options: tuple[tuple[str, str], ...] = CHAR_SCOPES
        self._file_dialog_open = False
        self._scheme = get_scheme(config.version)

        self.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.set_vexpand(True)

        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        outer.set_halign(Gtk.Align.CENTER)
        outer.set_size_request(760, -1)
        outer.set_margin_top(24)
        outer.set_margin_bottom(24)
        outer.set_margin_start(28)
        outer.set_margin_end(28)
        self.set_child(outer)

        heading = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.title_label = label("五笔打字通", "title-xl")
        self.title_label.set_xalign(0)
        subtitle = label(
            "支持五笔 98 版 / 86 版码元规则，边打边记键位。选择范围后即可开始。",
            "subtitle",
        )
        subtitle.set_xalign(0)
        subtitle.set_wrap(True)
        heading.append(self.title_label)
        heading.append(subtitle)
        outer.append(heading)

        form = card(spacing=18)
        grid = Gtk.Grid(column_spacing=24, row_spacing=14)
        grid.set_hexpand(True)
        form.append(grid)

        row = 0
        grid.attach(self._field_label("编码版本"), 0, row, 1, 1)
        self.version_dd = dropdown(
            list(VERSION_LABELS), VERSION_IDS.index(config.version)
        )
        self.version_dd.set_hexpand(True)
        self.version_dd.connect("notify::selected", self._on_version_changed)
        grid.attach(self.version_dd, 1, row, 1, 1)

        row += 1
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
        self.custom_label = self._field_label("自定义文稿")
        grid.attach(self.custom_label, 0, row, 1, 1)
        self.custom_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        self.custom_button = Gtk.Button(label="选择文本文件…")
        self.custom_button.connect("clicked", lambda _button: self._choose_text_file())
        self.custom_file_label = label("尚未选择文件", "hint")
        self.custom_file_label.set_hexpand(True)
        self.custom_box.append(self.custom_button)
        self.custom_box.append(self.custom_file_label)
        grid.attach(self.custom_box, 1, row, 1, 1)

        row += 1
        self.count_label = self._field_label("每组题数")
        grid.attach(self.count_label, 0, row, 1, 1)
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
        self._update_mode_visibility()

        best_card = card(spacing=4)
        best_title = label("最佳记录", "stat-label")
        best_title.set_xalign(0)
        self.best_label = label("", "best-value")
        self.best_label.set_xalign(0)
        self.best_note = label("按版本和练习模式分别保存", "hint")
        self.best_note.set_xalign(0)
        best_card.append(best_title)
        best_card.append(self.best_label)
        best_card.append(self.best_note)
        outer.append(best_card)

        self.mnemonic_card = card(spacing=8)
        mnemonic_header = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL, spacing=8
        )
        self.mnemonic_title = label("字根助记口诀", "card-title")
        self.mnemonic_title.set_xalign(0)
        self.mnemonic_title.set_hexpand(True)
        mnemonic_header.append(self.mnemonic_title)
        mnemonic_note = label("按横、竖、撇、捺、折五区排列", "hint")
        mnemonic_header.append(mnemonic_note)
        self.mnemonic_card.append(mnemonic_header)
        self.mnemonic_grid = Gtk.Grid(column_spacing=12, row_spacing=4)
        self.mnemonic_card.append(self.mnemonic_grid)
        outer.append(self.mnemonic_card)
        self._rebuild_mnemonic_grid()

        tips = label(
            "快捷键：Tab 跳过 · Backspace 退格 · 空格 提交简码 · Esc 结束本组",
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
    def _on_version_changed(self, drop: Gtk.DropDown, _pspec) -> None:
        if self._updating:
            return
        self.config.version = VERSION_IDS[drop.get_selected()]
        self._scheme = get_scheme(self.config.version)
        self._rebuild_scope()
        self._rebuild_mnemonic_grid()
        self.refresh_best()

    def _on_mode_changed(self, drop: Gtk.DropDown, _pspec) -> None:
        if self._updating:
            return
        self.config.mode = MODE_IDS[drop.get_selected()]
        self._rebuild_scope()
        self._update_mode_visibility()
        self.refresh_best()

    def _rebuild_scope(self) -> None:
        self._updating = True
        mode = self.config.mode
        if mode == "phrase":
            options = PHRASE_SCOPES
            target = self.config.phrase_scope
        elif mode == "text":
            options = TEXT_SCOPE_OPTIONS
            target = self.config.text_scope
        elif mode == "keys":
            options = self._scheme.key_scope_options
            target = self.config.key_scope
        else:
            options = CHAR_SCOPES
            target = self.config.char_scope
        self._scope_options = options
        self._scope_ids = [scope_id for _label, scope_id in options]
        self.scope_dd.set_model(
            Gtk.StringList.new([scope_label for scope_label, _sid in options])
        )
        self.scope_dd.set_enable_search(mode in ("text", "keys"))
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
        elif self.config.mode == "text":
            self.config.text_scope = scope_id
            self._update_custom_row()
            if scope_id == TEXT_CUSTOM_ID and not self.config.text_path:
                GLib.idle_add(self._choose_text_file)
        elif self.config.mode == "keys":
            self.config.key_scope = scope_id
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
        self.config.version = VERSION_IDS[self.version_dd.get_selected()]
        self._scheme = get_scheme(self.config.version)
        self.config.mode = MODE_IDS[self.mode_dd.get_selected()]
        selected = self.scope_dd.get_selected()
        if 0 <= selected < len(self._scope_ids):
            scope_id = self._scope_ids[selected]
            if self.config.mode == "phrase":
                self.config.phrase_scope = scope_id
            elif self.config.mode == "text":
                self.config.text_scope = scope_id
            elif self.config.mode == "keys":
                self.config.key_scope = scope_id
            else:
                self.config.char_scope = scope_id
        self.config.count = self.count_spin.get_value_as_int()
        self.config.hint = HINT_IDS[self.hint_dd.get_selected()]
        self.config.extended = self.extended_switch.get_active()

    # -- 文稿跟打 -----------------------------------------------------
    def _rebuild_mnemonic_grid(self) -> None:
        while (child := self.mnemonic_grid.get_first_child()) is not None:
            self.mnemonic_grid.remove(child)
        self.mnemonic_title.set_label(
            f"字根助记口诀 · {self._scheme.label}"
        )
        for row_index, (zone, letters) in enumerate(MNEMONIC_ROWS):
            zone_label = label(zone, "zone-label")
            zone_label.set_xalign(0)
            zone_label.set_valign(Gtk.Align.CENTER)
            self.mnemonic_grid.attach(zone_label, 0, row_index, 1, 1)
            for column, letter in enumerate(letters):
                cell = Gtk.Box(
                    orientation=Gtk.Orientation.HORIZONTAL, spacing=4
                )
                key_label = label(letter.upper(), "mnemonic-key")
                key_label.set_valign(Gtk.Align.CENTER)
                text_label = label(
                    self._scheme.mnemonics[letter], "mnemonic-text"
                )
                text_label.set_xalign(0)
                text_label.set_valign(Gtk.Align.CENTER)
                cell.append(key_label)
                cell.append(text_label)
                self.mnemonic_grid.attach(
                    cell, column + 1, row_index, 1, 1
                )

    # -- 文稿跟打 -----------------------------------------------------
    def _update_mode_visibility(self) -> None:
        is_text = self.config.mode == "text"
        self.count_label.set_visible(not is_text)
        self.count_spin.set_visible(not is_text)
        self.custom_label.set_visible(is_text)
        self.custom_box.set_visible(is_text)
        self.start_button.set_label("开始跟打" if is_text else "开始练习")
        self._update_custom_row()

    def _update_custom_row(self) -> None:
        if self.config.text_scope != TEXT_CUSTOM_ID:
            self.custom_file_label.set_label(
                "内置《小学生必备古诗 80 首》· 可加载自定义文本"
            )
            return
        path = self.config.text_path
        if not path or not Path(path).is_file():
            self.custom_file_label.set_label("尚未选择文件")
            return
        name = Path(path).name
        if len(name) > 30:
            name = name[:27] + "…"
        self.custom_file_label.set_label(f"已选择：{name}")

    def _select_scope(self, scope_id: str) -> None:
        if scope_id not in self._scope_ids:
            return
        self._updating = True
        self.scope_dd.set_selected(self._scope_ids.index(scope_id))
        self._updating = False
        self._update_custom_row()

    def _choose_text_file(self) -> bool:
        if self._file_dialog_open:
            return False
        dialog = Gtk.FileDialog(title="选择文稿文件")
        filters = Gio.ListStore.new(Gtk.FileFilter)
        text_filter = Gtk.FileFilter()
        text_filter.set_name("文本文件")
        for pattern in ("*.txt", "*.md", "*.text"):
            text_filter.add_pattern(pattern)
        filters.append(text_filter)
        dialog.set_filters(filters)
        dialog.set_default_filter(text_filter)
        self._file_dialog_open = True
        root = self.get_root()
        parent = root if isinstance(root, Gtk.Window) else None
        dialog.open(parent, None, self._on_text_file_chosen)
        return False

    def _on_text_file_chosen(self, dialog: Gtk.FileDialog, result) -> None:
        self._file_dialog_open = False
        try:
            file = dialog.open_finish(result)
        except GLib.Error:
            return
        if file is None or file.get_path() is None:
            return
        self._apply_text_path(Path(file.get_path()))

    def _apply_text_path(self, path: Path) -> bool:
        try:
            text = read_text_file(path)
        except OSError as error:
            self._alert("无法读取文件", str(error))
            return False
        if not any(is_hanzi(char, self.config.extended) for char in text):
            self._alert(
                "文件中没有可练习的汉字",
                "请选择包含中文的 UTF-8 或 GB18030 文本文件。",
            )
            return False
        self.config.text_path = str(path)
        self.config.text_scope = TEXT_CUSTOM_ID
        self._select_scope(TEXT_CUSTOM_ID)
        return True

    def _alert(self, message: str, detail: str = "") -> None:
        dialog = Gtk.AlertDialog(message=message, detail=detail)
        dialog.set_buttons(["知道了"])
        root = self.get_root()
        if isinstance(root, Gtk.Window):
            dialog.show(root)
        else:
            dialog.show()

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
