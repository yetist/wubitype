"""五笔版本（98 版 / 86 版）的码表、键位和图片配置。"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from .keymap import (
    KEYMAP,
    KEYMAP_86,
    KEY_SCOPE_LABELS,
    KEY_SCOPE_LABELS_86,
    KEY_SCOPE_OPTIONS,
    KEY_SCOPE_OPTIONS_86,
    MNEMONICS,
    MNEMONICS_86,
    KeyInfo,
)

#: 键名汉字（98 版 X 键不设键名）。
KEY_NAMES_98 = "王土大木工目日口田山禾白月人金言立水火之已子女又"
#: 86 版 X 键键名为“纟”。
KEY_NAMES_86 = KEY_NAMES_98 + "纟"


@dataclass(frozen=True, slots=True)
class Scheme:
    id: str
    label: str
    short_label: str
    main_file: str
    large_file: str
    table_image: str
    keymap: Mapping[str, KeyInfo]
    mnemonics: Mapping[str, str]
    key_scope_options: tuple[tuple[str, str], ...]
    key_scope_labels: Mapping[str, str]
    key_names: str
    z_label: str


SCHEMES: dict[str, Scheme] = {
    "98": Scheme(
        id="98",
        label="五笔 98 版",
        short_label="98 版",
        main_file="wubi98.main.txt",
        large_file="wubi98.large.txt",
        table_image="wubi98-table.png",
        keymap=KEYMAP,
        mnemonics=MNEMONICS,
        key_scope_options=KEY_SCOPE_OPTIONS,
        key_scope_labels=KEY_SCOPE_LABELS,
        key_names=KEY_NAMES_98,
        z_label="未用",
    ),
    "86": Scheme(
        id="86",
        label="五笔 86 版",
        short_label="86 版",
        main_file="wubi86.main.txt",
        large_file="wubi86.large.txt",
        table_image="wubi86-table.png",
        keymap=KEYMAP_86,
        mnemonics=MNEMONICS_86,
        key_scope_options=KEY_SCOPE_OPTIONS_86,
        key_scope_labels=KEY_SCOPE_LABELS_86,
        key_names=KEY_NAMES_86,
        z_label="学习键",
    ),
}

VERSION_IDS: tuple[str, ...] = tuple(SCHEMES)
VERSION_LABELS: tuple[str, ...] = tuple(
    scheme.label for scheme in SCHEMES.values()
)


def get_scheme(version: str) -> Scheme:
    return SCHEMES.get(version, SCHEMES["98"])
