"""DTC (Diagnostic Trouble Codes) page."""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGroupBox, QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox
)
from PyQt6.QtCore import Qt
from gui.dtc_database import decode_dtc_code


class DTCPage(QWidget):
    """Fault code reading and management page."""

    def __init__(self, engine=None, parent=None):
        super().__init__(parent)
        self.engine = engine
        self._setup_ui()
        if self.engine:
            self.engine.dtc_received.connect(self._on_dtcs_received)

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(12)

        # Header
        header = QHBoxLayout()
        title = QLabel("故障码诊断")
        title.setObjectName("titleLabel")
        header.addWidget(title)
        header.addStretch()
        layout.addLayout(header)

        # Action buttons
        btn_layout = QHBoxLayout()
        self._read_btn = QPushButton("读取故障码")
        self._read_btn.setMinimumWidth(140)
        self._read_btn.clicked.connect(self._read_dtcs)

        self._clear_btn = QPushButton("清除故障码")
        self._clear_btn.setObjectName("btnDanger")
        self._clear_btn.setMinimumWidth(140)
        self._clear_btn.clicked.connect(self._clear_dtcs)

        btn_layout.addWidget(self._read_btn)
        btn_layout.addWidget(self._clear_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        # Status label
        self._status = QLabel("点击\"读取故障码\"开始诊断")
        self._status.setObjectName("subtitleLabel")
        layout.addWidget(self._status)

        # DTC Table
        self._table = QTableWidget()
        self._table.setColumnCount(4)
        self._table.setHorizontalHeaderLabels(["故障码", "系统", "描述", "状态"])
        self._table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self._table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self._table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self._table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self._table.setAlternatingRowColors(True)
        self._table.verticalHeader().setVisible(False)
        layout.addWidget(self._table)

        # Info group
        info_group = QGroupBox("故障码说明")
        info_layout = QVBoxLayout(info_group)
        info_text = QLabel(
            "P = 动力系统 | C = 底盘系统 | B = 车身系统 | U = 通信系统\n"
            "故障码第一位: 0 = 通用, 1 = 制造商自定义, 2 = 通用/自定义, 3 = 保留\n"
            "读取前请确保车辆点火开关打开 (ON)，发动机可运行或不运行"
        )
        info_text.setObjectName("subtitleLabel")
        info_text.setWordWrap(True)
        info_layout.addWidget(info_text)
        layout.addWidget(info_group)

        layout.addStretch()

    def _read_dtcs(self):
        if not self.engine or not self.engine.is_connected:
            self._status.setText("请先连接车辆")
            self._status.setObjectName("errorLabel")
            self._status.style().unpolish(self._status)
            self._status.style().polish(self._status)
            return
        self._status.setText("正在读取故障码...")
        self._status.setObjectName("subtitleLabel")
        self._status.style().unpolish(self._status)
        self._status.style().polish(self._status)
        self._read_btn.setEnabled(False)
        self.engine.read_dtcs()
        self._read_btn.setEnabled(True)

    def _on_dtcs_received(self, dtcs: list):
        self._table.setRowCount(0)
        if not dtcs:
            self._status.setText("未发现故障码")
            self._status.setObjectName("successLabel")
            self._status.style().unpolish(self._status)
            self._status.style().polish(self._status)
            return

        self._status.setText(f"发现 {len(dtcs)} 个故障码")
        self._status.setObjectName("errorLabel")
        self._status.style().unpolish(self._status)
        self._status.style().polish(self._status)

        system_map = {"P": "动力", "C": "底盘", "B": "车身", "U": "通信"}
        for dtc in dtcs:
            row = self._table.rowCount()
            self._table.insertRow(row)
            prefix = dtc[0] if dtc else "P"
            system = system_map.get(prefix, "未知")
            desc = decode_dtc_code(dtc)
            self._table.setItem(row, 0, QTableWidgetItem(dtc))
            self._table.setItem(row, 1, QTableWidgetItem(system))
            self._table.setItem(row, 2, QTableWidgetItem(desc))
            self._table.setItem(row, 3, QTableWidgetItem("当前故障"))

    def _clear_dtcs(self):
        if not self.engine or not self.engine.is_connected:
            self._status.setText("请先连接车辆")
            return
        reply = QMessageBox.question(
            self, "确认清除",
            "确定要清除所有故障码吗？\n这将同时清除维修记录。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            if self.engine.clear_dtcs():
                self._table.setRowCount(0)
                self._status.setText("故障码已清除")
                self._status.setObjectName("successLabel")
                self._status.style().unpolish(self._status)
                self._status.style().polish(self._status)
