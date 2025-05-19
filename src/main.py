# src/main.py
import sys
import os
from PyQt6.QtWidgets import QApplication, QMessageBox  # QMessageBox für kritische Fehler beim Start

# Eigene Module
from src.ui.main_window import MainWindow
from src.core.db_setup import init_db
from src.utils.constants import CONFIG_DIR, DB_FILE as DEFAULT_DB_FILENAME  # DB_FILE aus constants ist der Dateiname


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("EPD Matcher")

    # Basispfad für Ressourcen (assets, DB)
    if getattr(sys, 'frozen', False):  # PyInstaller
        # Wenn die Anwendung mit PyInstaller gepackt ist, ist sys._MEIPASS der temporäre Ordner
        base_path = sys._MEIPASS
        # Der Konfigurationsordner sollte dann besser im Benutzerverzeichnis liegen
        # Die Konstante CONFIG_DIR aus utils.constants.py sollte das bereits berücksichtigen (z.B. AppData)
    else:
        # Entwicklungsumgebung: base_path ist das Hauptverzeichnis des Projekts (EPDMatcher_modular)
        # Annahme: main.py ist in EPDMatcher_modular/src/
        base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    # Stelle sicher, dass der Konfigurationsordner existiert (ConfigManager macht das auch, aber hier schadet es nicht)
    os.makedirs(CONFIG_DIR, exist_ok=True)

    # Datenbank-Pfad und Initialisierung
    # Die DB soll im Konfigurationsordner unter AppData/Roaming/EPDMatcher_modular liegen
    # DB_FILE aus constants.py sollte jetzt der volle Pfad zur DB sein oder zumindest der Dateiname
    # der dann mit CONFIG_DIR kombiniert wird.
    # Annahme: DB_FILE in constants.py ist nur der Dateiname "oekobaudat_epds.db"
    # und CONFIG_DIR ist der Ordner, in dem auch config.ini liegt.
    db_path_in_config_dir = os.path.join(CONFIG_DIR, DEFAULT_DB_FILENAME)

    try:
        # Versuche, die DB im Konfigurationsverzeichnis zu initialisieren
        init_db(db_path_in_config_dir)
        # Wenn init_db fehlschlägt (z.B. wegen Rechten), wird eine Exception ausgelöst.
    except Exception as e:
        QMessageBox.critical(None, "Datenbank Initialisierungsfehler",
                             f"Konnte die Datenbank unter {db_path_in_config_dir} nicht initialisieren.\n"
                             f"Stellen Sie sicher, dass das Verzeichnis beschreibbar ist.\nFehler: {e}")
        sys.exit(1)  # Beende die Anwendung bei schwerwiegendem DB-Fehler

    # Icon-Pfad (relativ zum base_path im src-Verzeichnis)
    # Dies ist jetzt in MainWindow, kann hier entfernt werden oder als Fallback dienen
    # icon_path = os.path.join(base_path, "src", "assets", "icon.ico")
    # if os.path.exists(icon_path):
    #     app.setWindowIcon(QIcon(icon_path))
    # else:
    #     print(f"WARNUNG: App-Icon nicht gefunden unter {icon_path}")

    try:
        window = MainWindow(base_path=base_path)  # Übergib base_path, falls MainWindow es für Assets braucht
        window.showMaximized()
        sys.exit(app.exec())
    except FileNotFoundError as e:  # Fängt den Fehler von MainWindow ab, wenn die DB nicht gefunden wird
        QMessageBox.critical(None, "Kritischer Fehler", str(e))
        sys.exit(1)
    except Exception as e:
        QMessageBox.critical(None, "Unerwarteter Fehler",
                             f"Ein unerwarteter Fehler ist aufgetreten:\n{e}\n\nDie Anwendung wird beendet.")
        # Optional: Logging des Fehlers
        # import traceback
        # traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()