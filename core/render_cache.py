"""
core/render_cache.py
LRU 快取渲染結果，避免重複讀檔與渲染。
key = (path, mtime)，檔案修改後自動失效。
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any, Optional


class RenderCache:
    """
    簡單 LRU 快取，key = (path_str, mtime)。
    maxsize 預設 32 個檔案，記憶體友善。
    """

    def __init__(self, maxsize: int = 32):
        self._maxsize = maxsize
        self._cache: dict[tuple[str, float], Any] = {}
        self._order: list[tuple[str, float]] = []

    def _make_key(self, path: Path) -> Optional[tuple[str, float]]:
        try:
            mtime = path.stat().st_mtime
            return (str(path), mtime)
        except OSError:
            return None

    def get(self, path: Path) -> Optional[Any]:
        key = self._make_key(path)
        if key is None:
            return None
        return self._cache.get(key)

    def set(self, path: Path, value: Any) -> None:
        key = self._make_key(path)
        if key is None:
            return
        if key in self._cache:
            self._order.remove(key)
        elif len(self._cache) >= self._maxsize:
            oldest = self._order.pop(0)
            self._cache.pop(oldest, None)
        self._cache[key] = value
        self._order.append(key)

    def invalidate(self, path: Path) -> None:
        path_str = str(path)
        keys_to_remove = [k for k in self._cache if k[0] == path_str]
        for k in keys_to_remove:
            self._cache.pop(k)
            if k in self._order:
                self._order.remove(k)

    def clear(self) -> None:
        self._cache.clear()
        self._order.clear()


# 全域單例
cache = RenderCache(maxsize=32)
