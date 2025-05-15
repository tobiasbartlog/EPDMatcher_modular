# gui_matcher_pyqt.py (Robustere Version mit Erklärungen)

import sys
import json
import sqlite3
import os
import re
import datetime
from difflib import SequenceMatcher
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QTextEdit, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget,
    QCheckBox, QPushButton, QGroupBox, QScrollArea, QRadioButton, QButtonGroup, QPlainTextEdit,
    QMessageBox, QSizePolicy, QTabWidget, QInputDialog, QProgressDialog, QLineEdit, QMenuBar, QTableWidgetItem,
    QFileDialog, QListWidget, QListWidgetItem, QFrame, QHeaderView
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QAction, QIcon
from configparser import ConfigParser, NoOptionError

from src import identstreetlayers

# --- Modulimporte mit Fehlerbehandlung ---
try:
    from openai import OpenAI
    import openai
except ImportError:
    print("FATAL ERROR: openai library not installed. Please install it: pip install openai")
    try:
        app_err = QApplication.instance()
        if app_err is None:
            app_err = QApplication(sys.argv)
        QMessageBox.critical(None, "Fatal Error", "OpenAI library not found.\nPlease install it: pip install openai")
    except Exception:
        pass
    sys.exit(1)

try:
    import src.fetch_epd

    fetch_epd_available = True
except ImportError:
    print("WARNING: 'fetch_epd.py' not found. Fetching EPD details will not work.")
    fetch_epd = None
    fetch_epd_available = False

try:
    from src.epd_environmental_parser import extract_environmental_data

    parser_available = True
except ImportError:
    print("WARNING: 'epd_environmental_parser.py' not found. Environmental data extraction/saving is disabled.")
    parser_available = False
# --- Ende Modulimporte ---


# --- Konfiguration ---
if getattr(sys, 'frozen', False):
    base_path = sys._MEIPASS
else:
    base_path = os.path.dirname(os.path.abspath(__file__))

DB_FILE = os.path.join(base_path, "oekobaudat_epds.db")
LABELS_COLUMN_NAME = "application_labels"
INDICATORS_TABLE_NAME = "epd_environmental_indicators"

# POSSIBLE_LABELS = [
#     "STRASSENBAU", "HOCHBAU_TRAGWERK", "HOCHBAU_FASSADE", "HOCHBAU_DACH",
#     "HOCHBAU_INNENAUSBAU", "TIEFBAU", "BRUECKENBAU", "TGA_HAUSTECHNIK",
#     "DAEMMSTOFFE", "ABDICHTUNG_BAUWERK", "LANDSCHAFTSBAU_AUSSENANLAGEN",
#     "INDUSTRIE_ANLAGENBAU", "MOEBEL_INNENEINRICHTUNG", "SONSTIGES_UNKLAR"
# ]
# RELEVANT_COLUMNS_FOR_LLM_CONTEXT = [
#     "name", "classification_path", "owner", "compliance", "data_sources", "sub_type",
#     "general_comment_de", "tech_desc_de", "tech_app_de", "use_advice_de"
# ]


