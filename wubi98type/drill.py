"""出题与打字判定逻辑（不依赖 GTK，便于单元测试）。"""

from __future__ import annotations

import random
import time
from dataclasses import dataclass
from enum import Enum

from .data import Entry


class PressResult(Enum):
    IGNORED = "ignored"
    CORRECT = "correct"
    WRONG = "wrong"
    ITEM_DONE = "item_done"
    SESSION_DONE = "session_done"


@dataclass(frozen=True, slots=True)
class Mistake:
    text: str
    code: str
    errors: int
    skipped: bool = False


class _Bucket:
    """洗牌后依次取题，取完自动补充，避免连续重复。"""

    def __init__(self, entries: list[Entry], rng: random.Random) -> None:
        self._entries = list(entries)
        self._rng = rng
        self._bag: list[Entry] = []
        self._last: Entry | None = None

    def take(self) -> Entry:
        if not self._bag:
            self._bag = list(self._entries)
            self._rng.shuffle(self._bag)
            if len(self._bag) > 1 and self._bag[-1] == self._last:
                self._bag[-1], self._bag[0] = self._bag[0], self._bag[-1]
        entry = self._bag.pop()
        self._last = entry
        return entry


class _Source:
    def __init__(
        self,
        buckets: list[tuple[list[Entry], float]],
        rng: random.Random,
    ) -> None:
        prepared = [
            (_Bucket(entries, rng), float(weight))
            for entries, weight in buckets
            if entries and weight > 0
        ]
        if not prepared:
            raise ValueError("题目池为空，请换一个练习范围")
        self._buckets = prepared
        self._rng = rng

    def next(self) -> Entry:
        if len(self._buckets) == 1:
            return self._buckets[0][0].take()
        total = sum(weight for _, weight in self._buckets)
        point = self._rng.random() * total
        for bucket, weight in self._buckets:
            point -= weight
            if point <= 0:
                return bucket.take()
        return self._buckets[-1][0].take()


class _SequenceSource:
    """按固定顺序出题，用于文稿跟打。"""

    def __init__(self, entries: list[Entry]) -> None:
        self._entries = list(entries)
        self._index = 0

    def next(self) -> Entry:
        if self._index >= len(self._entries):
            raise StopIteration("题目已取完")
        entry = self._entries[self._index]
        self._index += 1
        return entry


