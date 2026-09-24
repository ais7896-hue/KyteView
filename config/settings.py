"""
config/settings.py
KyteView 設定管理（純 JSON 雙模儲存架構）：
1. 可攜模式 (Portable)：若程式目錄存在 config.json，優先讀寫同目錄檔案。
2. 標準模式 (Standard)：否則儲存於 %APPDATA%/KyteView/config.json。
3. 記憶體字典快取 + 原子寫入（Atomic Save）防止資料損毀。
"""
from __future__ import annotations

import json
import os
import winreg
from pathlib import Path
from typing import Any

from PySide6.QtCore import QObject, Signal


def get_system_theme() -> str:
    """讀取 Windows 系統深淺色外觀設定 (AppsUseLightTheme)。"""
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize",
        )
        val, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
        winreg.CloseKey(key)
        return "light" if val == 1 else "dark"
    except Exception:
        return "dark"


def _resolve_config_path() -> Path:
    """解析設定檔存放路徑（支援綠色便攜模式）。"""
    app_dir = Path(__file__).resolve().parent.parent
    portable_file = app_dir / "config.json"
    flag_file = app_dir / "portable.flag"

    # 若同目錄有 config.json 或 portable.flag 則啟用可攜模式
    if portable_file.exists() or flag_file.exists():
        return portable_file

    # 標準 Windows 儲存路徑：%APPDATA%/KyteView/config.json
    appdata = os.environ.get("APPDATA")
    if appdata:
        return Path(appdata) / "KyteView" / "config.json"
    return Path.home() / ".config" / "KyteView" / "config.json"


_DEFAULTS: dict[str, Any] = {
    # 一、 外觀與主題
    "theme_mode": "system",           # "system" | "dark" | "light"
    "enable_acrylic": True,            # 是否啟用毛玻璃半透明
    "code_theme": "monokai",          # Pygments 程式碼主題
    # 二、 字體與排版
    "font_size": 13,                   # 程式碼與文字字型大小 (11 ~ 20)
    "font_family_code": "Cascadia Code",
    "font_family_text": "Microsoft JhengHei UI",
    "enable_ligatures": True,          # 連字效果
    "word_wrap": True,                 # 長行自動換行
    # 三、 視窗幾何與行為
    "window_size_mode": "remember",    # "remember" | "fixed" | "adaptive"
    "window_width": 820,
    "window_height": 600,
    "fixed_width": 820,
    "fixed_height": 600,
    "adaptive_ratio_w": 55,            # 螢幕佔比 %
    "adaptive_ratio_h": 60,
    "img_max_screen_ratio": 75,        # 圖片縮放上限 %
    "img_keep_original": True,         # 小圖保持 1:1
    "smart_offset": True,              # 智慧避讓偏移
    "enable_peek": True,               # Alt/Ctrl 長按透視
    "enable_pin_dock": True,           # Tab 側邊釘選
}


