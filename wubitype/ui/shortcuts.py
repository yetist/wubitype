"""快捷键帮助窗口。"""

from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")

from gi.repository import Gdk, Gtk  # noqa: E402

from .widgets import label  # noqa: E402

SECTIONS: tuple[tuple[str, tuple[tuple[str, str], ...]], ...] = (
    (
        "通用",
        (
            ("F1", "显示快捷键帮助"),
            ("F2", "查看当前版本键位图"),
            ("F3", "循环切换编码提示"),
            ("Ctrl+F", "打开编码查询"),
            ("Ctrl+Q", "退出程序"),
        ),
    ),
    (
        "打字界面",
        (
            ("a–y", "输入五笔编码"),
            ("Space", "提交简码"),
            ("Backspace", "退格"),
            ("Delete", "清空当前字已输入的码"),
            ("Tab", "跳过当前题"),
            ("Esc", "结束本组"),
            ("Ctrl+R", "重新开始"),
            ("Ctrl+P", "暂停 / 继续"),
        ),
    ),
    (
        "首页",
        (
            ("Ctrl+Enter", "开始练习"),
            ("F6", "切换五笔 98 / 86 版"),
            ("Ctrl+O", "加载自定义文稿（文稿跟打模式）"),
        ),
    ),
    (
        "结算页",
        (
            ("Enter", "再来一组"),
            ("R", "重练错题"),
            ("Esc", "返回首页"),
        ),
    ),
    (
        "编码查询",
        (
            ("Ctrl+1 / Ctrl+2", "切换编码反查 / 汉字查码"),
            ("Ctrl+L", "聚焦搜索框"),
            ("↑ / ↓", "浏览结果"),
            ("Enter / Ctrl+C", "复制当前结果"),
            ("Esc", "关闭窗口"),
        ),
    ),
)


class ShortcutsDialog(Gtk.Window):
    def __init__(self, parent: Gtk.Window) -> None:
        super().__init__(transient_for=parent, modal=True, title="快捷键")
        self.set_default_size(700, 760)
        self.set_size_request(520, 420)

        header = Gtk.HeaderBar()
        header.set_show_title_buttons(True)
        self.set_titlebar(header)

        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        outer.set_margin_top(16)
        outer.set_margin_bottom(16)
        outer.set_margin_start(20)
        outer.set_margin_end(20)
        self.set_child(outer)

        intro = label("五笔打字通快捷键", "title-md")
        intro.set_xalign(0)
        outer.append(intro)

        scroller = Gtk.ScrolledWindow()
        scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroller.set_overlay_scrolling(False)
        scroller.set_vexpand(True)
        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        scroller.set_child(content)
        outer.append(scroller)

        for section_title, rows in SECTIONS:
            section = Gtk.Box(
                orientation=Gtk.Orientation.VERTICAL, spacing=6
            )
            heading = label(section_title, "card-title")
            heading.set_xalign(0)
            section.append(heading)
            grid = Gtk.Grid(column_spacing=18, row_spacing=5)
            for row, (keys, description) in enumerate(rows):
                key_label = label(keys, "shortcut-key")
                key_label.set_xalign(0)
                desc_label = label(description, "shortcut-desc")
                desc_label.set_xalign(0)
                grid.attach(key_label, 0, row, 1, 1)
                grid.attach(desc_label, 1, row, 1, 1)
            section.append(grid)
            content.append(section)

        controller = Gtk.EventControllerKey()
        controller.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        controller.connect("key-pressed", self._on_key_pressed)
        self.add_controller(controller)

    def _on_key_pressed(self, _controller, keyval, _keycode, _state) -> bool:
        if keyval == Gdk.KEY_Escape:
            self.close()
            return True
        return False
