"""Main application window with sidebar navigation."""

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QStackedWidget,
    QPushButton, QLabel, QFrame, QStatusBar, QApplication
)
from PyQt6.QtCore import Qt, QSize, QTimer
from PyQt6.QtGui import QIcon, QFont

from gui.theme import DARK_THEME
from gui.obd_engine import OBDEngine
from gui.widgets.status_indicator import StatusIndicator
from gui.pages.dashboard_page import DashboardPage
from gui.pages.dtc_page import DTCPage
from gui.pages.logger_page import LoggerPage
from gui.pages.terminal_page import TerminalPage
from gui.pages.security_page import SecurityPage
from gui.pages.settings_page import SettingsPage


class MainWindow(QMainWindow):
    """Main application window."""

    NAV_ITEMS = [
        ("仪表盘", "dashboard"),
        ("故障码", "dtc"),
        ("数据记录", "logger"),
        ("命令终端", "terminal"),
        ("安全访问", "security"),
        ("连接设置", "settings"),
    ]

    def __init__(self):
        super().__init__()
        self.engine = OBDEngine()
        self._nav_buttons = {}
        self._setup_ui()
        self._connect_signals()
        self._navigate("dashboard")

    def _setup_ui(self):
        self.setWindowTitle("UDS 诊断终端 v2.0")
        self.setMinimumSize(1100, 700)
        self.resize(1280, 800)
        self.setStyleSheet(DARK_THEME)

        # Central widget
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Sidebar
        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.setSpacing(0)

        # App title in sidebar
        app_title = QLabel("UDS Terminal")
        app_title.setObjectName("sidebarTitle")
        sidebar_layout.addWidget(app_title)

        subtitle = QLabel("汽车诊断数据终端")
        subtitle.setObjectName("sidebarSubtitle")
        sidebar_layout.addWidget(subtitle)

        # Connection status
        self._status_indicator = StatusIndicator()
        sidebar_layout.addWidget(self._status_indicator)

        # Separator
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color: #0f3460; margin: 8px 16px;")
        sidebar_layout.addWidget(sep)

        # Nav buttons
        for label, key in self.NAV_ITEMS:
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda checked, k=key: self._navigate(k))
            sidebar_layout.addWidget(btn)
            self._nav_buttons[key] = btn

        sidebar_layout.addStretch()

        # Version label
        ver = QLabel("v2.0.0")
        ver.setStyleSheet("color: #303050; font-size: 10px; padding: 8px 16px;")
        sidebar_layout.addWidget(ver)

        main_layout.addWidget(sidebar)

        # Content area
        self._stack = QStackedWidget()
        self._stack.setObjectName("contentArea")
        self._pages = {}

        self._pages["dashboard"] = DashboardPage(engine=self.engine)
        self._pages["dtc"] = DTCPage(engine=self.engine)
        self._pages["logger"] = LoggerPage(engine=self.engine)
        self._pages["terminal"] = TerminalPage(engine=self.engine)
        self._pages["security"] = SecurityPage(engine=self.engine)
        self._pages["settings"] = SettingsPage(engine=self.engine)
        self._pages["settings"].set_callbacks(
            on_connect=self._on_connected,
            on_disconnect=self._on_disconnected
        )

        for page in self._pages.values():
            self._stack.addWidget(page)

        main_layout.addWidget(self._stack)

        # Status bar
        self._status_bar = QStatusBar()
        self.setStatusBar(self._status_bar)
        self._status_bar_label = QLabel("就绪")
        self._status_bar.addWidget(self._status_bar_label)

    def _connect_signals(self):
        self.engine.connection_changed.connect(self._on_connection_changed)
        self.engine.log_message.connect(self._on_log_message)
        self.engine.error_received.connect(self._on_error)

    def _navigate(self, key: str):
        if key in self._pages:
            self._stack.setCurrentWidget(self._pages[key])
        for k, btn in self._nav_buttons.items():
            btn.setChecked(k == key)

    def _on_connected(self):
        self._status_indicator.set_online(True)
        self._status_bar_label.setText("已连接")

    def _on_disconnected(self):
        self._status_indicator.set_online(False)
        self._status_bar_label.setText("已断开")
        # Stop any active streaming
        self._pages["dashboard"].stop()
        self._pages["logger"].stop()

    def _on_connection_changed(self, connected: bool):
        if connected:
            self._status_indicator.set_online(True)
        else:
            self._status_indicator.set_online(False)

    def _on_log_message(self, msg: str):
        self._status_bar_label.setText(msg)

    def _on_error(self, msg: str):
        self._status_bar_label.setText(f"错误: {msg}")

    def closeEvent(self, event):
        if self.engine.is_streaming:
            self.engine.stop_streaming()
        if self.engine.is_connected:
            self.engine.disconnect()
        event.accept()
