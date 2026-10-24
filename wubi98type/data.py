"""词库解析、汉字分级与练习题目池。

支持的词库文件是 Rime 风格的文本码表::

    KeyCode=abcdefghijklmnopqrstuvwxy
    Length=4
    ...
    [Data]
    aaaa 工
    aauh 藏

同一个字可能有多条编码（简码、全码、异体码），这里统一取最长的一条作为
练习用全码，并把最短编码长度当作常用程度的近似（五笔简码本身就是按字频
设置的）。
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

CODE_LETTERS = frozenset("abcdefghijklmnopqrstuvwxy")

#: 98 版一级简码（每个键位一个高频字）。
FIRST_LEVEL_CHARS = "一地在要工上是中国同和的有人我主产不为这民了发以经"
#: 98 版键名汉字（X 键不再设键名，共 24 个）。
KEY_NAME_CHARS = "王土大木工目日口田山禾白月人金言立水火之已子女又"

DATA_FILES = {
    "chars": "wubi98.single.txt",
    "chars_extended": "wubi98.large.txt",
    "phrases": "wubi98.main.txt",
}

CHAR_SCOPES: tuple[tuple[str, str], ...] = (
    ("一级简码（25 字）", "first"),
    ("键名汉字（24 字）", "keyname"),
    ("二级简码（常用）", "level2"),
    ("三级简码", "level3"),
    ("全码单字", "full"),
    ("全部单字", "all"),
)

PHRASE_SCOPES: tuple[tuple[str, str], ...] = (
    ("双字词", "two"),
    ("三字词", "three"),
    ("四字词", "four"),
    ("多字词", "multi"),
    ("全部词组", "all"),
)


@dataclass(frozen=True, slots=True)
class Entry:
    """一个练习题：汉字或词组，以及它的完整编码。"""

    text: str
    code: str
    min_code_len: int = 4

    @property
    def length(self) -> int:
        return len(self.code)


def is_hanzi(char: str, extended: bool = False) -> bool:
    cp = ord(char)
    if 0x4E00 <= cp <= 0x9FFF:
        return True
    if extended and (
        0x3400 <= cp <= 0x4DBF  # 扩展 A
        or 0xF900 <= cp <= 0xFAFF  # 兼容汉字
        or 0x20000 <= cp <= 0x2FA1F  # 扩展 B 及以后
    ):
        return True
    return False


def default_data_dir() -> Path:
    """按优先级寻找词库目录。"""
    candidates: list[Path] = []
    env = os.environ.get("WUBI98TYPE_DATA")
    if env:
        candidates.append(Path(env).expanduser())
    candidates.append(Path.cwd())
    package_dir = Path(__file__).resolve().parent
    candidates.append(package_dir.parent)
    candidates.append(package_dir)
    candidates.append(Path.home() / ".local/share/wubi98type")
    for path in candidates:
        if (path / DATA_FILES["chars"]).is_file():
            return path
    raise FileNotFoundError(
        "找不到词库文件 wubi98.single.txt。请把词库放在当前目录，"
        "或设置环境变量 WUBI98TYPE_DATA 指向词库目录。"
    )


def parse_table(path: Path) -> dict[str, list[str]]:
    """解析码表中 ``[Data]`` 之后的内容，返回 ``{词语: [编码...]}``。"""
    table: dict[str, list[str]] = {}
    in_data = False
    with open(path, encoding="utf-8-sig") as handle:
        for raw in handle:
            line = raw.strip()
            if not in_data:
                if line == "[Data]":
                    in_data = True
                continue
            if not line:
                continue
            parts = line.split(maxsplit=1)
            if len(parts) != 2:
                continue
            code, word = parts[0].strip().lower(), parts[1].strip()
            if not code or not word or len(code) > 4:
                continue
            if any(ch not in CODE_LETTERS for ch in code):
                continue
            table.setdefault(word, []).append(code)
    return table


def canonical_code(codes: Iterable[str]) -> str:
    """取最长的编码；同长时取字典序最大的，保证结果稳定。"""
    return max(set(codes), key=lambda code: (len(code), code))


def _make_entries(
    table: dict[str, list[str]],
    *,
    extended: bool,
    single: bool,
) -> list[Entry]:
    entries: list[Entry] = []
    for word, codes in table.items():
        if single:
            if len(word) != 1 or not is_hanzi(word, extended):
                continue
        else:
            if len(word) < 2 or not all(is_hanzi(ch, extended) for ch in word):
                continue
        code = canonical_code(codes)
        if not single and len(code) != 4:
            # 词组练习只取标准四码词组
            continue
        entries.append(Entry(word, code, min(len(c) for c in codes)))
    entries.sort(key=lambda e: (e.min_code_len, e.code, e.text))
    return entries


def _load_table(path: Path) -> dict[str, list[str]]:
    try:
        return parse_table(path)
    except OSError:
        return {}


class Dictionary:
    """加载好的单字与词组集合。"""

    _cache: dict[tuple[str, bool], "Dictionary"] = {}

    def __init__(
        self,
        chars: list[Entry],
        phrases: list[Entry],
        *,
        data_dir: Path | None = None,
        extended: bool = False,
    ) -> None:
        self.chars = chars
        self.phrases = phrases
        self.data_dir = data_dir
        self.extended = extended
        self._char_index = {entry.text: entry for entry in chars}

    @classmethod
    def load(cls, data_dir: Path | None = None, *, extended: bool = False) -> "Dictionary":
        data_dir = Path(data_dir) if data_dir else default_data_dir()
        key = (str(data_dir.resolve()), extended)
        cached = cls._cache.get(key)
        if cached is not None:
            return cached

        char_file = data_dir / (
            DATA_FILES["chars_extended"] if extended else DATA_FILES["chars"]
        )
        if not char_file.is_file():
            char_file = data_dir / DATA_FILES["chars"]
        phrase_file = data_dir / DATA_FILES["phrases"]

        chars = _make_entries(
            _load_table(char_file), extended=extended, single=True
        )
        phrases = _make_entries(
            _load_table(phrase_file), extended=extended, single=False
        )
        dictionary = cls(chars, phrases, data_dir=data_dir, extended=extended)
        cls._cache[key] = dictionary
        return dictionary

    # -- 分级 ---------------------------------------------------------
    def char_scope(self, scope: str) -> list[Entry]:
        if scope == "first":
            return [
                self._char_index[ch]
                for ch in FIRST_LEVEL_CHARS
                if ch in self._char_index
            ]
        if scope == "keyname":
            return [
                self._char_index[ch]
                for ch in KEY_NAME_CHARS
                if ch in self._char_index
            ]
        if scope == "level2":
            return [e for e in self.chars if e.min_code_len == 2]
        if scope == "level3":
            return [e for e in self.chars if e.min_code_len == 3]
        if scope == "full":
            return [e for e in self.chars if e.min_code_len >= 4]
        return list(self.chars)

    def phrase_scope(self, scope: str) -> list[Entry]:
        if scope == "two":
            return [e for e in self.phrases if len(e.text) == 2]
        if scope == "three":
            return [e for e in self.phrases if len(e.text) == 3]
        if scope == "four":
            return [e for e in self.phrases if len(e.text) == 4]
        if scope == "multi":
            return [e for e in self.phrases if len(e.text) >= 5]
        return list(self.phrases)

    def buckets(
        self,
        mode: str,
        char_scope: str = "level2",
        phrase_scope: str = "two",
    ) -> list[tuple[list[Entry], float]]:
        """返回 ``[(题目列表, 权重), ...]``，供出题器使用。"""
        if mode == "phrase":
            return [(self.phrase_scope(phrase_scope), 1.0)]
        if mode == "mixed":
            chars = self.char_scope(char_scope)
            phrases = [e for e in self.phrases if 2 <= len(e.text) <= 4]
            return [(chars, 0.7), (phrases, 0.3)]
        return [(self.char_scope(char_scope), 1.0)]

    def counts(self) -> dict[str, int]:
        return {"chars": len(self.chars), "phrases": len(self.phrases)}
