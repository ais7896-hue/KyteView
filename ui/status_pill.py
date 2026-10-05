"""
ui/status_pill.py
極簡呼吸指示器（Subtle Pill HUD）：
當使用者切換至檔案總管 (Explorer) 時，於右下角短暫淡入提示 KyteView 待命中，
不搶焦點、極簡低干擾、美觀流暢。
"""
from __future__ import annotations

from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve
from PySide6.QtWidgets import QWidget, QLabel, QHBoxLayout, QGraphicsOpacityEffect


class StatusPill(QWidget):
    """右下角極簡待命提示膠囊。"""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(
            parent,
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool,
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 10, 16, 10)

        from i18n import t
        self._label = QLabel(t("pill.standby"))
        self._label.setStyleSheet("""
            QLabel {
                color: #e0e7ff;
                background-color: rgba(15, 23, 42, 0.92);
                border: 1.5px solid rgba(99, 102, 241, 0.6);
                border-radius: 20px;
                padding: 8px 18px;
                font-size: 14px;
                font-weight: 600;
                font-family: 'Segoe UI', 'Microsoft JhengHei UI', sans-serif;
            }
        """)
        layout.addWidget(self._label)

        # 淡入淡出特效
        self._opacity_fx = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self._opacity_fx)
        self._opacity_fx.setOpacity(0.0)

        self._anim = QPropertyAnimation(self._opacity_fx, b"opacity")
        self._timer_fade = QTimer(self)
        self._timer_fade.setSingleShot(True)
        self._timer_fade.timeout.connect(self._fade_out)

    def flash(self, message: str | None = None, display_ms: int = 1500) -> None:
        """淡入顯示並在指定毫秒後淡出。"""
        from i18n import t
        if message:
            self._label.setText(message)
        else:
            self._label.setText(t("pill.standby"))

        self.adjustSize()
        screen = self.screen().availableGeometry()
        # 定位在螢幕右下角工作列邊緣
        target_x = screen.right() - self.width() - 20
        target_y = screen.bottom() - self.height() - 20
        self.move(target_x, target_y)

        self.show()

        # 淡入動畫
        self._anim.stop()
        self._anim.setDuration(220)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._anim.setStartValue(self._opacity_fx.opacity())
        self._anim.setEndValue(1.0)
        self._anim.start()

        # 設定停留時間
        self._timer_fade.stop()
        self._timer_fade.start(display_ms)

    def _fade_out(self) -> None:
        """淡出隱藏。"""
        self._anim.stop()
        self._anim.setDuration(350)
        self._anim.setEasingCurve(QEasingCurve.Type.InCubic)
        self._anim.setStartValue(self._opacity_fx.opacity())
        self._anim.setEndValue(0.0)
        self._anim.finished.connect(self._on_fade_finished)
        self._anim.start()

    def _on_fade_finished(self) -> None:
        if self._opacity_fx.opacity() <= 0.01:
            self.hide()
            try:
                self._anim.finished.disconnect(self._on_fade_finished)
            except RuntimeError:
                pass
