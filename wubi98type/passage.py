"""文稿跟打：把一段中文文本转换成按顺序练习的单字序列。"""

from __future__ import annotations

import codecs
from dataclasses import dataclass
from pathlib import Path

from .data import Dictionary, Entry, is_hanzi
from .drill import Session


@dataclass(frozen=True, slots=True)
class Passage:
    title: str
    text: str
    items: tuple[Entry, ...]
    positions: tuple[int, ...]

    @property
    def char_count(self) -> int:
        return len(self.items)

    def session(self, **kwargs) -> Session:
        return Session.sequence(self.items, **kwargs)


def normalise_text(text: str) -> str:
    return (
        text.replace("\ufeff", "")
        .replace("\r\n", "\n")
        .replace("\r", "\n")
    )


def read_text_file(path: Path) -> str:
    """读取常见编码的文本文件。"""
    data = path.read_bytes()
    if data.startswith(codecs.BOM_UTF16_LE) or data.startswith(
        codecs.BOM_UTF16_BE
    ):
        text = data.decode("utf-16")
    else:
        for encoding in ("utf-8-sig", "gb18030"):
            try:
                text = data.decode(encoding)
                break
            except UnicodeDecodeError:
                continue
        else:
            text = data.decode("utf-8", errors="replace")
    return normalise_text(text)


def build_passage(
    text: str,
    title: str,
    dictionary: Dictionary,
) -> Passage:
    """提取可打字的汉字及其在原文中的位置。

    标点、空格、换行不参与输入，但仍会显示在文稿中。
    """
    text = normalise_text(text).strip("\n")
    items: list[Entry] = []
    positions: list[int] = []
    for index, char in enumerate(text):
        if not is_hanzi(char, dictionary.extended):
            continue
        entry = dictionary.entry_for(char)
        if entry is None:
            continue
        items.append(entry)
        positions.append(index)
    if not items:
        raise ValueError("文稿中没有可练习的汉字")
    return Passage(
        title=title,
        text=text,
        items=tuple(items),
        positions=tuple(positions),
    )
