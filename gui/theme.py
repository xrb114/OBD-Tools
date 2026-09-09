"""Dark theme stylesheet for the application."""

DARK_THEME = """
/* ── Global ── */
QWidget {
    background-color: #1a1a2e;
    color: #e0e0e0;
    font-family: "Microsoft YaHei", "Segoe UI", "Consolas", sans-serif;
    font-size: 13px;
}

QMainWindow {
    background-color: #1a1a2e;
}

/* ── Sidebar ── */
#sidebar {
    background-color: #16213e;
    border-right: 1px solid #0f3460;
    min-width: 200px;
    max-width: 200px;
}

#sidebar QPushButton {
    background-color: transparent;
    color: #a0a0b8;
    border: none;
    border-radius: 8px;
    padding: 12px 16px;
    text-align: left;
    font-size: 14px;
    font-weight: 500;
    margin: 2px 8px;
}

#sidebar QPushButton:hover {
    background-color: #1a1a40;
    color: #e94560;
}

#sidebar QPushButton:checked {
    background-color: #0f3460;
    color: #e94560;
    font-weight: 700;
    border-left: 3px solid #e94560;
}

#sidebarTitle {
    color: #e94560;
    font-size: 18px;
    font-weight: 800;
    padding: 20px 16px 10px 16px;
}

#sidebarSubtitle {
    color: #606080;
    font-size: 11px;
    padding: 0 16px 16px 16px;
}

/* ── Content Area ── */
#contentArea {
    background-color: #1a1a2e;
    border: none;
}

/* ── Cards ── */
.card {
    background-color: #16213e;
    border: 1px solid #0f3460;
    border-radius: 12px;
    padding: 16px;
    margin: 4px;
}

/* ── Group Boxes ── */
QGroupBox {
    background-color: #16213e;
    border: 1px solid #0f3460;
    border-radius: 10px;
    margin-top: 12px;
    padding: 16px 12px 12px 12px;
    font-weight: 600;
    font-size: 13px;
    color: #e94560;
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 16px;
    padding: 0 8px;
    color: #e94560;
}

/* ── Buttons ── */
QPushButton {
    background-color: #0f3460;
    color: #e0e0e0;
    border: 1px solid #1a4a8a;
    border-radius: 8px;
    padding: 8px 20px;
    font-weight: 600;
    font-size: 13px;
    min-height: 18px;
}

QPushButton:hover {
    background-color: #1a4a8a;
    border-color: #e94560;
    color: #ffffff;
}

QPushButton:pressed {
    background-color: #e94560;
    color: #ffffff;
}

QPushButton:disabled {
    background-color: #0a0a1a;
    color: #404060;
    border-color: #1a1a3a;
}

QPushButton#btnConnect {
    background-color: #00b894;
    color: #ffffff;
    font-size: 14px;
    font-weight: 700;
    padding: 10px 24px;
}

QPushButton#btnConnect:hover {
    background-color: #00d9a7;
}

QPushButton#btnDisconnect {
    background-color: #e94560;
    color: #ffffff;
    font-size: 14px;
    font-weight: 700;
    padding: 10px 24px;
}

QPushButton#btnDisconnect:hover {
    background-color: #ff6b81;
}

QPushButton#btnClear {
    background-color: #6c5ce7;
    color: #ffffff;
}

QPushButton#btnClear:hover {
    background-color: #a29bfe;
}

QPushButton#btnDanger {
    background-color: #d63031;
    color: #ffffff;
}

QPushButton#btnDanger:hover {
    background-color: #ff7675;
}

/* ── Input Fields ── */
QLineEdit, QSpinBox, QComboBox {
    background-color: #0f0f23;
    color: #e0e0e0;
    border: 1px solid #1a4a8a;
    border-radius: 6px;
    padding: 8px 12px;
    font-size: 13px;
    min-height: 18px;
}

QLineEdit:focus, QSpinBox:focus, QComboBox:focus {
    border-color: #e94560;
}

QComboBox::drop-down {
    border: none;
    width: 24px;
}

QComboBox::down-arrow {
    image: none;
    border-left: 5px solid transparent;
    border-right: 5px solid transparent;
    border-top: 6px solid #e94560;
    margin-right: 8px;
}

QComboBox QAbstractItemView {
    background-color: #0f0f23;
    color: #e0e0e0;
    border: 1px solid #1a4a8a;
    selection-background-color: #0f3460;
    selection-color: #e94560;
}

/* ── Text Areas ── */
QTextEdit, QPlainTextEdit {
    background-color: #0f0f23;
    color: #00ff88;
    border: 1px solid #0f3460;
    border-radius: 8px;
    padding: 8px;
    font-family: "Cascadia Code", "Consolas", "Courier New", monospace;
    font-size: 13px;
    selection-background-color: #0f3460;
}

/* ── Tables ── */
QTableWidget, QTableView {
    background-color: #0f0f23;
    alternate-background-color: #141430;
    color: #e0e0e0;
    border: 1px solid #0f3460;
    border-radius: 8px;
    gridline-color: #1a1a40;
    selection-background-color: #0f3460;
    selection-color: #e94560;
    font-size: 12px;
}

QTableWidget::item, QTableView::item {
    padding: 6px 8px;
    border: none;
}

QHeaderView::section {
    background-color: #16213e;
    color: #e94560;
    border: none;
    border-bottom: 2px solid #0f3460;
    border-right: 1px solid #0f3460;
    padding: 8px 10px;
    font-weight: 700;
    font-size: 12px;
}

/* ── Scroll Bar ── */
QScrollBar:vertical {
    background: #0f0f23;
    width: 8px;
    border-radius: 4px;
}

QScrollBar::handle:vertical {
    background: #1a4a8a;
    border-radius: 4px;
    min-height: 30px;
}

QScrollBar::handle:vertical:hover {
    background: #e94560;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
    background: none;
}

/* ── Status Bar ── */
QStatusBar {
    background-color: #0f0f23;
    color: #606080;
    border-top: 1px solid #0f3460;
    font-size: 11px;
    padding: 2px 10px;
}

QStatusBar QLabel {
    color: #606080;
    padding: 2px 8px;
}

/* ── Tab Widget ── */
QTabWidget::pane {
    background-color: #16213e;
    border: 1px solid #0f3460;
    border-radius: 8px;
}

QTabBar::tab {
    background-color: #0f0f23;
    color: #a0a0b8;
    border: 1px solid #0f3460;
    border-bottom: none;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
    padding: 8px 20px;
    font-weight: 600;
    margin-right: 2px;
}

QTabBar::tab:selected {
    background-color: #16213e;
    color: #e94560;
    border-bottom: 2px solid #e94560;
}

QTabBar::tab:hover:!selected {
    background-color: #1a1a40;
    color: #e0e0e0;
}

/* ── Progress Bar ── */
QProgressBar {
    background-color: #0f0f23;
    border: 1px solid #0f3460;
    border-radius: 4px;
    text-align: center;
    color: #e0e0e0;
    font-size: 11px;
    min-height: 16px;
}

QProgressBar::chunk {
    background-color: #e94560;
    border-radius: 3px;
}

/* ── Check/Radio ── */
QCheckBox, QRadioButton {
    color: #e0e0e0;
    spacing: 8px;
}

QCheckBox::indicator, QRadioButton::indicator {
    width: 16px;
    height: 16px;
    border: 1px solid #1a4a8a;
    border-radius: 3px;
    background-color: #0f0f23;
}

QCheckBox::indicator:checked, QRadioButton::indicator:checked {
    background-color: #e94560;
    border-color: #e94560;
}

/* ── Tooltip ── */
QToolTip {
    background-color: #16213e;
    color: #e0e0e0;
    border: 1px solid #e94560;
    border-radius: 4px;
    padding: 6px 10px;
    font-size: 12px;
}

/* ── Label Variants ── */
QLabel#titleLabel {
    color: #e94560;
    font-size: 20px;
    font-weight: 800;
}

QLabel#subtitleLabel {
    color: #a0a0b8;
    font-size: 13px;
}

QLabel#gaugeValue {
    color: #00ff88;
    font-size: 28px;
    font-weight: 800;
    font-family: "Cascadia Code", "Consolas", monospace;
}

QLabel#gaugeName {
    color: #a0a0b8;
    font-size: 12px;
    font-weight: 600;
}

QLabel#gaugeUnit {
    color: #606080;
    font-size: 11px;
}

QLabel#statusOnline {
    color: #00b894;
    font-weight: 700;
}

QLabel#statusOffline {
    color: #636e72;
    font-weight: 700;
}

QLabel#errorLabel {
    color: #ff6b6b;
    font-weight: 600;
}

QLabel#successLabel {
    color: #00b894;
    font-weight: 600;
}
"""
