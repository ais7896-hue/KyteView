"""
KyteView i18n 多語言管理核心模組
"""
from __future__ import annotations

import ctypes
import locale
import os
from typing import Dict, Any, Optional
from PySide6.QtCore import QObject, Signal

from .zh_TW import TRANSLATIONS as ZH_TW_DICT
from .en_US import TRANSLATIONS as EN_US_DICT


def detect_system_language() -> str:
    """自動偵測 Windows 系統語言，中文環境返回 'zh_TW'，其餘返回 'en_US'"""
    try:
        lang_id = ctypes.windll.kernel32.GetUserDefaultUILanguage() & 0xFF
        if lang_id == 0x04:
            return "zh_TW"
    except Exception:
        pass

    try:
        loc = locale.getdefaultlocale()[0]
        if loc and loc.lower().startswith("zh"):
            return "zh_TW"
    except Exception:
        pass

    return "en_US"


class I18nManager(QObject):
    language_changed = Signal(str)
    _instance: Optional[I18nManager] = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if getattr(self, "_initialized", False):
            return
        super().__init__()
        self._initialized = True
        self._current_setting: str = "system"
        self._resolved_lang: str = "zh_TW"
        self._dictionaries: Dict[str, Dict[str, str]] = {
            "zh_TW": ZH_TW_DICT,
            "en_US": EN_US_DICT,
        }
        self.apply_language("system")

    @property
    def current_language(self) -> str:
        return self._resolved_lang

    @property
    def setting(self) -> str:
        return self._current_setting

    def apply_language(self, lang: str):
        self._current_setting = lang
        if lang == "system":
            self._resolved_lang = detect_system_language()
        elif lang in self._dictionaries:
            self._resolved_lang = lang
        else:
            self._resolved_lang = "en_US"
        self.language_changed.emit(self._resolved_lang)

    def translate(self, key: str, /, default: Optional[str] = None, **kwargs: Any) -> str:
        dic = self._dictionaries.get(self._resolved_lang, ZH_TW_DICT)
        text = dic.get(key)
        if text is None:
            text = ZH_TW_DICT.get(key, EN_US_DICT.get(key, default or key))

        if kwargs and isinstance(text, str):
            try:
                return text.format(**kwargs)
            except Exception:
                return text
        return text or ""


i18n = I18nManager()
t = i18n.translate


def set_language(lang: str):
    i18n.apply_language(lang)


def get_current_language() -> str:
    return i18n.current_language
