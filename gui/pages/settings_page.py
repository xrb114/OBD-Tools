"""Settings and connection configuration page."""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGroupBox, QLineEdit, QSpinBox, QComboBox, QFormLayout,
    QCheckBox, QTextEdit, QFrame
)
from PyQt6.QtCore import Qt
from gui.transport import TCPTransport, SerialTransport, list_serial_ports


class SettingsPage(QWidget):
    """Connection settings and configuration page."""

    def __init__(self, engine=None, parent=None):
        super().__init__(parent)
        self.engine = engine
        self._transport = None
        self._connected = False
        self._on_connect_callback = None
        self._on_disconnect_callback = None
        self._setup_ui()
        self._refresh_ports()

    def set_callbacks(self, on_connect=None, on_disconnect=None):
        self._on_connect_callback = on_connect
        self._on_disconnect_callback = on_disconnect

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(16)

        # Header
        title = QLabel("连接设置")
        title.setObjectName("titleLabel")
        layout.addWidget(title)

        # Connection type selector
        type_group = QGroupBox("连接方式")
        type_layout = QVBoxLayout(type_group)

        self._conn_type = QComboBox()
        self._conn_type.addItems([
            "USB/串口 ELM327",
            "WiFi/TCP ELM327",
            "OBD 模拟器 (本地)"
        ])
        self._conn_type.currentIndexChanged.connect(self._on_type_changed)
        type_layout.addWidget(self._conn_type)

        # Stacked config panels
        self._serial_panel = self._create_serial_panel()
        self._tcp_panel = self._create_tcp_panel()
        self._sim_panel = self._create_sim_panel()
        type_layout.addWidget(self._serial_panel)
        type_layout.addWidget(self._tcp_panel)
        type_layout.addWidget(self._sim_panel)
        layout.addWidget(type_group)

        # Connection status and buttons
        conn_frame = QFrame()
        conn_layout = QHBoxLayout(conn_frame)

        self._status_label = QLabel("状态: 未连接")
        self._status_label.setObjectName("subtitleLabel")
        conn_layout.addWidget(self._status_label)
        conn_layout.addStretch()

        self._connect_btn = QPushButton("连接")
        self._connect_btn.setObjectName("btnConnect")
        self._connect_btn.setMinimumWidth(120)
        self._connect_btn.clicked.connect(self._on_connect_clicked)
        conn_layout.addWidget(self._connect_btn)

        self._disconnect_btn = QPushButton("断开")
        self._disconnect_btn.setObjectName("btnDisconnect")
        self._disconnect_btn.setMinimumWidth(120)
        self._disconnect_btn.setEnabled(False)
        self._disconnect_btn.clicked.connect(self._on_disconnect_clicked)
        conn_layout.addWidget(self._disconnect_btn)

        layout.addWidget(conn_frame)

        # ELM327 info
        info_group = QGroupBox("ELM327 初始化参数")
        info_layout = QFormLayout(info_group)
        self._protocol = QComboBox()
        self._protocol.addItems(["自动", "ISO 15765-4 (CAN)", "ISO 14230-4 (KWP2000)", "ISO 9141-2", "SAE J1850"])
        info_layout.addRow("协议:", self._protocol)

        self._header_check = QCheckBox("显示消息头 (ATH1)")
        info_layout.addRow("", self._header_check)

        self._echo_check = QCheckBox("回显 (ATE1)")
        info_layout.addRow("", self._echo_check)

        layout.addWidget(info_group)

        # Connection log
        log_group = QGroupBox("连接日志")
        log_layout = QVBoxLayout(log_group)
        self._log = QTextEdit()
        self._log.setReadOnly(True)
        self._log.setMaximumHeight(150)
        self._log.setStyleSheet("""
            QTextEdit {
                background-color: #0a0a14;
                color: #606080;
                font-family: Consolas;
                font-size: 11px;
            }
        """)
        log_layout.addWidget(self._log)
        layout.addWidget(log_group)

        layout.addStretch()
        self._on_type_changed(0)

    def _create_serial_panel(self):
        panel = QGroupBox("串口配置")
        layout = QFormLayout(panel)
        self._port_combo = QComboBox()
        self._port_combo.setMinimumWidth(200)
        layout.addRow("COM 端口:", self._port_combo)

        refresh_btn = QPushButton("刷新端口")
        refresh_btn.clicked.connect(self._refresh_ports)
        layout.addRow("", refresh_btn)

        self._baud = QComboBox()
        self._baud.addItems(["9600", "38400", "115200", "230400", "460800", "921600"])
        self._baud.setCurrentText("38400")
        layout.addRow("波特率:", self._baud)
        return panel

    def _create_tcp_panel(self):
        panel = QGroupBox("TCP/WiFi 配置")
        layout = QFormLayout(panel)
        self._host = QLineEdit("127.0.0.1")
        layout.addRow("IP 地址:", self._host)
        self._port = QSpinBox()
        self._port.setRange(1, 65535)
        self._port.setValue(35000)
        layout.addRow("端口:", self._port)
        return panel

    def _create_sim_panel(self):
        panel = QGroupBox("模拟器配置")
        layout = QFormLayout(panel)
        self._sim_host = QLineEdit("127.0.0.1")
        layout.addRow("IP 地址:", self._sim_host)
        self._sim_port = QSpinBox()
        self._sim_port.setRange(1, 65535)
        self._sim_port.setValue(35000)
        layout.addRow("端口:", self._sim_port)
        return panel

    def _on_type_changed(self, index):
        self._serial_panel.setVisible(index == 0)
        self._tcp_panel.setVisible(index == 1)
        self._sim_panel.setVisible(index == 2)

    def _refresh_ports(self):
        self._port_combo.clear()
        ports = list_serial_ports()
        if ports:
            for p in ports:
                self._port_combo.addItem(f"{p['device']} - {p['description']}", p['device'])
        else:
            self._port_combo.addItem("未检测到串口", "")
            self._log.append("提示: 未检测到串口设备，请检查连接或安装驱动")

    def _on_connect_clicked(self):
        if not self.engine:
            return
        idx = self._conn_type.currentIndex()
        if idx == 0:
            port_data = self._port_combo.currentData()
            port_name = port_data if port_data else self._port_combo.currentText().split(" - ")[0]
            self._transport = SerialTransport(
                port=port_name,
                baudrate=int(self._baud.currentText())
            )
            self._log.append(f"正在连接串口 {port_name}...")
        elif idx == 1:
            self._transport = TCPTransport(
                host=self._host.text(),
                port=self._port.value()
            )
            self._log.append(f"正在连接 {self._host.text()}:{self._port.value()}...")
        else:
            self._transport = TCPTransport(
                host=self._sim_host.text(),
                port=self._sim_port.value()
            )
            self._log.append(f"正在连接模拟器 {self._sim_host.text()}:{self._sim_port.value()}...")

        self._transport.log_message = None  # Avoid signal issues
        self.engine.set_transport(self._transport)
        if self.engine.connect():
            self._connected = True
            self._status_label.setText("状态: 已连接")
            self._status_label.setObjectName("successLabel")
            self._connect_btn.setEnabled(False)
            self._disconnect_btn.setEnabled(True)
            self._log.append("连接成功!")
            if self._on_connect_callback:
                self._on_connect_callback()
        else:
            self._log.append("连接失败，请检查设备和配置")
            self._status_label.setText("状态: 连接失败")
            self._status_label.setObjectName("errorLabel")

        self._status_label.style().unpolish(self._status_label)
        self._status_label.style().polish(self._status_label)

    def _on_disconnect_clicked(self):
        if self.engine:
            self.engine.disconnect()
        self._connected = False
        self._status_label.setText("状态: 已断开")
        self._status_label.setObjectName("subtitleLabel")
        self._connect_btn.setEnabled(True)
        self._disconnect_btn.setEnabled(False)
        self._log.append("已断开连接")
        self._status_label.style().unpolish(self._status_label)
        self._status_label.style().polish(self._status_label)
        if self._on_disconnect_callback:
            self._on_disconnect_callback()

    @property
    def is_connected(self):
        return self._connected
