"""编码反查：根据五笔编码查找对应的单字与词组。"""

from __future__ import annotations

import bisect
from dataclasses import dataclass
from pathlib import Path

from .data import (
    CODE_LETTERS,
    default_data_dir,
    is_hanzi,
    parse_table,
)
from .schemes import get_scheme


def clean_code(text: str) -> str:
    """只保留 a–y，最多 4 位。"""
    return "".join(char for char in text.lower() if char in CODE_LETTERS)[:4]


@dataclass(frozen=True, slots=True)
class LookupItem:
    code: str
    text: str
    kind: str

    @property
    def kind_label(self) -> str:
        return "单字" if self.kind == "char" else "词组"


@dataclass(frozen=True, slots=True)
class LookupResult:
    query: str
    exact: tuple[LookupItem, ...] = ()
    exact_total: int = 0
    prefix: tuple[LookupItem, ...] = ()
    prefix_total: int = 0

    @property
    def total(self) -> int:
        return self.exact_total + self.prefix_total

    @property
    def truncated(self) -> bool:
        return (
            self.exact_total > len(self.exact)
            or self.prefix_total > len(self.prefix)
        )


class ReverseLookup:
    """保留码表中所有简码/全码索引，用于反查。"""

    _cache: dict[tuple[str, bool, str], "ReverseLookup"] = {}

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

        slots: dict[str, set[str]] = {}
        if char_file == main_file:
            table = self._load_table(main_file)
            self._add_table(slots, table, extended, single=True)
            self._add_table(slots, table, extended, single=False)
        else:
            self._add_table(
                slots,
                self._load_table(char_file),
                extended,
                single=True,
            )
            self._add_table(
                slots,
                self._load_table(main_file),
                extended,
                single=False,
            )
        self._index: dict[str, tuple[str, ...]] = {
            code: tuple(sorted(words, key=lambda word: (len(word) != 1, word)))
            for code, words in slots.items()
        }
        self._codes = sorted(self._index)
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
    ) -> "ReverseLookup":
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
        slots: dict[str, set[str]],
        table: dict[str, list[str]],
        extended: bool,
        *,
        single: bool,
    ) -> None:
        for word, codes in table.items():
            if single:
                if len(word) != 1 or not is_hanzi(word, extended):
                    continue
            elif len(word) < 2 or not all(
                is_hanzi(char, extended) for char in word
            ):
                continue
            for code in codes:
                slots.setdefault(code, set()).add(word)

    def search(
        self,
        query: str,
        *,
        include_phrases: bool = True,
        limit: int = 150,
    ) -> LookupResult:
        query = clean_code(query)
        if not query:
            return LookupResult(query="")

        def wanted(word: str) -> bool:
            return include_phrases or len(word) == 1

        words = [word for word in self._index.get(query, ()) if wanted(word)]
        exact = tuple(
            LookupItem(query, word, "char" if len(word) == 1 else "phrase")
            for word in words[:limit]
        )

        prefix: list[LookupItem] = []
        prefix_total = 0
        start = bisect.bisect_left(self._codes, query)
        for code in self._codes[start:]:
            if not code.startswith(query):
                break
            if code == query:
                continue
            for word in self._index[code]:
                if not wanted(word):
                    continue
                prefix_total += 1
                if len(prefix) < limit:
                    prefix.append(
                        LookupItem(
                            code,
                            word,
                            "char" if len(word) == 1 else "phrase",
                        )
                    )
        return LookupResult(
            query=query,
            exact=exact,
            exact_total=len(words),
            prefix=tuple(prefix),
            prefix_total=prefix_total,
        )
