"""
renderers/video_renderer.py
KyteView 影片預覽器。
技術特點：
- PySide6 原生 QMediaPlayer + QAudioOutput + QVideoWidget (微軟 WMF 硬解加速，0 外部依賴)。
- 靜音自動播放 (Muted Autoplay)，防止突然爆音。
- macOS QuickLook 級極簡懸浮控制條 (Hover Controls)，滑鼠移入平滑淡入，移出/靜止自動淡出。
- 支援進度條點擊直接跳轉與拖曳刷時間軸 (Scrubbing)。
- 支援短影片自動無限循環播放 (Loop)。
- 點擊畫面切換播放/暫停。
- 冷門格式/硬解失敗平滑降級為中繼資料卡片 + 一鍵預設播放器開啟。
- 視窗關閉或切換檔案時完整釋放解碼與音訊通道。
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from PySide6.QtCore import (
    Qt, QUrl, QTimer, QPoint, QSize, Signal, QPropertyAnimation, QEasingCurve,
)
from PySide6.QtGui import QMouseEvent, QFont, QCursor
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QSlider, QFrame, QSizePolicy, QGraphicsOpacityEffect,
)
from PySide6.QtMultimedia import (
    QMediaPlayer, QAudioOutput, QMediaMetaData,
)
from PySide6.QtMultimediaWidgets import QVideoWidget

from renderers.base import BaseRenderer
from config.settings import settings
from config.theme import get_theme_colors


def _format_time(ms: int) -> str:
    total_seconds = max(0, ms // 1000)
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    return f"{minutes:02d}:{seconds:02d}"


class _ClickableSlider(QSlider):
    """支援直接點擊定位與拖曳滑動的微型時間軸進度條。"""
    seek_requested = Signal(int)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(Qt.Orientation.Horizontal, parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setTracking(True)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            val = self._pos_to_val(event.position().x())
            self.setValue(val)
            self.seek_requested.emit(val)
            event.accept()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if event.buttons() & Qt.MouseButton.LeftButton:
            val = self._pos_to_val(event.position().x())
            self.setValue(val)
            self.seek_requested.emit(val)
            event.accept()
        super().mouseMoveEvent(event)

    def _pos_to_val(self, x: float) -> int:
        w = max(1, self.width())
        ratio = max(0.0, min(1.0, x / w))
        return int(self.minimum() + ratio * (self.maximum() - self.minimum()))


class _VideoOverlay(QFrame):
    """
    覆蓋在視訊上方的懸浮控制條。
    包含播放/暫停、時間顯示、時間軸進度條、靜音切換按鈕。
    """
    def __init__(self, parent: VideoPlayerWidget) -> None:
        super().__init__(parent)
        self._player_widget = parent
        self.setObjectName("video_control_bar")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 6, 14, 6)
        layout.setSpacing(10)

        # 播放/暫停按鈕
        self.btn_play = QPushButton("⏸")
        self.btn_play.setFixedSize(26, 26)
        self.btn_play.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_play.clicked.connect(self._player_widget.toggle_play)
        layout.addWidget(self.btn_play)

        # 時間顯示
        self.lbl_time = QLabel("00:00 / 00:00")
        self.lbl_time.setFont(QFont("Segoe UI", 9, QFont.Weight.Medium))
        self.lbl_time.setStyleSheet("color: rgba(255, 255, 255, 0.85); background: transparent;")
        layout.addWidget(self.lbl_time)

        # 時間軸滑桿
        self.slider = _ClickableSlider()
        self.slider.setRange(0, 1000)
        self.slider.seek_requested.connect(self._player_widget.seek_position)
        layout.addWidget(self.slider, 1)

        # 靜音切換按鈕
        self.btn_mute = QPushButton("🔇")
        self.btn_mute.setFixedSize(26, 26)
        self.btn_mute.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_mute.setToolTip("靜音 / 取消靜音")
        self.btn_mute.clicked.connect(self._player_widget.toggle_mute)
        layout.addWidget(self.btn_mute)

        self.setStyleSheet("""
            QFrame#video_control_bar {
                background: rgba(18, 18, 22, 0.82);
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 18px;
            }
            QPushButton {
                background: transparent;
                color: #ffffff;
                border: none;
                border-radius: 13px;
                font-size: 13px;
                font-family: 'Segoe UI Symbol', 'Segoe UI', sans-serif;
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 0.16);
            }
            QSlider::groove:horizontal {
                height: 4px;
                background: rgba(255, 255, 255, 0.22);
                border-radius: 2px;
            }
            QSlider::sub-page:horizontal {
                background: #6366f1;
                border-radius: 2px;
            }
            QSlider::handle:horizontal {
                width: 12px;
                height: 12px;
                margin: -4px 0;
                background: #ffffff;
                border-radius: 6px;
            }
            QSlider::handle:horizontal:hover {
                background: #818cf8;
                transform: scale(1.2);
            }
        """)

        # 淡入淡出透明度動畫
        self._opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self._opacity_effect)
        self._anim = QPropertyAnimation(self._opacity_effect, b"opacity")
        self._anim.setDuration(220)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)

    def set_overlay_visible(self, visible: bool) -> None:
        self._anim.stop()
        target = 1.0 if visible else 0.0
        self._anim.setStartValue(self._opacity_effect.opacity())
        self._anim.setEndValue(target)
        self._anim.start()


class VideoPlayerWidget(QWidget):
    """
    整合 QMediaPlayer + QVideoWidget + 懸浮控制條的極速播放元件。
    """
    resolution_detected = Signal(int, int)

    def __init__(self, path: Path, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._path = path
        self._duration_ms = 0
        self._is_user_seeking = False
        self._has_detected_res = False

        self.setMouseTracking(True)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 1. 視訊畫面輸出
        self.video_widget = QVideoWidget(self)
        self.video_widget.setMouseTracking(True)
        self.video_widget.setStyleSheet("background-color: #000000;")
        layout.addWidget(self.video_widget)

        # 2. 懸浮控制列 (浮動放置於底端中央)
        self.overlay = _VideoOverlay(self)
        self.overlay.setFixedHeight(36)
        self.overlay.set_overlay_visible(False)

        # 控制條自動隱藏定時器 (滑鼠靜止 2.2 秒後淡出)
        self._hide_timer = QTimer(self)
        self._hide_timer.setSingleShot(True)
        self._hide_timer.setInterval(2200)
        self._hide_timer.timeout.connect(lambda: self.overlay.set_overlay_visible(False))

        # 3. 多媒體播放核心
        self.audio_output = QAudioOutput(self)
        self.audio_output.setMuted(True)  # 預設靜音自動播放，安全不爆音

        self.player = QMediaPlayer(self)
        self.player.setAudioOutput(self.audio_output)
        self.player.setVideoOutput(self.video_widget)

        # 信號連接
        self.player.durationChanged.connect(self._on_duration_changed)
        self.player.positionChanged.connect(self._on_position_changed)
        self.player.mediaStatusChanged.connect(self._on_media_status_changed)
        self.player.errorOccurred.connect(self._on_error_occurred)
        self.player.metaDataChanged.connect(self._check_video_resolution)

        # 點擊畫面切換播放/暫停事件過濾
        self.video_widget.installEventFilter(self)

        # 載入影片檔並開始播放
        self.player.setSource(QUrl.fromLocalFile(str(path)))
        self.player.play()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        # 動態將懸浮控制條置中放置在離底部 16px 處
        bar_w = min(self.width() - 36, 480)
        bar_h = 36
        bar_x = (self.width() - bar_w) // 2
        bar_y = max(10, self.height() - bar_h - 14)
        self.overlay.setGeometry(bar_x, bar_y, bar_w, bar_h)

    def eventFilter(self, watched, event) -> bool:
        if watched == self.video_widget:
            if event.type() == QMouseEvent.Type.MouseButtonPress:
                if event.button() == Qt.MouseButton.LeftButton:
                    self.toggle_play()
                    return True
            elif event.type() in (QMouseEvent.Type.MouseMove, QMouseEvent.Type.Enter):
                self._show_controls()
            elif event.type() == QMouseEvent.Type.Leave:
                self._hide_timer.start(500)
        return super().eventFilter(watched, event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        super().mouseMoveEvent(event)
        self._show_controls()

    def _show_controls(self) -> None:
        self.overlay.set_overlay_visible(True)
        self._hide_timer.start()

    def toggle_play(self) -> None:
        if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.player.pause()
            self.overlay.btn_play.setText("▶")
            self._show_controls()
        else:
            self.player.play()
            self.overlay.btn_play.setText("⏸")
            self._show_controls()

    def toggle_mute(self) -> None:
        is_muted = not self.audio_output.isMuted()
        self.audio_output.setMuted(is_muted)
        self.overlay.btn_mute.setText("🔇" if is_muted else "🔊")
        self._show_controls()

    def seek_position(self, slider_val: int) -> None:
        if self._duration_ms > 0:
            target_ms = int((slider_val / 1000.0) * self._duration_ms)
            self.player.setPosition(target_ms)
            self._show_controls()

    def _on_duration_changed(self, dur_ms: int) -> None:
        self._duration_ms = dur_ms
        self._update_time_label(self.player.position(), dur_ms)
        self._check_video_resolution()

    def _on_position_changed(self, pos_ms: int) -> None:
        if self._duration_ms > 0:
            progress = int((pos_ms / self._duration_ms) * 1000)
            self.overlay.slider.blockSignals(True)
            self.overlay.slider.setValue(progress)
            self.overlay.slider.blockSignals(False)
        self._update_time_label(pos_ms, self._duration_ms)

    def _update_time_label(self, cur_ms: int, dur_ms: int) -> None:
        cur_str = _format_time(cur_ms)
        dur_str = _format_time(dur_ms) if dur_ms > 0 else "--:--"
        self.overlay.lbl_time.setText(f"{cur_str} / {dur_str}")

    def _on_media_status_changed(self, status: QMediaPlayer.MediaStatus) -> None:
        if status == QMediaPlayer.MediaStatus.EndOfMedia:
            # 短影片播放結束自動無限循環重播 (Loop)
            self.player.setPosition(0)
            self.player.play()
            self.overlay.btn_play.setText("⏸")
        elif status in (QMediaPlayer.MediaStatus.BufferedMedia, QMediaPlayer.MediaStatus.LoadedMedia):
            self._check_video_resolution()

    def _check_video_resolution(self) -> None:
        """偵測影片真實原生解析度並通知外層視窗自適應調整長寬比。"""
        if self._has_detected_res:
            return
        meta = self.player.metaData()
        res = meta.value(QMediaMetaData.Key.Resolution)
        if isinstance(res, QSize) and res.width() > 0 and res.height() > 0:
            self._has_detected_res = True
            self.resolution_detected.emit(res.width(), res.height())

    def _on_error_occurred(self, error: QMediaPlayer.Error, error_string: str) -> None:
        """無法解碼或硬解出錯時，優雅降級為中繼資料資訊卡。"""
        if error == QMediaPlayer.Error.NoError:
            return
        self._show_fallback_card(error_string)

    def _show_fallback_card(self, error_str: str) -> None:
        self.video_widget.hide()
        self.overlay.hide()

        fallback = QWidget(self)
        fb_layout = QVBoxLayout(fallback)
        fb_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        fb_layout.setSpacing(14)

        icon_lbl = QLabel("🎬")
        icon_lbl.setFont(QFont("Segoe UI Emoji", 42))
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        fb_layout.addWidget(icon_lbl)

        title_lbl = QLabel(self._path.name)
        title_lbl.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        title_lbl.setStyleSheet("color: #f3f4f6;")
        title_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        fb_layout.addWidget(title_lbl)

        try:
            size_mb = self._path.stat().st_size / (1024 * 1024)
            size_str = f"{size_mb:.1f} MB"
        except Exception:
            size_str = "未知大小"

        ext_str = self._path.suffix.upper().lstrip(".")
        desc_lbl = QLabel(f"格式：{ext_str} 視訊  ·  大小：{size_str}\n（Windows 系統內建解碼器未支援該編碼或硬體受限）")
        desc_lbl.setStyleSheet("color: #a1a1aa; font-size: 11px;")
        desc_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        fb_layout.addWidget(desc_lbl)

        btn_open = QPushButton("↗ 使用系統預設播放器開啟")
        btn_open.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_open.setFixedHeight(34)
        btn_open.setStyleSheet("""
            QPushButton {
                background: #4f46e5;
                color: #ffffff;
                font-weight: bold;
                border-radius: 6px;
                padding: 6px 16px;
            }
            QPushButton:hover {
                background: #4338ca;
            }
        """)
        btn_open.clicked.connect(lambda: os.startfile(str(self._path)))
        fb_layout.addWidget(btn_open)

        self.layout().addWidget(fallback)

    def cleanup(self) -> None:
        """徹底停止播放、解綁音訊輸出與視訊輸出，釋放解碼硬體資源。"""
        try:
            self._hide_timer.stop()
            self.player.stop()
            self.player.setVideoOutput(None)
            self.player.setAudioOutput(None)
            self.player.setSource(QUrl())
        except Exception:
            pass


class VideoRenderer(BaseRenderer):
    def __init__(self) -> None:
        self._current_widget: Optional[VideoPlayerWidget] = None

    def render(self, path: Path) -> QWidget:
        self._current_widget = VideoPlayerWidget(path)
        return self._current_widget

    def cleanup(self) -> None:
        if self._current_widget:
            self._current_widget.cleanup()
            self._current_widget = None
