"""内置练习文章：扫描数据目录下的 text/ 文件夹。"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .data import default_data_dir

ARTICLE_PREFIX = "article:"


@dataclass(frozen=True, slots=True)
class Article:
    path: Path
    title: str

    @property
    def id(self) -> str:
        return ARTICLE_PREFIX + self.path.name

    @property
    def label(self) -> str:
        return f"文章：{self.title}"


def article_directory(data_dir: Path | None = None) -> Path | None:
    try:
        root = Path(data_dir) if data_dir else default_data_dir()
    except FileNotFoundError:
        return None
    directory = root / "text"
    return directory if directory.is_dir() else None


def load_articles(data_dir: Path | None = None) -> tuple[Article, ...]:
    directory = article_directory(data_dir)
    if directory is None:
        return ()
    paths = sorted(
        (path for path in directory.glob("*.txt") if path.is_file()),
        key=lambda path: path.stem,
    )
    return tuple(Article(path=path, title=path.stem) for path in paths)


def find_article(
    scope_id: str,
    data_dir: Path | None = None,
) -> Article | None:
    if not scope_id.startswith(ARTICLE_PREFIX):
        return None
    for article in load_articles(data_dir):
        if article.id == scope_id:
            return article
    return None
