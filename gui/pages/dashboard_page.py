"""Dashboard page - real-time gauges and data display."""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QGroupBox, QFrame
)
from PyQt6.QtCore import Qt
from gui.widgets.circular_gauge import CircularGauge


class DashboardPage(QWidget):
    """Main dashboard with real-time gauges for vehicle data."""

    # Gauge definitions: PID, title, unit, min, max
    GAUGE_DEFS = [
        ("010C", "发动机转速", "RPM", 0, 8000),
        ("010D", "车速", "km/h", 0, 260),
        ("0105", "冷却液温度", "°C", -40, 210),
        ("0104", "发动机负载", "%", 0, 100),
        ("0111", "节气门位置", "%", 0, 100),
        ("0110", "空气流量", "g/s", 0, 655),
        ("0170", "长期燃油修正","%",-10,10)
    ]

    # Secondary data PIDs
    EXTRA_PIDS = [
        ("0106", "短期燃油修正", "%"),
        ("0107", "长期燃油修正", "%"),
        ("010F", "进气温度", "°C"),
        ("011F", "运行时间", "s"),
    ]

    def __init__(self, engine=None, parent=None):
        super().__init__(parent)
        self.engine = engine
        self._gauges = {}
        self._extra_labels = {}
        self._setup_ui()
        if self.engine:
            self.engine.data_updated.connect(self._on_data_updated)

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(12)

        # Header
        header = QHBoxLayout()
        title = QLabel("实时数据仪表盘")
        title.setObjectName("titleLabel")
        self._stream_btn = QPushButton("开始监测")
        self._stream_btn.setMinimumWidth(120)
        self._stream_btn.clicked.connect(self._toggle_stream)
        header.addWidget(title)
        header.addStretch()
        header.addWidget(self._stream_btn)
        layout.addLayout(header)

        # Gauges grid
        grid = QGridLayout()
        grid.setSpacing(8)
        for i, (pid, name, unit, vmin, vmax) in enumerate(self.GAUGE_DEFS):
            gauge = CircularGauge(title=name, unit=unit, min_val=vmin, max_val=vmax)
            gauge.setMinimumSize(170, 170)
            self._gauges[pid] = gauge
            grid.addWidget(gauge, i // 3, i % 3)
        layout.addLayout(grid)

        # Extra data panel
        extra_group = QGroupBox("附加参数")
        extra_layout = QHBoxLayout(extra_group)
        extra_layout.setSpacing(16)
        for pid, name, unit in self.EXTRA_PIDS:
            frame = QFrame()
            frame_layout = QVBoxLayout(frame)
            frame_layout.setContentsMargins(8, 4, 8, 4)
            name_lbl = QLabel(name)
            name_lbl.setObjectName("gaugeName")
            name_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            val_lbl = QLabel("--")
            val_lbl.setObjectName("gaugeValue")
            val_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            val_lbl.setStyleSheet("font-size: 20px;")
            unit_lbl = QLabel(unit)
            unit_lbl.setObjectName("gaugeUnit")
            unit_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            frame_layout.addWidget(name_lbl)
            frame_layout.addWidget(val_lbl)
            frame_layout.addWidget(unit_lbl)
            extra_layout.addWidget(frame)
            self._extra_labels[pid] = val_lbl
        layout.addWidget(extra_group)

        layout.addStretch()

    def _toggle_stream(self):
        if not self.engine or not self.engine.is_connected:
            return
        if self.engine.is_streaming:
            self.engine.stop_streaming()
            self._stream_btn.setText("开始监测")
            self._stream_btn.setStyleSheet("")
        else:
            self.engine.start_streaming(500)
            self._stream_btn.setText("停止监测")
            self._stream_btn.setStyleSheet("background-color: #e94560; color: white;")

    def _on_data_updated(self, data: dict):
        for pid, gauge in self._gauges.items():
            if pid in data and "value" in data[pid]:
                gauge.set_value(data[pid]["value"])
        for pid, label in self._extra_labels.items():
            if pid in data and "value" in data[pid]:
                unit = data[pid].get("unit", "")
                label.setText(f"{data[pid]['value']} {unit}")

    def stop(self):
        if self.engine and self.engine.is_streaming:
            self.engine.stop_streaming()
            self._stream_btn.setText("开始监测")
            self._stream_btn.setStyleSheet("")
