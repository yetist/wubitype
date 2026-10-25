"""主窗口与页面切换。"""

from __future__ import annotations

from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")

from gi.repository import Gdk, Gio, GLib, Gtk  # noqa: E402

from .. import __version__  # noqa: E402
from ..config import Config, HINTS, save_config  # noqa: E402
from ..data import (  # noqa: E402
    CHAR_SCOPES,
    PHRASE_SCOPES,
    Dictionary,
    default_data_dir,
)
from ..drill import Session  # noqa: E402
from ..encoding import WordIndex  # noqa: E402
from ..lookup import ReverseLookup  # noqa: E402
from ..passage import Passage, build_passage, read_text_file  # noqa: E402
from ..poems import POEM_BY_ID  # noqa: E402
from ..schemes import get_scheme  # noqa: E402
from .home import MODE_IDS, MODE_LABELS, HomeView  # noqa: E402
from .lookup import LookupDialog  # noqa: E402
from .practice import PracticeView  # noqa: E402
from .summary import SummaryView  # noqa: E402
from .widgets import label  # noqa: E402


class MainWindow(Gtk.ApplicationWindow):
    def __init__(self, application: Gtk.Application, config: Config) -> None:
        super().__init__(application=application)
        self.config = config
        self.dictionary: Dictionary | None = None
        self._keymap_window: Gtk.Window | None = None
        self._lookup_window: LookupDialog | None = None
        self._lookup_paused: Session | None = None
        self._recordable = True

        self.set_title("五笔打字通")
        self.set_default_size(980, 880)
        self.set_size_request(880, 700)

        header = Gtk.HeaderBar()
        header.set_show_title_buttons(True)
        title = label("五笔打字通", "header-title")
        header.set_title_widget(title)

        menu = Gio.Menu()
        menu.append("编码查询", "win.lookup")

        hint_menu = Gio.Menu()
        for hint_label, hint in (
            ("完整编码", "full"),
            ("逐码提示", "next"),
            ("关闭提示", "none"),
        ):
            item = Gio.MenuItem.new(hint_label, None)
            item.set_action_and_target_value(
                "win.hint", GLib.Variant.new_string(hint)
            )
            hint_menu.append_item(item)
        menu.append_submenu("编码提示", hint_menu)

        menu.append("查看键位图", "win.keymap")
        menu.append("清空最佳成绩", "win.clear-records")
        menu.append("关于", "win.about")
        menu_button = Gtk.MenuButton(icon_name="open-menu-symbolic", menu_model=menu)
        menu_button.set_tooltip_text("菜单")
        header.pack_end(menu_button)

        lookup_button = Gtk.Button(icon_name="edit-find-symbolic")
        lookup_button.set_tooltip_text("编码查询")
        lookup_button.connect("clicked", lambda _button: self._show_lookup())
        header.pack_end(lookup_button)
        self.set_titlebar(header)

        self._install_actions()

        self.stack = Gtk.Stack(
            transition_type=Gtk.StackTransitionType.CROSSFADE,
            transition_duration=160,
        )
        self.set_child(self.stack)

        self.home = HomeView(
            self.config,
            self._start_from_home,
            self._sync_hint_action,
        )
        self.practice = PracticeView(
            on_finish=self._finish_session,
            on_restart=self._restart,
            on_abort=self._abort,
        )
        self.practice_page = Gtk.ScrolledWindow()
        self.practice_page.set_policy(
            Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC
        )
        self.practice_page.set_overlay_scrolling(False)
        self.practice_page.set_vexpand(True)
        self.practice_page.set_child(self.practice)
        self.summary = SummaryView(
            on_again=self._again,
            on_retry=self._retry_mistakes,
            on_home=self._go_home,
        )
        self.stack.add_named(self.home, "home")
        self.stack.add_named(self.practice_page, "practice")
        self.stack.add_named(self.summary, "summary")
        self.stack.set_visible_child(self.home)

        key_controller = Gtk.EventControllerKey()
        key_controller.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        key_controller.connect("key-pressed", self._on_key_pressed)
        self.add_controller(key_controller)

        self.connect("close-request", self._on_close)

    # -- 动作与菜单 ---------------------------------------------------
    def _install_actions(self) -> None:
        self.hint_action = Gio.SimpleAction.new_stateful(
            "hint",
            GLib.VariantType.new("s"),
            GLib.Variant.new_string(self.config.hint),
        )
        self.hint_action.connect("change-state", self._on_hint_action)
        self.add_action(self.hint_action)

        actions = (
            ("about", self._show_about),
            ("lookup", self._show_lookup),
            ("keymap", self._show_keymap),
            ("clear-records", self._clear_records),
        )
        for name, handler in actions:
            action = Gio.SimpleAction.new(name, None)
            action.connect("activate", lambda _action, _param, fn=handler: fn())
            self.add_action(action)

    def _on_hint_action(
        self, action: Gio.SimpleAction, value: GLib.Variant
    ) -> None:
        hint = value.get_string()
        if hint not in HINTS:
            return
        action.set_state(value)
        self._set_hint(hint)

    def _set_hint(self, hint: str) -> None:
        if hint not in HINTS:
            return
        self.config.hint = hint
        self.home.set_hint(hint)
        self.practice.set_hint(hint)
        self._sync_hint_action()

    def _sync_hint_action(self) -> None:
        state = self.hint_action.get_state()
        if state is None or state.get_string() != self.config.hint:
            self.hint_action.set_state(
                GLib.Variant.new_string(self.config.hint)
            )

    def _show_about(self) -> None:
        dialog = Gtk.AboutDialog(transient_for=self, modal=True)
        dialog.set_program_name("五笔打字通")
        dialog.set_version(__version__)
        dialog.set_comments(
            "用 GTK4 编写的五笔打字通，支持五笔 98 / 86 版。\n"
            "提供码元规则出题、键位提示、速度与准确率统计、错题重练。"
        )
        dialog.set_license_type(Gtk.License.MIT_X11)
        dialog.set_logo_icon_name("input-keyboard-symbolic")
        dialog.set_authors(["wubitype contributors"])
        dialog.present()

    def _show_lookup(self) -> None:
        if self._lookup_window is not None:
            self._lookup_window.present()
            return
        try:
            lookup = ReverseLookup.load(
                extended=self.config.extended,
                version=self.config.version,
            )
            words = WordIndex.load(
                extended=self.config.extended,
                version=self.config.version,
            )
        except (OSError, FileNotFoundError) as error:
            self._alert("无法加载码表", str(error))
            return
        dialog = LookupDialog(self, lookup, words)
        if (
            self.stack.get_visible_child_name() == "practice"
            and self.practice.session is not None
            and not self.practice.session.is_finished
        ):
            self.practice.session.pause()
            self._lookup_paused = self.practice.session
        dialog.connect("close-request", self._on_lookup_closed)
        self._lookup_window = dialog
        dialog.present()

    def _on_lookup_closed(self, _window: Gtk.Window) -> bool:
        if self._lookup_paused is not None:
            self._lookup_paused.resume()
            self._lookup_paused = None
        self._lookup_window = None
        return False

    def _show_keymap(self) -> None:
        if self._keymap_window is not None:
            self._keymap_window.present()
            return
        scheme = get_scheme(self.config.version)
        try:
            data_dir = self.dictionary.data_dir if self.dictionary else default_data_dir()
        except FileNotFoundError:
            data_dir = Path.cwd()
        candidates = (
            data_dir / scheme.table_image,
            Path.cwd() / scheme.table_image,
            Path(__file__).resolve().parents[2] / scheme.table_image,
        )
        image = next((path for path in candidates if path.is_file()), None)
        if image is None:
            self._alert(f"找不到键位图 {scheme.table_image}")
            return
        window = Gtk.Window(
            transient_for=self,
            modal=True,
            title=f"{scheme.short_label}键位图",
        )
        window.set_default_size(1100, 720)
        header = Gtk.HeaderBar()
        header.set_show_title_buttons(True)
        window.set_titlebar(header)
        picture = Gtk.Picture(file=Gio.File.new_for_path(str(image)))
        picture.set_can_shrink(True)
        picture.set_margin_top(8)
        picture.set_margin_bottom(8)
        picture.set_margin_start(8)
        picture.set_margin_end(8)
        window.set_child(picture)
        window.connect("close-request", self._on_keymap_closed)
        self._keymap_window = window
        window.present()

    def _on_keymap_closed(self, window: Gtk.Window) -> bool:
        self._keymap_window = None
        return False

    def _clear_records(self) -> None:
        dialog = Gtk.AlertDialog()
        dialog.set_message("清空最佳成绩？")
        dialog.set_detail("所有练习模式的最佳记录都会被删除，此操作无法撤销。")
        dialog.set_buttons(["取消", "清空"])
        dialog.set_cancel_button(0)
        dialog.set_default_button(0)
        dialog.choose(self, None, self._on_clear_chosen)

    def _on_clear_chosen(self, dialog: Gtk.AlertDialog, result) -> None:
        try:
            choice = dialog.choose_finish(result)
        except GLib.Error:
            return
        if choice == 1:
            self.config.best.clear()
            save_config(self.config)
            self.home.refresh_best()

    def _alert(self, message: str, detail: str = "") -> None:
        dialog = Gtk.AlertDialog(message=message, detail=detail)
        dialog.set_buttons(["知道了"])
        dialog.show(self)

    # -- 会话流程 -----------------------------------------------------
    def _start_from_home(self) -> None:
        self.home.sync_config()
        self._start_session()

    def _start_session(
        self,
        items=None,
        meta: str | None = None,
        *,
        recordable: bool = True,
    ) -> None:
        self._recordable = recordable
        version = self.config.version
        scheme = get_scheme(version)
        try:
            if (
                self.dictionary is None
                or self.dictionary.extended != self.config.extended
                or self.dictionary.version != version
            ):
                self.dictionary = Dictionary.load(
                    extended=self.config.extended,
                    version=version,
                )
        except (OSError, FileNotFoundError) as error:
            self._alert("无法加载词库", str(error))
            return

        try:
            if items is not None:
                buckets = [(list(items), 1.0)]
                total = len(items)
                meta = meta or f"{scheme.short_label} · 错题重练 · {total} 题"
                passage = None
            elif self.config.mode == "text":
                passage = self._build_text_passage()
                total = passage.char_count
                meta = f"{scheme.short_label} · 文稿跟打 · {passage.title} · {total} 字"
            else:
                passage = None
                buckets = self.dictionary.buckets(
                    self.config.mode,
                    self.config.char_scope,
                    self.config.phrase_scope,
                    self.config.key_scope,
                )
                total = self.config.count
                meta = meta or self._meta_label(total)
            if passage is not None:
                session = Session.sequence(passage.items)
            else:
                session = Session(buckets, total)
        except (ValueError, OSError) as error:
            self._alert("无法开始练习", str(error))
            return
        self.practice.set_version(scheme.id)
        self.practice.start(session, meta, self.config.hint, passage=passage)
        self.practice_page.get_vadjustment().set_value(0)
        self.stack.set_visible_child(self.practice_page)
        # 清除“开始练习”按钮焦点，确保 Tab/Esc 等按键交给练习页处理
        self.set_focus(None)

    def _meta_label(self, total: int) -> str:
        scheme = get_scheme(self.config.version)
        mode_label = MODE_LABELS[MODE_IDS.index(self.config.mode)]
        if self.config.mode == "keys":
            scope_label = scheme.key_scope_labels.get(
                self.config.key_scope, "全部键位"
            )
            return (
                f"{scheme.short_label} · {mode_label} · "
                f"{scope_label} · {total} 题"
            )
        if self.config.mode == "phrase":
            options = PHRASE_SCOPES
            scope_id = self.config.phrase_scope
        else:
            options = CHAR_SCOPES
            scope_id = self.config.char_scope
        scope_label = next(
            (label_text for label_text, sid in options if sid == scope_id),
            "全部",
        )
        return (
            f"{scheme.short_label} · {mode_label} · "
            f"{scope_label} · {total} 题"
        )

    def _build_text_passage(self) -> Passage:
        assert self.dictionary is not None
        if self.config.text_scope == "custom":
            path = Path(self.config.text_path)
            if not path.is_file():
                raise ValueError("请先在首页选择自定义文本文件")
            text = read_text_file(path)
            title = path.name
        else:
            poem = POEM_BY_ID.get(self.config.text_scope)
            if poem is None:
                raise ValueError("找不到所选古诗")
            text = poem.text
            title = f"《{poem.display_title}》"
        index = WordIndex.load(
            extended=self.config.extended,
            version=self.config.version,
        )
        return build_passage(text, title, index)

    def _finish_session(self, session: Session, *, aborted: bool = False) -> None:
        record = False
        if not aborted and self._recordable and session.index > 0:
            record = self.config.record(
                self.config.mode,
                speed=session.speed,
                accuracy=session.accuracy,
                chars=session.chars_completed,
            )
            save_config(self.config)
        self.summary.show(session, record=record, aborted=aborted)
        self.stack.set_visible_child(self.summary)

    def _restart(self) -> None:
        self.home.sync_config()
        self._start_session()

    def _abort(self, session: Session | None = None) -> None:
        session = session or self.practice.session
        if session is None:
            self._go_home()
            return
        if session.keystrokes == 0 and session.index == 0:
            self.practice.stop()
            self._go_home()
            return
        self._finish_session(session, aborted=True)

    def _again(self) -> None:
        self.home.sync_config()
        self._start_session()

    def _retry_mistakes(self) -> None:
        session = self.summary.session
        if session is None:
            return
        items = session.retry_items()
        if not items:
            return
        self._start_session(
            items,
            f"错题重练 · {len(items)} 题",
            recordable=False,
        )

    def _go_home(self) -> None:
        self.practice.stop()
        self.home.refresh_best()
        self.stack.set_visible_child(self.home)
        save_config(self.config)

    # -- 键盘 ---------------------------------------------------------
    def _on_key_pressed(
        self,
        _controller: Gtk.EventControllerKey,
        keyval: int,
        _keycode: int,
        state: Gdk.ModifierType,
    ) -> bool:
        if self.stack.get_visible_child_name() == "summary":
            if keyval == Gdk.KEY_Escape:
                self._go_home()
                return True
            return False
        if self.stack.get_visible_child_name() != "practice":
            return False
        if state & (
            Gdk.ModifierType.CONTROL_MASK
            | Gdk.ModifierType.ALT_MASK
            | Gdk.ModifierType.SUPER_MASK
        ):
            return False
        if keyval == Gdk.KEY_Escape:
            self.practice.abort()
            return True
        if keyval == Gdk.KEY_Tab or keyval == Gdk.KEY_ISO_Left_Tab:
            self.practice.skip()
            return True
        if keyval == Gdk.KEY_BackSpace:
            self.practice.backspace()
            return True
        if keyval == Gdk.KEY_space:
            self.practice.commit_short()
            return True
        lowered = Gdk.keyval_to_lower(keyval)
        if Gdk.KEY_a <= lowered <= Gdk.KEY_y:
            self.practice.type(chr(lowered))
            return True
        return False

    # -- 退出 ---------------------------------------------------------
    def _on_close(self, _window: Gtk.Window) -> bool:
        self.practice.stop()
        self.home.sync_config()
        save_config(self.config)
        return False
