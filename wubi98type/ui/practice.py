"""练习页面：显示题目、编码槽、统计和虚拟键盘。"""

from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Pango", "1.0")

from gi.repository import GLib, Gtk, Pango  # noqa: E402

from ..drill import PressResult, Session  # noqa: E402
from ..keymap import MNEMONICS  # noqa: E402
from ..keytable import KeyTableImages  # noqa: E402
from ..passage import Passage  # noqa: E402
from .keyboard import KeyboardView  # noqa: E402
from .widgets import card, label, stat_block  # noqa: E402

KEY_PREVIEW_SIZE = (132, 162)
PASSAGE_HEIGHT = 150


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
        self.passage: Passage | None = None
        self._passage_index: int | None = None
        self._passage_done_upto = 0
        self._passage_current: tuple[int, int] | None = None

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
        prompt_card = Gtk.Overlay()
        prompt_card.add_css_class("card")
        prompt_card.add_css_class("prompt-card")
        self.append(prompt_card)
        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        prompt_card.set_child(content)

        header_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.meta_label = label("", "meta")
        self.meta_label.set_xalign(0)
        self.meta_label.set_hexpand(True)
        self.streak_label = label("", "streak")
        self.streak_label.set_xalign(1)
        header_row.append(self.meta_label)
        header_row.append(self.streak_label)
        content.append(header_row)

        holder = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        holder.set_size_request(-1, 116)
        holder.set_valign(Gtk.Align.CENTER)
        self.char_label = label("", "big-char")
        self.char_label.set_xalign(0.5)
        self.char_label.set_yalign(0.5)
        self.char_label.set_vexpand(True)
        holder.append(self.char_label)
        content.append(holder)
        self.char_holder = holder

        self.passage_view = Gtk.TextView()
        self.passage_view.add_css_class("passage-view")
        self.passage_view.set_editable(False)
        self.passage_view.set_cursor_visible(False)
        self.passage_view.set_can_focus(False)
        self.passage_view.set_wrap_mode(Gtk.WrapMode.CHAR)
        self.passage_view.set_left_margin(10)
        self.passage_view.set_right_margin(10)
        self.passage_view.set_top_margin(4)
        self.passage_view.set_bottom_margin(4)
        self.passage_buffer = Gtk.TextBuffer()
        self.passage_buffer.create_tag("base", pixels_below_lines=5)
        self.passage_buffer.create_tag("done", foreground="#2ec27e")
        self.passage_buffer.create_tag(
            "current",
            background="#3584e4",
            foreground="#ffffff",
            weight=Pango.Weight.BOLD,
        )
        self.passage_view.set_buffer(self.passage_buffer)
        self.passage_scroller = Gtk.ScrolledWindow()
        self.passage_scroller.set_policy(
            Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC
        )
        self.passage_scroller.set_size_request(-1, PASSAGE_HEIGHT)
        self.passage_scroller.set_child(self.passage_view)
        self.passage_scroller.set_visible(False)
        content.append(self.passage_scroller)

        self.segment_label = label("", "segment-label")
        self.segment_label.set_halign(Gtk.Align.CENTER)
        self.segment_label.set_visible(False)
        content.append(self.segment_label)

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
        content.append(self.code_row)

        self.mnemonic_box = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL, spacing=6
        )
        self.mnemonic_box.set_halign(Gtk.Align.CENTER)
        self.mnemonic_box.set_visible(False)
        self.mnemonic_key = label("", "mnemonic-key")
        self.mnemonic_text = label("", "mnemonic-text")
        self.mnemonic_box.append(self.mnemonic_key)
        self.mnemonic_box.append(self.mnemonic_text)
        content.append(self.mnemonic_box)

        self.feedback_label = label("", "feedback")
        self.feedback_label.set_xalign(0.5)
        self.feedback_label.set_size_request(-1, 22)
        content.append(self.feedback_label)

        self.progress_bar = Gtk.ProgressBar()
        self.progress_bar.add_css_class("practice-progress")
        self.progress_bar.set_fraction(0.0)
        content.append(self.progress_bar)

        # 当前键位图形（仅在开启编码提示时显示）
        self.key_images = KeyTableImages()
        self.key_preview = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL, spacing=2
        )
        self.key_preview.add_css_class("key-preview")
        self.key_preview.set_halign(Gtk.Align.END)
        self.key_preview.set_valign(Gtk.Align.CENTER)
        self.key_preview.set_margin_end(20)
        self.key_preview.set_visible(False)
        self.key_preview_caption = label("当前键位", "stat-label")
        self.key_preview_caption.set_xalign(0.5)
        self.key_picture = Gtk.Picture()
        self.key_picture.add_css_class("key-preview-picture")
        self.key_picture.set_size_request(*KEY_PREVIEW_SIZE)
        self.key_picture.set_can_shrink(True)
        self.key_picture.set_content_fit(Gtk.ContentFit.CONTAIN)
        self.key_preview.append(self.key_preview_caption)
        self.key_preview.append(self.key_picture)
        prompt_card.add_overlay(self.key_preview)

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
    def start(
        self,
        session: Session,
        meta: str,
        hint: str = "next",
        passage: Passage | None = None,
    ) -> None:
        self.stop()
        self._finish_token += 1
        self.session = session
        self.hint = hint
        self.passage = passage
        self._active = True
        self.meta_label.set_label(meta)
        self._set_feedback("开始输入", "")
        self.keyboard.reset()
        if passage is not None:
            self._prepare_passage(passage)
            self.char_holder.set_visible(False)
            self.passage_scroller.set_visible(True)
        else:
            self.char_holder.set_visible(True)
            self.passage_scroller.set_visible(False)
            self.segment_label.set_visible(False)
            self.char_label.set_label("")
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
            if self.passage is None:
                self.char_label.set_label("")
            else:
                self._update_passage(session)
            self.segment_label.set_visible(False)
            for box in self.code_boxes:
                box.set_visible(False)
            self.mnemonic_box.set_visible(False)
            self.key_preview.set_visible(False)
            self.keyboard.set_expected(None)
        else:
            if self.passage is None:
                self.char_label.set_label(current.text)
                self._apply_size_class(len(current.text))
            else:
                self._update_passage(session)
                kind = "词组" if len(current.text) > 1 else "单字"
                self.segment_label.set_label(
                    f"{current.text} · {kind} · {len(current.code)} 码"
                )
                self.segment_label.set_visible(True)
            self._update_boxes(current.code, session.typed)
            self.keyboard.set_expected(session.expected)
            self._update_mnemonic(session.expected)
            self._update_key_preview(session.expected)
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

    def _update_key_preview(self, expected: str | None) -> None:
        if self.hint == "none" or not expected:
            self.key_preview.set_visible(False)
            return
        texture = self.key_images.texture(expected, KEY_PREVIEW_SIZE)
        if texture is None:
            self.key_preview.set_visible(False)
            return
        self.key_picture.set_paintable(texture)
        self.key_preview_caption.set_label(f"当前键位 · {expected.upper()}")
        self.key_preview.set_visible(True)

    # -- 文稿 ---------------------------------------------------------
    def _prepare_passage(self, passage: Passage) -> None:
        self.passage_buffer.set_text(passage.text)
        start, end = self.passage_buffer.get_bounds()
        self.passage_buffer.apply_tag_by_name("base", start, end)
        self._passage_index = None
        self._passage_done_upto = 0
        self._passage_current = None

    def _update_passage(self, session: Session) -> None:
        passage = self.passage
        if passage is None:
            return
        index = min(session.index, len(passage.positions))
        if index == self._passage_index:
            return
        self._passage_index = index
        buffer = self.passage_buffer
        if self._passage_current is not None:
            start, end = self._passage_current
            buffer.remove_tag_by_name(
                "current",
                buffer.get_iter_at_offset(start),
                buffer.get_iter_at_offset(end),
            )
            self._passage_current = None
        while self._passage_done_upto < index:
            item = passage.items[self._passage_done_upto]
            position = passage.positions[self._passage_done_upto]
            buffer.apply_tag_by_name(
                "done",
                buffer.get_iter_at_offset(position),
                buffer.get_iter_at_offset(position + len(item.text)),
            )
            self._passage_done_upto += 1
        if index < len(passage.positions):
            item = passage.items[index]
            position = passage.positions[index]
            end = position + len(item.text)
            start_iter = buffer.get_iter_at_offset(position)
            buffer.apply_tag_by_name(
                "current",
                start_iter,
                buffer.get_iter_at_offset(end),
            )
            self._passage_current = (position, end)
            self.passage_view.scroll_to_iter(start_iter, 0.25, False, 0.0, 0.35)
        else:
            self.passage_view.scroll_to_iter(
                buffer.get_end_iter(), 0.25, False, 0.0, 1.0
            )

    def _update_stats(self) -> None:
        session = self.session
        if session is None:
            return
        if self.passage is not None:
            total = max(1, self.passage.char_count)
            done = total if session.is_finished else session.chars_completed
            self.progress_value.set_label(f"{done}/{total}")
            fraction = done / total
        else:
            position = min(session.index + 1, session.total)
            if session.is_finished:
                position = session.total
            self.progress_value.set_label(f"{position}/{session.total}")
            fraction = session.progress
        self.speed_value.set_label(f"{session.speed:.0f}")
        self.accuracy_value.set_label(f"{session.accuracy:.0f}%")
        self.time_value.set_label(_clock(session.elapsed))
        self.progress_bar.set_fraction(min(1.0, max(0.0, fraction)))

    def _set_feedback(self, text: str, kind: str) -> None:
        self.feedback_label.set_label(text)
        for css in ("ok", "bad", "warn"):
            self.feedback_label.remove_css_class(css)
        if kind:
            self.feedback_label.add_css_class(kind)
