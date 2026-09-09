"""Styled data table widget."""

from PyQt6.QtWidgets import QTableWidget, QHeaderView, QAbstractItemView
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor


class DataTable(QTableWidget):
    """Pre-styled table widget matching the dark theme."""

    def __init__(self, columns=None, parent=None):
        super().__init__(parent)
        if columns:
            self.setColumnCount(len(columns))
            self.setHorizontalHeaderLabels(columns)
        self.setAlternatingRowColors(True)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.verticalHeader().setVisible(False)
        self.horizontalHeader().setStretchLastSection(True)
        self.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.setShowGrid(False)

    def add_row(self, values: list):
        row = self.rowCount()
        self.insertRow(row)
        for col, val in enumerate(values):
            self.setItem(row, col, self._make_item(str(val)))
        return row

    def _make_item(self, text: str):
        from PyQt6.QtWidgets import QTableWidgetItem
        item = QTableWidgetItem(text)
        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        return item

    def clear_data(self):
        self.setRowCount(0)

    def set_column_widths(self, widths: list):
        for i, w in enumerate(widths):
            if i < self.columnCount():
                self.setColumnWidth(i, w)
