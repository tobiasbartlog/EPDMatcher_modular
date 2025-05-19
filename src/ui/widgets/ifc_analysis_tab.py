# src/ui/widgets/ifc_analysis_tab.py
import os  # Für os.path.basename
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QPushButton, QTextEdit,
                             QListWidget, QListWidgetItem, QProgressDialog,
                             QMessageBox, QHBoxLayout, QLabel, QFileDialog, QApplication)  # QMessageBox, QHBoxLayout, QLabel hinzugefügt
from PyQt6.QtCore import pyqtSignal, Qt

# Importiere das neue StackItemWidget
from .stack_item_widget import StackItemWidget


class IfcAnalysisTab(QWidget):
    # Signal: sendet eine Liste von ausgewählten Layer-Daten (jedes ein dict)
    layers_selected_for_epd_match_signal = pyqtSignal(list)

    # stacks_ready = pyqtSignal(list) # Altes Signal, kann ersetzt oder beibehalten werden, falls noch anderswo genutzt

    def __init__(self, ifc_service, parent=None):
        super().__init__(parent)
        self.ifc_service = ifc_service
        self.current_ifc_path = None  # Pfad zur aktuell geladenen IFC-Datei
        self.candidate_ifc_stacks_data = []  # Speichert die Rohdaten der Stapel
        self.stack_item_widgets_in_list = []  # Speichert Referenzen auf die StackItemWidgets in der Liste
        self.currently_selected_stack_item_widget = None  # Das StackItemWidget des angeklickten Listenelements

        self._build_ui()

    def update_ifc_service(self, ifc_service):  # Nützlich, falls Service-Parameter geändert werden
        self.ifc_service = ifc_service
        print("IfcAnalysisTab: IFC Service aktualisiert.")

    def _build_ui(self):
        main_layout = QVBoxLayout(self)

        # Bereich für IFC-Datei Auswahl und Anzeige
        file_selection_layout = QHBoxLayout()
        self.upload_btn = QPushButton("1. IFC-Datei auswählen & analysieren")
        self.upload_btn.clicked.connect(self.on_select_and_analyze_ifc)
        file_selection_layout.addWidget(self.upload_btn)
        self.ifc_file_display_label = QLabel("Keine IFC-Datei ausgewählt.")
        self.ifc_file_display_label.setWordWrap(True)
        file_selection_layout.addWidget(self.ifc_file_display_label, 1)  # Nimmt mehr Platz
        main_layout.addLayout(file_selection_layout)

        # Log-Bereich
        self.log_text_edit = QTextEdit()  # Umbenannt von self.log für Klarheit
        self.log_text_edit.setReadOnly(True)
        self.log_text_edit.setFixedHeight(100)  # Höhe begrenzen
        main_layout.addWidget(self.log_text_edit)

        # Liste für die Stapel-Kandidaten
        self.stacks_list_widget = QListWidget()  # Umbenannt von self.list_widget
        # Wichtig: itemClicked verbinden, um das ausgewählte StackItemWidget zu setzen
        self.stacks_list_widget.itemClicked.connect(self.on_stack_list_item_clicked)
        main_layout.addWidget(self.stacks_list_widget)

        # Button, um ausgewählte Layer zu bestätigen
        self.confirm_layers_btn = QPushButton("2. Ausgewählte Layer für EPD-Suche verwenden")
        self.confirm_layers_btn.setEnabled(False)  # Initial deaktiviert
        self.confirm_layers_btn.clicked.connect(self.on_confirm_selected_layers)
        main_layout.addWidget(self.confirm_layers_btn, alignment=Qt.AlignmentFlag.AlignCenter)

        self.setLayout(main_layout)

    def on_select_and_analyze_ifc(self):
        # QFileDialog.getOpenFileName gibt ein Tupel (filePath, selectedFilter) zurück
        path, _ = QFileDialog.getOpenFileName(
            self,
            "IFC-Datei für Analyse auswählen",
            self.current_ifc_path or "",  # Letzten Pfad vorschlagen
            "IFC-Dateien (*.ifc);;Alle Dateien (*)"
        )
        if not path:
            self.log_text_edit.append("IFC-Auswahl abgebrochen.")
            return

        self.current_ifc_path = path
        self.ifc_file_display_label.setText(f"Analysiere: {os.path.basename(self.current_ifc_path)}")
        self.log_text_edit.clear()
        self.log_text_edit.append(f"Starte IFC-Analyse für: {self.current_ifc_path}")
        self.stacks_list_widget.clear()  # Alte Ergebnisse aus der Liste entfernen
        self.stack_item_widgets_in_list.clear()
        self.currently_selected_stack_item_widget = None
        self.confirm_layers_btn.setEnabled(False)
        QApplication.processEvents()

        progress = QProgressDialog("Analysiere IFC-Datei...", None, 0, 100, self)
        progress.setWindowTitle("IFC Analyse Fortschritt")
        progress.setWindowModality(Qt.WindowModality.ApplicationModal)  # Blockiert andere Interaktionen
        progress.setCancelButton(None)  # Kein Abbrechen-Button
        progress.setMinimumDuration(0)  # Sofort anzeigen
        progress.setValue(0)
        progress.show()
        QApplication.processEvents()

        try:
            self.candidate_ifc_stacks_data = self.ifc_service.analyse(
                ifc_path=self.current_ifc_path,
                message_cb=lambda msg: (self.log_text_edit.append(msg), QApplication.processEvents()),
                progress_cb=lambda current, total, status_text: (
                    progress.setLabelText(status_text),
                    progress.setValue(int(current / total * 100) if total > 0 else 0),
                    QApplication.processEvents()
                )
            )
        except Exception as e:
            progress.close()
            self.log_text_edit.append(f"Fehler während der IFC-Analyse: {e}")
            QMessageBox.critical(self, "IFC Analyse Fehler", f"Ein Fehler ist aufgetreten:\n{e}")
            return

        progress.close()

        if not self.candidate_ifc_stacks_data:
            self.log_text_edit.append("Keine Stapel im IFC-Modell gefunden oder Filter zu streng.")
            QMessageBox.information(self, "IFC Analyse", "Keine Elementstapel im Modell gefunden.")
            return

        self.log_text_edit.append(f"Analyse fertig: {len(self.candidate_ifc_stacks_data)} Stapel-Kandidaten gefunden.")
        self._display_candidate_stacks(self.candidate_ifc_stacks_data)
        # self.stacks_ready.emit(self.candidate_ifc_stacks_data) # Altes Signal, falls noch benötigt

    def _display_candidate_stacks(self, stacks_data: list):
        self.stacks_list_widget.clear()
        self.stack_item_widgets_in_list.clear()
        self.currently_selected_stack_item_widget = None
        self.confirm_layers_btn.setEnabled(False)

        if not stacks_data:
            self.log_text_edit.append("Keine Stapel-Daten zum Anzeigen vorhanden.")
            return

        for i, stack_info in enumerate(stacks_data):
            list_item = QListWidgetItem(self.stacks_list_widget)  # Parent ist das ListWidget
            stack_widget = StackItemWidget(i, stack_info)  # Kein Parent, da es via setItemWidget verwaltet wird

            list_item.setSizeHint(stack_widget.sizeHint())  # Wichtig für korrekte Größe
            # Speichere eine Referenz auf das StackItemWidget im QListWidgetItem
            # (oder umgekehrt, oder halte eine separate Liste, die Indizes abgleicht)
            # Hier: Speichere das Widget direkt im Item für einfachen Zugriff
            list_item.setData(Qt.ItemDataRole.UserRole, stack_widget)  # Speichere das Widget selbst

            self.stacks_list_widget.addItem(list_item)
            self.stacks_list_widget.setItemWidget(list_item, stack_widget)
            self.stack_item_widgets_in_list.append(stack_widget)  # Behalte eine Referenz

        self.log_text_edit.append(
            f"{len(stacks_data)} Stapel zur Liste hinzugefügt. Klicken Sie auf einen Stapel, um Layer auszuwählen.")

    def on_stack_list_item_clicked(self, list_item: QListWidgetItem):
        """Wird aufgerufen, wenn ein Element in der QListWidget angeklickt wird."""
        if not list_item:
            self.currently_selected_stack_item_widget = None
            self.confirm_layers_btn.setEnabled(False)
            return

        # Hole das StackItemWidget, das mit diesem QListWidgetItem verbunden ist
        widget = self.stacks_list_widget.itemWidget(list_item)
        # Alternative, wenn im UserRole gespeichert: widget = list_item.data(Qt.ItemDataRole.UserRole)

        if isinstance(widget, StackItemWidget):
            self.currently_selected_stack_item_widget = widget
            self.confirm_layers_btn.setEnabled(True)  # Button aktivieren, da ein Stapel ausgewählt ist
            self.log_text_edit.append(
                f"Stapel {widget.stack_index + 1} ausgewählt. Bitte Layer ankreuzen und bestätigen.")
        else:
            self.currently_selected_stack_item_widget = None
            self.confirm_layers_btn.setEnabled(False)

    def on_confirm_selected_layers(self):
        if not self.currently_selected_stack_item_widget:
            QMessageBox.warning(self, "Auswahl fehlt", "Bitte wählen Sie zuerst einen Stapel aus der Liste aus.")
            return

        selected_layers = self.currently_selected_stack_item_widget.get_selected_layers_data()

        if not selected_layers:
            QMessageBox.information(self, "Keine Layer ausgewählt",
                                    "Es wurden keine Layer (Schichten) im aktuell ausgewählten Stapel angekreuzt.")
            return

        self.log_text_edit.append(f"{len(selected_layers)} Layer für EPD-Suche ausgewählt und an Matcher-Tab gesendet.")
        # Sende das Signal mit den Daten der ausgewählten Layer
        self.layers_selected_for_epd_match_signal.emit(selected_layers)

        QMessageBox.information(self, "Layer übernommen",
                                f"{len(selected_layers)} Layer wurden für die EPD-Suche vorbereitet.\n"
                                "Die Layer erscheinen als neue Tabs im 'EPD Matching'-Bereich.")