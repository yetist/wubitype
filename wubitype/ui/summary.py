"""结算页面：成绩、错题与后续操作。"""

from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")

from gi.repository import GLib, Gtk  # noqa: E402

from ..drill import Session  # noqa: E402
from .widgets import card, label  # noqa: E402


def _clock(seconds: float) -> str:
    seconds = int(max(0, seconds))
    return f"{seconds // 60}:{seconds % 60:02d}"


class SummaryView(Gtk.ScrolledWindow):
    def __init__(self, on_again, on_retry, on_home) -> None:
        super().__init__()
        self.on_again = on_again
        self.on_retry = on_retry
        self.on_home = on_home
        self.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.set_vexpand(True)

        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        outer.set_halign(Gtk.Align.CENTER)
        outer.set_size_request(760, -1)
        outer.set_margin_top(30)
        outer.set_margin_bottom(30)
        outer.set_margin_start(28)
        outer.set_margin_end(28)
        self.set_child(outer)

        title_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        self.title_label = label("本组完成", "title-xl")
        self.title_label.set_xalign(0)
        self.record_label = label("★ 新纪录", "record-badge")
        self.record_label.set_xalign(0)
        self.record_label.set_visible(False)
        title_box.append(self.title_label)
        title_box.append(self.record_label)
        outer.append(title_box)

        hero = card(spacing=0)
        hero_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=16)
        hero_row.set_homogeneous(True)
        speed_box, self.speed_value = self._hero("字/分", "速度")
        accuracy_box, self.accuracy_value = self._hero("%", "准确率")
        hero_row.append(speed_box)
        hero_row.append(accuracy_box)
        hero.append(hero_row)
        outer.append(hero)

        detail_card = card(spacing=0)
        grid = Gtk.Grid(column_spacing=8, row_spacing=16)
        grid.set_hexpand(True)
        self.details: dict[str, Gtk.Label] = {}
        entries = (
            ("用时", "time"),
            ("击键速度（键/分）", "key_speed"),
            ("击键数", "keys"),
            ("错误次数", "errors"),
            ("最长连击", "streak"),
            ("完成字数", "chars"),
        )
        for index, (caption, key) in enumerate(entries):
            block = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
            block.set_hexpand(True)
            block.set_halign(Gtk.Align.CENTER)
            value = label("—", "detail-value")
            value.set_xalign(0.5)
            caption_label = label(caption, "stat-label")
            caption_label.set_xalign(0.5)
            block.append(value)
            block.append(caption_label)
            grid.attach(block, index % 3, index // 3, 1, 1)
            self.details[key] = value
        detail_card.append(grid)
        outer.append(detail_card)

        mistake_card = card(spacing=8)
        mistake_header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.mistake_title = label("错题", "card-title")
        self.mistake_title.set_xalign(0)
        self.mistake_title.set_hexpand(True)
        mistake_header.append(self.mistake_title)
        mistake_card.append(mistake_header)

        self.mistake_area = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        scroller = Gtk.ScrolledWindow()
        scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroller.set_max_content_height(190)
        scroller.set_propagate_natural_height(True)
        scroller.set_child(self.mistake_area)
        mistake_card.append(scroller)
        self.mistake_empty = label("全部正确，非常棒！", "hint")
        self.mistake_empty.set_xalign(0)
        mistake_card.append(self.mistake_empty)
        outer.append(mistake_card)

        buttons = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        self.again_button = Gtk.Button(label="再来一组")
        self.again_button.add_css_class("suggested-action")
        self.again_button.add_css_class("start-button")
        self.again_button.set_hexpand(True)
        self.again_button.connect("clicked", lambda _b: self.on_again())
        self.retry_button = Gtk.Button(label="重练错题（R）")
        self.retry_button.add_css_class("start-button")
        self.retry_button.set_hexpand(True)
        self.retry_button.set_tooltip_text("快捷键：R")
        self.retry_button.connect("clicked", lambda _b: self.retry_mistakes())
        home_button = Gtk.Button(label="返回首页（Esc）")
        home_button.add_css_class("start-button")
        home_button.set_hexpand(True)
        home_button.set_tooltip_text("快捷键：Esc")
        home_button.connect("clicked", lambda _b: self.on_home())
        buttons.append(self.again_button)
        buttons.append(self.retry_button)
        buttons.append(home_button)
        outer.append(buttons)

        self.session: Session | None = None

    @staticmethod
    def _hero(unit: str, caption: str) -> tuple[Gtk.Box, Gtk.Label]:
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        box.set_hexpand(True)
        box.set_halign(Gtk.Align.CENTER)
        value_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        value_row.set_halign(Gtk.Align.CENTER)
        value = label("0", "hero-value")
        value_row.append(value)
        unit_label = label(unit, "hero-unit")
        unit_label.set_valign(Gtk.Align.END)
        unit_label.set_margin_bottom(10)
        value_row.append(unit_label)
        caption_label = label(caption, "stat-label")
        caption_label.set_xalign(0.5)
        box.append(value_row)
        box.append(caption_label)
        return box, value

    def show(self, session: Session, *, record: bool = False, aborted: bool = False) -> None:
        self.session = session
        self.title_label.set_label("本组已结束" if aborted else "本组完成")
        self.record_label.set_visible(bool(record and not aborted))
        self.speed_value.set_label(f"{session.speed:.0f}")
        self.accuracy_value.set_label(f"{session.accuracy:.1f}")
        self.details["time"].set_label(_clock(session.elapsed))
        self.details["key_speed"].set_label(f"{session.keystroke_speed:.0f}")
        self.details["keys"].set_label(str(session.keystrokes))
        self.details["errors"].set_label(str(session.errors))
        self.details["streak"].set_label(str(session.best_streak))
        self.details["chars"].set_label(str(session.chars_completed))
        self._fill_mistakes(session)

    def retry_mistakes(self) -> None:
        if self.retry_button.get_sensitive():
            self.on_retry()

    def _fill_mistakes(self, session: Session) -> None:
        while (child := self.mistake_area.get_first_child()) is not None:
            self.mistake_area.remove(child)

        groups: dict[tuple[str, str], list[int]] = {}
        for mistake in session.mistakes:
            key = (mistake.text, mistake.code)
            stats = groups.setdefault(key, [0, 0])
            stats[0] += mistake.errors
            if mistake.skipped:
                stats[1] = 1
        self.mistake_title.set_label(f"错题（{len(groups)}）")
        self.retry_button.set_sensitive(bool(groups))
        self.mistake_empty.set_visible(not groups)
        for (text, code), (errors, skipped) in groups.items():
            row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
            row.add_css_class("mistake-row")
            word = label(text, "mistake-word")
            word.set_xalign(0)
            code_label = label(code.upper(), "mistake-code")
            code_label.set_xalign(0)
            note_text = " · ".join(
                part
                for part in (
                    f"错 {errors} 次" if errors else "",
                    "跳过" if skipped else "",
                )
                if part
            ) or "已记录"
            note = label(note_text, "mistake-note")
            note.set_xalign(1)
            note.set_hexpand(True)
            row.append(word)
            row.append(code_label)
            row.append(note)
            self.mistake_area.append(row)
