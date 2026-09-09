"""Security Access (0x27) and Authentication (0x29) page."""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGroupBox, QComboBox, QLineEdit, QTextEdit, QFormLayout,
    QFrame, QTabWidget
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QFont


class SecurityPage(QWidget):
    """UDS Security Access and Authentication testing page."""

    def __init__(self, engine=None, parent=None):
        super().__init__(parent)
        self.engine = engine
        self._setup_ui()
        if self.engine:
            self.engine.security_state_changed.connect(self._on_security_changed)
            self.engine.raw_response_received.connect(self._on_response)

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(12)

        title = QLabel("安全访问与认证")
        title.setObjectName("titleLabel")
        layout.addWidget(title)

        tabs = QTabWidget()

        # Tab 1: Security Access 0x27
        sa_tab = QWidget()
        sa_layout = QVBoxLayout(sa_tab)

        sa_group = QGroupBox("0x27 Security Access - 种子密钥")
        sa_form = QFormLayout(sa_group)

        self._sa_level = QComboBox()
        self._sa_level.addItems(["Level 01 (标准)", "Level 03", "Level 05 (MD5)", "Level 11"])
        sa_form.addRow("安全等级:", self._sa_level)

        btn_layout = QHBoxLayout()
        self._seed_btn = QPushButton("请求种子 (27xx)")
        self._seed_btn.clicked.connect(self._request_seed)
        self._key_btn = QPushButton("发送密钥 (27xx)")
        self._key_btn.clicked.connect(self._send_key)
        self._key_btn.setEnabled(False)
        btn_layout.addWidget(self._seed_btn)
        btn_layout.addWidget(self._key_btn)
        sa_form.addRow("", btn_layout)

        self._seed_display = QLineEdit()
        self._seed_display.setReadOnly(True)
        self._seed_display.setPlaceholderText("种子值")
        sa_form.addRow("收到种子:", self._seed_display)

        self._key_display = QLineEdit()
        self._key_display.setReadOnly(True)
        self._key_display.setPlaceholderText("计算的密钥值")
        sa_form.addRow("计算密钥:", self._key_display)

        sa_layout.addWidget(sa_group)

        # Status
        self._sa_status = QLabel("未解锁")
        self._sa_status.setObjectName("errorLabel")
        sa_layout.addWidget(self._sa_status)

        sa_layout.addStretch()
        tabs.addTab(sa_tab, "Security Access")

        # Tab 2: Authentication 0x29
        auth_tab = QWidget()
        auth_layout = QVBoxLayout(auth_tab)

        auth_group = QGroupBox("0x29 Authentication")
        auth_form = QFormLayout(auth_group)

        self._auth_func = QComboBox()
        self._auth_func.addItems([
            "01 - deAuthenticate",
            "02 - authenticateOneSender",
            "03 - authenticateOneReceiver",
            "04 - bidirectionalCertificate",
            "05 - challengeResponse",
            "06 - proofOfOwnership",
            "07 - verifyServerCertificate"
        ])
        auth_form.addRow("子功能:", self._auth_func)

        self._auth_btn = QPushButton("执行认证")
        self._auth_btn.clicked.connect(self._run_auth)
        auth_form.addRow("", self._auth_btn)

        auth_layout.addWidget(auth_group)

        # Auth log
        self._auth_log = QTextEdit()
        self._auth_log.setReadOnly(True)
        self._auth_log.setFont(QFont("Cascadia Code", 11))
        auth_layout.addWidget(self._auth_log)

        tabs.addTab(auth_tab, "Authentication")

        layout.addWidget(tabs)

        # Response log
        log_group = QGroupBox("通信日志")
        log_layout = QVBoxLayout(log_group)
        self._log = QTextEdit()
        self._log.setReadOnly(True)
        self._log.setMaximumHeight(180)
        self._log.setFont(QFont("Cascadia Code", 11))
        log_layout.addWidget(self._log)
        layout.addWidget(log_group)

    def _get_level_int(self):
        idx = self._sa_level.currentIndex()
        levels = [1, 3, 5, 11]
        return levels[idx] if idx < len(levels) else 1

    def _request_seed(self):
        if not self.engine or not self.engine.is_connected:
            self._sa_status.setText("请先连接设备")
            return
        level = self._get_level_int()
        self._log.append(f"[发送] 27{level:02X} - 请求种子 (Level {level})")
        response = self.engine.security_request_seed(level)
        self._seed_display.setText(response)
        self._key_btn.setEnabled(True)

        # Auto-calculate key
        if response and "7F" not in response:
            hex_bytes = response.replace("\n", " ").split()
            seed_hex = "".join(hex_bytes[2:]) if len(hex_bytes) > 2 else ""
            key = self.engine.security_calculate_key(seed_hex, level)
            self._key_display.setText(key)
            self._log.append(f"[种子] {seed_hex}")
            self._log.append(f"[计算] 密钥 = {key}")

    def _send_key(self):
        if not self.engine or not self.engine.is_connected:
            return
        level = self._get_level_int()
        key = self._key_display.text().strip()
        if not key:
            self._sa_status.setText("无密钥可发送")
            return
        self._log.append(f"[发送] 27{level + 1:02X}{key} - 发送密钥")
        success = self.engine.security_send_key(level, key)
        if success:
            self._sa_status.setText(f"Level {level} 已解锁")
            self._sa_status.setObjectName("successLabel")
        else:
            self._sa_status.setText("密钥验证失败")
            self._sa_status.setObjectName("errorLabel")
        self._sa_status.style().unpolish(self._sa_status)
        self._sa_status.style().polish(self._sa_status)

    def _run_auth(self):
        if not self.engine or not self.engine.is_connected:
            self._auth_log.append("请先连接设备")
            return
        idx = self._auth_func.currentIndex()
        sub_func = f"{idx + 1:02X}"
        self._auth_log.append(f"执行 0x29 子功能 {sub_func}...")
        response = self.engine.send_raw(f"29{sub_func}")
        self._auth_log.append(f"响应: {response}")

    def _on_security_changed(self, level: str, unlocked: bool):
        if unlocked:
            self._sa_status.setText(f"{level} 已解锁")
            self._sa_status.setObjectName("successLabel")
        else:
            self._sa_status.setText(f"{level} 未解锁")
            self._sa_status.setObjectName("errorLabel")
        self._sa_status.style().unpolish(self._sa_status)
        self._sa_status.style().polish(self._sa_status)

    def _on_response(self, response: str):
        pass  # Could add auto-logging here
