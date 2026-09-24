"""
renderers/pptx_renderer.py
KyteView PowerPoint 簡報極速瀏覽器：
- 支援 .pptx, .ppt
- 核心效能捷徑：優先讀取 .pptx 內建 docProps/thumbnail.jpeg 封面縮圖（2~5ms 秒開）。
- 多頁投影片大綱與文字要點解析（python-pptx 輕量原生）。
- 專屬 16:9 / 4:3 簡報畫布比例與深淺主題適配。
- 底部懸浮翻頁膠囊（Page Navigator），支援 PageUp/Down、左右鍵、滾輪翻頁。
- 舊版 .ppt 二進位格式優雅降級為簡報屬性卡片。
"""
from __future__ import annotations

import os
import subprocess
import zipfile
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, QSize, QByteArray, Signal
from PySide6.QtGui import QPixmap, QImage, QKeyEvent, QWheelEvent, QFont, QCursor
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QStackedWidget, QTextBrowser, QFrame, QSizePolicy, QApplication,
)

from renderers.base import BaseRenderer
from config.settings import settings
from config.theme import get_theme_colors


@dataclass
class SlideData:
    index: int
    title: str
    bullets: list[str]
    image_bytes: Optional[bytes] = None


def _format_size(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"


def _extract_thumbnail(path: Path) -> Optional[bytes]:
    """2~5ms 瞬開：自 .pptx 讀取封面預覽圖。"""
    try:
        with zipfile.ZipFile(path, "r") as zf:
            namelist = zf.namelist()
            for cand in ("docProps/thumbnail.jpeg", "docProps/thumbnail.jpg", "docProps/thumbnail.png"):
                if cand in namelist:
                    return zf.read(cand)
    except Exception:
        pass
    return None


def _get_slide_ratio(path: Path) -> tuple[float, str]:
    """從 presentation.xml 讀取投影片比例（16:9 或 4:3）。"""
    try:
        with zipfile.ZipFile(path, "r") as zf:
            if "ppt/presentation.xml" in zf.namelist():
                xml_data = zf.read("ppt/presentation.xml")
                root = ET.fromstring(xml_data)
                for elem in root.iter():
                    if elem.tag.endswith("sldSz"):
                        cx = int(elem.attrib.get("cx", 0))
                        cy = int(elem.attrib.get("cy", 0))
                        if cx > 0 and cy > 0:
                            ratio = cx / cy
                            ratio_label = "16:9" if abs(ratio - 16 / 9) < 0.15 else ("4:3" if abs(ratio - 4 / 3) < 0.15 else f"{ratio:.2f}:1")
                            return ratio, ratio_label
    except Exception:
        pass
    return 16 / 9, "16:9"


# ── 舊版 .ppt 降級卡片 ────────────────────────────────────────────────────────
class _PptLegacyWidget(QWidget):
    """舊版 Office 97-2003 .ppt 二進位格式降級卡片。"""
    def __init__(self, path: Path, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._path = path
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(16)

        c = get_theme_colors()
        is_dark = settings.is_dark()

        # 簡報圖示
        lbl_icon = QLabel("📊")
        lbl_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_icon.setStyleSheet("font-size: 54px;")
        layout.addWidget(lbl_icon)

        # 檔名
        lbl_name = QLabel(path.name)
        lbl_name.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_name.setWordWrap(True)
        lbl_name.setStyleSheet(f"font-size: 16px; font-weight: 600; color: {c['title_color']};")
        layout.addWidget(lbl_name)

        # 檔案資訊
        try:
            sz_str = _format_size(path.stat().st_size)
            dt_str = datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
        except OSError:
            sz_str, dt_str = "—", "—"

        lbl_desc = QLabel(
            f"舊版 PowerPoint 簡報 (Office 97-2003 二進位格式)\n"
            f"檔案大小：{sz_str}   ·   修改日期：{dt_str}\n\n"
            f"建議使用微軟 PowerPoint 或預設程式開啟完整檢視"
        )
        lbl_desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_desc.setStyleSheet(f"color: {c['subtitle_color']}; font-size: 13px; line-height: 1.6;")
        layout.addWidget(lbl_desc)

        # 開啟按鈕
        btn_open = QPushButton("↗  使用系統預設程式開啟 (Enter)")
        btn_open.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_open.setFixedHeight(36)
        btn_open.setStyleSheet(f"""
            QPushButton {{
                background: {'#6366f1' if is_dark else '#4f46e5'};
                color: #ffffff;
                border-radius: 8px;
                padding: 0 20px;
                font-size: 13px;
                font-weight: 600;
                border: none;
            }}
            QPushButton:hover {{
                background: {'#4f46e5' if is_dark else '#4338ca'};
            }}
        """)
        btn_open.clicked.connect(self._open_external)
        layout.addWidget(btn_open, alignment=Qt.AlignmentFlag.AlignCenter)

    def _open_external(self) -> None:
        try:
            subprocess.Popen(["explorer", str(self._path.resolve())], shell=True)
        except Exception:
            pass

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self._open_external()
            return
        super().keyPressEvent(event)


# ── 主 PPTX 預覽畫面 ──────────────────────────────────────────────────────────
class PptxBrowserWidget(QWidget):
    """PPTX 投影片現代極速瀏覽器。"""
    def __init__(self, path: Path, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._path = path
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        self._ratio, self._ratio_label = _get_slide_ratio(path)
        self._thumb_bytes = _extract_thumbnail(path)
        self._slides: list[SlideData] = []
        self._current_index = 0
        self._view_mode = "cover"  # "cover" 或 "outline"

        self._load_slides_content()
        self._build_ui()
        self._update_slide_display()

    def _load_slides_content(self) -> None:
        """使用 python-pptx 輕量解析投影片標題與文字大綱。"""
        try:
            from pptx import Presentation
            prs = Presentation(str(self._path))
            for i, slide in enumerate(prs.slides):
                title = ""
                bullets: list[str] = []
                image_bytes: Optional[bytes] = None

                for shape in slide.shapes:
                    if shape.has_text_frame:
                        txt = shape.text.strip()
                        if not txt:
                            continue
                        if not title and (shape == slide.shapes[0] or len(txt) <= 60 and "\n" not in txt):
                            title = txt
                        else:
                            for p in shape.text_frame.paragraphs:
                                p_txt = p.text.strip()
                                if p_txt and p_txt != title and p_txt not in bullets:
                                    bullets.append(p_txt)

                    # 取得投影片配圖
                    if image_bytes is None and shape.shape_type == 13:  # MSO_SHAPE_TYPE.PICTURE
                        try:
                            image_bytes = shape.image.blob
                        except Exception:
                            pass

                if not title:
                    title = f"投影片 {i + 1}"

                self._slides.append(SlideData(
                    index=i + 1,
                    title=title,
                    bullets=bullets,
                    image_bytes=image_bytes,
                ))
        except Exception as e:
            print(f"[PPTX] 大綱解析略過: {e}")

        # 若無多頁大綱但有封面，仍建立第一頁
        if not self._slides:
            self._slides.append(SlideData(
                index=1,
                title=self._path.stem,
                bullets=[],
                image_bytes=self._thumb_bytes,
            ))

    def _build_ui(self) -> None:
        c = get_theme_colors()
        is_dark = settings.is_dark()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 8, 14, 10)
        layout.setSpacing(8)

        # 頂部小列：視圖切換（若有封面縮圖且有大綱時提供切換）
        top_bar = QHBoxLayout()
        top_bar.setContentsMargins(0, 0, 0, 0)

        self._lbl_page_badge = QLabel("Slide 1")
        self._lbl_page_badge.setStyleSheet(f"""
            QLabel {{
                background-color: {'rgba(99, 102, 241, 0.15)' if is_dark else 'rgba(79, 70, 229, 0.10)'};
                color: {'#a5b4fc' if is_dark else '#4f46e5'};
                border-radius: 4px;
                padding: 2px 8px;
                font-size: 11px;
                font-weight: 600;
            }}
        """)
        top_bar.addWidget(self._lbl_page_badge)
        top_bar.addStretch()

        if self._thumb_bytes:
            self._btn_toggle_view = QPushButton("📄 切換大綱檢視")
            self._btn_toggle_view.setCursor(Qt.CursorShape.PointingHandCursor)
            self._btn_toggle_view.setFixedHeight(24)
            self._btn_toggle_view.setStyleSheet(f"""
                QPushButton {{
                    background: transparent;
                    color: {c['subtitle_color']};
                    border: 1px solid {'rgba(255, 255, 255, 0.12)' if is_dark else 'rgba(0, 0, 0, 0.12)'};
                    border-radius: 5px;
                    padding: 0 10px;
                    font-size: 11px;
                }}
                QPushButton:hover {{
                    background: {'rgba(255, 255, 255, 0.08)' if is_dark else 'rgba(0, 0, 0, 0.05)'};
                    color: {c['title_color']};
                }}
            """)
            self._btn_toggle_view.clicked.connect(self._toggle_view_mode)
            top_bar.addWidget(self._btn_toggle_view)

        layout.addLayout(top_bar)

        # 中央畫布區（16:9 或 4:3 比例展示）
        self._stack = QStackedWidget()
        self._stack.setStyleSheet("background: transparent;")

        # Page 0: 封面全彩影像視圖
        self._cover_container = QWidget()
        cover_layout = QVBoxLayout(self._cover_container)
        cover_layout.setContentsMargins(0, 0, 0, 0)
        self._lbl_cover_img = QLabel()
        self._lbl_cover_img.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._lbl_cover_img.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored)
        cover_layout.addWidget(self._lbl_cover_img)
        self._stack.addWidget(self._cover_container)

        # Page 1: 投影片大綱卡片視圖
        self._outline_container = QFrame()
        self._outline_container.setObjectName("outline_card")
        card_bg = "rgba(255, 255, 255, 0.04)" if is_dark else "rgba(0, 0, 0, 0.02)"
        card_border = "rgba(255, 255, 255, 0.08)" if is_dark else "rgba(0, 0, 0, 0.08)"
        self._outline_container.setStyleSheet(f"""
            QFrame#outline_card {{
                background-color: {card_bg};
                border: 1px solid {card_border};
                border-radius: 8px;
            }}
        """)
        outline_layout = QVBoxLayout(self._outline_container)
        outline_layout.setContentsMargins(20, 16, 20, 16)
        outline_layout.setSpacing(12)

        self._lbl_slide_title = QLabel("投影片標題")
        self._lbl_slide_title.setStyleSheet(f"""
            color: {c['title_color']};
            font-size: 17px;
            font-weight: 700;
        """)
        self._lbl_slide_title.setWordWrap(True)
        outline_layout.addWidget(self._lbl_slide_title)

        content_row = QHBoxLayout()
        content_row.setSpacing(16)

        self._txt_bullets = QTextBrowser()
        self._txt_bullets.setFrameShape(QFrame.Shape.NoFrame)
        self._txt_bullets.setStyleSheet("background: transparent; font-size: 13px; line-height: 1.6;")
        content_row.addWidget(self._txt_bullets, 2)

        self._lbl_slide_pic = QLabel()
        self._lbl_slide_pic.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._lbl_slide_pic.setVisible(False)
        self._lbl_slide_pic.setStyleSheet("border-radius: 6px; background: rgba(0,0,0,0.1);")
        content_row.addWidget(self._lbl_slide_pic, 1)

        outline_layout.addLayout(content_row, 1)
        self._stack.addWidget(self._outline_container)

        layout.addWidget(self._stack, 1)

        # 底部懸浮翻頁膠囊（Page Navigator）
        nav_box = QHBoxLayout()
        nav_box.setContentsMargins(4, 2, 4, 0)
        nav_box.setSpacing(8)

        # 摘要資訊
        total_p = len(self._slides)
        try:
            sz_str = _format_size(self._path.stat().st_size)
        except OSError:
            sz_str = "—"
        self._lbl_summary = QLabel(f"共 {total_p} 張投影片 · {self._ratio_label} 比例 · {sz_str}")
        self._lbl_summary.setStyleSheet(f"color: {c['subtitle_color']}; font-size: 11px;")
        nav_box.addWidget(self._lbl_summary)

        nav_box.addStretch()

        # 翻頁膠囊
        capsule = QFrame()
        capsule.setObjectName("capsule")
        cap_bg = "rgba(255, 255, 255, 0.08)" if is_dark else "rgba(0, 0, 0, 0.06)"
        cap_border = "rgba(255, 255, 255, 0.12)" if is_dark else "rgba(0, 0, 0, 0.10)"
        capsule.setStyleSheet(f"""
            QFrame#capsule {{
                background-color: {cap_bg};
                border: 1px solid {cap_border};
                border-radius: 14px;
            }}
            QPushButton {{
                background: transparent;
                color: {c['title_color']};
                border: none;
                font-size: 12px;
                font-weight: 700;
                width: 26px;
                height: 24px;
                border-radius: 12px;
            }}
            QPushButton:hover {{
                background: {'rgba(255, 255, 255, 0.15)' if is_dark else 'rgba(0, 0, 0, 0.08)'};
            }}
        """)
        cap_layout = QHBoxLayout(capsule)
        cap_layout.setContentsMargins(4, 2, 8, 2)
        cap_layout.setSpacing(4)

        self._btn_prev = QPushButton("◀")
        self._btn_prev.setToolTip("上一張 (Left / PageUp)")
        self._btn_prev.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_prev.clicked.connect(self.prev_slide)
        cap_layout.addWidget(self._btn_prev)

        self._lbl_page_num = QLabel(f"Slide 1 / {total_p}")
        self._lbl_page_num.setStyleSheet(f"color: {c['title_color']}; font-size: 11px; font-weight: 600; padding: 0 4px;")
        cap_layout.addWidget(self._lbl_page_num)

        self._btn_next = QPushButton("▶")
        self._btn_next.setToolTip("下一張 (Right / PageDown)")
        self._btn_next.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_next.clicked.connect(self.next_slide)
        cap_layout.addWidget(self._btn_next)

        nav_box.addWidget(capsule)
        layout.addLayout(nav_box)

    def _toggle_view_mode(self) -> None:
        """在視覺封面與大綱視圖間手動切換。"""
        if self._view_mode == "cover":
            self._view_mode = "outline"
            self._btn_toggle_view.setText("🖼️ 切換封面檢視")
        else:
            self._view_mode = "cover"
            self._btn_toggle_view.setText("📄 切換大綱檢視")
        self._update_slide_display()

    def _update_slide_display(self) -> None:
        if not self._slides:
            return

        total = len(self._slides)
        slide = self._slides[self._current_index]
        self._lbl_page_num.setText(f"Slide {self._current_index + 1} / {total}")
        self._lbl_page_badge.setText(f"Slide {self._current_index + 1} of {total}")
        self._btn_prev.setEnabled(self._current_index > 0)
        self._btn_next.setEnabled(self._current_index < total - 1)

        # 首頁若有縮圖且處於 cover 模式，顯示封面圖
        if self._current_index == 0 and self._thumb_bytes and self._view_mode == "cover":
            self._stack.setCurrentWidget(self._cover_container)
            self._render_cover_image()
            if hasattr(self, "_btn_toggle_view"):
                self._btn_toggle_view.setVisible(True)
                self._btn_toggle_view.setText("📄 切換大綱檢視")
        else:
            # 顯示大綱內容
            self._stack.setCurrentWidget(self._outline_container)
            if hasattr(self, "_btn_toggle_view"):
                self._btn_toggle_view.setVisible(self._thumb_bytes is not None and self._current_index == 0)

            c = get_theme_colors()
            is_dark = settings.is_dark()
            bullet_color = c['subtitle_color']
            txt_color = c['title_color']

            self._lbl_slide_title.setText(slide.title)

            # 產生排版精美的 HTML 清單
            if slide.bullets:
                html_items = "".join(f"<li style='margin-bottom: 8px; color: {txt_color};'>{item}</li>" for item in slide.bullets)
                html = f"""
                <ul style='margin-left: -15px; padding-left: 20px; line-height: 1.6; color: {bullet_color};'>
                    {html_items}
                </ul>
                """
            else:
                html = f"<p style='color: {bullet_color}; font-style: italic; margin-top: 10px;'>此投影片以圖表或圖像為主，無主要文字要點</p>"

            self._txt_bullets.setHtml(html)

            # 插圖展示
            if slide.image_bytes:
                pix = QPixmap()
                pix.loadFromData(slide.image_bytes)
                if not pix.isNull():
                    scaled_pix = pix.scaled(240, 200, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                    self._lbl_slide_pic.setPixmap(scaled_pix)
                    self._lbl_slide_pic.setVisible(True)
                else:
                    self._lbl_slide_pic.setVisible(False)
            else:
                self._lbl_slide_pic.setVisible(False)

    def _render_cover_image(self) -> None:
        if not self._thumb_bytes:
            return
        pix = QPixmap()
        pix.loadFromData(self._thumb_bytes)
        if not pix.isNull():
            w = max(200, self._lbl_cover_img.width())
            h = max(150, self._lbl_cover_img.height())
            scaled = pix.scaled(w, h, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            self._lbl_cover_img.setPixmap(scaled)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if self._current_index == 0 and self._thumb_bytes and self._view_mode == "cover":
            self._render_cover_image()

    def prev_slide(self) -> None:
        if self._current_index > 0:
            self._current_index -= 1
            # 翻到非首頁自動切為大綱，回首頁可回到封面
            if self._current_index > 0:
                self._view_mode = "outline"
            self._update_slide_display()

    def next_slide(self) -> None:
        if self._current_index < len(self._slides) - 1:
            self._current_index += 1
            if self._current_index > 0:
                self._view_mode = "outline"
            self._update_slide_display()

    def keyPressEvent(self, event: QKeyEvent) -> None:
        key = event.key()
        if key in (Qt.Key.Key_PageDown, Qt.Key.Key_Right, Qt.Key.Key_Down, Qt.Key.Key_Space):
            self.next_slide()
            event.accept()
        elif key in (Qt.Key.Key_PageUp, Qt.Key.Key_Left, Qt.Key.Key_Up):
            self.prev_slide()
            event.accept()
        elif key == Qt.Key.Key_Home:
            self._current_index = 0
            self._update_slide_display()
            event.accept()
        elif key == Qt.Key.Key_End:
            self._current_index = max(0, len(self._slides) - 1)
            self._update_slide_display()
            event.accept()
        else:
            super().keyPressEvent(event)

    def wheelEvent(self, event: QWheelEvent) -> None:
        delta = event.angleDelta().y()
        if delta < -30:
            self.next_slide()
            event.accept()
        elif delta > 30:
            self.prev_slide()
            event.accept()
        else:
            super().wheelEvent(event)


def _extract_pptx_meta(path: Path) -> dict:
    meta = {
        "creator": "未知",
        "modified": "未知",
        "created": "未知",
        "slides": "未知",
    }
    try:
        with zipfile.ZipFile(path, "r") as zf:
            nl = zf.namelist()
            if "docProps/core.xml" in nl:
                root = ET.fromstring(zf.read("docProps/core.xml"))
                for elem in root.iter():
                    tag = elem.tag.lower()
                    if tag.endswith("creator") and elem.text:
                        meta["creator"] = elem.text.strip()
                    elif tag.endswith("created") and elem.text:
                        meta["created"] = elem.text.replace("T", " ").replace("Z", "")[:19]
                    elif tag.endswith("modified") and elem.text:
                        meta["modified"] = elem.text.replace("T", " ").replace("Z", "")[:19]
            if "docProps/app.xml" in nl:
                root = ET.fromstring(zf.read("docProps/app.xml"))
                for elem in root.iter():
                    tag = elem.tag.lower()
                    if tag.endswith("slides") and elem.text:
                        meta["slides"] = elem.text.strip()
    except Exception:
        pass
    return meta


class _PptxProCardWidget(QWidget):
    """免費版降級模式：顯示封面縮圖、簡報屬性卡片（頁數、作者、時間）與專業版解鎖引導。"""
    def __init__(self, path: Path, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._path = path
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(12)

        is_dark = settings.is_dark()
        c = get_theme_colors()

        # 1. 嘗試載入封面縮圖
        thumb_bytes = _extract_thumbnail(path)
        if thumb_bytes:
            qimg = QImage.fromData(thumb_bytes)
            if not qimg.isNull():
                lbl_thumb = QLabel()
                pix = QPixmap.fromImage(qimg)
                lbl_thumb.setPixmap(pix.scaled(440, 248, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
                lbl_thumb.setAlignment(Qt.AlignmentFlag.AlignCenter)
                lbl_thumb.setStyleSheet("""
                    QLabel {
                        border: 1px solid rgba(255, 255, 255, 0.12);
                        border-radius: 8px;
                        background: #000000;
                    }
                """)
                layout.addWidget(lbl_thumb)
            else:
                lbl_icon = QLabel("📊")
                lbl_icon.setFont(QFont("Segoe UI Emoji", 40))
                lbl_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
                layout.addWidget(lbl_icon)
        else:
            lbl_icon = QLabel("📊")
            lbl_icon.setFont(QFont("Segoe UI Emoji", 40))
            lbl_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(lbl_icon)

        title_lbl = QLabel(path.name)
        title_lbl.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        title_lbl.setStyleSheet(f"color: {c.text};")
        title_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_lbl)

        meta = _extract_pptx_meta(path)
        try:
            size_kb = path.stat().st_size / 1024
            size_str = f"{size_kb:.1f} KB" if size_kb < 1024 else f"{size_kb/1024:.1f} MB"
        except Exception:
            size_str = "未知大小"

        card = QFrame()
        card.setFixedWidth(380)
        card_bg = "rgba(255, 255, 255, 0.04)" if is_dark else "rgba(0, 0, 0, 0.03)"
        card_border = "rgba(255, 255, 255, 0.08)" if is_dark else "rgba(0, 0, 0, 0.08)"
        card.setStyleSheet(f"""
            QFrame {{
                background: {card_bg};
                border: 1px solid {card_border};
                border-radius: 8px;
                padding: 10px 16px;
            }}
        """)
        c_layout = QVBoxLayout(card)
        c_layout.setSpacing(6)

        def add_row(k: str, v: str):
            row = QHBoxLayout()
            lbl_k = QLabel(k)
            lbl_k.setStyleSheet(f"color: {c.text_secondary}; font-size: 11px;")
            lbl_v = QLabel(v)
            lbl_v.setStyleSheet(f"color: {c.text}; font-size: 11px; font-weight: 500;")
            lbl_v.setAlignment(Qt.AlignmentFlag.AlignRight)
            row.addWidget(lbl_k)
            row.addWidget(lbl_v)
            c_layout.addLayout(row)

        add_row("簡報大小", size_str)
        if meta["slides"] != "未知":
            add_row("投影片張數", f"{meta['slides']} 頁")
        if meta["creator"] != "未知":
            add_row("建立者", meta["creator"])
        if meta["modified"] != "未知":
            add_row("最後修改", meta["modified"])

        layout.addWidget(card)

        # 專業版提示橫條
        tip_lbl = QLabel("🔒 多頁投影片翻頁與大綱解析為專業版專屬功能，免費版提供封面與屬性預覽")
        tip_lbl.setStyleSheet(f"color: {c.text_secondary}; font-size: 11px;")
        tip_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(tip_lbl)

        btn_box = QHBoxLayout()
        btn_box.setSpacing(10)
        btn_box.setAlignment(Qt.AlignmentFlag.AlignCenter)

        btn_unlock = QPushButton("★ 解鎖完整簡報多頁翻閱")
        btn_unlock.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_unlock.setFixedHeight(32)
        btn_unlock.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #d97706, stop:1 #f59e0b);
                color: #ffffff;
                font-weight: 600;
                font-size: 11px;
                border-radius: 6px;
                padding: 4px 16px;
                border: none;
            }
            QPushButton:hover {
                background: #b45309;
            }
        """)
        from ui.license_dialog import show_license_dialog
        btn_unlock.clicked.connect(lambda: show_license_dialog(self.window()))
        btn_box.addWidget(btn_unlock)

        btn_open = QPushButton("↗ 系統預設程式開啟")
        btn_open.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_open.setFixedHeight(32)
        btn_open_bg = "rgba(255, 255, 255, 0.08)" if is_dark else "rgba(0, 0, 0, 0.06)"
        btn_open.setStyleSheet(f"""
            QPushButton {{
                background: {btn_open_bg};
                color: {c.text};
                font-size: 11px;
                border-radius: 6px;
                padding: 4px 14px;
                border: 1px solid {card_border};
            }}
            QPushButton:hover {{
                background: rgba(255, 255, 255, 0.14);
            }}
        """)
        btn_open.clicked.connect(lambda: os.startfile(str(path)))
        btn_box.addWidget(btn_open)

        layout.addLayout(btn_box)


# ── Renderer 接口 ─────────────────────────────────────────────────────────────
class PptxRenderer(BaseRenderer):
    """PowerPoint 簡報渲染器。"""
    def __init__(self) -> None:
        self._current_widget: Optional[QWidget] = None

    def render(self, path: Path) -> QWidget:
        suffix = path.suffix.lower()
        from core.license import LicenseManager
        if not LicenseManager.get_instance().is_unlimited():
            self._current_widget = _PptxProCardWidget(path)
            return self._current_widget

        if suffix == ".ppt":
            self._current_widget = _PptLegacyWidget(path)
        else:
            self._current_widget = PptxBrowserWidget(path)
        return self._current_widget

    def cleanup(self) -> None:
        self._current_widget = None

