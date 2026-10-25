"""98 版键位与码元数据。"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class KeyInfo:
    letter: str
    code: str
    name: str
    radicals: tuple[str, ...]

    @property
    def zone(self) -> int:
        return int(self.code[0])

    @property
    def position(self) -> int:
        return int(self.code[1])


def _key(letter: str, code: str, name: str, radicals: str) -> KeyInfo:
    return KeyInfo(letter, code, name, tuple(radicals.split()))


KEYMAP: dict[str, KeyInfo] = {
    info.letter: info
    for info in (
        # 3 区（撇）
        _key("q", "35", "金", "金 钅 儿 夕 犭 鱼"),
        _key("w", "34", "人", "人 八 亻 儿 几 攵"),
        _key("e", "33", "月", "月 用 力 毛 衣 乃"),
        _key("r", "32", "白", "白 厂 斤 丘 气 手 扌"),
        _key("t", "31", "禾", "禾 竹 丿 攵 彳"),
        # 4 区（捺）
        _key("y", "41", "言", "言 讠 文 方 亠 广"),
        _key("u", "42", "立", "立 辛 六 门 疒 羊"),
        _key("i", "43", "水", "水 氵 小 业 灬"),
        _key("o", "44", "火", "火 灬 业 广 米"),
        _key("p", "45", "之", "之 辶 廴 宀 衤 礻"),
        # 1 区（横）
        _key("a", "15", "工", "工 匚 戈 弋 七 艹"),
        _key("s", "14", "木", "木 丁 西 甫"),
        _key("d", "13", "大", "大 犬 戊 厂 古 石"),
        _key("f", "12", "土", "土 士 干 十 寸 雨"),
        _key("g", "11", "王", "王 一 五 夫 丰 廿"),
        # 2 区（竖）
        _key("h", "21", "目", "目 上 止 卜 虍 丨"),
        _key("j", "22", "日", "日 曰 早 虫 刂"),
        _key("k", "23", "口", "口 川 丿"),
        _key("l", "24", "田", "田 甲 口 四 车 罒"),
        _key("m", "25", "山", "山 由 贝 冂 几"),
        # 5 区（折）
        _key("x", "55", "纟", "纟 母 弓 匕 比"),
        _key("c", "54", "又", "又 巴 马 厶"),
        _key("v", "53", "女", "女 刀 九 艮 彐"),
        _key("b", "52", "子", "子 了 阝 卩 也 乃"),
        _key("n", "51", "已", "已 己 尸 心 忄 羽"),
    )
}

#: 86 版键位与主要码元（与 wubi86-table.png 对应）。
KEYMAP_86: dict[str, KeyInfo] = {
    info.letter: info
    for info in (
        # 3 区（撇）
        _key("q", "35", "金", "金 钅 儿 夕 犭 鱼"),
        _key("w", "34", "人", "人 八 亻 登 祭 头"),
        _key("e", "33", "月", "月 用 乃 舟 衣 豕"),
        _key("r", "32", "白", "白 手 扌 斤 厂 丘 气"),
        _key("t", "31", "禾", "禾 竹 丿 攵 彳"),
        # 4 区（捺）
        _key("y", "41", "言", "言 讠 文 方 广 亠 圭"),
        _key("u", "42", "立", "立 辛 六 门 疒 丬"),
        _key("i", "43", "水", "水 氵 小 业 灬"),
        _key("o", "44", "火", "火 灬 业 米"),
        _key("p", "45", "之", "之 辶 廴 宀 衤 礻"),
        # 1 区（横）
        _key("a", "15", "工", "工 匚 戈 弋 七 艹 廿"),
        _key("s", "14", "木", "木 丁 西"),
        _key("d", "13", "大", "大 犬 三 羊 古 石 厂"),
        _key("f", "12", "土", "土 士 二 干 十 寸 雨"),
        _key("g", "11", "王", "王 一 五 戈 廿 卄"),
        # 2 区（竖）
        _key("h", "21", "目", "目 上 止 卜 虎 虍 皮"),
        _key("j", "22", "日", "日 曰 早 虫 刂"),
        _key("k", "23", "口", "口 川 丿"),
        _key("l", "24", "田", "田 甲 口 四 车 力 罒"),
        _key("m", "25", "山", "山 由 贝 冂 几 骨"),
        # 5 区（折）
        _key("x", "55", "纟", "纟 幺 弓 匕 比 丝"),
        _key("c", "54", "又", "又 巴 马 厶"),
        _key("v", "53", "女", "女 刀 九 艮 山 白 彐"),
        _key("b", "52", "子", "子 了 阝 卩 也 耳 框"),
        _key("n", "51", "已", "已 己 尸 心 忄 羽"),
    )
}

ROWS: tuple[str, ...] = ("qwertyuiop", "asdfghjkl", "xcvbnm")
UNUSED_KEYS = ("z",)

#: 98 版字根助记口诀（与 wubi98-table.png 底部口诀一致）。
MNEMONICS: dict[str, str] = {
    "g": "王旁青头五夫一",
    "f": "土干十寸未甘雨",
    "d": "大犬戊其古石厂",
    "s": "木丁西甫一四里",
    "a": "工戈草头右框七",
    "h": "目上卜止虎头具",
    "j": "日早两竖与虫依",
    "k": "口中两川三个竖",
    "l": "田甲方框四车里",
    "m": "山由贝骨下框集",
    "t": "禾竹反文双人立",
    "r": "白斤气丘叉手提",
    "e": "月用力豸毛衣白",
    "w": "人八登头单人几",
    "q": "金夕鸟儿犭边鱼",
    "y": "言文方点谁人去",
    "u": "立辛六羊病门里",
    "i": "水族三点鳖头小",
    "o": "火业广鹿四点米",
    "p": "之字宝盖补礻衤",
    "n": "已类左框心尸羽",
    "b": "子耳了也乃框皮",
    "v": "女刀九艮山西倒",
    "c": "又巴牛厶马失蹄",
    "x": "幺母贯头弓和匕",
}

#: 86 版字根助记口诀（与 wubi86-table.png 底部口诀一致）。
MNEMONICS_86: dict[str, str] = {
    "g": "王旁青头戋五一",
    "f": "土士二千十寸雨",
    "d": "大犬三羊古石厂",
    "s": "木丁西在一四里",
    "a": "工戈草头右框七",
    "h": "目止具头卜虎皮",
    "j": "日早两竖与虫依",
    "k": "口中一川三个竖",
    "l": "田甲方框四车力",
    "m": "山由骨头贝框几",
    "t": "禾竹反文双人立",
    "r": "白斤气头手边提",
    "e": "月乃用舟家衣下",
    "w": "人八登祭把头取",
    "q": "金夕犭儿包头鱼",
    "y": "言文方广在四一",
    "u": "立辛两点病门里",
    "i": "水族三点兴头小",
    "o": "火业头四点米",
    "p": "之字宝盖补礻衤",
    "n": "已类左框心尸羽",
    "b": "子耳了也框上举",
    "v": "女刀九艮山白倒",
    "c": "又巴马丢矢矣",
    "x": "绞丝互幺弓和匕",
}

#: 口诀按五区排列，供界面展示。
MNEMONIC_ROWS: tuple[tuple[str, str], ...] = (
    ("横", "gfdsa"),
    ("竖", "hjklm"),
    ("撇", "trewq"),
    ("捺", "yuiop"),
    ("折", "nbvcx"),
)

ZONE_NAMES = {1: "横", 2: "竖", 3: "撇", 4: "捺", 5: "折"}
ZONE_KEYS: dict[int, str] = {
    1: "gfdsa",
    2: "hjklm",
    3: "trewq",
    4: "yuiop",
    5: "nbvcx",
}
KEY_SCOPE_OPTIONS: tuple[tuple[str, str], ...] = tuple(
    (
        f"{zone} 区 · {ZONE_NAMES[zone]}（{' '.join(key.upper() for key in keys)}）",
        f"zone-{zone}",
    )
    for zone, keys in ZONE_KEYS.items()
) + tuple(
    (
        f"{letter.upper()} 键 · {KEYMAP[letter].code} {KEYMAP[letter].name}"
        f" · {MNEMONICS[letter]}",
        f"key-{letter}",
    )
    for keys in ZONE_KEYS.values()
    for letter in keys
)
KEY_SCOPE_LABELS: dict[str, str] = {
    scope_id: scope_label for scope_label, scope_id in KEY_SCOPE_OPTIONS
}
KEY_SCOPE_OPTIONS_86: tuple[tuple[str, str], ...] = tuple(
    (
        f"{zone} 区 · {ZONE_NAMES[zone]}（{' '.join(key.upper() for key in keys)}）",
        f"zone-{zone}",
    )
    for zone, keys in ZONE_KEYS.items()
) + tuple(
    (
        f"{letter.upper()} 键 · {KEYMAP_86[letter].code} {KEYMAP_86[letter].name}"
        f" · {MNEMONICS_86[letter]}",
        f"key-{letter}",
    )
    for keys in ZONE_KEYS.values()
    for letter in keys
)
KEY_SCOPE_LABELS_86: dict[str, str] = {
    scope_id: scope_label for scope_label, scope_id in KEY_SCOPE_OPTIONS_86
}
ZONE_COLORS = {
    1: (0.84, 0.38, 0.32),
    2: (0.24, 0.58, 0.34),
    3: (0.26, 0.47, 0.78),
    4: (0.55, 0.38, 0.72),
    5: (0.72, 0.60, 0.16),
}


def expected_key(code: str, typed_count: int) -> str | None:
    if 0 <= typed_count < len(code):
        return code[typed_count]
    return None