class Session:
    """一组练习的完整状态机。

    - 输错不前进，计入错误数，必须重打当前字母；
    - 打满编码自动进入下一题；
    - 退格只撤回本字已输入的编码；
    - 跳过/出错较多的字会进入错题表，可单独重练。
    """

    def __init__(
        self,
        buckets: list[tuple[list[Entry], float]] | None = None,
        total: int | None = None,
        *,
        source: _Source | _SequenceSource | None = None,
        rng: random.Random | None = None,
        now=time.monotonic,
    ) -> None:
        self._rng = rng or random.Random()
        self._now = now
        if source is None:
            if not buckets:
                raise ValueError("题目池为空，请换一个练习范围")
            source = _Source(buckets, self._rng)
            if total is None:
                total = len(buckets[0][0])
        if total is None:
            raise ValueError("缺少题目数量")
        self._source = source
        self.total = max(1, int(total))
        self.index = 0
        self.current: Entry | None = self._source.next()
        self.typed: list[str] = []
        self.keystrokes = 0
        self.correct_keystrokes = 0
        self.errors = 0
        self.streak = 0
        self.best_streak = 0
        self.chars_completed = 0
        self.mistakes: list[Mistake] = []
        self.start_time: float | None = None
        self.end_time: float | None = None
        self.paused_total = 0.0
        self._pause_start: float | None = None
        self._item_errors = 0

    @property
    def is_paused(self) -> bool:
        return self._pause_start is not None

    def pause(self) -> None:
        if (
            self.start_time is None
            or self.is_finished
            or self._pause_start is not None
        ):
            return
        self._pause_start = self._now()

    def resume(self) -> None:
        if self._pause_start is None:
            return
        self.paused_total += self._now() - self._pause_start
        self._pause_start = None

    @classmethod
    def sequence(
        cls,
        entries,
        *,
        rng: random.Random | None = None,
        now=time.monotonic,
    ) -> "Session":
        entries = list(entries)
        if not entries:
            raise ValueError("文稿中没有可练习的汉字")
        return cls(
            total=len(entries),
            source=_SequenceSource(entries),
            rng=rng,
            now=now,
        )

    # -- 状态查询 -----------------------------------------------------
    @property
    def expected(self) -> str | None:
        if self.current is None or len(self.typed) >= len(self.current.code):
            return None
        return self.current.code[len(self.typed)]

    @property
    def is_finished(self) -> bool:
        return self.end_time is not None

    @property
    def elapsed(self) -> float:
        if self.start_time is None:
            return 0.0
        if self.end_time is not None:
            end = self.end_time
        elif self._pause_start is not None:
            end = self._pause_start
        else:
            end = self._now()
        return max(0.0, end - self.start_time - self.paused_total)

    @property
    def speed(self) -> float:
        """每分钟正确完成的字数。"""
        elapsed = self.elapsed
        if elapsed < 1.0 or self.chars_completed == 0:
            return 0.0
        return self.chars_completed / (elapsed / 60.0)

    @property
    def keystroke_speed(self) -> float:
        elapsed = self.elapsed
        if elapsed < 1.0:
            return 0.0
        return self.keystrokes / (elapsed / 60.0)

    @property
    def accuracy(self) -> float:
        if self.keystrokes == 0:
            return 100.0
        return self.correct_keystrokes / self.keystrokes * 100.0

    @property
    def progress(self) -> float:
        return self.index / self.total

    # -- 输入 ---------------------------------------------------------
    def _ensure_started(self) -> None:
        if self.start_time is None:
            self.start_time = self._now()

    def press(self, letter: str) -> PressResult:
        if self.is_finished or self.current is None:
            return PressResult.IGNORED
        letter = letter.lower()
        expected = self.expected
        if expected is None or len(letter) != 1:
            return PressResult.IGNORED
        self._ensure_started()
        self.keystrokes += 1
        if letter != expected:
            self.errors += 1
            self._item_errors += 1
            self.streak = 0
            return PressResult.WRONG

        self.correct_keystrokes += 1
        self.typed.append(letter)
        self.streak += 1
        self.best_streak = max(self.best_streak, self.streak)
        if len(self.typed) >= len(self.current.code):
            return self._complete_current()
        return PressResult.CORRECT

    def backspace(self) -> bool:
        if self.is_finished or not self.typed:
            return False
        self.typed.pop()
        return True

    def skip(self) -> PressResult:
        if self.is_finished:
            return PressResult.IGNORED
        self._ensure_started()
        return self._complete_current(skipped=True)

    def _complete_current(self, *, skipped: bool = False) -> PressResult:
        assert self.current is not None
        if self._item_errors or skipped:
            self.mistakes.append(
                Mistake(
                    text=self.current.text,
                    code=self.current.code,
                    errors=self._item_errors,
                    skipped=skipped,
                )
            )
        if not skipped:
            self.chars_completed += len(self.current.text)
        self.index += 1
        self.typed.clear()
        self._item_errors = 0
        if self.index >= self.total:
            self.end_time = self._now()
            self.current = None
            return PressResult.SESSION_DONE
        self.current = self._source.next()
        return PressResult.ITEM_DONE

    # -- 汇总 ---------------------------------------------------------
    def retry_items(self) -> list[Entry]:
        seen: set[tuple[str, str]] = set()
        items: list[Entry] = []
        for mistake in self.mistakes:
            key = (mistake.text, mistake.code)
            if key in seen:
                continue
            seen.add(key)
            items.append(Entry(mistake.text, mistake.code))
        return items

    def summary(self) -> dict[str, object]:
        return {
            "speed": round(self.speed, 1),
            "keystroke_speed": round(self.keystroke_speed, 1),
            "accuracy": round(self.accuracy, 1),
            "errors": self.errors,
            "keystrokes": self.keystrokes,
            "chars": self.chars_completed,
            "best_streak": self.best_streak,
            "elapsed": self.elapsed,
            "items": self.index,
            "mistakes": list(self.mistakes),
        }
