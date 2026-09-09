"""Raw terminal/command page for direct ELM327 communication."""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QTextEdit, QGroupBox, QComboBox, QCompleter
)
from PyQt6.QtCore import Qt, QStringListModel
from PyQt6.QtGui import QTextCursor, QColor, QFont


class TerminalPage(QWidget):
    """Raw command terminal with history and auto-complete."""

    # Common commands for auto-complete
    COMMON_COMMANDS = [
        "ATZ", "ATE0", "ATE1", "ATL0", "ATL1", "ATH0", "ATH1",
        "ATS0", "ATS1", "ATSP0", "ATSP1", "ATSP2", "ATSP3",
        "ATI", "ATRV", "ATDP", "AT@1",
        "0100", "0101", "0103", "0104", "0105", "0106", "0107",
        "010C", "010D", "010F", "0110", "0111", "0113", "011C",
        "011F", "0121", "03", "04", "0902",
        "1001", "1002", "1003",
        "1101", "1102", "1103",
        "22F190", "22F191", "22F192", "22F193", "22F194",
        "2701", "2702", "2703", "2704", "2705", "2706",
        "2E", "31", "34", "36", "37", "38",
    ]

    def __init__(self, engine=None, parent=None):
        super().__init__(parent)
        self.engine = engine
        self._history = []
        self._history_index = -1
        self._setup_ui()
        if self.engine:
            self.engine.raw_command_sent.connect(self._on_command_sent)
            self.engine.raw_response_received.connect(self._on_response_received)
            self.engine.log_message.connect(self._on_log)

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(12)

        # Header
        header = QHBoxLayout()
        title = QLabel("命令终端")
        title.setObjectName("titleLabel")
        header.addWidget(title)
        header.addStretch()

        self._clear_btn = QPushButton("清屏")
        self._clear_btn.setObjectName("btnClear")
        self._clear_btn.clicked.connect(self._clear_output)
        header.addWidget(self._clear_btn)
        layout.addLayout(header)

        # Quick commands
        quick_group = QGroupBox("快捷命令")
        quick_layout = QHBoxLayout(quick_group)
        quick_cmds = [
            ("ATZ", "复位"),
            ("0100", "支持PID"),
            ("03", "读DTC"),
            ("0902", "读VIN"),
            ("ATH1", "头开"),
            ("ATH0", "头关"),
        ]
        for cmd, label in quick_cmds:
            btn = QPushButton(f"{label}\n{cmd}")
            btn.setToolTip(cmd)
            btn.setMinimumHeight(48)
            btn.clicked.connect(lambda checked, c=cmd: self._send_command(c))
            quick_layout.addWidget(btn)
        quick_layout.addStretch()
        layout.addWidget(quick_group)

        # Output area
        self._output = QTextEdit()
        self._output.setReadOnly(True)
        self._output.setFont(QFont("Cascadia Code", 12))
        self._output.setStyleSheet("""
            QTextEdit {
                background-color: #0a0a14;
                color: #00ff88;
                border: 1px solid #0f3460;
                border-radius: 8px;
                padding: 12px;
            }
        """)
        layout.addWidget(self._output)

        # Input area
        input_layout = QHBoxLayout()

        self._prompt = QLabel("OBD>")
        self._prompt.setStyleSheet("color: #e94560; font-weight: bold; font-size: 14px; font-family: Consolas;")
        self._prompt.setFixedWidth(50)
        input_layout.addWidget(self._prompt)

        self._input = QLineEdit()
        self._input.setPlaceholderText("输入AT或OBD命令，回车发送...")
        self._input.setFont(QFont("Cascadia Code", 13))
        self._input.returnPressed.connect(self._on_return_pressed)
        input_layout.addWidget(self._input)

        self._send_btn = QPushButton("发送")
        self._send_btn.setMinimumWidth(80)
        self._send_btn.clicked.connect(self._on_return_pressed)
        input_layout.addWidget(self._send_btn)

        layout.addLayout(input_layout)

        # Auto-complete
        completer = QCompleter(self.COMMON_COMMANDS)
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        completer.setFilterMode(Qt.MatchFlag.MatchContains)
        self._input.setCompleter(completer)

        self._append_output("UDS 终端已就绪", "#606080")
        self._append_output("输入 AT 或 OBD 命令开始通信", "#606080")
        self._append_output("────────────────────────────────", "#1a4a8a")

    def _on_return_pressed(self):
        cmd = self._input.text().strip().upper()
        if not cmd:
            return
        self._input.clear()
        self._send_command(cmd)

    def _send_command(self, cmd: str):
        if not self.engine or not self.engine.is_connected:
            self._append_output("错误: 未连接设备", "#ff6b6b")
            return
        self._history.append(cmd)
        self._history_index = len(self._history)
        self._append_output(f">>> {cmd}", "#e94560")
        response = self.engine.send_raw(cmd)
        self._append_output(response, "#00ff88")

    def _on_command_sent(self, cmd: str):
        pass  # Handled in _send_command

    def _on_response_received(self, response: str):
        pass  # Handled in _send_command

    def _on_log(self, msg: str):
        self._append_output(f"[系统] {msg}", "#fdcb6e")

    def _append_output(self, text: str, color: str = "#e0e0e0"):
        self._output.setTextColor(QColor(color))
        self._output.append(text)
        cursor = self._output.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self._output.setTextCursor(cursor)
        self._output.ensureCursorVisible()

    def _clear_output(self):
        self._output.clear()
        self._append_output("终端已清屏", "#606080")

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Up and self._history:
            self._history_index = max(0, self._history_index - 1)
            self._input.setText(self._history[self._history_index])
        elif event.key() == Qt.Key.Key_Down and self._history:
            self._history_index = min(len(self._history), self._history_index + 1)
            if self._history_index < len(self._history):
                self._input.setText(self._history[self._history_index])
            else:
                self._input.clear()
        else:
            super().keyPressEvent(event)
