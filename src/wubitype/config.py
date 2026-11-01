"""用户设置与最佳成绩的持久化。"""

from __future__ import annotations

import json
import os
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

MODES = ("char", "phrase", "mixed", "keys", "text")
HINTS = ("full", "next", "none")
CHAR_SCOPE_IDS = ("first", "keyname", "level2", "level3", "full", "all")
PHRASE_SCOPE_IDS = ("two", "three", "four", "multi", "all")
# 历史成绩上限：保留较长的历史，曲线绘出最近 30 组
HISTORY_LIMIT = 200
HISTORY_DRAW_LIMIT = 30


def config_path() -> Path:
    base = os.environ.get("XDG_CONFIG_HOME")
    root = Path(base) if base else Path.home() / ".config"
    return root / "wubitype" / "config.json"


def legacy_config_path() -> Path:
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
    history: list[dict[str, float | int | str]] = field(default_factory=list)

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
        if (
            self.text_scope != "custom"
            and not self.text_scope.startswith("poem-")
            and not self.text_scope.startswith("article:")
        ):
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
        if not isinstance(self.history, list):
            self.history = []
        self.history = [
            dict(item) for item in self.history if isinstance(item, dict)
        ][-HISTORY_LIMIT:]
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

    def record_history(
        self,
        mode: str,
        *,
        speed: float,
        accuracy: float,
        chars: int,
        keystrokes: int,
        errors: int,
        streak: int,
        elapsed: float,
    ) -> dict[str, float | int | str]:
        """追加一组成绩记录，超出上限时丢掉最早的记录。"""
        record: dict[str, float | int | str] = {
            "ts": int(time.time()),
            "mode": mode if mode in MODES else "char",
            "version": self.version,
            "speed": round(speed, 1),
            "accuracy": round(accuracy, 1),
            "chars": int(chars),
            "keys": int(keystrokes),
            "errors": int(errors),
            "streak": int(streak),
            "elapsed": round(elapsed, 1),
        }
        self.history.append(record)
        del self.history[:-HISTORY_LIMIT]
        return record

    def history_for(self, mode: str) -> list[dict[str, float | int | str]]:
        """返回当前版本、指定模式下按时间升序的历史记录。"""
        records = [
            dict(item)
            for item in self.history
            if item.get("mode") == mode and item.get("version") == self.version
        ]
        records.sort(key=lambda item: float(item.get("ts") or 0.0))
        return records


def load_config(path: Path | None = None) -> Config:
    explicit = path is not None
    if path is None:
        path = config_path()
        if not path.is_file():
            legacy = legacy_config_path()
            if legacy.is_file():
                path = legacy
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return Config()
    if not isinstance(data, dict):
        return Config()
    known = {field_name for field_name in Config.__dataclass_fields__}
    config = Config(
        **{k: v for k, v in data.items() if k in known}
    ).normalise()
    if not explicit and path != config_path():
        save_config(config)
    return config


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
