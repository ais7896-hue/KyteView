"""
renderers/audio_renderer.py
極速音訊播放與波形渲染器：
- miniaudio 極速解碼峰值資料（< 15ms，捨棄 librosa/matplotlib）
- QPainter 繪製 SoundCloud 風格條形柱波形
- PySide6 QtMultimedia (QMediaPlayer + QAudioOutput) 播放控制
"""
from __future__ import annotations

from pathlib import Path
from typing import Sequence

import miniaudio

from PySide6.QtCore import QPointF, QRectF, QTime, QUrl, Qt
from PySide6.QtGui import QColor, QLinearGradient, QPainter, QPaintEvent
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from renderers.base import BaseRenderer


class _WaveformWidget(QWidget):
    """繪製類 SoundCloud 漸層柱狀波形，並依播放進度點亮。"""

    def __init__(self, peaks: Sequence[float], parent: QWidget | None = None):
        super().__init__(parent)
        self._peaks = peaks or [0.1] * 60
        self._progress: float = 0.0  # 0.0 ~ 1.0
        self.setFixedHeight(120)

    def set_progress(self, val: float) -> None:
        self._progress = max(0.0, min(1.0, val))
        self.update()

    def paintEvent(self, event: QPaintEvent) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()
        n = len(self._peaks)
        if n == 0:
            return

        bar_width = max(2.0, (w / n) * 0.65)
        gap = max(1.0, (w / n) * 0.35)
        total_bar_w = bar_width + gap

        # 漸層色彩（已播放 vs 未播放）
        played_color = QColor("#6366f1")  # 活力靛藍
        unplayed_color = QColor("#2e2e38")  # 暗灰柱條

        curr_x = self._progress * w

        for i, peak in enumerate(self._peaks):
            x = i * total_bar_w
            bar_h = max(6.0, peak * (h - 20))
            y = (h - bar_h) / 2.0

            color = played_color if (x + bar_width / 2.0) <= curr_x else unplayed_color
            p.setBrush(color)
            p.setPen(Qt.PenStyle.NoPen)
            p.drawRoundedRect(QRectF(x, y, bar_width, bar_h), 2.0, 2.0)

        p.end()


def _extract_peaks(path: Path, num_bars: int = 80) -> list[float]:
    """使用 miniaudio 抽樣取得正規化峰值陣列 (0.0 ~ 1.0)。"""
    try:
        decoded = miniaudio.decode_file(str(path), nchannels=1, sample_rate=8000)
        samples = decoded.samples
        if not samples:
            return [0.2] * num_bars

        step = max(1, len(samples) // num_bars)
        peaks = []
        for i in range(num_bars):
            chunk = samples[i * step : (i + 1) * step]
            if chunk:
                peak = max(abs(s) for s in chunk)
                peaks.append(float(peak))
            else:
                peaks.append(0.0)

        max_val = max(peaks) if peaks and max(peaks) > 0 else 1.0
        return [p / max_val for p in peaks]
    except Exception:
        # Fallback 假波形，不卡死
        return [0.1 + (i % 5) * 0.15 for i in range(num_bars)]


class AudioRenderer(BaseRenderer):
    def __init__(self) -> None:
        self._player: QMediaPlayer | None = None
        self._audio_output: QAudioOutput | None = None

    def render(self, path: Path) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # 讀取音訊基本資訊
        info_str = "音訊檔案"
        try:
            info = miniaudio.get_file_info(str(path))
            duration_sec = info.duration
            info_str = (
                f"{info.file_format.name.upper()} · {info.sample_rate} Hz · "
                f"{info.nchannels} 聲道 · {duration_sec:.1f} 秒"
            )
        except Exception:
            pass

        # 1. 檔案資訊標籤
        meta_label = QLabel(info_str)
        meta_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        meta_label.setStyleSheet("color: #9ca3af; font-size: 13px; font-weight: 500;")
        layout.addWidget(meta_label)

        # 2. 波形元件
        peaks = _extract_peaks(path, num_bars=75)
        waveform = _WaveformWidget(peaks)
        layout.addWidget(waveform)

        # 3. 播放器初始化
        self._player = QMediaPlayer()
        self._audio_output = QAudioOutput()
        self._player.setAudioOutput(self._audio_output)
        self._player.setSource(QUrl.fromLocalFile(str(path)))

        # 4. 控制列
        ctrl_layout = QHBoxLayout()
        ctrl_layout.setSpacing(12)

        btn_play = QPushButton("▶")
        btn_play.setFixedSize(40, 40)
        btn_play.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_play.setStyleSheet("""
            QPushButton {
                background: #6366f1;
                color: #ffffff;
                border-radius: 20px;
                font-size: 16px;
                font-weight: bold;
                border: none;
            }
            QPushButton:hover { background: #4f46e5; }
        """)

        time_label = QLabel("00:00 / 00:00")
        time_label.setStyleSheet("color: #9ca3af; font-size: 12px; min-width: 90px;")

        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setRange(0, 1000)
        slider.setStyleSheet("""
            QSlider::groove:horizontal {
                height: 4px;
                background: #27272a;
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
                background: #e0e7ff;
                border-radius: 6px;
            }
        """)

        ctrl_layout.addWidget(btn_play)
        ctrl_layout.addWidget(slider)
        ctrl_layout.addWidget(time_label)
        layout.addLayout(ctrl_layout)

        def toggle_play():
            if not self._player:
                return
            if self._player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
                self._player.pause()
                btn_play.setText("▶")
            else:
                self._player.play()
                btn_play.setText("⏸")

        btn_play.clicked.connect(toggle_play)

        def on_position_changed(pos_ms: int):
            dur_ms = self._player.duration() if self._player else 0
            if dur_ms > 0:
                prog = pos_ms / dur_ms
                waveform.set_progress(prog)
                if not slider.isSliderDown():
                    slider.setValue(int(prog * 1000))

                t_cur = QTime(0, 0, 0).addMSecs(pos_ms).toString("mm:ss")
                t_dur = QTime(0, 0, 0).addMSecs(dur_ms).toString("mm:ss")
                time_label.setText(f"{t_cur} / {t_dur}")

        self._player.positionChanged.connect(on_position_changed)

        def on_slider_moved(val: int):
            if self._player and self._player.duration() > 0:
                self._player.setPosition(int((val / 1000.0) * self._player.duration()))

        slider.sliderMoved.connect(on_slider_moved)

        # 預設自動啟動播放（如 macOS QuickLook 體驗）
        self._player.play()
        btn_play.setText("⏸")

        return container

    def cleanup(self) -> None:
        if self._player:
            self._player.stop()
            self._player = None
        self._audio_output = None
