"""
renderers/base.py
抽象 Renderer 介面，所有 Renderer 必須繼承此類。
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from PySide6.QtWidgets import QWidget


class BaseRenderer(ABC):
    """
    每個 Renderer 負責：
    1. render(path) → 回傳一個 QWidget 供 PreviewWindow 顯示
    2. （可選）cleanup() → 釋放資源
    """

    @abstractmethod
    def render(self, path: Path) -> QWidget:
        """
        讀取 path 並回傳填好內容的 QWidget。
        此方法應在主執行緒呼叫。
        """
        ...

    def cleanup(self) -> None:
        """釋放 renderer 持有的資源（可選實作）。"""
        pass

    @property
    def name(self) -> str:
        return self.__class__.__name__
