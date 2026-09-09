"""Connection status indicator widget."""

from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QPainter, QPen, QBrush


class StatusIndicator(QWidget):
    """Small status dot with label for connection state."""

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(8)

        self._dot = _StatusDot()
        self._dot.setFixedSize(12, 12)

        self._label = QLabel("未连接")
        self._label.setObjectName("statusOffline")

        layout.addWidget(self._dot)
        layout.addWidget(self._label)
        layout.addStretch()

        self.set_online(False)

    def set_online(self, online: bool, text: str = ""):
        self._dot.set_online(online)
        if text:
            self._label.setText(text)
        else:
            self._label.setText("已连接" if online else "未连接")
        self._label.setObjectName("statusOnline" if online else "statusOffline")
        self._label.style().unpolish(self._label)
        self._label.style().polish(self._label)


class _StatusDot(QWidget):
    """Small colored circle indicator."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._online = False

    def set_online(self, online: bool):
        self._online = online
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        color = QColor("#00b894") if self._online else QColor("#636e72")
        painter.setBrush(QBrush(color))
        painter.setPen(QPen(color.darker(120), 1))
        painter.drawEllipse(1, 1, self.width() - 2, self.height() - 2)
        painter.end()
