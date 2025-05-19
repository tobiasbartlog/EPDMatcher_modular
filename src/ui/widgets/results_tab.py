### src/ui/results_tab.py

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QTabWidget, QPlainTextEdit, QTableWidget, QTableWidgetItem, QMessageBox
import json

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
        print(f"ResultsTab: on_match_selected aufgerufen für UUID: {uuid}")
        if not uuid:
            self.text_edit.setPlainText("Keine UUID für Details ausgewählt.")
            if hasattr(self, 'table'):  # Prüfen, ob table existiert
                self.table.clearContents()
                self.table.setRowCount(0)
            return

        details = None  # Initialisieren
        try:
            details = (self.epd_service.get_details(uuid))
            print(f"ResultsTab: Details für {uuid} geladen: {details is not None}")
        except Exception as e:
            print(f"ResultsTab: Fehler beim Laden der Details für {uuid}: {e}")
            QMessageBox.critical(self, "Fehler", f"Konnte EPD-Details nicht laden:\n{e}")
            self.text_edit.setPlainText(f"Fehler beim Laden der Details für UUID {uuid}:\n{e}")
            if hasattr(self, 'table'):
                self.table.clearContents()
                self.table.setRowCount(0)
            return

        if details is None:
            QMessageBox.warning(self, "Nicht gefunden", f"Keine Details für EPD UUID {uuid} gefunden.")
            self.text_edit.setPlainText(f"Keine Details für EPD UUID {uuid} gefunden.")
            if hasattr(self, 'table'):
                self.table.clearContents()
                self.table.setRowCount(0)
            return

        # ----- BEGINN TESTWEISE AUSKOMMENTIEREN -----
        # # Text-Details füllen
        self.text_edit.clear()
        print("ResultsTab: Fülle Text-Details...")
        for k, v in details.items():
            if k != 'environmental':
                try:
                    self.text_edit.appendPlainText(f"{k}: {str(v)}")
                except Exception as e_text:
                    print(f"ResultsTab: Fehler beim Anhängen von '{k}': {e_text}")

        env_data = details.get('environmental')
        if env_data:
            self.text_edit.appendPlainText("\n-- Environmental --")
            if isinstance(env_data, dict):
                if "error" in env_data:
                     self.text_edit.appendPlainText(f"Fehler bei Umweltdaten: {env_data['error']}")
                else:
                    for k, block in env_data.items():
                        try:
                            block_str = json.dumps(block, indent=2, ensure_ascii=False) if isinstance(block, (dict, list)) else str(block)
                            self.text_edit.appendPlainText(f"{k}: {block_str}")
                        except Exception as e_env_text:
                             print(f"ResultsTab: Fehler beim Anhängen von Umweltdatenblock '{k}': {e_env_text}")
            else:
                self.text_edit.appendPlainText(f"Umweltdaten: {str(env_data)}")

        # Tabellen-Details füllen
        if hasattr(self, 'table'): # Prüfen, ob table existiert
            self.table.clearContents()
            keys_for_table = [k for k in details if k != 'environmental']
            self.table.setRowCount(len(keys_for_table))
            self.table.setColumnCount(2)
            self.table.setHorizontalHeaderLabels(["Feld", "Wert"])

            print(f"ResultsTab: Fülle Tabelle mit {len(keys_for_table)} Einträgen...")
            for i, key in enumerate(keys_for_table):
                try:
                    value_str = str(details[key])
                    self.table.setItem(i, 0, QTableWidgetItem(key))
                    self.table.setItem(i, 1, QTableWidgetItem(value_str))
                except Exception as e_table:
                    print(f"ResultsTab: Fehler beim Setzen von Tabelleneintrag '{key}': {e_table}")
                    if self.table.item(i,0) is None: self.table.setItem(i, 0, QTableWidgetItem(key))
                    if self.table.item(i,1) is None: self.table.setItem(i, 1, QTableWidgetItem("Fehler beim Laden des Werts"))
