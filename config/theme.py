"""
config/theme.py
全域深色/淺色主題樣式設定。
"""
from __future__ import annotations

from config.settings import settings


def get_theme_colors(theme: str | None = None) -> dict[str, str]:
    if theme is None:
        theme = settings.effective_theme

    if theme == "light":
        d = {
            "window_bg": "rgba(245, 246, 248, 0.96)",
            "window_border": "rgba(0, 0, 0, 0.12)",
            "title_color": "#1f2937",
            "subtitle_color": "#6b7280",
            "btn_color": "#4b5563",
            "btn_hover": "rgba(0, 0, 0, 0.08)",
            "btn_close_hover": "rgba(239, 68, 68, 0.15)",
            "btn_close_hover_text": "#dc2626",
            "sep_color": "rgba(0, 0, 0, 0.08)",
            "text_color": "#1f2937",
            "code_style": "friendly",
            "code_bg": "#ffffff",
            "table_bg": "#ffffff",
            "table_alt_bg": "#f9fafb",
            "table_text": "#111827",
            "table_grid": "rgba(0, 0, 0, 0.06)",
            "table_header_bg": "#f3f4f6",
            "table_header_text": "#4b5563",
            "table_select_bg": "#dbeafe",
            "audio_unplayed": "#e5e7eb",
            "audio_played": "#4f46e5",
            "audio_text": "#4b5563",
        }
    else:
        d = {
            "window_bg": "rgba(18, 18, 20, 0.95)",
            "window_border": "rgba(255, 255, 255, 0.12)",
            "title_color": "#f3f4f6",
            "subtitle_color": "#888888",
            "btn_color": "#888888",
            "btn_hover": "rgba(255, 255, 255, 0.1)",
            "btn_close_hover": "rgba(255, 80, 80, 0.3)",
            "btn_close_hover_text": "#ff6b6b",
            "sep_color": "rgba(255, 255, 255, 0.06)",
            "text_color": "#d4d4d4",
            "code_style": "monokai",
            "code_bg": "#121214",
            "table_bg": "#18181b",
            "table_alt_bg": "#1f1f23",
            "table_text": "#d1d5db",
            "table_grid": "rgba(255, 255, 255, 0.06)",
            "table_header_bg": "#27272a",
            "table_header_text": "#9ca3af",
            "table_select_bg": "#2b3b55",
            "audio_unplayed": "#2e2e38",
            "audio_played": "#6366f1",
            "audio_text": "#9ca3af",
        }

    # 程式碼高亮風格
    custom_code_style = getattr(settings, "code_theme", None)
    if custom_code_style:
        d["code_style"] = custom_code_style

    return d
