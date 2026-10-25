"""用户设置与最佳成绩的持久化。"""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path

MODES = ("char", "phrase", "mixed", "keys", "text")
HINTS = ("full", "next", "none")
CHAR_SCOPE_IDS = ("first", "keyname", "level2", "level3", "full", "all")
PHRASE_SCOPE_IDS = ("two", "three", "four", "multi", "all")


def config_path() -> Path:
    base = os.environ.get("XDG_CONFIG_HOME")
    root = Path(base) if base else Path.home() / ".config"
    return root / "wubi98type" / "config.json"


@dataclass
class Config:
    version: str = "98"
    mode: str = "char"
    char_scope: str = "level2"
    phrase_scope: str = "two"
    key_scope: str = "zone-1"
    text_scope: str = "poem-01"
    text_path: str = ""
    count: int = 20
    hint: str = "next"
    extended: bool = False
    best: dict[str, dict[str, float]] = field(default_factory=dict)

    def normalise(self) -> "Config":
        if self.version not in ("98", "86"):
            self.version = "98"
        if self.mode not in MODES:
            self.mode = "char"
        if self.char_scope not in CHAR_SCOPE_IDS:
            self.char_scope = "level2"
        if self.phrase_scope not in PHRASE_SCOPE_IDS:
            self.phrase_scope = "two"
        valid_key_scope = (
            self.key_scope in {f"zone-{zone}" for zone in range(1, 6)}
            or self.key_scope
            in {f"key-{letter}" for letter in "abcdefghijklmnopqrstuvwxy"}
        )
        if not valid_key_scope:
            self.key_scope = "zone-1"
        if self.text_scope != "custom" and not self.text_scope.startswith("poem-"):
            self.text_scope = "poem-01"
        if not isinstance(self.text_path, str):
            self.text_path = ""
        if self.hint not in HINTS:
            self.hint = "next"
        self.count = max(1, min(500, int(self.count)))
        if not isinstance(self.best, dict):
            self.best = {}
        # 兼容旧版按模式保存的成绩：归入 98 版
        for mode in MODES:
            if mode in self.best and f"98:{mode}" not in self.best:
                self.best[f"98:{mode}"] = self.best.pop(mode)
        return self

    def _best_key(self, mode: str) -> str:
        return f"{self.version}:{mode}"

    def best_for(self, mode: str) -> dict[str, float] | None:
        value = self.best.get(self._best_key(mode))
        return value if isinstance(value, dict) else None

    def record(self, mode: str, *, speed: float, accuracy: float, chars: int) -> bool:
        """记录成绩，返回是否破纪录。"""
        if chars <= 0 or accuracy < 80:
            return False
        previous = self.best_for(mode)
        score = speed * (accuracy / 100.0)
        if previous is not None and score <= float(previous.get("score", 0.0)):
            return False
        self.best[self._best_key(mode)] = {
            "speed": round(speed, 1),
            "accuracy": round(accuracy, 1),
            "chars": chars,
            "score": round(score, 1),
        }
        return True


def load_config(path: Path | None = None) -> Config:
    path = path or config_path()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return Config()
    if not isinstance(data, dict):
        return Config()
    known = {field_name for field_name in Config.__dataclass_fields__}
    return Config(**{k: v for k, v in data.items() if k in known}).normalise()


def save_config(config: Config, path: Path | None = None) -> None:
    path = path or config_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(
            json.dumps(asdict(config), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        tmp.replace(path)
    except OSError:
        # 配置写入失败不应影响练习
        pass
