# src/main.py
import sys
import os
from PyQt6.QtWidgets import QApplication, QMainWindow, QTabWidget, QMessageBox
from PyQt6.QtGui import QIcon

# Core / Config
from src.core.config_manager import ConfigManager
from src.core.db_setup import init_db, get_connection

# Services
from src.services.epd_service import EPDService
from src.services.llm_service import LLMService
from src.services.fuzzy_service import fuzzy_search
from src.services.ifc_service import IFCService

# UI-Tabs
from src.ui.widgets.epd_matcher_tab import EpdMatcherTab
from src.ui.widgets.ifc_analysis_tab import IfcAnalysisTab
from src.ui.widgets.results_tab import ResultsTab


class MainWindow(QMainWindow):
    def __init__(self, base_path: str):
        super().__init__()
        self.base_path = base_path
        self.setWindowTitle("EPD Matcher")
        self.setMinimumSize(1000, 700)

        # Icon laden
        icon_path = os.path.join(base_path, "assets", "icon.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        # Datenbank initialisieren (erstes Mal)
        db_file = os.path.join(base_path, "assets", "oekobaudat_epds.db")
        init_db(db_file)

        # Config & Services
        cfg = ConfigManager()
        llm = LLMService(api_key=cfg.api_key)
        ifc = IFCService()  # implementiere select_ifc_file + analyse(...)
        # epd_service kann man als Objekt oder als Modul-Funktionssatz anbieten
        # wir packen beide fetch und details in ein kleines Objekt:
        class EpdSrv:
            @staticmethod
            def fetch_epds_by_labels(labels, cols):
                return fetch_epds_by_labels(labels, cols)
            @staticmethod
            def get_available_labels():
                # aus Konstanten oder DB ermitteln
                return cfg.possible_labels
            @staticmethod
            def get_relevant_columns():
                return cfg.relevant_columns
            @staticmethod
            def get_epd_details(uuid):
                return get_epd_details(uuid)

        epd_srv = EpdSrv()

        # Central TabWidget
        self.tabs = QTabWidget(self)
        self.setCentralWidget(self.tabs)

        # 1) EPD-Matcher
        self.matcher_tab = EpdMatcherTab(
            epd_service=epd_srv,
            llm_service=llm,
            fuzzy_search=fuzzy_search
        )
        self.tabs.addTab(self.matcher_tab, "EPD Matching")

        # 2) IFC-Analyse
        self.ifc_tab = IfcAnalysisTab(ifc_service=ifc)
        self.tabs.addTab(self.ifc_tab, "IFC Analyse")

        # 3) Details/Ergebnisse
        self.results_tab = ResultsTab(epd_service=epd_srv)
        self.tabs.addTab(self.results_tab, "Details")

        # Signal-Verknüpfungen
        # Wenn im Matcher Tab eine EPD ausgewählt wurde, zeige Details:
        self.matcher_tab.match_selected.connect(self.on_match_selected)
        # Wenn die IFC-Analyse neue Stacks liefert, kann der Matcher sie nutzen:
        self.ifc_tab.stacks_ready.connect(self.on_ifc_stacks_ready)

    def on_match_selected(self, uuid: str):
        """ Slot, wenn EPD aus Matcher ausgewählt wird """
        # Tab auf Details umschalten und Daten füllen
        self.tabs.setCurrentWidget(self.results_tab)
        self.results_tab.on_match_selected(uuid)

    def on_ifc_stacks_ready(self, stacks: list):
        """ Slot, wenn IFC-Analyse fertig ist. Hier könntest Du z.B.
            automatisch in den Matcher-Reiter Tabs für jede Schicht erzeugen. """
        # Beispiel: Umschalten zum Matcher-Tab
        self.tabs.setCurrentWidget(self.matcher_tab)
        # Und eine Hilfsmethode aufrufen, die die `matcher_tab` mit den Stacks versorgt:
        try:
            self.matcher_tab.populate_from_ifc(stacks)
        except AttributeError:
            # falls noch nicht implementiert – nur exemplarisch
            pass


if __name__ == "__main__":
    app = QApplication(sys.argv)

    # Base-Path ermitteln (für assets, DB etc.)
    if getattr(sys, "frozen", False):
        base = sys._MEIPASS
    else:
        base = os.path.dirname(os.path.abspath(__file__))

    window = MainWindow(base)
    window.showMaximized()
    sys.exit(app.exec())
