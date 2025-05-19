# src/ui/main_window.py

from PyQt6.QtWidgets import QMainWindow, QApplication
from PyQt6.QtGui     import QIcon
from src.core.config_manager import ConfigManager
from src.services.epd_service   import EPDService
from src.services.ifc_service   import IFCService
from src.services.llm_service   import LLMService
from src.services.fuzzy_service import fuzzy_search
from src.ui.widgets.epd_matcher_tab import EpdMatcherTab
from src.ui.widgets.ifc_analysis_tab import IfcAnalysisTab
from src.ui.widgets.results_tab import ResultsTab
# from src.ui.styles import GLOBAL_STYLES

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        # --- Config & Services ---
        cfg = ConfigManager()
        self.epd_svc = EPDService()
        self.llm_svc = LLMService(api_key=cfg.api_key, model=cfg.model)
        self.ifc_svc = IFCService(
            min_proxy_thickness=cfg.ifc_min_proxy_thickness,
            xy_tolerance=cfg.ifc_xy_tolerance,
            min_elements_in_stack=cfg.ifc_min_elements_in_stack
        )

        # --- UI Setup ---
        self.setWindowTitle("EPD Matcher")
        self.setWindowIcon(QIcon(":/icons/app_icon.png"))
        #self.setStyleSheet(GLOBAL_STYLES)

        # Erstelle die einzelnen Tab-Widgets und injiziere jeweils die benötigten Services
        self.epd_tab = EpdMatcherTab(epd_service=self.epd_svc, llm_service=self.llm_svc)
        self.ifc_tab = IfcAnalysisTab(ifc_service=self.ifc_svc)
        self.results_tab = ResultsTab()

        # QTabWidget zusammenstellen
        self.tabs = QTabWidget()
        self.tabs.addTab(self.epd_tab,     "EPD Matching")
        self.tabs.addTab(self.ifc_tab,     "IFC Analyse")
        self.tabs.addTab(self.results_tab, "Ergebnisse")
        self.setCentralWidget(self.tabs)
