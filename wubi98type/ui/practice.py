"""练习页面：显示题目、编码槽、统计和虚拟键盘。"""

from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")

from gi.repository import GLib, Gtk  # noqa: E402

from ..drill import PressResult, Session  # noqa: E402
from ..keymap import MNEMONICS  # noqa: E402
from .keyboard import KeyboardView  # noqa: E402
from .widgets import card, label, stat_block  # noqa: E402


def _clock(seconds: float) -> str:
    seconds = int(max(0, seconds))
    return f"{seconds // 60}:{seconds % 60:02d}"


class PracticeView(Gtk.Box):
    def __init__(self, on_finish, on_restart, on_abort) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.set_margin_top(16)
        self.set_margin_bottom(16)
        self.set_margin_start(20)
        self.set_margin_end(20)

        self.on_finish = on_finish
        self.on_restart = on_restart
        self.on_abort = on_abort

        self.session: Session | None = None
        self._active = False
        self._timer_id: int | None = None
        self._finish_token = 0
        self.hint = "next"

        # 统计条
        stats_card = card(spacing=0)
        stats_card.add_css_class("stats-card")
        stats_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        stats_row.set_homogeneous(True)
        self.progress_value: Gtk.Label
        self.speed_value: Gtk.Label
        self.accuracy_value: Gtk.Label
        self.time_value: Gtk.Label
        for caption in ("进度", "速度（字/分）", "准确率", "用时"):
            block, value = stat_block(caption)
            stats_row.append(block)
            if caption == "进度":
                self.progress_value = value
            elif caption == "速度（字/分）":
                self.speed_value = value
            elif caption == "准确率":
                self.accuracy_value = value
            else:
                self.time_value = value
        stats_card.append(stats_row)
        self.append(stats_card)

        # 题目卡片
        prompt_card = card(spacing=2)
        prompt_card.add_css_class("prompt-card")
        self.append(prompt_card)

        header_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.meta_label = label("", "meta")
        self.meta_label.set_xalign(0)
        self.meta_label.set_hexpand(True)
        self.streak_label = label("", "streak")
        self.streak_label.set_xalign(1)
        header_row.append(self.meta_label)
        header_row.append(self.streak_label)
        prompt_card.append(header_row)

        holder = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        holder.set_size_request(-1, 116)
        holder.set_valign(Gtk.Align.CENTER)
        self.char_label = label("", "big-char")
        self.char_label.set_xalign(0.5)
        self.char_label.set_yalign(0.5)
        self.char_label.set_vexpand(True)
        holder.append(self.char_label)
        prompt_card.append(holder)

        self.code_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        self.code_row.set_halign(Gtk.Align.CENTER)
        self.code_boxes: list[Gtk.Label] = []
        for _ in range(4):
            box = label("", "code-box")
            box.set_size_request(46, 54)
            box.set_xalign(0.5)
            box.set_yalign(0.5)
            self.code_row.append(box)
            self.code_boxes.append(box)
        prompt_card.append(self.code_row)

        self.mnemonic_box = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL, spacing=6
        )
        self.mnemonic_box.set_halign(Gtk.Align.CENTER)
        self.mnemonic_box.set_visible(False)
        self.mnemonic_key = label("", "mnemonic-key")
        self.mnemonic_text = label("", "mnemonic-text")
        self.mnemonic_box.append(self.mnemonic_key)
        self.mnemonic_box.append(self.mnemonic_text)
        prompt_card.append(self.mnemonic_box)

        self.feedback_label = label("", "feedback")
        self.feedback_label.set_xalign(0.5)
        self.feedback_label.set_size_request(-1, 22)
        prompt_card.append(self.feedback_label)

        self.progress_bar = Gtk.ProgressBar()
        self.progress_bar.add_css_class("practice-progress")
        self.progress_bar.set_fraction(0.0)
        prompt_card.append(self.progress_bar)

        # 虚拟键盘
        keyboard_card = card(spacing=0)
        keyboard_card.add_css_class("keyboard-card")
        self.keyboard = KeyboardView()
        self.keyboard.set_halign(Gtk.Align.CENTER)
        keyboard_card.append(self.keyboard)
        self.append(keyboard_card)

        # 底部操作
        footer = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        restart = Gtk.Button(label="重新开始")
        restart.add_css_class("flat")
        restart.connect("clicked", lambda _b: self.on_restart())
        skip = Gtk.Button(label="跳过（Tab）")
        skip.add_css_class("flat")
        skip.connect("clicked", lambda _b: self.skip())
        abort = Gtk.Button(label="结束本组（Esc）")
        abort.add_css_class("flat")
        abort.connect("clicked", lambda _b: self.on_abort())
        footer.append(restart)
        spacer = Gtk.Box()
        spacer.set_hexpand(True)
        footer.append(spacer)
        footer.append(skip)
        footer.append(abort)
        self.append(footer)

    # -- 生命周期 -----------------------------------------------------
    def start(self, session: Session, meta: str, hint: str = "next") -> None:
        self.stop()
        self._finish_token += 1
        self.session = session
        self.hint = hint
        self._active = True
        self.meta_label.set_label(meta)
        self._set_feedback("开始输入", "")
        self.keyboard.reset()
        self._refresh()
        self._timer_id = GLib.timeout_add(200, self._tick)

    def stop(self) -> None:
        self._active = False
        if self._timer_id is not None:
            GLib.source_remove(self._timer_id)
            self._timer_id = None

    def _tick(self) -> bool:
        if not self._active or self.session is None:
            return False
        self._update_stats()
        return True

    # -- 输入 ---------------------------------------------------------
    def type(self, letter: str) -> None:
        if not self._active or self.session is None:
            return
        session = self.session
        result = session.press(letter)
        if result is PressResult.IGNORED:
            return
        if result is PressResult.WRONG:
            self.keyboard.flash(letter, False)
            self._set_feedback("✗ 再试一次", "bad")
        else:
            self.keyboard.flash(letter, True)
            if result is PressResult.CORRECT:
                self._set_feedback(f"✓ 连击 {session.streak}", "ok")
            elif result is PressResult.ITEM_DONE:
                self._set_feedback("✓ 完成", "ok")
            elif result is PressResult.SESSION_DONE:
                self.keyboard.set_expected(None)
                self._set_feedback("✓ 本组完成", "ok")
                self._schedule_finish()
        self._refresh()

    def backspace(self) -> None:
        if not self._active or self.session is None:
            return
        if self.session.backspace():
            self._set_feedback("已退格", "")
            self._refresh()

    def skip(self) -> None:
        if not self._active or self.session is None:
            return
        current = self.session.current
        if current is None:
            return
        text, code = current.text, current.code
        result = self.session.skip()
        if result is PressResult.SESSION_DONE:
            self.keyboard.set_expected(None)
            self._schedule_finish()
        self._set_feedback(f"已跳过「{text}」 {code}", "warn")
        self._refresh()

    def abort(self) -> None:
        if self.session is not None:
            self._finish_token += 1
            self.stop()
            self.on_abort(self.session)

    # -- 刷新 ---------------------------------------------------------
    def _schedule_finish(self) -> None:
        self.stop()
        token = self._finish_token
        session = self.session

        def finish() -> bool:
            if token == self._finish_token and session is not None:
                self.on_finish(session)
            return False

        GLib.timeout_add(380, finish)

    def _refresh(self) -> None:
        session = self.session
        if session is None:
            return
        current = session.current
        if current is None:
            self.char_label.set_label("")
            for box in self.code_boxes:
                box.set_visible(False)
            self.mnemonic_box.set_visible(False)
            self.keyboard.set_expected(None)
        else:
            self.char_label.set_label(current.text)
            self._apply_size_class(len(current.text))
            self._update_boxes(current.code, session.typed)
            self.keyboard.set_expected(session.expected)
            self._update_mnemonic(session.expected)
        self._update_stats()
        self.streak_label.set_label(
            f"连击 {session.streak} · 错误 {session.errors}"
        )

    def _apply_size_class(self, length: int) -> None:
        for name in ("size-1", "size-2", "size-3", "size-4", "size-5", "size-6"):
            self.char_label.remove_css_class(name)
        if length <= 1:
            css = "size-1"
        elif length == 2:
            css = "size-2"
        elif length <= 4:
            css = "size-3"
        elif length <= 8:
            css = "size-4"
        elif length <= 12:
            css = "size-5"
        else:
            css = "size-6"
        self.char_label.add_css_class(css)

    def _update_boxes(self, code: str, typed: list[str]) -> None:
        for index, box in enumerate(self.code_boxes):
            for css in ("filled", "next", "empty"):
                box.remove_css_class(css)
            if index >= len(code):
                box.set_visible(False)
                continue
            box.set_visible(True)
            if index < len(typed):
                text = typed[index]
                box.add_css_class("filled")
            elif self.hint == "full":
                text = code[index]
                box.add_css_class("empty")
            elif self.hint == "next" and index == len(typed):
                text = code[index]
                box.add_css_class("next")
            else:
                text = "·"
                box.add_css_class("empty")
            box.set_label(text)

    def _update_mnemonic(self, expected: str | None) -> None:
        mnemonic = MNEMONICS.get(expected or "")
        if not mnemonic:
            self.mnemonic_box.set_visible(False)
            return
        self.mnemonic_key.set_label(expected.upper())
        self.mnemonic_text.set_label(mnemonic)
        self.mnemonic_box.set_visible(True)

    def _update_stats(self) -> None:
        session = self.session
        if session is None:
            return
        position = min(session.index + 1, session.total)
        if session.is_finished:
            position = session.total
        self.progress_value.set_label(f"{position}/{session.total}")
        self.speed_value.set_label(f"{session.speed:.0f}")
        self.accuracy_value.set_label(f"{session.accuracy:.0f}%")
        self.time_value.set_label(_clock(session.elapsed))
        self.progress_bar.set_fraction(
            min(1.0, max(0.0, session.progress))
        )

    def _set_feedback(self, text: str, kind: str) -> None:
        self.feedback_label.set_label(text)
        for css in ("ok", "bad", "warn"):
            self.feedback_label.remove_css_class(css)
        if kind:
            self.feedback_label.add_css_class(kind)
