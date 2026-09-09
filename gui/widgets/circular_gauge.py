"""Circular gauge widget drawn with QPainter for high-performance real-time display."""

import math
from PyQt6.QtCore import Qt, QRectF, pyqtProperty, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QPainter, QPen, QColor, QFont, QLinearGradient
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel


class CircularGauge(QWidget):
    """High-performance circular gauge widget with smooth animations."""

    def __init__(self, title="", unit="", min_val=0, max_val=100, parent=None):
        super().__init__(parent)
        self._title = title
        self._unit = unit
        self._min_val = float(min_val)
        self._max_val = float(max_val)
        self._value = 0.0
        self._target_value = 0.0
        self._animated_value = 0.0
        self._color = QColor("#e94560")
        self._bg_color = QColor("#0f3460")
        self._text_color = QColor("#e0e0e0")
        self._gauge_bg = QColor("#0a0a1a")
        self.setMinimumSize(160, 160)
        self.setMaximumSize(260, 260)

        # Animation
        self._animation = QPropertyAnimation(self, b"animatedValue")
        self._animation.setDuration(300)
        self._animation.setEasingCurve(QEasingCurve.Type.OutCubic)

    def get_animated_value(self):
        return self._animated_value

    def set_animated_value(self, val):
        self._animated_value = val
        self.update()

    animatedValue = pyqtProperty(float, get_animated_value, set_animated_value)

    def set_value(self, value):
        try:
            value = float(value)
        except (TypeError, ValueError):
            return
        value = max(self._min_val, min(self._max_val, value))
        self._value = value
        self._animation.stop()
        self._animation.setStartValue(self._animated_value)
        self._animation.setEndValue(value)
        self._animation.start()

    def set_color(self, color: str):
        self._color = QColor(color)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        size = min(w, h)
        margin = 12
        cx, cy = w / 2, h / 2
        radius = size / 2 - margin
        line_width = max(8, int(size * 0.08))
        start_angle = 225 * 16
        span_angle = -270 * 16

        # Background arc
        pen = QPen(self._gauge_bg, line_width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        arc_rect = QRectF(cx - radius, cy - radius, radius * 2, radius * 2)
        painter.drawArc(arc_rect, start_angle, span_angle)

        # Value arc
        pct = (self._animated_value - self._min_val) / (self._max_val - self._min_val) if self._max_val != self._min_val else 0
        pct = max(0.0, min(1.0, pct))
        value_span = int(span_angle * pct)

        # Color based on value percentage
        if pct < 0.6:
            color = QColor("#00b894")
        elif pct < 0.85:
            color = QColor("#fdcb6e")
        else:
            color = QColor("#e94560")

        pen = QPen(color, line_width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.drawArc(arc_rect, start_angle, value_span)

        # Tick marks
        tick_count = 10
        inner_r = radius - line_width - 4
        outer_r = radius - line_width + 2
        pen = QPen(QColor("#1a4a8a"), 1)
        painter.setPen(pen)
        for i in range(tick_count + 1):
            angle = math.radians(225 - 270 * i / tick_count)
            x1 = cx + inner_r * math.cos(angle)
            y1 = cy - inner_r * math.sin(angle)
            x2 = cx + outer_r * math.cos(angle)
            y2 = cy - outer_r * math.sin(angle)
            painter.drawLine(int(x1), int(y1), int(x2), int(y2))

        # Value text
        font_size = max(14, int(size * 0.18))
        font = QFont("Cascadia Code", font_size, QFont.Weight.Bold)
        painter.setFont(font)
        painter.setPen(color)
        value_text = f"{self._animated_value:.0f}" if self._animated_value == int(self._animated_value) else f"{self._animated_value:.1f}"
        text_rect = QRectF(cx - radius, cy - 12, radius * 2, font_size + 8)
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter, value_text)

        # Unit
        unit_size = max(10, int(size * 0.08))
        font = QFont("Microsoft YaHei", unit_size)
        painter.setFont(font)
        painter.setPen(QColor("#606080"))
        unit_rect = QRectF(cx - radius, cy + font_size - 4, radius * 2, unit_size + 8)
        painter.drawText(unit_rect, Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop, self._unit)

        # Title
        title_size = max(10, int(size * 0.08))
        font = QFont("Microsoft YaHei", title_size, QFont.Weight.DemiBold)
        painter.setFont(font)
        painter.setPen(QColor("#a0a0b8"))
        title_rect = QRectF(cx - radius, cy - radius + 6, radius * 2, title_size + 8)
        painter.drawText(title_rect, Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop, self._title)

        painter.end()