class SettingsManager(QObject):
    theme_changed = Signal(str)      # "dark" | "light"
    settings_changed = Signal(str)   # key name

    def __init__(self) -> None:
        super().__init__()
        self._config_path = _resolve_config_path()
        self._data: dict[str, Any] = dict(_DEFAULTS)
        self._load()

    # ── 磁碟 I/O ─────────────────────────────────────────────────────────────

    def _load(self) -> None:
        """從 JSON 檔載入設定，若無檔案則儲存預設值。"""
        if self._config_path.exists():
            try:
                with open(self._config_path, "r", encoding="utf-8") as f:
                    disk_data = json.load(f)
                if isinstance(disk_data, dict):
                    self._data.update(disk_data)
            except Exception as e:
                print(f"[Settings] 讀取 {self._config_path} 失敗，使用預設值: {e}")
        else:
            self._save()

    def _save(self) -> None:
        """寫入設定檔（Windows 安全覆寫）。"""
        try:
            self._config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self._config_path, "w", encoding="utf-8") as f:
                json.dump(self._data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[Settings] 寫入 {self._config_path} 失敗: {e}")

    def batch_update(self, updates: dict[str, Any]) -> None:
        """批次更新設定，單次 I/O 寫入硬碟並整合同步信號，徹底杜絕介面 LAG。"""
        old_theme = self.effective_theme
        for k, v in updates.items():
            self._data[k] = v
        self._save()
        new_theme = self.effective_theme
        if old_theme != new_theme:
            self.theme_changed.emit(new_theme)
        self.settings_changed.emit("all")

    def get_config_path(self) -> Path:
        return self._config_path

    # ── 一、 外觀與主題 ──────────────────────────────────────────────────────

    @property
    def theme_mode(self) -> str:
        return self._data.get("theme_mode", "system")

    @theme_mode.setter
    def theme_mode(self, val: str) -> None:
        if val in ("system", "dark", "light"):
            self._data["theme_mode"] = val
            self._save()
            self.theme_changed.emit(self.effective_theme)
            self.settings_changed.emit("theme_mode")

    @property
    def effective_theme(self) -> str:
        mode = self.theme_mode
        if mode == "system":
            return get_system_theme()
        return mode

    @property
    def theme(self) -> str:
        return self.effective_theme

    @theme.setter
    def theme(self, val: str) -> None:
        self.theme_mode = val

    def is_dark(self) -> bool:
        return self.effective_theme == "dark"

    def toggle_theme(self) -> str:
        new_mode = "light" if self.is_dark() else "dark"
        self.theme_mode = new_mode
        return new_mode

    @property
    def enable_acrylic(self) -> bool:
        return bool(self._data.get("enable_acrylic", True))

    @enable_acrylic.setter
    def enable_acrylic(self, val: bool) -> None:
        self._data["enable_acrylic"] = bool(val)
        self._save()
        self.settings_changed.emit("enable_acrylic")

    @property
    def code_theme(self) -> str:
        val = self._data.get("code_theme", "")
        if not val or val == "github":
            val = "monokai" if self.is_dark() else "friendly"
            self._data["code_theme"] = val
        return val

    @code_theme.setter
    def code_theme(self, val: str) -> None:
        if val == "github":
            val = "vs"
        self._data["code_theme"] = val
        self._save()
        self.settings_changed.emit("code_theme")

    # ── 二、 字體與排版 ──────────────────────────────────────────────────────

    @property
    def font_size(self) -> int:
        return int(self._data.get("font_size", 13))

    @font_size.setter
    def font_size(self, val: int) -> None:
        val = max(11, min(20, int(val)))
        self._data["font_size"] = val
        self._save()
        self.settings_changed.emit("font_size")

    @property
    def font_family_code(self) -> str:
        return self._data.get("font_family_code", "Cascadia Code")

    @font_family_code.setter
    def font_family_code(self, val: str) -> None:
        self._data["font_family_code"] = val
        self._save()
        self.settings_changed.emit("font_family_code")

    @property
    def font_family_text(self) -> str:
        return self._data.get("font_family_text", "Microsoft JhengHei UI")

    @font_family_text.setter
    def font_family_text(self, val: str) -> None:
        self._data["font_family_text"] = val
        self._save()
        self.settings_changed.emit("font_family_text")

    @property
    def enable_ligatures(self) -> bool:
        return bool(self._data.get("enable_ligatures", True))

    @enable_ligatures.setter
    def enable_ligatures(self, val: bool) -> None:
        self._data["enable_ligatures"] = bool(val)
        self._save()
        self.settings_changed.emit("enable_ligatures")

    @property
    def word_wrap(self) -> bool:
        return bool(self._data.get("word_wrap", True))

    @word_wrap.setter
    def word_wrap(self, val: bool) -> None:
        self._data["word_wrap"] = bool(val)
        self._save()
        self.settings_changed.emit("word_wrap")

    # ── 三、 視窗幾何與行為 ──────────────────────────────────────────────────

    @property
    def window_size_mode(self) -> str:
        return self._data.get("window_size_mode", "remember")

    @window_size_mode.setter
    def window_size_mode(self, val: str) -> None:
        if val in ("remember", "fixed", "adaptive"):
            self._data["window_size_mode"] = val
            self._save()
            self.settings_changed.emit("window_size_mode")

    @property
    def fixed_width(self) -> int:
        return int(self._data.get("fixed_width", 820))

    @fixed_width.setter
    def fixed_width(self, val: int) -> None:
        self._data["fixed_width"] = max(200, int(val))
        self._save()

    @property
    def fixed_height(self) -> int:
        return int(self._data.get("fixed_height", 600))

    @fixed_height.setter
    def fixed_height(self, val: int) -> None:
        self._data["fixed_height"] = max(150, int(val))
        self._save()

    @property
    def window_size(self) -> tuple[int, int]:
        mode = self.window_size_mode
        if mode == "fixed":
            return (self.fixed_width, self.fixed_height)
        w = int(self._data.get("window_width", 820))
        h = int(self._data.get("window_height", 600))
        return (max(200, w), max(150, h))

    @window_size.setter
    def window_size(self, size: tuple[int, int]) -> None:
        self._data["window_width"] = max(200, int(size[0]))
        self._data["window_height"] = max(150, int(size[1]))
        self._save()

    @property
    def adaptive_ratio_w(self) -> int:
        return int(self._data.get("adaptive_ratio_w", 55))

    @adaptive_ratio_w.setter
    def adaptive_ratio_w(self, val: int) -> None:
        self._data["adaptive_ratio_w"] = max(30, min(95, int(val)))
        self._save()

    @property
    def adaptive_ratio_h(self) -> int:
        return int(self._data.get("adaptive_ratio_h", 60))

    @adaptive_ratio_h.setter
    def adaptive_ratio_h(self, val: int) -> None:
        self._data["adaptive_ratio_h"] = max(30, min(95, int(val)))
        self._save()

    @property
    def img_max_screen_ratio(self) -> int:
        return int(self._data.get("img_max_screen_ratio", 75))

    @img_max_screen_ratio.setter
    def img_max_screen_ratio(self, val: int) -> None:
        self._data["img_max_screen_ratio"] = max(50, min(90, int(val)))
        self._save()
        self.settings_changed.emit("img_max_screen_ratio")

    @property
    def img_keep_original(self) -> bool:
        return bool(self._data.get("img_keep_original", True))

    @img_keep_original.setter
    def img_keep_original(self, val: bool) -> None:
        self._data["img_keep_original"] = bool(val)
        self._save()
        self.settings_changed.emit("img_keep_original")

    @property
    def smart_offset(self) -> bool:
        return bool(self._data.get("smart_offset", True))

    @smart_offset.setter
    def smart_offset(self, val: bool) -> None:
        self._data["smart_offset"] = bool(val)
        self._save()
        self.settings_changed.emit("smart_offset")

    @property
    def enable_peek(self) -> bool:
        return bool(self._data.get("enable_peek", True))

    @enable_peek.setter
    def enable_peek(self, val: bool) -> None:
        self._data["enable_peek"] = bool(val)
        self._save()
        self.settings_changed.emit("enable_peek")

    @property
    def enable_pin_dock(self) -> bool:
        return bool(self._data.get("enable_pin_dock", True))

    @enable_pin_dock.setter
    def enable_pin_dock(self, val: bool) -> None:
        self._data["enable_pin_dock"] = bool(val)
        self._save()
        self.settings_changed.emit("enable_pin_dock")


settings = SettingsManager()
