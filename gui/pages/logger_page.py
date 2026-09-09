"""Data logger page with CSV recording and log viewing."""

import csv
import os
import time
from datetime import datetime

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGroupBox, QFileDialog, QTableWidget, QTableWidgetItem,
    QHeaderView, QComboBox, QSpinBox, QProgressBar
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor


class LoggerPage(QWidget):
    """Data logging page with CSV recording and playback."""

    LOG_DIR = "logs"

    def __init__(self, engine=None, parent=None):
        super().__init__(parent)
        self.engine = engine
        self._recording = False
        self._log_file = None
        self._log_writer = None
        self._record_count = 0
        self._record_timer = QTimer()
        self._record_timer.timeout.connect(self._record_tick)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(12)

        # Header
        header = QHBoxLayout()
        title = QLabel("数据记录器")
        title.setObjectName("titleLabel")
        header.addWidget(title)
        header.addStretch()
        layout.addLayout(header)

        # Record controls
        rec_group = QGroupBox("录制控制")
        rec_layout = QHBoxLayout(rec_group)

        rec_layout.addWidget(QLabel("采样间隔:"))
        self._interval = QSpinBox()
        self._interval.setRange(100, 10000)
        self._interval.setValue(500)
        self._interval.setSuffix(" ms")
        self._interval.setMinimumWidth(120)
        rec_layout.addWidget(self._interval)

        self._record_btn = QPushButton("开始录制")
        self._record_btn.setMinimumWidth(120)
        self._record_btn.clicked.connect(self._toggle_recording)
        rec_layout.addWidget(self._record_btn)

        self._export_btn = QPushButton("导出日志")
        self._export_btn.setMinimumWidth(120)
        self._export_btn.clicked.connect(self._export_log)
        rec_layout.addWidget(self._export_btn)

        rec_layout.addStretch()
        layout.addWidget(rec_group)

        # Status bar
        status_layout = QHBoxLayout()
        self._status = QLabel("就绪")
        self._status.setObjectName("subtitleLabel")
        self._count_label = QLabel("记录数: 0")
        self._count_label.setObjectName("subtitleLabel")
        self._file_label = QLabel("")
        self._file_label.setObjectName("subtitleLabel")
        status_layout.addWidget(self._status)
        status_layout.addStretch()
        status_layout.addWidget(self._count_label)
        status_layout.addWidget(self._file_label)
        layout.addLayout(status_layout)

        # Progress bar (shows recording progress visually)
        self._progress = QProgressBar()
        self._progress.setRange(0, 0)
        self._progress.setVisible(False)
        self._progress.setMaximumHeight(4)
        layout.addWidget(self._progress)

        # Live data table
        data_group = QGroupBox("当前数据快照")
        data_layout = QVBoxLayout(data_group)
        self._live_table = QTableWidget()
        self._live_table.setColumnCount(4)
        self._live_table.setHorizontalHeaderLabels(["PID", "参数", "数值", "单位"])
        self._live_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self._live_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self._live_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self._live_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self._live_table.verticalHeader().setVisible(False)
        self._live_table.setAlternatingRowColors(True)
        data_layout.addWidget(self._live_table)
        layout.addWidget(data_group)

        # Log files list
        log_group = QGroupBox("历史日志文件")
        log_layout = QVBoxLayout(log_group)
        self._log_list = QTableWidget()
        self._log_list.setColumnCount(3)
        self._log_list.setHorizontalHeaderLabels(["文件名", "大小", "操作"])
        self._log_list.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self._log_list.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self._log_list.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self._log_list.verticalHeader().setVisible(False)
        self._log_list.setAlternatingRowColors(True)
        log_layout.addWidget(self._log_list)

        refresh_btn = QPushButton("刷新列表")
        refresh_btn.clicked.connect(self._refresh_log_list)
        log_layout.addWidget(refresh_btn)
        layout.addWidget(log_group)

        self._refresh_log_list()
        if self.engine:
            self.engine.data_updated.connect(self._on_data_updated)

    def _toggle_recording(self):
        if self._recording:
            self._stop_recording()
        else:
            self._start_recording()

    def _start_recording(self):
        if not self.engine or not self.engine.is_connected:
            self._status.setText("请先连接车辆")
            self._status.setObjectName("errorLabel")
            self._status.style().unpolish(self._status)
            self._status.style().polish(self._status)
            return

        os.makedirs(self.LOG_DIR, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = os.path.join(self.LOG_DIR, f"obd_{ts}.csv")

        self._log_file = open(filepath, "w", newline="", encoding="utf-8-sig")
        self._log_writer = csv.writer(self._log_file)
        headers = ["timestamp"]
        for pid in ["0104", "0105", "0106", "0107", "010C", "010D", "010F", "0110", "0111", "011F"]:
            from gui.obd_engine import OBDEngine
            if pid in OBDEngine.PID_DEFINITIONS:
                headers.append(OBDEngine.PID_DEFINITIONS[pid]["name"])
            else:
                headers.append(pid)
        self._log_writer.writerow(headers)
        self._log_file.flush()

        self._record_count = 0
        self._recording = True
        self._record_btn.setText("停止录制")
        self._record_btn.setStyleSheet("background-color: #e94560; color: white;")
        self._progress.setVisible(True)
        self._status.setText(f"录制中: {filepath}")
        self._status.setObjectName("successLabel")
        self._status.style().unpolish(self._status)
        self._status.style().polish(self._status)
        self._file_label.setText(os.path.basename(filepath))

        interval = self._interval.value()
        self._record_timer.start(interval)

    def _stop_recording(self):
        self._record_timer.stop()
        self._recording = False
        if self._log_file:
            self._log_file.close()
            self._log_file = None
            self._log_writer = None
        self._record_btn.setText("开始录制")
        self._record_btn.setStyleSheet("")
        self._progress.setVisible(False)
        self._status.setText(f"录制完成，共 {self._record_count} 条记录")
        self._status.setObjectName("successLabel")
        self._status.style().unpolish(self._status)
        self._status.style().polish(self._status)
        self._refresh_log_list()

    def _record_tick(self):
        if not self.engine or not self.engine.is_connected:
            self._stop_recording()
            return
        data = self.engine.last_data
        if not data:
            return
        row = [datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]]
        for pid in ["0104", "0105", "0106", "0107", "010C", "010D", "010F", "0110", "0111", "011F"]:
            if pid in data and "value" in data[pid]:
                row.append(data[pid]["value"])
            else:
                row.append("")
        if self._log_writer:
            self._log_writer.writerow(row)
            self._log_file.flush()
            self._record_count += 1
            self._count_label.setText(f"记录数: {self._record_count}")

    def _on_data_updated(self, data: dict):
        self._live_table.setRowCount(0)
        for pid, info in data.items():
            if "error" in info:
                continue
            row = self._live_table.rowCount()
            self._live_table.insertRow(row)
            self._live_table.setItem(row, 0, QTableWidgetItem(pid))
            self._live_table.setItem(row, 1, QTableWidgetItem(info.get("name", "")))
            val_item = QTableWidgetItem(str(info.get("value", "")))
            val_item.setForeground(QColor("#00ff88"))
            self._live_table.setItem(row, 2, val_item)
            self._live_table.setItem(row, 3, QTableWidgetItem(info.get("unit", "")))

    def _refresh_log_list(self):
        self._log_list.setRowCount(0)
        if not os.path.exists(self.LOG_DIR):
            return
        for f in sorted(os.listdir(self.LOG_DIR), reverse=True):
            if f.endswith(".csv"):
                filepath = os.path.join(self.LOG_DIR, f)
                size = os.path.getsize(filepath)
                row = self._log_list.rowCount()
                self._log_list.insertRow(row)
                self._log_list.setItem(row, 0, QTableWidgetItem(f))
                if size < 1024:
                    size_str = f"{size} B"
                else:
                    size_str = f"{size / 1024:.1f} KB"
                self._log_list.setItem(row, 1, QTableWidgetItem(size_str))

    def _export_log(self):
        if not os.path.exists(self.LOG_DIR):
            return
        filepath, _ = QFileDialog.getOpenFileName(
            self, "选择日志文件", self.LOG_DIR, "CSV Files (*.csv)"
        )
        if filepath:
            save_path, _ = QFileDialog.getSaveFileName(
                self, "导出为", "", "CSV Files (*.csv)"
            )
            if save_path:
                import shutil
                shutil.copy2(filepath, save_path)
                self._status.setText(f"已导出到: {save_path}")

    def stop(self):
        if self._recording:
            self._stop_recording()