# --- DB-Hilfsfunktionen (global, außerhalb der Klasse) ---
def create_env_indicator_table_json(cursor):
    try:
        cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS {INDICATORS_TABLE_NAME} (
            uuid TEXT PRIMARY KEY,
            lcia_results_json TEXT,
            key_flows_json TEXT,
            biogenic_carbon_json TEXT,
            last_updated TEXT,
            FOREIGN KEY (uuid) REFERENCES epds (uuid) ON DELETE CASCADE
        )
        """)
        print(f"DEBUG: Tabelle '{INDICATORS_TABLE_NAME}' (JSON) initialisiert/überprüft.")
    except sqlite3.Error as e:
        print(f"ERROR: Fehler beim Erstellen der Tabelle {INDICATORS_TABLE_NAME}: {e}")
        raise


def save_env_data_to_db_json(cursor, uuid, env_data):
    if not uuid or not env_data: print("DEBUG: Keine UUID/Daten zum Speichern."); return False
    lcia_json = json.dumps(env_data.get('LCIA Results', {}), ensure_ascii=False, indent=2)
    flows_json = json.dumps(env_data.get('Key Flows', {}), ensure_ascii=False, indent=2)
    biogen_json = json.dumps(env_data.get('Biogener Kohlenstoff', {}), ensure_ascii=False, indent=2)
    now_str = datetime.datetime.now().isoformat()
    sql = f"""
    INSERT OR REPLACE INTO {INDICATORS_TABLE_NAME}
    (uuid, lcia_results_json, key_flows_json, biogenic_carbon_json, last_updated)
    VALUES (?, ?, ?, ?, ?)
    """
    try:
        cursor.execute(sql, (uuid, lcia_json, flows_json, biogen_json, now_str))
        print(f"DEBUG: JSON-Daten für UUID {uuid} gespeichert/aktualisiert.")
        return True
    except sqlite3.Error as e:
        print(f"ERROR: Fehler Speichern JSON-Daten für {uuid}: {e}")
        return False


# CONFIG_DIR = os.path.join(os.getenv("APPDATA") or os.path.expanduser("~"), "EPDMatcher")
# CONFIG_PATH = os.path.join(CONFIG_DIR, "config.ini")
# DEFAULT_TOP_N = 70
# DEFAULT_IFC_MIN_PROXY_THICKNESS = 0.01
# DEFAULT_IFC_XY_TOLERANCE = 0.5
# DEFAULT_IFC_MIN_ELEMENTS_IN_STACK = 4


# def load_config():
#     os.makedirs(CONFIG_DIR, exist_ok=True)
#     cfg = ConfigParser()
#     if os.path.exists(CONFIG_PATH):
#         cfg.read(CONFIG_PATH, encoding="utf-8")
#
#     if not cfg.has_section("openai"):
#         cfg.add_section("openai")
#     api_key = cfg.get("openai", "api_key", fallback="")
#     if not cfg.has_option("openai", "api_key"):
#         cfg.set("openai", "api_key", api_key)
#     try:
#         top_n = cfg.getint("openai", "top_n_for_llm")
#     except (ValueError, NoOptionError):
#         top_n = DEFAULT_TOP_N
#     if not cfg.has_option("openai", "top_n_for_llm") or str(cfg.get("openai", "top_n_for_llm")) != str(top_n):
#         cfg.set("openai", "top_n_for_llm", str(top_n))
#
#     if not cfg.has_section("ifc_settings"):
#         cfg.add_section("ifc_settings")
#     try:
#         ifc_min_proxy_thickness = cfg.getfloat("ifc_settings", "min_proxy_thickness")
#     except (ValueError, NoOptionError):
#         ifc_min_proxy_thickness = DEFAULT_IFC_MIN_PROXY_THICKNESS
#     if not cfg.has_option("ifc_settings", "min_proxy_thickness") or \
#             str(cfg.get("ifc_settings", "min_proxy_thickness", fallback=str(DEFAULT_IFC_MIN_PROXY_THICKNESS))) != str(
#         ifc_min_proxy_thickness):
#         cfg.set("ifc_settings", "min_proxy_thickness", str(ifc_min_proxy_thickness))
#     try:
#         ifc_xy_tolerance = cfg.getfloat("ifc_settings", "xy_tolerance")
#     except (ValueError, NoOptionError):
#         ifc_xy_tolerance = DEFAULT_IFC_XY_TOLERANCE
#     if not cfg.has_option("ifc_settings", "xy_tolerance") or \
#             str(cfg.get("ifc_settings", "xy_tolerance", fallback=str(DEFAULT_IFC_XY_TOLERANCE))) != str(
#         ifc_xy_tolerance):
#         cfg.set("ifc_settings", "xy_tolerance", str(ifc_xy_tolerance))
#     try:
#         ifc_min_elements_in_stack = cfg.getint("ifc_settings", "min_elements_in_stack")
#     except (ValueError, NoOptionError):
#         ifc_min_elements_in_stack = DEFAULT_IFC_MIN_ELEMENTS_IN_STACK
#     if not cfg.has_option("ifc_settings", "min_elements_in_stack") or \
#             str(cfg.get("ifc_settings", "min_elements_in_stack",
#                         fallback=str(DEFAULT_IFC_MIN_ELEMENTS_IN_STACK))) != str(ifc_min_elements_in_stack):
#         cfg.set("ifc_settings", "min_elements_in_stack", str(ifc_min_elements_in_stack))
#
#     with open(CONFIG_PATH, "w", encoding="utf-8") as f:
#         cfg.write(f)
#     return (api_key, top_n,
#             ifc_min_proxy_thickness, ifc_xy_tolerance, ifc_min_elements_in_stack)


# Am Anfang von guifull.py, nach den Imports

class StackItemWidget(QWidget):
    def __init__(self, stack_index, stack_info, parent=None):
        super().__init__(parent)
        self.stack_index = stack_index
        self.stack_info = stack_info
        self.layer_checkboxes = []

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(5, 5, 5, 5)  # Kleiner Innenabstand
        self.main_layout.setSpacing(3)

        # Stil für den Rahmen (wird auf das Widget selbst angewendet)
        self.setStyleSheet("""
            StackItemWidget {
                border: 1px solid #cccccc; /* Rahmen etwas dunkler für bessere Sichtbarkeit */
                border-radius: 4px;
                background-color: #f0f0f0; /* Heller Grauton für bessere Erkennbarkeit */
                padding: 3px; /* Etwas Innenabstand, damit der Inhalt nicht am Rand klebt */
            }
            StackItemWidget:selected { /* Optional: Spezieller Stil, wenn das ListWidget-Item ausgewählt ist */
                background-color: #e0e8f0; /* Heller Blauton bei Auswahl */
            }
            QLabel {
                border: none; /* Kein doppelter Rahmen für Labels innen */
                background-color: transparent;
            }
        """)

        # Titel des Stapels
        approx_mid_x = self.stack_info.get('approx_mid_x', 0.0)
        approx_mid_y = self.stack_info.get('approx_mid_y', 0.0)
        count = self.stack_info.get('count', 0)
        title_text = f"Stapel {self.stack_index + 1} (X={approx_mid_x:.2f}, Y={approx_mid_y:.2f} | {count} Elemente)"
        title_label = QLabel(f"<b>{title_text}</b>")  # Fett für den Titel
        self.main_layout.addWidget(title_label)

        # Horizontale Linie als Trenner
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        self.main_layout.addWidget(line)

        # Details für jedes Element (Layer) im Stapel
        elements = self.stack_info.get('elements', [])
        for k, elem_data in enumerate(elements):
            elem_name = elem_data.get('name', 'N/A')
            elem_guid_short = elem_data.get('guid', 'N/A')[:8]
            elem_min_z = elem_data.get('min_z', 0.0)
            elem_max_z = elem_data.get('max_z', 0.0)
            elem_thickness = elem_data.get('thickness_global_bbox', 0.0)

            layer_layout = QHBoxLayout()  # Layout für Checkbox und Label

            checkbox = QCheckBox()
            checkbox.setVisible(True)  # Checkboxen initial verstecken
            checkbox.setStyleSheet("""
                QCheckBox::indicator {
                border: 1px solid #707070; /* Dunkelgrauer Rahmen für den Indikator */
                width: 13px;
                height: 13px;
                border-radius: 3px;
                }
                QCheckBox::indicator:checked {
                background-color: #0078d4; /* Blauer Hintergrund, wenn ausgewählt */
                border: 1px solid #005a9e;
                }
                QCheckBox::indicator:unchecked {
                background-color: #ffffff; /* Weißer Hintergrund, wenn nicht ausgewählt */
                }
            """)
            checkbox.setProperty("layer_data", elem_data)  # Speichere Layer-Daten in der Checkbox
            self.layer_checkboxes.append(checkbox)
            layer_layout.addWidget(checkbox)

            layer_text = (f"Layer {k + 1}: {elem_name} (ID: {elem_guid_short}...)\n"
                          f"  Z: {elem_min_z:.3f}m bis {elem_max_z:.3f}m | Dicke: {elem_thickness:.3f}m")
            layer_label = QLabel(layer_text)
            layer_label.setWordWrap(True)
            layer_layout.addWidget(layer_label, 1)  # Label nimmt mehr Platz

            self.main_layout.addLayout(layer_layout)

        self.setLayout(self.main_layout)

    def set_checkbox_visibility(self, visible):
        for checkbox in self.layer_checkboxes:
            checkbox.setVisible(visible)

    def get_selected_layers_data(self):
        selected_data = []
        for checkbox in self.layer_checkboxes:
            if checkbox.isChecked():
                selected_data.append(checkbox.property("layer_data"))
        return selected_data

class EPDMatcherApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowIcon(QIcon(os.path.join(base_path, "icon.ico")))
        self.central = QWidget()
        self.setCentralWidget(self.central)
        self.main_layout = QVBoxLayout(self.central)

        self.candidate_ifc_stacks_data = []
        self.stack_item_widgets = []  # NEU: Liste für die Custom Widgets
        self.currently_selected_stack_widget = None  # NEU: Referenz auf das Widget mit sichtbaren Checkboxen

        (self.api_key, self.top_n_for_llm,
         self.ifc_min_proxy_thickness,
         self.ifc_xy_tolerance,
         self.ifc_min_elements_in_stack) = load_config()

        try:
            self.openai_client = OpenAI(api_key=self.api_key, timeout=60.0)
        except Exception as e:
            QMessageBox.critical(self, "OpenAI Fehler", f"Fehler bei Client-Initialisierung:\n{e}")
            QTimer.singleShot(0, self.close);
            return

        self.label_checkboxes = {}
        self.column_checkboxes = {}
        self.radio_buttons = []
        self.radio_group = QButtonGroup(self)
        self.loading_dialog = None

        # Für IFC Analyse Tab
        self.current_ifc_for_analysis = None
        self.candidate_ifc_stacks_data = []  # Wird schon weiter oben initialisiert, hier ggf. redundant
        self.stack_item_widgets = []
        self.currently_selected_stack_widget = None
        # self.ifc_message_box = None # Wird in setup_ui_layout erstellt und zugewiesen
        # self.ifc_stacks_listwidget = None # Wird in setup_ui_layout erstellt und zugewiesen
        # self.confirm_stack_button = None # Wird in setup_ui_layout erstellt und zugewiesen
        # self.ifc_file_display_label = None # Wird in setup_ui_layout erstellt und zugewiesen

        # NEU: Für dynamische Tabs im EPD Matching Bereich (schon vorhanden)
        self.layer_epd_search_tabs = None
        self.manual_input_box = None
        self.active_layer_search_widgets = []

        # NEU: Für dynamische Ergebnis-Tabs
        self.result_details_tab_widget = None  # QTabWidget für Text-Details
        self.result_tables_tab_widget = None  # QTabWidget für Tabellen-Details
        self.active_result_widgets = {}  # Speichert {'context_title': {'text_edit': QPlainTextEdit, 'tables': {'general': QTW, ...}, 'details_tab_index': int, 'tables_tab_index': int}}
        self.current_epd_search_context_title = "Manuelle Suche"  # Default Kontext

        self.setWindowTitle("EPD Matcher")
        self.setMinimumSize(1100, 800)
        self.apply_stylesheet()
        self.setup_ui_layout()

    def fuzzy_search(self, user_input: str, epds: list[dict], columns: list[str], cutoff: float = 0.5):
        # Sicherstellen, dass user_input ein String ist und nicht leer
        if not isinstance(user_input, str) or not user_input:
            print("DEBUG fuzzy_search: Ungültiger user_input (kein String oder leer), gebe leere Liste zurück.")
            return []

        ui = user_input.lower()
        hits = []

        if not epds:  # Wenn keine EPDs vorhanden sind, direkt leere Liste zurückgeben
            print("DEBUG fuzzy_search: Keine EPDs zum Durchsuchen vorhanden.")
            return []

        for epd_idx, epd in enumerate(epds):
            if not isinstance(epd, dict):  # Zusätzliche Sicherheit
                print(f"DEBUG fuzzy_search: EPD bei Index {epd_idx} ist kein Dictionary, wird übersprungen.")
                continue

            parts = []
            # Name immer als erstes Teil, sicherstellen, dass es ein String ist
            name_val = epd.get("name", "")  # Default auf Leerstring, falls "name" fehlt
            parts.append(str(name_val) if name_val is not None else "")

            for col in columns:
                val = epd.get(col)
                # Nur Strings oder konvertierbare Werte hinzufügen, None-Werte als Leerstring behandeln
                parts.append(str(val) if val is not None else "")

            text_to_match = ""
            try:
                # Alle Teile explizit in Strings umwandeln, bevor sie verbunden werden
                text_to_match = " \u23AF ".join(map(str, parts)).lower()  # \u23AF ist der horizontale Strich
            except Exception as e_join:
                print(
                    f"DEBUG fuzzy_search: Fehler beim Erstellen von text_to_match für EPD {epd.get('uuid', 'Unbekannt')}: {e_join}")
                continue  # Nächstes EPD

            if not text_to_match:  # Überspringen, wenn kein Text zum Matchen vorhanden ist
                # print(f"DEBUG fuzzy_search: Kein text_to_match für EPD {epd.get('uuid', 'Unbekannt')}, wird übersprungen.")
                continue

            try:
                # SequenceMatcher erwartet Strings.
                # Stellen Sie sicher, dass ui und text_to_match definitiv Strings sind.
                if not isinstance(ui, str) or not isinstance(text_to_match, str):
                    print(
                        f"DEBUG fuzzy_search: Ungültige Typen für SequenceMatcher. ui: {type(ui)}, text_to_match: {type(text_to_match)}")
                    continue

                m = SequenceMatcher(None, ui, text_to_match, autojunk=False)  # autojunk=False kann manchmal helfen

                # find_longest_match kann bei sehr großen Unterschieden in Längen oder komplexen Strings viel Zeit beanspruchen
                match = m.find_longest_match(0, len(ui), 0, len(text_to_match))

                score = 0.0
                if len(ui) > 0:  # Vermeide Division durch Null
                    score = match.size / len(ui)

                if score >= cutoff:
                    hits.append((score, epd))
            except Exception as e_sm:
                # Fehler während SequenceMatcher abfangen (sehr wichtig für C-Layer Probleme)
                print(f"DEBUG fuzzy_search: KRITISCHER FEHLER mit SequenceMatcher. Überspringe dieses EPD.")
                print(f"  Fehlerdetails: {e_sm}")
                print(f"  Input ui (erste 50 Zeichen): '{ui[:50]}...'")
                print(f"  Input text_to_match (erste 50 Zeichen): '{text_to_match[:50]}...'")
                # Hier könnten Sie optional das problematische EPD loggen: print(f"  Problematisches EPD: {epd}")
                continue  # Nächstes EPD

        hits.sort(key=lambda x: x[0], reverse=True)
        # Stelle sicher, dass self.top_n_for_llm ein gültiger Integer ist
        try:
            limit = int(self.top_n_for_llm)
        except ValueError:
            limit = 10  # Fallback-Limit

        return [h_epd for h_score, h_epd in hits[:limit]]


    def show_about_dialog(self):
        QMessageBox.information(
            self, "Über EPD Matcher",
            "EPD Matcher v1.1.1\n"
            "© 2024-2025 Tobias Bartlog\n"
            "Alle Rechte vorbehalten.\n\n"
            "Lizenz: non-commercial use only\n"
            "https://github.com/tobiasbartlog/epd-matcher"
        )

    def change_top_n(self):
        val, ok = QInputDialog.getInt(
            self, "Anzahl Matches einstellen",
            "Wie viele EPDs sollen maximal abgefragt werden (LLM)?",
            value=self.top_n_for_llm, min=1, max=500
        )
        if not ok: return
        self.top_n_for_llm = val
        cfg = ConfigParser()
        cfg.read(CONFIG_PATH, encoding="utf-8")
        if not cfg.has_section("openai"): cfg.add_section("openai")
        cfg.set("openai", "top_n_for_llm", str(val))
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            cfg.write(f)
        QMessageBox.information(self, "Gespeichert", f"Top-N für LLM auf {val} gesetzt.")

    def change_api_key(self):
        cfg = ConfigParser()
        cfg.read(CONFIG_PATH, encoding="utf-8")
        current = cfg.get("openai", "api_key", fallback="")
        key, ok = QInputDialog.getText(self, "OpenAI API-Key",
                                       "Bitte neuen OpenAI API-Key eingeben:",
                                       QLineEdit.EchoMode.Password, current)
        if not ok: return
        self.api_key = key.strip()
        if not cfg.has_section("openai"): cfg.add_section("openai")
        cfg.set("openai", "api_key", self.api_key)
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            cfg.write(f)
        try:
            self.openai_client = OpenAI(api_key=self.api_key, timeout=60.0)
            QMessageBox.information(self, "API-Key gespeichert", "Der OpenAI API-Key wurde aktualisiert.")
        except Exception as e:
            QMessageBox.critical(self, "Fehler", f"Fehler beim Initialisieren des Clients mit neuem Key:\n{e}")

    def open_ifc_settings_dialog(self):
        val_thickness, ok1 = QInputDialog.getDouble(
            self, "IFC Parameter: Minimale Dicke",
            "Minimale Dicke für IfcBuildingElementProxy (in Metern, z.B. 0.01):",
            value=self.ifc_min_proxy_thickness, decimals=3, min=0.001, max=10.0
        )
        if not ok1: return
        val_tolerance, ok2 = QInputDialog.getDouble(
            self, "IFC Parameter: XY-Toleranz",
            "XY-Toleranz für Mittelpunktgruppierung (in Metern, z.B. 0.5):",
            value=self.ifc_xy_tolerance, decimals=2, min=0.01, max=100.0
        )
        if not ok2: return
        val_min_elements, ok3 = QInputDialog.getInt(
            self, "IFC Parameter: Minimale Stapelhöhe",
            "Minimale Anzahl Elemente in einem erkannten Stapel:",
            value=self.ifc_min_elements_in_stack, min=1, max=100
        )
        if not ok3: return
        self.ifc_min_proxy_thickness = val_thickness
        self.ifc_xy_tolerance = val_tolerance
        self.ifc_min_elements_in_stack = val_min_elements
        cfg = ConfigParser()
        cfg.read(CONFIG_PATH, encoding="utf-8")
        if not cfg.has_section("ifc_settings"): cfg.add_section("ifc_settings")
        cfg.set("ifc_settings", "min_proxy_thickness", str(self.ifc_min_proxy_thickness))
        cfg.set("ifc_settings", "xy_tolerance", str(self.ifc_xy_tolerance))
        cfg.set("ifc_settings", "min_elements_in_stack", str(self.ifc_min_elements_in_stack))
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            cfg.write(f)
        QMessageBox.information(self, "Gespeichert", "Die Parameter für die IFC Analyse wurden aktualisiert.")

    def upload_ifc_file(self):
        options = QFileDialog.Option.ReadOnly
        file_path, _ = QFileDialog.getOpenFileName(
            self, "IFC-Datei auswählen", "", "IFC-Dateien (*.ifc);;Alle Dateien (*)", options=options
        )
        if file_path:
            self.output_box.appendPlainText(f"\n--- IFC-Datei ausgewählt (Allgemein) ---")
            self.output_box.appendPlainText(f"Pfad: {file_path}")
            self.tabs.setCurrentIndex(2)
            QMessageBox.information(self, "IFC-Datei geladen", f"Die IFC-Datei wurde ausgewählt:\n{file_path}")
        else:
            self.output_box.appendPlainText("\n--- IFC-Upload (Allgemein) abgebrochen ---")

    def handle_ifc_analyse_action(self):
        options = QFileDialog.Option.ReadOnly
        file_path, _ = QFileDialog.getOpenFileName(
            self, "IFC-Datei für Layer Analyse auswählen", "", "IFC-Dateien (*.ifc);;Alle Dateien (*)", options=options
        )
        if file_path:
            self.current_ifc_for_analysis = file_path
            if self.ifc_file_display_label:
                self.ifc_file_display_label.setText(f"Analysiere: {os.path.basename(file_path)}")
            if self.ifc_message_box: self.ifc_message_box.clear()
            if self.ifc_stacks_listwidget: self.ifc_stacks_listwidget.clear()
            if self.confirm_stack_button: self.confirm_stack_button.setEnabled(False)
            if self.ifc_message_box: self.ifc_message_box.appendPlainText(f"Lade und analysiere IFC: {file_path}...")
            QApplication.processEvents()
            if hasattr(self, 'loading_dialog') and self.loading_dialog is not None: self.loading_dialog.close()
            self.loading_dialog = QProgressDialog("Analysiere IFC-Datei...", None, 0, 100, self)
            self.loading_dialog.setWindowModality(Qt.WindowModality.ApplicationModal)
            self.loading_dialog.setCancelButton(None)
            self.loading_dialog.setMinimumDuration(0);
            self.loading_dialog.setValue(0);
            self.loading_dialog.show()
            QApplication.processEvents()
            QTimer.singleShot(50, lambda: self._execute_ifc_analysis(file_path))
        else:
            if self.ifc_file_display_label: self.ifc_file_display_label.setText("Keine IFC-Datei ausgewählt.")
            if self.ifc_message_box: self.ifc_message_box.appendPlainText("IFC-Auswahl abgebrochen.")

    def on_stack_selected(self, list_widget_item: QListWidgetItem):
        """Wird aufgerufen, wenn ein Stapel in der Liste ausgewählt (angeklickt) wird."""
        if not list_widget_item:
            # print("DEBUG ON_STACK_SELECTED: list_widget_item ist None (Auswahl aufgehoben).")
            if self.confirm_stack_button:
                self.confirm_stack_button.setEnabled(False)
            self.currently_selected_stack_widget = None  # Kein Widget mehr ausgewählt
            return

        selected_stack_index = list_widget_item.data(Qt.ItemDataRole.UserRole)

        # print(f"DEBUG ON_STACK_SELECTED: Geklicktes Item hat Index aus data(): {selected_stack_index}")

        if selected_stack_index is None or not (0 <= selected_stack_index < len(self.stack_item_widgets)):
            # print(f"DEBUG ON_STACK_SELECTED: Ungültiger Index {selected_stack_index}")
            if self.confirm_stack_button:
                self.confirm_stack_button.setEnabled(False)
            self.currently_selected_stack_widget = None
            return

        # Speichere das aktuell ausgewählte Widget, damit confirm_selected_layers_action weiß, wo es nachsehen soll
        self.currently_selected_stack_widget = self.stack_item_widgets[selected_stack_index]
        # print(f"DEBUG ON_STACK_SELECTED: self.currently_selected_stack_widget gesetzt auf: {self.currently_selected_stack_widget}")

        if self.confirm_stack_button:
            # Button aktivieren, da jetzt ein Stapel ausgewählt ist (unabhängig von Checkbox-Status)
            # Der Benutzer kann dann Checkboxen an- oder abwählen und dann bestätigen.
            self.confirm_stack_button.setEnabled(True)

    def _execute_ifc_analysis(self, ifc_file_path):
        try:
            def gui_message_callback(message_text):
                if self.ifc_message_box: self.ifc_message_box.appendPlainText(message_text)
                QApplication.processEvents()

            def gui_progress_callback(current_step, total_steps, status_text):
                if hasattr(self, 'loading_dialog') and self.loading_dialog:
                    self.loading_dialog.setLabelText(status_text)
                    progress_value = 0
                    if total_steps > 0: progress_value = int((current_step / total_steps) * 100)
                    if progress_value == 0 and current_step > 0 and total_steps > 0: progress_value = 1
                    if current_step == total_steps: progress_value = 100
                    self.loading_dialog.setValue(progress_value)
                    QApplication.processEvents()

            gui_message_callback(f"Starte IFC-Analyse für: {os.path.basename(ifc_file_path)}")
            ifc_model = identstreetlayers.load_model_from_path(
                ifc_file_path, message_callback=gui_message_callback
            )
            if not ifc_model:
                gui_message_callback("Fehler: IFC-Modell konnte nicht geladen werden.")
                if hasattr(self, 'loading_dialog') and self.loading_dialog: self.loading_dialog.close()
                return
            self.candidate_ifc_stacks_data = identstreetlayers.find_stacked_elements_by_xy_midpoint(
                ifc_model,
                min_proxy_thickness_param=self.ifc_min_proxy_thickness,
                xy_tolerance_param=self.ifc_xy_tolerance,
                min_elements_in_stack_param=self.ifc_min_elements_in_stack,
                message_callback=gui_message_callback,
                progress_callback=gui_progress_callback
            )
            self._display_candidate_stacks_in_list(self.candidate_ifc_stacks_data)
        except FileNotFoundError as e_fnf:
            if hasattr(self, 'loading_dialog') and self.loading_dialog: self.loading_dialog.close()
            QMessageBox.critical(self, "Fehler", str(e_fnf))
            if self.ifc_message_box: self.ifc_message_box.appendPlainText(f"Fehler: {e_fnf}")
        except ImportError as e_imp:
            if hasattr(self, 'loading_dialog') and self.loading_dialog: self.loading_dialog.close()
            QMessageBox.critical(self, "Import Fehler",
                                 f"Modul 'src.identstreetlayers' nicht gefunden.\nDetails: {e_imp}")
            if self.ifc_message_box: self.ifc_message_box.appendPlainText(f"Import Fehler: {e_imp}")
            import traceback;
            traceback.print_exc()
        except Exception as e_general:
            if hasattr(self, 'loading_dialog') and self.loading_dialog: self.loading_dialog.close()
            QMessageBox.critical(self, "IFC Analyse Fehler", f"Unerwarteter Fehler:\n{e_general}")
            if self.ifc_message_box: self.ifc_message_box.appendPlainText(f"Unerwarteter Fehler: {e_general}")
            import traceback;
            traceback.print_exc()
        finally:
            if hasattr(self, 'loading_dialog') and self.loading_dialog: self.loading_dialog.close()

    def _display_candidate_stacks_in_list(self, stacks_data):
        # Debug-Ausgaben können später entfernt werden
        print(
            f"DEBUG DISPLAY: _display_candidate_stacks_in_list called. stacks_data Länge: {len(stacks_data) if stacks_data is not None else 'None'}.")
        print(
            f"DEBUG DISPLAY: self.ifc_stacks_listwidget ist aktuell: {self.ifc_stacks_listwidget} (Typ: {type(self.ifc_stacks_listwidget)})")

        if self.ifc_stacks_listwidget is None:
            print("DEBUG DISPLAY: self.ifc_stacks_listwidget ist tatsächlich None. Anzeige nicht möglich.")
            if self.ifc_message_box: self.ifc_message_box.appendPlainText("Fehler: Listen-Widget nicht initialisiert.")
            return
        elif not isinstance(self.ifc_stacks_listwidget, QListWidget):
            print(
                f"DEBUG DISPLAY: self.ifc_stacks_listwidget ist kein QListWidget, sondern: {type(self.ifc_stacks_listwidget)}. Anzeige nicht möglich.")
            if self.ifc_message_box: self.ifc_message_box.appendPlainText("Fehler: Listen-Widget hat falschen Typ.")
            return

        self.ifc_stacks_listwidget.clear()
        self.stack_item_widgets.clear()  # Auch die Liste der Custom Widgets leeren
        self.currently_selected_stack_widget = None
        if self.confirm_stack_button: self.confirm_stack_button.setEnabled(False)

        if not stacks_data:
            if self.ifc_message_box: self.ifc_message_box.appendPlainText("Keine Stapel-Daten zum Anzeigen vorhanden.")
            return

        item_added_count = 0
        for i, stack_info in enumerate(stacks_data):
            if not isinstance(stack_info, dict):
                if self.ifc_message_box: self.ifc_message_box.appendPlainText(
                    f"Warnung: Ungültiges Stapelformat bei Index {i}.")
                continue

            # Erstelle das Custom Widget für den Stapel
            # Wichtig: QListWidget wird hier NICHT als Parent übergeben,
            # da setItemWidget die Ownership übernimmt.
            stack_widget = StackItemWidget(i, stack_info)
            self.stack_item_widgets.append(stack_widget)

            # Erstelle ein QListWidgetItem. Es dient als "Träger" für unser custom widget.
            list_item = QListWidgetItem()  # Ohne Parent erstellen

            # WICHTIG: Setze die Größe des QListWidgetItem auf die des Custom Widgets.
            # Dies ist entscheidend, damit das QListWidget weiß, wie viel Platz es reservieren soll.
            list_item.setSizeHint(stack_widget.sizeHint())

            # Speichere den Index des Stapels im QListWidgetItem (nützlich für on_stack_selected)
            list_item.setData(Qt.ItemDataRole.UserRole, i)

            # Füge das (noch leere) QListWidgetItem zum QListWidget hinzu.
            self.ifc_stacks_listwidget.addItem(list_item)

            # Setze NUN unser benutzerdefiniertes Widget für dieses QListWidgetItem.
            # Das QListWidget übernimmt die Verwaltung des stack_widget.
            self.ifc_stacks_listwidget.setItemWidget(list_item, stack_widget)

            item_added_count += 1

        if item_added_count > 0:
            if self.ifc_message_box: self.ifc_message_box.appendPlainText(
                f"{item_added_count} Stapel-Kandidaten zur Liste hinzugefügt. Klicken Sie auf einen Stapel, um Schichten auszuwählen.")
        elif stacks_data:
            if self.ifc_message_box: self.ifc_message_box.appendPlainText(
                "Stapeldaten vorhanden, aber keine Elemente konnten zur Liste hinzugefügt werden.")

    def confirm_selected_layers_action(self):
        if not self.currently_selected_stack_widget:
            QMessageBox.warning(self, "Auswahl fehlt",
                                "Bitte wählen Sie zuerst einen Stapel aus der Liste und klicken Sie ihn an.")
            return

        selected_layers_data = self.currently_selected_stack_widget.get_selected_layers_data()

        if not selected_layers_data:
            QMessageBox.information(self, "Keine Schichten ausgewählt",
                                    "Es wurden keine Schichten im aktuell angezeigten Stapel angekreuzt.")
            return

        if not self.layer_epd_search_tabs:  # Sicherheitscheck
            QMessageBox.critical(self, "UI Fehler", "Das TabWidget für die Schichtsuche wurde nicht initialisiert.")
            return

        # Bestehende dynamische Schicht-Tabs entfernen (außer "Manuelle Suche")
        # Gehe rückwärts durch die Tabs, um Indexprobleme beim Entfernen zu vermeiden
        for i in range(self.layer_epd_search_tabs.count() - 1, 0,
                       -1):  # Startet beim letzten Tab, stoppt vor dem ersten (Manuelle Suche)
            if self.layer_epd_search_tabs.tabText(i) != "Manuelle Suche":
                self.layer_epd_search_tabs.removeTab(i)

        self.active_layer_search_widgets.clear()  # Alte Referenzen löschen

        if self.ifc_message_box:
            self.ifc_message_box.appendPlainText(f"{len(selected_layers_data)} Schicht(en) für EPD-Suche vorbereitet:")

        first_new_tab_index = -1

        for idx, layer_data in enumerate(selected_layers_data):
            layer_name = layer_data.get('name', f'Unbenannte Schicht {idx + 1}')

            if self.ifc_message_box:
                self.ifc_message_box.appendPlainText(
                    f"  -> Erstelle Tab für Schicht: {layer_name} (GUID: {layer_data.get('guid', 'N/A')[:8]}...)")

            # Neues Widget und Layout für den Schicht-Tab
            layer_tab_content = QWidget()
            layer_tab_layout = QVBoxLayout(layer_tab_content)

            # Eingabefeld für diese spezifische Schicht
            layer_input_box = QTextEdit()
            layer_input_box.setPlainText(layer_name)  # Name der Schicht als Standard-Suchbegriff
            layer_input_box.setPlaceholderText(f"Suchbegriff für EPDs zu '{layer_name}' eingeben oder anpassen.")
            layer_input_box.setFixedHeight(80)
            layer_tab_layout.addWidget(layer_input_box)
            # Optional: Weitere Infos zur Schicht im Tab anzeigen (z.B. als QLabel)
            # layer_info_label = QLabel(f"Details: GUID {layer_data.get('guid', 'N/A')}, Dicke: {layer_data.get('thickness_global_bbox', 0.0):.3f}m")
            # layer_tab_layout.addWidget(layer_info_label)
            layer_tab_content.setLayout(layer_tab_layout)

            # Neuen Tab zum layer_epd_search_tabs hinzufügen
            current_tab_index = self.layer_epd_search_tabs.addTab(layer_tab_content, layer_name)
            if first_new_tab_index == -1:
                first_new_tab_index = current_tab_index  # Merke dir den Index des ersten neuen Tabs

            # Speichere Referenz auf das Eingabefeld für diese Schicht
            self.active_layer_search_widgets.append({
                'name': layer_name,
                'data': layer_data,
                'input_widget': layer_input_box,
                'tab_index': current_tab_index  # Speichere den tatsächlichen Index des Tabs
            })

        QMessageBox.information(self, "Schichten übernommen",
                                f"{len(selected_layers_data)} Schicht(en) wurden als separate Reiter zum 'EPD Matching'-Tab hinzugefügt.")

        self.tabs.setCurrentIndex(0)  # Zum Haupt-Tab "EPD Matching" wechseln
        if first_new_tab_index != -1:
            self.layer_epd_search_tabs.setCurrentIndex(first_new_tab_index)  # Den ersten neuen Schicht-Tab auswählen

        # Alte Logik zum direkten Befüllen von self.input_box ist nicht mehr nötig
        # if self.confirm_stack_button: self.confirm_stack_button.setEnabled(False) # Kann bleiben oder entfernt werden


    def apply_stylesheet(self):
        self.setStyleSheet("""
            QWidget { font-family: 'Segoe UI', sans-serif; font-size: 10pt; color: #333; background-color: #fdfdfd; }
            QGroupBox { font-weight: bold; margin-top: 10px; border: 1px solid #dcdcdc; border-radius: 6px; padding-top: 15px; }
            QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top left; padding: 0 5px 0 5px; left: 10px; background-color: #fdfdfd; }
            QPushButton { padding: 9px 18px; border-radius: 5px; background-color: #0078d4; color: white; font-weight: bold; min-width: 100px; }
            QPushButton:hover { background-color: #005a9e; }
            QPushButton:disabled { background-color: #e0e0e0; color: #a0a0a0; }
            QTextEdit, QPlainTextEdit { background-color: #ffffff; border: 1px solid #dcdcdc; border-radius: 5px; color: #333; padding: 5px; }
            QCheckBox, QRadioButton { spacing: 5px; }
            QRadioButton { border: 1px solid #e0e0e0; padding: 8px; border-radius: 6px; background-color: #fff; margin-bottom: 5px; }
            QRadioButton::indicator { width: 15px; height: 15px; }
            QRadioButton::hover { background-color: #f5f5f5; }
            QRadioButton::checked { background-color: #e7f3ff; border: 1px solid #0078d4; }
            QScrollArea { border: none; }
            QTabWidget::pane { border: 1px solid #dcdcdc; border-top: none; background-color: #ffffff; border-bottom-left-radius: 5px; border-bottom-right-radius: 5px; }
            QTabBar::tab { padding: 10px 15px; background: #f0f0f0; border: 1px solid #dcdcdc; border-bottom: none; border-top-left-radius: 5px; border-top-right-radius: 5px; margin-right: 2px; }
            QTabBar::tab:selected { background: #ffffff; font-weight: bold; border-bottom: 1px solid #ffffff; }
            QTabBar::tab:!selected:hover { background: #e5e5e5; }
            QLabel#ResultBadge { color: #107c10; font-weight: bold; padding: 3px 8px; background-color: #dff6dd; border-radius: 4px; }
            QLabel#ContextIndicator { color: #555; font-size: 9pt; }
        """)

    def setup_ui_layout(self):
        menubar = QMenuBar(self)
        file_menu = menubar.addMenu("Datei")
        act_upload_ifc = QAction("IFC-Datei hochladen...", self)
        act_upload_ifc.triggered.connect(self.upload_ifc_file)
        file_menu.addAction(act_upload_ifc)

        settings_menu = menubar.addMenu("Einstellungen")
        act_topn = QAction("Anzahl EPDs (Top N)...", self)
        act_topn.triggered.connect(self.change_top_n)
        settings_menu.addAction(act_topn)
        act_key = QAction("OpenAI-Key...", self)
        act_key.triggered.connect(self.change_api_key)
        settings_menu.addAction(act_key)
        act_ifc_settings = QAction("IFC Analyse Parameter...", self)
        act_ifc_settings.triggered.connect(self.open_ifc_settings_dialog)
        settings_menu.addAction(act_ifc_settings)

        help_menu = menubar.addMenu("Hilfe")
        act_about = QAction("Über EPD Matcher…", self)
        act_about.triggered.connect(self.show_about_dialog)
        help_menu.addAction(act_about)
        self.setMenuBar(menubar)

        main_layout_container = self.main_layout

        top_bar_layout = QHBoxLayout()
        self.context_indicator = QLabel("Aktueller Bereich: EPD Matching")
        self.context_indicator.setObjectName("ContextIndicator")
        self.result_badge = QLabel()
        self.result_badge.setObjectName("ResultBadge")
        top_bar_layout.addWidget(self.context_indicator)
        top_bar_layout.addStretch()
        top_bar_layout.addWidget(self.result_badge)
        self.main_layout.addLayout(top_bar_layout)

        self.tabs = QTabWidget(self)
        self.tabs.currentChanged.connect(self.update_tab_label)

        # Tab 1: EPD Matching
        match_tab = QWidget();
        match_layout = QVBoxLayout(match_tab)
        #input_group = QGroupBox("1. Produkt- oder Materialbeschreibung");
        #input_layout_v = QVBoxLayout(input_group)
        #self.input_box = QTextEdit();
        #self.input_box.setPlaceholderText("z. B. Asphalttragschicht AC 16 TS");
        #self.input_box.setFixedHeight(80)
        #input_layout_v.addWidget(self.input_box);

        # NEU: Gruppe für Produktbeschreibung mit untergeordnetem TabWidget
        input_group = QGroupBox("1. Produkt- oder Materialbeschreibung")
        input_group_layout = QVBoxLayout(input_group)  # Layout für die GroupBox

        self.layer_epd_search_tabs = QTabWidget()  # Neues TabWidget für Schichten
        input_group_layout.addWidget(self.layer_epd_search_tabs)

        # Standard-Tab für manuelle Eingabe erstellen
        manual_search_tab = QWidget()
        manual_search_layout = QVBoxLayout(manual_search_tab)

        self.manual_input_box = QTextEdit()  # Das ursprüngliche self.input_box
        self.manual_input_box.setPlaceholderText(
            "Manuelle Eingabe für EPD-Suche (z.B. Asphalttragschicht AC 16 TS) oder "
            "wählen Sie Schichten aus der IFC Analyse."
        )
        self.manual_input_box.setFixedHeight(100)  # Etwas mehr Höhe
        manual_search_layout.addWidget(self.manual_input_box)
        manual_search_tab.setLayout(manual_search_layout)

        self.layer_epd_search_tabs.addTab(manual_search_tab, "Manuelle Suche")

        match_layout.addWidget(input_group)
        method_group = QGroupBox("Suchmethode wählen");
        method_layout_h = QHBoxLayout(method_group)
        self.rb_api = QRadioButton("API Matching");
        self.rb_fuzzy = QRadioButton("Stichwortsuche")
        self.rb_api.setChecked(True);
        method_layout_h.addWidget(self.rb_api);
        method_layout_h.addWidget(self.rb_fuzzy)
        match_layout.addWidget(method_group)
        filter_row_layout = QHBoxLayout()
        self.label_group_box = self.create_checkbox_group("2. Anwendung wählen (Filter)", POSSIBLE_LABELS,
                                                          self.label_checkboxes, False)
        if "STRASSENBAU" in self.label_checkboxes: self.label_checkboxes["STRASSENBAU"].setChecked(True)
        filter_row_layout.addWidget(self.label_group_box)
        self.column_group_box = self.create_checkbox_group("3. Spalten für erweiterten Kontext",
                                                           RELEVANT_COLUMNS_FOR_LLM_CONTEXT, self.column_checkboxes,
                                                           False)
        if "name" in self.column_checkboxes: self.column_checkboxes["name"].setChecked(True)
        filter_row_layout.addWidget(self.column_group_box)
        match_layout.addLayout(filter_row_layout)
        self.find_button = QPushButton("4. Passende EPDs finden");
        self.find_button.clicked.connect(self.find_matches)
        match_layout.addWidget(self.find_button, alignment=Qt.AlignmentFlag.AlignCenter)

        self.match_results_group = QGroupBox("5. Vom LLM vorgeschlagene EPDs (Auswahl)")
        # Das Layout für die GroupBox selbst
        vbox_match_group_layout = QVBoxLayout(self.match_results_group)

        # ScrollArea erstellen
        scroll_area_epd_results = QScrollArea()
        scroll_area_epd_results.setWidgetResizable(True)  # Wichtig!
        scroll_area_epd_results.setFrameShape(QFrame.Shape.StyledPanel)  # Optional: Rahmen um ScrollArea
        # scroll_area_epd_results.setStyleSheet("QScrollArea { border: none; }") # Optional: Rahmen entfernen

        # Container-Widget, das gescrollt wird und das Layout für die RadioButtons enthält
        self.match_results_container_widget = QWidget()  # Benenne es um für Klarheit
        self.match_area = QVBoxLayout(self.match_results_container_widget)  # Layout für den Container
        self.match_area.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.match_area.setContentsMargins(3, 3, 3, 3)  # Kleiner Innenabstand im Scrollbereich

        # Setze den Container als Widget der ScrollArea
        scroll_area_epd_results.setWidget(self.match_results_container_widget)

        # Füge die ScrollArea zum Layout der GroupBox hinzu
        vbox_match_group_layout.addWidget(scroll_area_epd_results)

        match_layout.addWidget(self.match_results_group)
        # Die SizePolicy für die GroupBox ist gut, damit sie sich ausdehnt
        self.match_results_group.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        self.details_button = QPushButton("6. Details für Auswahl abrufen");
        self.details_button.setEnabled(False)
        self.details_button.clicked.connect(self.show_details)
        match_layout.addWidget(self.details_button, alignment=Qt.AlignmentFlag.AlignCenter)
        self.tabs.addTab(match_tab, "EPD Matching")

        # Tab 2: IFC Layer Analyse
        self.ifc_analyse_tab = QWidget();
        ifc_analyse_layout_v = QVBoxLayout(self.ifc_analyse_tab)
        self.load_ifc_analyse_button = QPushButton("1. IFC-Datei für Analyse auswählen & starten")
        self.load_ifc_analyse_button.clicked.connect(self.handle_ifc_analyse_action)
        ifc_analyse_layout_v.addWidget(self.load_ifc_analyse_button)
        self.ifc_file_display_label = QLabel("Keine IFC-Datei ausgewählt.")
        ifc_analyse_layout_v.addWidget(self.ifc_file_display_label)
        ifc_results_group = QGroupBox("2. Gefundene Elementstapel (Kandidaten)")
        ifc_results_group.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)  # Hinzugefügt
        ifc_results_layout_v_group = QVBoxLayout(ifc_results_group)  # Layout für die GroupBox

        self.ifc_stacks_listwidget = QListWidget()
        print(
            f"DEBUG SETUP: self.ifc_stacks_listwidget initialisiert als: {self.ifc_stacks_listwidget} (Typ: {type(self.ifc_stacks_listwidget)})")  # <--- NEUE DEBUG-ZEILE

        self.ifc_stacks_listwidget.setSizePolicy(QSizePolicy.Policy.Expanding,
                                                 QSizePolicy.Policy.Expanding)  # Hinzugefügt
        self.ifc_stacks_listwidget.setMinimumHeight(100)  # Hinzugefügt
        self.ifc_stacks_listwidget.itemClicked.connect(self.on_stack_selected)
        ifc_results_layout_v_group.addWidget(self.ifc_stacks_listwidget)  # Zum GroupBox-Layout
        self.confirm_stack_button = QPushButton("3. Ausgewählten Stapel für EPD-Suche verwenden")
        self.confirm_stack_button.setEnabled(False)
        self.confirm_stack_button.clicked.connect(self.confirm_selected_layers_action)
        ifc_results_layout_v_group.addWidget(self.confirm_stack_button,  # Es ist self.confirm_stack_button
                                             alignment=Qt.AlignmentFlag.AlignCenter)
        ifc_analyse_layout_v.addWidget(ifc_results_group)  # GroupBox zum Tab-Layout
        self.ifc_message_box = QPlainTextEdit();
        self.ifc_message_box.setReadOnly(True);
        self.ifc_message_box.setFixedHeight(100)
        ifc_analyse_layout_v.addWidget(self.ifc_message_box)
        self.tabs.insertTab(1, self.ifc_analyse_tab, "IFC Layer Analyse")

        # --- Tab 3: Ergebnisse / Details ---
        output_tab = QWidget()
        output_tab_layout = QVBoxLayout(output_tab)
        self.result_details_tab_widget = QTabWidget()
        placeholder = QLabel("Wählen Sie eine EPD aus, um Details anzuzeigen.")
        placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.result_details_tab_widget.addTab(placeholder, "Keine Auswahl")
        output_tab_layout.addWidget(self.result_details_tab_widget)
        self.tabs.addTab(output_tab, "Ergebnisse / Details")

        # --- Tab 4: Ergebnisse Tabellen ---
        tables_overview_tab = QWidget()
        tables_layout = QVBoxLayout(tables_overview_tab)

        # Hier nur **ein** QTabWidget für **alle** Tabellen-Details
        self.result_tables_tab_widget = QTabWidget()
        placeholder_tbl = QLabel("Wählen Sie eine EPD aus, um Tabellen-Details anzuzeigen.")
        placeholder_tbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.result_tables_tab_widget.addTab(placeholder_tbl, "Keine Auswahl")

        tables_layout.addWidget(self.result_tables_tab_widget)
        tables_overview_tab.setLayout(tables_layout)
        self.tabs.addTab(tables_overview_tab, "Ergebnisse Tabellen")

        # — Jetzt das Tabs-Widget ins Hauptlayout —
        self.main_layout.addWidget(self.tabs)



    def update_tab_label(self, index):
        self.context_indicator.setText("Aktueller Bereich: " + self.tabs.tabText(index))

    def create_checkbox_group(self, title, items, storage_dict, default_checked=False):
        group_box = QGroupBox(title);
        scroll = QScrollArea();
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; }");
        container = QWidget();
        layout = QVBoxLayout(container)  # Layout dem Container zuweisen
        for item in items:
            cb = QCheckBox(item);
            cb.setChecked(default_checked);
            layout.addWidget(cb);
            storage_dict[item] = cb
        layout.addStretch();
        scroll.setWidget(container)  # Container in ScrollArea
        vbox = QVBoxLayout(group_box);
        vbox.addWidget(scroll)  # ScrollArea in GroupBox-Layout
        group_box.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        return group_box

    def find_matches(self):
        print("\nDEBUG: find_matches AUFGERUFEN")

        # UI-Reset für die EPD-Auswahlliste und den Status
        print("DEBUG find_matches: Schritt 1 - UI-Reset für EPD-Auswahl beginnt")
        try:
            self.clear_match_area()  # Stellt sicher, dass RadioButtons etc. weg sind
            print("DEBUG find_matches: clear_match_area BEENDET")

            if self.result_badge:
                self.result_badge.setText("")
            else:
                print("DEBUG find_matches: self.result_badge ist None")

            if self.details_button:
                self.details_button.setEnabled(False)
            else:
                print("DEBUG find_matches: self.details_button ist None")
            print("DEBUG find_matches: Schritt 1 - UI-Reset für EPD-Auswahl BEENDET")
        except Exception as e_reset:
            print(f"EXCEPTION während UI-Reset in find_matches: {e_reset}")
            QMessageBox.critical(self, "Fehler im UI Reset", f"Fehler: {e_reset}")
            return

        user_input = ""
        search_context_title = "Unbekannter Suchkontext"

        print("DEBUG find_matches: Schritt 2 - Benutzereingabe ermitteln beginnt")
        try:
            if not self.layer_epd_search_tabs:
                QMessageBox.critical(self, "Schwerer UI Fehler",
                                     "Das TabWidget für die Eingabe (layer_epd_search_tabs) ist nicht initialisiert.")
                print("DEBUG: find_matches - self.layer_epd_search_tabs ist None!")
                return
            print(f"DEBUG find_matches: self.layer_epd_search_tabs: {self.layer_epd_search_tabs}")

            current_search_tab_index = self.layer_epd_search_tabs.currentIndex()
            current_search_tab_widget = self.layer_epd_search_tabs.widget(current_search_tab_index)

            if current_search_tab_widget is None:
                QMessageBox.critical(self, "Schwerer UI Fehler",
                                     f"Konnte das Widget für den aktuellen Such-Tab (Index: {current_search_tab_index}) nicht abrufen.")
                print(f"DEBUG: find_matches - current_search_tab_widget ist None für Index {current_search_tab_index}")
                return

            search_context_title = self.layer_epd_search_tabs.tabText(current_search_tab_index)
            # Merke dir den Kontext, damit show_details() weiß, in welchen Tab es das Ergebnis legen soll
            self.current_epd_search_context_title = search_context_title
            print(
                f"DEBUG find_matches: Aktueller Such-Tab Index: {current_search_tab_index}, Titel: '{search_context_title}'")

            if search_context_title == "Manuelle Suche":
                print(f"DEBUG find_matches: Pfad 'Manuelle Suche'. self.manual_input_box: {self.manual_input_box}")
                if self.manual_input_box and isinstance(self.manual_input_box, QTextEdit):
                    user_input = self.manual_input_box.toPlainText().strip()
                    print(f"DEBUG find_matches: Manuelle Eingabe: '{user_input}'")
                else:
                    QMessageBox.critical(self, "UI Fehler",
                                         "Manuelles Eingabefeld (self.manual_input_box) ist nicht korrekt initialisiert oder nicht vom Typ QTextEdit.")
                    print(
                        f"DEBUG find_matches - self.manual_input_box ist None oder falscher Typ: {type(self.manual_input_box)}")
                    return
            else:  # Es ist ein dynamischer Schicht-Tab
                found_widget_info = None
                for layer_info in self.active_layer_search_widgets:
                    if layer_info.get('input_widget') and layer_info[
                        'input_widget'].parentWidget() == current_search_tab_widget:
                        found_widget_info = layer_info
                        break
                print(
                    f"DEBUG find_matches: Pfad 'Dynamischer Schicht-Tab'. Gefundenes Widget-Info: {found_widget_info is not None}")
                if found_widget_info and isinstance(found_widget_info['input_widget'], QTextEdit):
                    user_input = found_widget_info['input_widget'].toPlainText().strip()
                    print(f"DEBUG find_matches: Eingabe aus Schicht-Tab '{search_context_title}': '{user_input}'")
                else:
                    QMessageBox.warning(self, "Fehler",
                                        f"Konnte das zugehörige Eingabefeld für den Schicht-Tab '{search_context_title}' nicht finden oder es ist nicht vom Typ QTextEdit.")
                    print(
                        f"DEBUG find_matches - Eingabefeld für Schicht-Tab '{search_context_title}' nicht gefunden oder falscher Typ.")
                    return
            print("DEBUG find_matches: Schritt 2 - Benutzereingabe ermitteln BEENDET")
        except Exception as e_input:
            print(f"EXCEPTION während Benutzereingabe-Ermittlung in find_matches: {e_input}")
            QMessageBox.critical(self, "Fehler bei Eingabeermittlung", f"Fehler: {e_input}")
            return

        if not user_input:
            QMessageBox.warning(self, "Eingabe fehlt",
                                f"Bitte eine Beschreibung im Tab '{search_context_title}' eingeben.")
            print("DEBUG find_matches: user_input ist leer. Abbruch.")
            return

        if not isinstance(user_input, str):
            QMessageBox.critical(self, "Interner Fehler",
                                 f"Der Benutzereingabewert ist kein Text (Typ: {type(user_input)}).")
            print(f"DEBUG find_matches: user_input ist kein String nach der Zuweisung: {type(user_input)}")
            return

        print("DEBUG find_matches: Schritt 3 - Filterparameter sammeln beginnt")
        try:
            selected_labels = [lbl for lbl, cb in self.label_checkboxes.items() if cb.isChecked()]
            selected_columns = [col for col, cb in self.column_checkboxes.items() if cb.isChecked()]
            print(f"DEBUG find_matches: Selected Labels: {selected_labels}, Selected Columns: {selected_columns}")
            if not selected_labels:
                QMessageBox.warning(self, "Label fehlt", "Mind. ein Label wählen.")
                print("DEBUG find_matches: Keine Labels ausgewählt. Abbruch.")
                return
            if self.rb_api.isChecked() and not selected_columns:
                QMessageBox.warning(self, "Spalten fehlen", "Mind. eine Spalte für LLM wählen.")
                print("DEBUG find_matches: API-Modus, aber keine Spalten ausgewählt. Abbruch.")
                return
            print("DEBUG find_matches: Schritt 3 - Filterparameter sammeln BEENDET")
        except Exception as e_filter:
            print(f"EXCEPTION während Filterparameter-Sammeln in find_matches: {e_filter}")
            QMessageBox.critical(self, "Fehler bei Filterparametern", f"Fehler: {e_filter}")
            return

        print("DEBUG find_matches: Schritt 4 - EPDs aus DB holen beginnt")
        epds = []  # Initialisieren für den Fall eines Fehlers
        try:
            epds = self.fetch_epds_by_labels(selected_labels, selected_columns)
            print(f"DEBUG find_matches: {len(epds) if epds is not None else 'None'} EPDs aus DB geholt.")
            if not epds:  # Beinhaltet auch den Fall, dass fetch_epds_by_labels None zurückgibt
                QMessageBox.information(self, "Keine Treffer", "Keine EPDs für die aktuellen Filter gefunden.")
                print("DEBUG find_matches: Keine EPDs aus DB. Abbruch.")
                return
            print("DEBUG find_matches: Schritt 4 - EPDs aus DB holen BEENDET")
        except Exception as e_fetch:
            print(f"EXCEPTION während fetch_epds_by_labels in find_matches: {e_fetch}")
            QMessageBox.critical(self, "DB Fehler", f"Schwerer Fehler beim Holen der EPDs: {e_fetch}")
            return

        print("DEBUG find_matches: Schritt 5 - Lade-Dialog vorbereiten beginnt")
        try:
            if hasattr(self, 'loading_dialog') and self.loading_dialog is not None:
                print("DEBUG find_matches: Schließe existierenden Lade-Dialog.")
                self.loading_dialog.close()
            self.loading_dialog = QProgressDialog("Ermittle Matches …", None, 0, 0, self)
            self.loading_dialog.setWindowModality(Qt.WindowModality.ApplicationModal)
            self.loading_dialog.setCancelButton(None)
            self.loading_dialog.setMinimumDuration(0)
            print("DEBUG find_matches: Lade-Dialog wird angezeigt.")
            self.loading_dialog.show()
            QApplication.processEvents()
            print("DEBUG find_matches: Schritt 5 - Lade-Dialog vorbereiten BEENDET")
        except Exception as e_dialog:
            print(f"EXCEPTION während Lade-Dialog-Vorbereitung in find_matches: {e_dialog}")
            QMessageBox.critical(self, "UI Fehler", f"Fehler beim Anzeigen des Lade-Dialogs: {e_dialog}")
            return

        print("DEBUG find_matches: Schritt 6 - Timer für Suchausführung wird gestartet")
        try:
            if self.rb_api.isChecked():
                QTimer.singleShot(50, lambda: self._execute_find_matches(user_input, epds, selected_columns))
            else:
            # Wir übergeben jetzt auch den Kontext-Titel
                QTimer.singleShot(50, lambda: self._execute_find_matches_fuzzy(
                user_input, epds, selected_columns, self.current_epd_search_context_title))

            print("DEBUG find_matches: Schritt 6 - Timer für Suchausführung BEENDET")
        except Exception as e_timer:
            print(f"EXCEPTION während Timer-Start in find_matches: {e_timer}")
            QMessageBox.critical(self, "Timer Fehler", f"Fehler beim Starten der Suche: {e_timer}")
            if hasattr(self,
                       'loading_dialog') and self.loading_dialog: self.loading_dialog.close()  # Dialog schließen bei Fehler
            return

        print("DEBUG: find_matches ERFOLGREICH BEENDET (Timer gestartet)")


    def _execute_find_matches(self, user_input, epds, selected_columns):
        prompt = self.build_prompt(user_input, epds, selected_columns)
        llm_response_raw = self.call_llm_api(prompt)
        if hasattr(self, 'loading_dialog') and self.loading_dialog: self.loading_dialog.close()
        self.process_llm_response(llm_response_raw)

    def _execute_find_matches_fuzzy(self, user_input, epds, selected_columns, context_title):
        # DEBUG-Ausgabe hinzufügen
        self.current_epd_search_context_title = context_title
        print(f"DEBUG _execute_find_matches_fuzzy: user_input='{user_input}' (Typ: {type(user_input)}), "
              f"Anzahl EPDs: {len(epds) if epds else 'None'}, "
              f"selected_columns: {selected_columns}")
        if hasattr(self, "loading_dialog") and self.loading_dialog: self.loading_dialog.close()
        self.clear_match_area()
        results = self.fuzzy_search(user_input, epds, selected_columns, cutoff=0.4)
        for i, epd in enumerate(results, start=1):
            uuid = epd["uuid"];
            name = epd["name"];
            conn = None
            try:
                conn = sqlite3.connect(DB_FILE);
                cur = conn.cursor()
                cur.execute("SELECT ref_year, valid_until, owner FROM epds WHERE uuid = ?", (uuid,))
                ref_year, valid_until, owner = cur.fetchone() or (None, None, None)
            finally:
                if conn: conn.close()
            display_text = (f"{i}. {name}  ({uuid[:8]}… | Ref: {ref_year} | Bis: {valid_until} | Owner: {owner})")
            rb = QRadioButton(display_text);
            rb.setToolTip(f"UUID: {uuid}");
            rb.setProperty("match_uuid", uuid)
            self.radio_group.addButton(rb);
            self.match_area.addWidget(rb);
            self.radio_buttons.append(rb)
        if results:
            self.details_button.setEnabled(True);
            self.result_badge.setText(f"✔ {len(results)} Matches");
            self.result_badge.setStyleSheet("color: #107c10; font-weight: bold;")
        else:
            self.result_badge.setText("Keine Matches");
            self.result_badge.setStyleSheet("color: orange; font-weight: bold;")

    def call_llm_api(self, prompt: str) -> str:
        print("INFO: Sende Anfrage an OpenAI API...")
        QApplication.processEvents()  # Kann hier bleiben, um UI-Responsivität während des Wartens zu signalisieren
        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo", messages=[{"role": "system", "content": "You are an assistant..."},
                                                 {"role": "user", "content": prompt}],
                max_tokens=500, temperature=0.5, response_format={"type": "json_object"}
            )  # Gekürzt für Lesbarkeit
            if response.choices: return response.choices[0].message.content.strip()
            return '{"error": "Keine gültige Antwort von LLM (keine choices)."}'
        except openai.AuthenticationError:
            return '{"error": "OpenAI Authentifizierung fehlgeschlagen. API Key prüfen!"}'
        except openai.RateLimitError:
            return '{"error": "OpenAI Rate Limit erreicht."}'
        except openai.BadRequestError as e:
            if "response_format" in str(e): return '{"error": "Modell unterstützt JSON-Format nicht."}'
            err_detail = str(e);
            try:
                if hasattr(e, 'body') and e.body: err_detail = json.dumps(e.body, indent=2)
            except:
                pass
            return f'{{"error": "OpenAI Bad Request: {err_detail}"}}'
        except openai.APIConnectionError as e:
            return f'{{"error": "Verbindung zur OpenAI API fehlgeschlagen: {e}"}}'
        except openai.APIStatusError as e:
            return f'{{"error": "OpenAI API Status Fehler: Status={e.status_code}, Antwort={e.response}"}}'
        except openai.APITimeoutError:
            return '{"error": "OpenAI API Anfrage Timeout."}'
        except Exception as e:
            return f'{{"error": "Unerwarteter Fehler bei OpenAI: {e}"}}'

    def process_llm_response(self, llm_response_raw):
        print(f"\n--- LLM Antwort (Roh) ---")
        print(llm_response_raw)
        print(f"--- Ende Roh ---\n")
        try:
            json_match = re.search(r"```json\s*([\s\S]*?)\s*```", llm_response_raw)
            llm_json_str = json_match.group(1) if json_match else llm_response_raw
            llm_data = json.loads(llm_json_str)
            if isinstance(llm_data, dict) and 'error' in llm_data:
                print(f"LLM API Fehler: {llm_data.get('error', 'Unbekannter LLM Fehler')}")
                self.result_badge.setText("LLM Fehler");
                self.result_badge.setStyleSheet("color: red; font-weight: bold;");
                return
            count = 0;
            matches_list = None
            if isinstance(llm_data, dict) and 'matches' in llm_data and isinstance(llm_data['matches'], list):
                matches_list = llm_data['matches']
            elif isinstance(llm_data, dict) and all(k.isdigit() for k in llm_data.keys()):
                matches_list = list(llm_data.values())
            if matches_list is not None:
                for item in matches_list[:self.top_n_for_llm]:
                    if isinstance(item, dict) and 'uuid' in item and 'name' in item:
                        count += 1;
                        uuid = item['uuid'];
                        name = item.get('name', 'N/A');
                        reason = item.get('begruendung', 'N/A');
                        conn = None
                        try:
                            conn = sqlite3.connect(DB_FILE);
                            cur = conn.cursor()
                            cur.execute("SELECT ref_year, valid_until, owner FROM epds WHERE uuid = ?", (uuid,))
                            ref_year, valid_until, owner = cur.fetchone() or (None, None, None)
                        finally:
                            if conn: conn.close()
                        display_text = (
                            f"{count}. {name} ({uuid[:8]}… | Ref: {ref_year} | Bis: {valid_until} | Owner: {owner})\n{reason}")
                        rb = QRadioButton(display_text);
                        rb.setToolTip(f"UUID: {uuid}");
                        rb.setProperty("match_uuid", uuid)
                        self.radio_group.addButton(rb);
                        self.match_area.addWidget(rb);
                        self.radio_buttons.append(rb)
                    else:
                        self.output_box.appendPlainText(f"\nWARNUNG: Ungültiger Match: {item}")
                if count > 0:
                    self.details_button.setEnabled(True);
                    self.result_badge.setText(f"✔ {count} Matches")
                    self.result_badge.setStyleSheet(
                        "color: #107c10; font-weight: bold; background-color: #dff6dd; border-radius: 4px; padding: 3px 8px;")
                    self.tabs.setCurrentIndex(0)
                else:
                    self.output_box.appendPlainText("\nKeine gültigen Matches gefunden.");
                    self.result_badge.setText("Keine Matches")
                    self.result_badge.setStyleSheet("color: orange; font-weight: bold;")
            else:
                self.output_box.appendPlainText(f"\nUnerwartetes JSON Format:\n{llm_response_raw}")
                self.result_badge.setText("Formatfehler");
                self.result_badge.setStyleSheet("color: red; font-weight: bold;")
        except json.JSONDecodeError:
            self.output_box.appendPlainText(f"\nJSON Parse Fehler:\n{llm_response_raw}")
            self.result_badge.setText("JSON Fehler");
            self.result_badge.setStyleSheet("color: red; font-weight: bold;")
        except Exception as e:
            self.output_box.appendPlainText(f"\nFehler Verarbeitung LLM Antwort: {e}")
            self.result_badge.setText("Verarbeitungsfehler");
            self.result_badge.setStyleSheet("color: red; font-weight: bold;")
            import traceback;
            traceback.print_exc()

    def show_details(self):
        selected_button = self.radio_group.checkedButton()
        if not selected_button: QMessageBox.warning(self, "Auswahl fehlt", "EPD auswählen."); return
        uuid = selected_button.property("match_uuid")
        if not uuid: QMessageBox.critical(self, "Interner Fehler", "UUID nicht lesbar."); return
        if hasattr(self, 'loading_dialog') and self.loading_dialog is not None: self.loading_dialog.close()
        self.loading_dialog = QProgressDialog(f"Lade Details für EPD {uuid[:8]}...", None, 0, 0, self)
        self.loading_dialog.setWindowModality(Qt.WindowModality.ApplicationModal);
        self.loading_dialog.setCancelButton(None)
        self.loading_dialog.setMinimumDuration(0);
        self.loading_dialog.setValue(0);
        self.loading_dialog.show();
        QApplication.processEvents()
        QTimer.singleShot(100, lambda: self._execute_show_details(uuid))

    def _execute_show_details(self, uuid):
        import traceback

        context = self.current_epd_search_context_title or "Unbekannter Kontext"
        print(f"DEBUG _execute_show_details: UUID={uuid}, Kontext='{context}'")

        # --- 1) Text-Tab anlegen oder holen ---
        try:
            if context in self.active_result_widgets and 'text_edit' in self.active_result_widgets[context]:
                text_edit = self.active_result_widgets[context]['text_edit']
            else:
                # Platzhalter-Tab entfernen
                if (self.result_details_tab_widget.count() == 1 and
                    self.result_details_tab_widget.tabText(0) == "Keine Auswahl"):
                    self.result_details_tab_widget.removeTab(0)

                page = QWidget()
                layout = QVBoxLayout(page)
                text_edit = QPlainTextEdit()
                text_edit.setReadOnly(True)
                layout.addWidget(text_edit)
                idx = self.result_details_tab_widget.addTab(page, context)

                self.active_result_widgets.setdefault(context, {})['text_edit'] = text_edit
                self.active_result_widgets[context]['details_tab_index'] = idx

            # Tab auswählen
            self.result_details_tab_widget.setCurrentIndex(
                self.active_result_widgets[context]['details_tab_index']
            )
        except Exception as e:
            print("ERROR beim Anlegen/Holen des Text-Tabs:", e)
            traceback.print_exc()
            return

        # --- Kopftext schreiben ---
        text_edit.clear()
        text_edit.appendPlainText(f"--- Details für EPD UUID {uuid} ---\n(Kontext: {context})\n\n")

        # --- 2) Fetch & Parser ---
        structured_env_data = {}
        try:
            if not fetch_epd_available:
                raise ImportError("fetch_epd.py nicht verfügbar.")
            details = src.fetch_epd.get_epd_by_id(uuid)
            if isinstance(details, dict) and not details.get('error'):
                text_edit.appendPlainText("Rohdaten geladen.\n")
                if parser_available:
                    structured_env_data = extract_environmental_data(details)
                    text_edit.appendPlainText("Parser erfolgreich.\n\n")
                else:
                    text_edit.appendPlainText("Kein Parser, nur Rohdaten.\n\n")
            else:
                raise RuntimeError(details.get('error', 'Unbekannter Fetch-Fehler'))
        except Exception as e:
            text_edit.appendPlainText(f"FEHLER beim Laden/Parsen: {e}\n")
            print("ERROR fetch/parse:", e)
            traceback.print_exc()

        # --- 3) Tabellen-Tab anlegen oder holen ---
        try:
            if context not in self.active_result_widgets or 'tables_tab_index' not in self.active_result_widgets[context]:
                # Platzhalter entfernen
                if (self.result_tables_tab_widget.count() == 1 and
                    self.result_tables_tab_widget.tabText(0) == "Keine Auswahl"):
                    self.result_tables_tab_widget.removeTab(0)

                page = QWidget()
                vlay = QVBoxLayout(page)
                inner_tabs = QTabWidget()

                # Allgemein
                gen_tbl = QTableWidget()
                gen_tbl.setColumnCount(2)
                gen_tbl.setHorizontalHeaderLabels(["Feld", "Wert"])
                inner_tabs.addTab(gen_tbl, "Allgemein")

                # LCIA
                lcia_tbl = QTableWidget()
                inner_tabs.addTab(lcia_tbl, "LCIA Results")

                # Flows
                flows_tbl = QTableWidget()
                inner_tabs.addTab(flows_tbl, "Key Flows")

                vlay.addWidget(inner_tabs)
                idx = self.result_tables_tab_widget.addTab(page, context)

                d = self.active_result_widgets.setdefault(context, {})
                d.update({
                    'tables_tab_index': idx,
                    'general_table':     gen_tbl,
                    'lcia_table':        lcia_tbl,
                    'flows_table':       flows_tbl,
                    'tables_inner_tabs': inner_tabs
                })
            else:
                d = self.active_result_widgets[context]
                gen_tbl   = d['general_table']
                lcia_tbl  = d['lcia_table']
                flows_tbl = d['flows_table']
        except Exception as e:
            print("ERROR beim Anlegen/Holen der Tabellen-Tabs:", e)
            traceback.print_exc()
            return

        # --- 4) Füllen der Tabellen ---
        # 4.1 Allgemein
        try:
            gen_tbl.clearContents()
            keys = ["UUID", "Name", "Version", "Gültig Bis"]
            vals = [
                uuid,
                details.get("name", "N/A"),
                details.get("version", "N/A"),
                details.get("valid_until", "N/A")
            ]
            gen_tbl.setRowCount(len(keys))
            for r, (k, v) in enumerate(zip(keys, vals)):
                gen_tbl.setItem(r, 0, QTableWidgetItem(k))
                gen_tbl.setItem(r, 1, QTableWidgetItem(str(v)))
            gen_tbl.horizontalHeader().setStretchLastSection(True)
        except Exception as e:
            print("ERROR beim Befüllen Allgemein-Tabelle:", e)
            traceback.print_exc()

        # 4.2 LCIA Results
        try:
            lcia_tbl.clearContents()
            lcia = structured_env_data.get("LCIA Results", {})
            if lcia:
                phases = list(next(iter(lcia.values())).keys())
                lcia_tbl.setColumnCount(1 + len(phases))
                lcia_tbl.setHorizontalHeaderLabels(["Indikator"] + phases)
                lcia_tbl.setRowCount(len(lcia))
                for r, (ind, data) in enumerate(lcia.items()):
                    lcia_tbl.setItem(r, 0, QTableWidgetItem(ind))
                    for c, ph in enumerate(phases, start=1):
                        item = QTableWidgetItem(str(data.get(ph, "")))
                        item.setTextAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignVCenter)
                        lcia_tbl.setItem(r, c, item)
                hdr = lcia_tbl.horizontalHeader()
                hdr.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
                for c in range(1, lcia_tbl.columnCount()):
                    hdr.setSectionResizeMode(c, QHeaderView.ResizeMode.Stretch)
        except Exception as e:
            print("ERROR beim Befüllen LCIA-Tabelle:", e)
            traceback.print_exc()

        # 4.3 Key Flows
        try:
            flows_tbl.clearContents()
            flows = structured_env_data.get("Key Flows", {})
            if flows:
                phases = list(next(iter(flows.values())).keys())
                flows_tbl.setColumnCount(1 + len(phases))
                flows_tbl.setHorizontalHeaderLabels(["Flow"] + phases)
                flows_tbl.setRowCount(len(flows))
                for r, (flow, data) in enumerate(flows.items()):
                    flows_tbl.setItem(r, 0, QTableWidgetItem(flow))
                    for c, ph in enumerate(phases, start=1):
                        item = QTableWidgetItem(str(data.get(ph, "")))
                        item.setTextAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignVCenter)
                        flows_tbl.setItem(r, c, item)
                hdr2 = flows_tbl.horizontalHeader()
                hdr2.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
                for c in range(1, flows_tbl.columnCount()):
                    hdr2.setSectionResizeMode(c, QHeaderView.ResizeMode.Stretch)
        except Exception as e:
            print("ERROR beim Befüllen Flows-Tabelle:", e)
            traceback.print_exc()

        # --- 5) Zum Tabellen-Tab wechseln und Lade-Dialog schließen ---
        self.result_tables_tab_widget.setCurrentIndex(
            self.active_result_widgets[context]['tables_tab_index']
        )
        if hasattr(self, 'loading_dialog') and self.loading_dialog:
            self.loading_dialog.close()



    def save_details_to_db(self, uuid, structured_env_data, target_text_edit: QPlainTextEdit):  # NEUER Parameter
        conn_save = None
        try:
            # Verwende das übergebene target_text_edit für Ausgaben
            if target_text_edit:
                target_text_edit.appendPlainText(f"\n--- Speichere Umweltinfos für {uuid[:8]}... ---")
            else:
                print(f"DEBUG save_details_to_db: Speichere Umweltinfos für {uuid[:8]}...")
            QApplication.processEvents()  # Erlaube UI-Updates

            conn_save = sqlite3.connect(DB_FILE)
            cursor_save = conn_save.cursor()
            create_env_indicator_table_json(cursor_save)
            save_success = save_env_data_to_db_json(cursor_save, uuid, structured_env_data)

            if save_success:
                conn_save.commit()
                if target_text_edit:
                    target_text_edit.appendPlainText(f"\n--- Umweltinfos für {uuid[:8]} gespeichert. ---")
                else:
                    print(f"DEBUG save_details_to_db: Umweltinfos für {uuid[:8]} gespeichert.")

                if self.result_badge:  # result_badge ist global für die App
                    self.result_badge.setText("✔ Details gespeichert")
                    self.result_badge.setStyleSheet(
                        "color: #107c10; font-weight: bold; background-color: #dff6dd; border-radius: 4px; padding: 3px 8px;")
            else:
                if target_text_edit:
                    target_text_edit.appendPlainText(
                        f"\n--- FEHLER: Umweltinfos für {uuid[:8]} nicht gespeichert (siehe DEBUG Konsole). ---")
                else:
                    print(f"DEBUG save_details_to_db: FEHLER - Umweltinfos für {uuid[:8]} nicht gespeichert.")

                if self.result_badge:
                    self.result_badge.setText("DB Speicherfehler")
                    self.result_badge.setStyleSheet("color: red; font-weight: bold;")

        except sqlite3.Error as e_sql:
            print(f"FEHLER DB Speichern (sqlite3): {e_sql}")
            if target_text_edit: target_text_edit.appendPlainText(f"\n--- FEHLER DB Speichern: {e_sql} ---")
            if self.result_badge: self.result_badge.setText("DB Fehler"); self.result_badge.setStyleSheet(
                "color: red; font-weight: bold;")
        except Exception as e_allg:
            print(f"FEHLER DB Speichern (allg.): {e_allg}")
            if target_text_edit: target_text_edit.appendPlainText(f"\n--- FEHLER DB Speichern: {e_allg} ---")
            if self.result_badge: self.result_badge.setText("DB Fehler"); self.result_badge.setStyleSheet(
                "color: red; font-weight: bold;")
            import traceback;
            traceback.print_exc()
        finally:
            if conn_save: conn_save.close(); print("DEBUG: DB Verbindung (Speichern) geschlossen.")

    def clear_match_area(self):
        for rb in self.radio_buttons: self.radio_group.removeButton(rb); rb.setParent(None); rb.deleteLater()
        self.radio_buttons.clear()

    def build_prompt(self, user_input, epds, columns):
        epds_for_prompt_list = epds[:self.top_n_for_llm]
        lines = []
        for epd in epds_for_prompt_list:
            parts = [f"UUID: {epd['uuid']}", f"Name: {epd.get('name', 'N/A')}"]
            for col in columns:
                value = epd.get(col)
                if value and col not in ('uuid', 'name'):
                    parts.append(f"{col}: {str(value)[:150]}")
            lines.append(" | ".join(parts))
        epd_context = "\n - ".join(lines) if lines else "Keine EPDs im Kontext."
        # Gekürzter System-Prompt für Lesbarkeit
        return f"""Finde die relevantesten EPDs... (System-Prompt wie zuvor) ...
Benutzeranfrage: "{user_input}"
--- Beginn VORGEFILTERTE EPD Liste ({len(epds_for_prompt_list)} Einträge) ---
 - {epd_context}
--- Ende VORGEFILTERTE EPD Liste ---
JSON Antwort:"""

    def fetch_epds_by_labels(self, labels, columns):
        if not os.path.exists(DB_FILE):
            QMessageBox.critical(self, "DB Fehler", f"DB nicht gefunden: {DB_FILE}");
            return []
        cols_to_fetch_set = set(["uuid", "name"]);
        cols_to_fetch_set.update(columns)
        cols_to_fetch = list(cols_to_fetch_set)
        conn = None
        try:
            conn = sqlite3.connect(DB_FILE);
            conn.row_factory = sqlite3.Row;
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='epds';")
            if not cursor.fetchone(): QMessageBox.critical(self, "DB Fehler", "Tabelle 'epds' fehlt."); return []
            cursor.execute(f"PRAGMA table_info('epds')");
            columns_in_db = [info['name'] for info in cursor.fetchall()]
            if LABELS_COLUMN_NAME not in columns_in_db:
                QMessageBox.critical(self, "DB Fehler", f"Spalte '{LABELS_COLUMN_NAME}' fehlt.");
                return []

            valid_cols_to_fetch = []  # Nur Spalten verwenden, die wirklich existieren
            for col in cols_to_fetch:
                if col in columns_in_db:
                    valid_cols_to_fetch.append(col)
                else:
                    QMessageBox.warning(self, "DB Warnung",
                                        f"Spalte '{col}' für Kontext nicht in DB gefunden, wird ignoriert.")

            if not valid_cols_to_fetch:
                QMessageBox.critical(self, "DB Fehler", "Keine gültigen Spalten zum Abfragen.");
                return []

            where_clauses = [];
            params = []
            for lbl in labels:
                where_clauses.append(f'"{LABELS_COLUMN_NAME}" LIKE ?')
                params.append(f"%{lbl}%")
            if not where_clauses: return []
            where_condition = " OR ".join(where_clauses)
            cols_str = ", ".join(f'"{col}"' for col in valid_cols_to_fetch)  # Verwende valid_cols_to_fetch
            query = f"SELECT {cols_str} FROM epds WHERE ({where_condition})"
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            if self.output_box: self.output_box.appendPlainText(f"Fehler DB-Abfrage: {e}")
            QMessageBox.critical(self, "DB Fehler", f"Fehler DB-Abfrage:\n{e}")
            import traceback;
            traceback.print_exc()
            return []
        finally:
            if conn: conn.close()


# --- Start der Anwendung ---
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setApplicationName("EPD Matcher")
    icon_path = os.path.join(base_path, "icon.ico")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))
    else:
        print(f"WARNUNG: Icon nicht gefunden unter {icon_path}")
    window = EPDMatcherApp()
    window.showMaximized()
    if not fetch_epd_available:
        QMessageBox.critical(None, "Import Fehler",
                             f"Das Modul 'src{os.sep}fetch_epd.py' fehlt oder konnte nicht geladen werden.\nDetails abrufen funktioniert nicht.")
    window.show()
    sys.exit(app.exec())
