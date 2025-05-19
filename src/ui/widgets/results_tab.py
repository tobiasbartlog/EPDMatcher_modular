### src/ui/results_tab.py

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QTabWidget, QPlainTextEdit, QTableWidget, QTableWidgetItem

class ResultsTab(QWidget):
    def __init__(self, epd_service, parent=None):
        super().__init__(parent)
        self.epd_service = epd_service
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        self.tabs = QTabWidget()
        # Text-Details
        self.text_edit = QPlainTextEdit()
        self.text_edit.setReadOnly(True)
        self.tabs.addTab(self.text_edit, "Details")
        # Table-Details
        self.table = QTableWidget()
        self.tabs.addTab(self.table, "Tabelle")
        layout.addWidget(self.tabs)

    def on_match_selected(self, uuid: str):
        details = self.epd_service.get_epd_details(uuid)
        # fill text
        self.text_edit.clear()
        for k, v in details.items():
            if k != 'environmental':
                self.text_edit.appendPlainText(f"{k}: {v}")
        # if environmental data exists
        env = details.get('environmental')
        if env:
            self.text_edit.appendPlainText("\n-- Environmental --")
            for k, block in env.items():
                self.text_edit.appendPlainText(f"{k}: {block}")
        # fill table (example general fields)
        self.table.clear()
        keys = [k for k in details if k != 'environmental']
        self.table.setColumnCount(2)
        self.table.setRowCount(len(keys))
        self.table.setHorizontalHeaderLabels(["Feld", "Wert"])
        for i, key in enumerate(keys):
            self.table.setItem(i, 0, QTableWidgetItem(key))
            self.table.setItem(i, 1, QTableWidgetItem(str(details[key])))