"""文稿跟打：把一段中文文本按最长词组优先切分成练习序列。"""

from __future__ import annotations

import codecs
from dataclasses import dataclass
from pathlib import Path

from .data import Entry
from .drill import Session
from .encoding import WordIndex


@dataclass(frozen=True, slots=True)
class Passage:
    title: str
    text: str
    items: tuple[Entry, ...]
    positions: tuple[int, ...]

    @property
    def char_count(self) -> int:
        return sum(len(item.text) for item in self.items)

    @property
    def segment_count(self) -> int:
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
    index: WordIndex,
) -> Passage:
    """按最长词组优先切分，单字使用最少击键编码。

    标点、空格、换行不参与输入，但仍会显示在文稿中。
    """
    text = normalise_text(text).strip("\n")
    segments = index.segment(text)
    items = tuple(
        Entry(segment.text, segment.code, codes=(segment.code,))
        for segment in segments
    )
    positions = tuple(segment.start for segment in segments)
    if not items:
        raise ValueError("文稿中没有可练习的汉字")
    return Passage(
        title=title,
        text=text,
        items=items,
        positions=positions,
    )
