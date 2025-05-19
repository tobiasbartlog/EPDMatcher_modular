# src/ui/main_window.py
import os
from PyQt6.QtWidgets import (
    QMainWindow, QTabWidget, QMessageBox, QInputDialog, QLineEdit,
    QApplication  # Nur für processEvents, falls direkt benötigt
)
from PyQt6.QtGui import QIcon, QAction

from src.core.config_manager import ConfigManager
from src.services.epd_service import EPDService
from src.services.ifc_service import IFCService
from src.services.llm_service import LLMService
# Die fuzzy_search Funktion wird direkt im EpdMatcherTab importiert und verwendet.

from src.ui.widgets.epd_matcher_tab import EpdMatcherTab
from src.ui.widgets.ifc_analysis_tab import IfcAnalysisTab
from src.ui.widgets.results_tab import ResultsTab
from src.utils.constants import DB_FILE as DEFAULT_DB_FILENAME  # Für den Fall, dass base_path nicht funktioniert


class MainWindow(QMainWindow):
    def __init__(self, base_path: str):
        super().__init__()
        self.base_path = base_path

        # --- Config & Services ---
        self.cfg = ConfigManager()

        # Pfad zur Datenbank bestimmen
        # Annahme: DB_FILE aus constants.py ist nur der Dateiname.
        # assets_dir wird relativ zum base_path des Projekts erwartet.
        db_path_constructed = os.path.join(self.base_path, "assets", DEFAULT_DB_FILENAME)

        # Fallback, falls der base_path nicht korrekt ermittelt wurde oder die DB woanders liegt
        # Diese Logik hängt stark davon ab, wie DB_FILE in constants.py definiert ist
        # und wo die DB tatsächlich liegt.
        if not os.path.exists(db_path_constructed) and os.path.exists(DEFAULT_DB_FILENAME):
            db_actual_path = DEFAULT_DB_FILENAME  # Nutze den direkten Pfad aus constants, falls er absolut ist
        elif os.path.exists(db_path_constructed):
            db_actual_path = db_path_constructed
        else:
            # Letzter Ausweg: Versuche es im aktuellen Arbeitsverzeichnis oder einem vordefinierten Ort
            # Für jetzt geben wir einen Fehler aus, wenn die DB nicht gefunden wird.
            # In einer robusten Anwendung müsste hier eine bessere Logik her (z.B. User fragen).
            QMessageBox.critical(self, "Datenbankfehler",
                                 f"Datenbankdatei nicht gefunden unter {db_path_constructed} oder {DEFAULT_DB_FILENAME}. Bitte Pfade in src/utils/constants.py prüfen.")
            # Beende die Anwendung oder biete einen Dialog zur Auswahl der DB an.
            # Hier vereinfacht:
            raise FileNotFoundError(f"Database not found at {db_path_constructed} or {DEFAULT_DB_FILENAME}")

        self.epd_svc = EPDService(db_path=db_actual_path)
        self.llm_svc = LLMService(api_key=self.cfg.api_key, model=self.cfg.model)
        self.ifc_svc = IFCService(
            min_proxy_thickness=self.cfg.ifc_min_proxy_thickness,
            xy_tolerance=self.cfg.ifc_xy_tolerance,
            min_elements_in_stack=self.cfg.ifc_min_elements_in_stack
        )

        # --- UI Setup ---
        self.setWindowTitle("EPD Matcher (Modular)")
        self.setMinimumSize(1100, 800)  # Aus oldfile.py übernommen

        icon_path_constructed = os.path.join(self.base_path, "assets", "icon.ico")
        if os.path.exists(icon_path_constructed):
            self.setWindowIcon(QIcon(icon_path_constructed))
        else:
            print(f"WARNUNG: Icon nicht gefunden unter {icon_path_constructed}")
            # Fallback, falls das Icon direkt im src-Verzeichnis oder assets ohne base_path-Konstruktion liegt
            fallback_icon_path = os.path.join("assets", "icon.ico")  # Relativ zum Startskript
            if os.path.exists(fallback_icon_path):
                self.setWindowIcon(QIcon(fallback_icon_path))
            else:
                print(f"WARNUNG: Icon auch nicht unter {fallback_icon_path} gefunden.")

        # Erstelle die einzelnen Tab-Widgets
        self.epd_tab = EpdMatcherTab(
            epd_service=self.epd_svc,
            llm_service=self.llm_svc,
            config_manager=self.cfg  # Für top_n etc.
        )
        self.ifc_tab = IfcAnalysisTab(
            ifc_service=self.ifc_svc)  # cfg hier optional, wenn IFC-Settings nur global geändert werden
        self.results_tab = ResultsTab(epd_service=self.epd_svc)

        # QTabWidget zusammenstellen
        self.tabs = QTabWidget()
        self.tabs.addTab(self.epd_tab, "EPD Matching")
        self.tabs.addTab(self.ifc_tab, "IFC Analyse")
        self.tabs.addTab(self.results_tab, "Ergebnisse")
        self.setCentralWidget(self.tabs)

        self.setup_menu()
        self._connect_signals()

    def setup_menu(self):
        menubar = self.menuBar()
        # Datei-Menü (optional, da IFC-Upload im Tab ist)
        # file_menu = menubar.addMenu("Datei")
        # act_upload_ifc_general = QAction("IFC-Datei hochladen (Allgemein)...", self)
        # act_upload_ifc_general.triggered.connect(self.upload_ifc_general)
        # file_menu.addAction(act_upload_ifc_general)

        settings_menu = menubar.addMenu("Einstellungen")

        act_openai_model = QAction("OpenAI Modell...", self)
        act_openai_model.triggered.connect(self.change_openai_model)
        settings_menu.addAction(act_openai_model)

        act_topn = QAction("Anzahl EPDs (Top N für LLM)...", self)
        act_topn.triggered.connect(self.change_top_n)
        settings_menu.addAction(act_topn)

        act_key = QAction("OpenAI API-Key...", self)
        act_key.triggered.connect(self.change_api_key)
        settings_menu.addAction(act_key)

        settings_menu.addSeparator()

        act_ifc_settings = QAction("IFC Analyse Parameter...", self)
        act_ifc_settings.triggered.connect(self.open_ifc_settings_dialog)
        settings_menu.addAction(act_ifc_settings)

        help_menu = menubar.addMenu("Hilfe")
        act_about = QAction("Über EPD Matcher…", self)
        act_about.triggered.connect(self.show_about_dialog)
        help_menu.addAction(act_about)

    def _connect_signals(self):
        # Wenn im Matcher Tab eine EPD ausgewählt wurde, zeige Details im ResultsTab
        # Annahme: EpdMatcherTab hat ein Signal 'match_selected' das eine UUID sendet
        self.epd_tab.match_selected.connect(self.results_tab.on_match_selected)
        self.epd_tab.match_selected.connect(lambda uuid: self.tabs.setCurrentWidget(self.results_tab))

        # Wenn die IFC-Analyse neue Stacks/Layer liefert, kann der Matcher sie nutzen
        # Annahme: IfcAnalysisTab hat ein Signal 'stacks_ready' oder 'layers_for_epd_search_ready'
        # das eine Liste von Layer-Daten (z.B. Dictionaries) sendet.
        # Und EpdMatcherTab hat einen Slot, um diese Daten zu empfangen.
        # self.ifc_tab.stacks_ready.connect(self.epd_tab.populate_from_ifc_stacks)
        # Beispiel für eine direktere Weitergabe an den EPD-Tab für die Erstellung von Such-Tabs:
        if hasattr(self.ifc_tab, 'layers_selected_for_epd_match_signal') and \
                hasattr(self.epd_tab, 'handle_ifc_layers_for_search'):
            self.ifc_tab.layers_selected_for_epd_match_signal.connect(
                self.epd_tab.handle_ifc_layers_for_search
            )
            self.ifc_tab.layers_selected_for_epd_match_signal.connect(
                lambda: self.tabs.setCurrentWidget(self.epd_tab)
            )
        # Die Signale in den Tabs müssen noch exakt definiert werden.
        # z.B. in ifc_analysis_tab.py:
        # layers_selected_for_epd_match_signal = pyqtSignal(list)
        # Und in epd_matcher_tab.py ein Slot:
        # @pyqtSlot(list)
        # def handle_ifc_layers_for_search(self, layers_data): ...

    def change_openai_model(self):
        current_model = self.cfg.model
        text, ok = QInputDialog.getText(self, "OpenAI Modell",
                                        "Bitte OpenAI Modellnamen eingeben (z.B. gpt-3.5-turbo, gpt-4):",
                                        QLineEdit.EchoMode.Normal, current_model)
        if ok and text and text.strip():
            self.cfg.model = text.strip()
            try:
                # LLMService neu initialisieren oder aktualisieren
                self.llm_svc = LLMService(api_key=self.cfg.api_key, model=self.cfg.model)
                # Den EpdMatcherTab informieren, falls er eine eigene Referenz hält
                if hasattr(self.epd_tab, 'update_llm_service'):
                    self.epd_tab.update_llm_service(self.llm_svc)
                QMessageBox.information(self, "Modell gespeichert",
                                        f"Das OpenAI Modell wurde auf '{self.cfg.model}' aktualisiert.")
            except Exception as e:
                QMessageBox.critical(self, "Fehler",
                                     f"Fehler beim Aktualisieren des LLM Service mit neuem Modell:\n{e}")

    def change_top_n(self):
        val, ok = QInputDialog.getInt(
            self, "Anzahl EPDs (Top N für LLM)",
            "Wie viele EPDs sollen maximal als Kontext für das LLM abgefragt werden?",
            value=self.cfg.top_n, min=1, max=500
        )
        if ok:
            self.cfg.top_n = val
            QMessageBox.information(self, "Gespeichert", f"Top-N für LLM auf {val} gesetzt.")
            # Der EpdMatcherTab greift direkt auf cfg.top_n zu, wenn er es braucht.

    def change_api_key(self):
        current_key = self.cfg.api_key
        key, ok = QInputDialog.getText(self, "OpenAI API-Key",
                                       "Bitte neuen OpenAI API-Key eingeben:",
                                       QLineEdit.EchoMode.Password, current_key)
        if ok and key:  # Nur fortfahren, wenn OK geklickt und Text nicht leer ist
            self.cfg.api_key = key.strip()
            try:
                # LLMService neu initialisieren oder aktualisieren
                self.llm_svc = LLMService(api_key=self.cfg.api_key, model=self.cfg.model)
                # Den EpdMatcherTab informieren, falls er eine eigene Referenz hält
                if hasattr(self.epd_tab, 'update_llm_service'):
                    self.epd_tab.update_llm_service(self.llm_svc)

                QMessageBox.information(self, "API-Key gespeichert", "Der OpenAI API-Key wurde aktualisiert.")
            except Exception as e:
                QMessageBox.critical(self, "Fehler", f"Fehler beim Initialisieren des Clients mit neuem Key:\n{e}")

    def open_ifc_settings_dialog(self):
        # Für jeden Parameter einzeln oder einen benutzerdefinierten Dialog erstellen
        # Hier Beispiel für min_proxy_thickness
        val_thickness, ok1 = QInputDialog.getDouble(
            self, "IFC: Minimale Proxy-Dicke",
            "Minimale Dicke für IfcBuildingElementProxy (in Metern, z.B. 0.01 für 1cm):",
            value=self.cfg.ifc_min_proxy_thickness, decimals=3, min=0.001, max=10.0
        )
        if not ok1: return

        val_tolerance, ok2 = QInputDialog.getDouble(
            self, "IFC: XY-Toleranz",
            "XY-Toleranz für Mittelpunktgruppierung (in Metern, z.B. 0.5 für 50cm):",
            value=self.cfg.ifc_xy_tolerance, decimals=2, min=0.01, max=100.0
        )
        if not ok2: return

        val_min_elements, ok3 = QInputDialog.getInt(
            self, "IFC: Minimale Stapelhöhe",
            "Minimale Anzahl Elemente in einem erkannten Stapel (vertikale Säule):",
            value=self.cfg.ifc_min_elements_in_stack, min=1, max=100
        )
        if not ok3: return

        # Werte im ConfigManager aktualisieren
        self.cfg.ifc_min_proxy_thickness = val_thickness
        self.cfg.ifc_xy_tolerance = val_tolerance
        self.cfg.ifc_min_elements_in_stack = val_min_elements

        try:
            # IFCService neu initialisieren oder aktualisieren
            self.ifc_svc = IFCService(
                min_proxy_thickness=self.cfg.ifc_min_proxy_thickness,
                xy_tolerance=self.cfg.ifc_xy_tolerance,
                min_elements_in_stack=self.cfg.ifc_min_elements_in_stack
            )
            # Den IfcAnalysisTab informieren, falls er eine eigene Referenz hält
            if hasattr(self.ifc_tab, 'update_ifc_service'):
                self.ifc_tab.update_ifc_service(self.ifc_svc)
            QMessageBox.information(self, "Gespeichert", "Die Parameter für die IFC Analyse wurden aktualisiert.")
        except Exception as e:
            QMessageBox.critical(self, "Fehler", f"Fehler beim Aktualisieren des IFC Service:\n{e}")

    def show_about_dialog(self):
        QMessageBox.information(
            self, "Über EPD Matcher",
            "EPD Matcher v0.2 (Modular)\n"  # Beispiel Versionsnummer
            "© 2024-2025 Tobias Bartlog\n"
            "Alle Rechte vorbehalten.\n\n"
            "Entwickelt im Rahmen einer Forschungsarbeit.\n"
            "Weitere Informationen: https://github.com/tobiasbartlog/epdmatcher_modular"  # Platzhalter URL
        )

    # def upload_ifc_general(self): # Falls noch benötigt
    #     # Diese Funktion war in oldfile.py, aber IFC-Upload ist nun im IfcAnalysisTab
    #     # Falls ein allgemeiner Upload-Dialog im Menü gewünscht ist:
    #     path, _ = QFileDialog.getOpenFileName(self, "IFC-Datei auswählen", "", "IFC-Dateien (*.ifc)")
    #     if path:
    #         QMessageBox.information(self, "IFC Geladen", f"IFC-Datei ausgewählt:\n{path}\n\nNutzen Sie den 'IFC Analyse'-Tab zur Verarbeitung.")