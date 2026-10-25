"""汉字查码与文稿切分：按最长词组优先，单字使用最少击键简码。"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .data import default_data_dir, is_hanzi, parse_table
from .schemes import get_scheme


@dataclass(frozen=True, slots=True)
class WordEntry:
    text: str
    codes: tuple[str, ...]
    kind: str

    @property
    def kind_label(self) -> str:
        return "单字" if self.kind == "char" else "词组"

    @property
    def preferred_code(self) -> str:
        """最少击键编码：一级/二级简码优先。"""
        return self.codes[0]

    @property
    def full_code(self) -> str:
        return self.codes[-1]

    @property
    def has_short_code(self) -> bool:
        return len(self.preferred_code) < len(self.full_code)


@dataclass(frozen=True, slots=True)
class Segment:
    text: str
    start: int
    end: int
    entry: WordEntry

    @property
    def code(self) -> str:
        return self.entry.preferred_code

    @property
    def full_code(self) -> str:
        return self.entry.full_code

    @property
    def kind(self) -> str:
        return self.entry.kind

    @property
    def kind_label(self) -> str:
        return self.entry.kind_label


@dataclass(frozen=True, slots=True)
class EncodeResult:
    text: str
    segments: tuple[Segment, ...]
    missing: tuple[str, ...]

    @property
    def minimal_code(self) -> str:
        return "".join(segment.code for segment in self.segments)

    @property
    def minimal_code_spaced(self) -> str:
        return " ".join(segment.code for segment in self.segments)

    @property
    def full_code(self) -> str:
        return "".join(segment.full_code for segment in self.segments)

    @property
    def full_code_spaced(self) -> str:
        return " ".join(segment.full_code for segment in self.segments)

    @property
    def char_count(self) -> int:
        return sum(len(segment.text) for segment in self.segments)

    @property
    def has_short_codes(self) -> bool:
        return any(segment.entry.has_short_code for segment in self.segments)


class WordIndex:
    """字词索引：保留全部编码，并按最长词组优先切分文本。"""

    _cache: dict[tuple[str, bool, str], "WordIndex"] = {}

    def __init__(
        self,
        data_dir: Path | None = None,
        *,
        extended: bool = False,
        version: str = "98",
    ) -> None:
        data_dir = Path(data_dir) if data_dir else default_data_dir()
        scheme = get_scheme(version)
        main_file = data_dir / scheme.main_file
        if not main_file.is_file():
            raise FileNotFoundError(
                f"找不到 {scheme.main_file}，无法使用{scheme.label}。"
            )
        char_file = data_dir / scheme.large_file if extended else main_file
        if not char_file.is_file():
            char_file = main_file

        words: dict[str, WordEntry] = {}
        if char_file == main_file:
            table = self._load_table(main_file)
            self._add_table(words, table, extended, single=True)
            self._add_table(words, table, extended, single=False)
        else:
            self._add_table(
                words,
                self._load_table(char_file),
                extended,
                single=True,
            )
            self._add_table(
                words,
                self._load_table(main_file),
                extended,
                single=False,
            )
        self._words = words
        self._max_word_len = max((len(word) for word in words), default=1)
        self.data_dir = data_dir
        self.extended = extended
        self.version = scheme.id
        self.scheme = scheme

    @classmethod
    def load(
        cls,
        data_dir: Path | None = None,
        *,
        extended: bool = False,
        version: str = "98",
    ) -> "WordIndex":
        data_dir = Path(data_dir) if data_dir else default_data_dir()
        scheme = get_scheme(version)
        key = (str(data_dir.resolve()), extended, scheme.id)
        cached = cls._cache.get(key)
        if cached is None:
            cached = cls(data_dir, extended=extended, version=version)
            cls._cache[key] = cached
        return cached

    @staticmethod
    def _load_table(path: Path) -> dict[str, list[str]]:
        try:
            return parse_table(path)
        except OSError:
            return {}

    @staticmethod
    def _add_table(
        words: dict[str, WordEntry],
        table: dict[str, list[str]],
        extended: bool,
        *,
        single: bool,
    ) -> None:
        for word, codes in table.items():
            if single:
                if len(word) != 1 or not is_hanzi(word, extended):
                    continue
                kind = "char"
            else:
                if len(word) < 2 or not all(
                    is_hanzi(char, extended) for char in word
                ):
                    continue
                kind = "phrase"
            ordered = tuple(
                sorted(set(codes), key=lambda code: (len(code), code))
            )
            if ordered:
                words[word] = WordEntry(word, ordered, kind)

    def get(self, word: str) -> WordEntry | None:
        return self._words.get(word)

    def segment(self, text: str) -> list[Segment]:
        """从最长词组到单字做最大匹配。"""
        segments: list[Segment] = []
        index = 0
        length = len(text)
        while index < length:
            if not is_hanzi(text[index], self.extended):
                index += 1
                continue
            match: WordEntry | None = None
            end = index
            upper = min(length, index + self._max_word_len)
            for candidate_end in range(upper, index, -1):
                candidate = self._words.get(text[index:candidate_end])
                if candidate is not None:
                    match = candidate
                    end = candidate_end
                    break
            if match is None:
                index += 1
                continue
            segments.append(Segment(match.text, index, end, match))
            index = end
        return segments

    def encode(self, text: str) -> EncodeResult:
        segments = self.segment(text)
        covered = {
            index
            for segment in segments
            for index in range(segment.start, segment.end)
        }
        missing = tuple(
            char
            for index, char in enumerate(text)
            if is_hanzi(char, self.extended) and index not in covered
        )
        return EncodeResult(text, tuple(segments), missing)
