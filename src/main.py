# src/main.py
import sys
import os
from PyQt6.QtWidgets import QApplication, QMessageBox # Evtl. weitere Qt-Imports für den Start
from PyQt6.QtGui import QIcon
from utils.constants import DB_FILE #usw. Konstanten hier einfügen

# --- WICHTIG: Passe diesen Import an, sobald EPDMatcherApp verschoben ist ---
# Momentan wird es noch nicht funktionieren, da EPDMatcherApp noch nicht in ui.main_window ist
# from ui.main_window import EPDMatcherApp

# Dein base_path (wird evtl. angepasst, je nachdem wo main.py und assets liegen)
if getattr(sys, 'frozen', False):
    # base_path für PyInstaller, falls du es später nutzt
    application_path = os.path.dirname(sys.executable)
    base_path = sys._MEIPASS # für Assets im Bundle
else:
    application_path = os.path.dirname(os.path.abspath(__file__))
    # base_path zeigt jetzt auf das src-Verzeichnis
    # Wenn deine Assets einen Ordner höher liegen (im Projektroot), dann:
    # project_root_path = os.path.dirname(application_path)
    # oder wenn assets in src/assets liegen:
    # base_path = application_path
    base_path = os.path.dirname(os.path.abspath(__file__)) # Fürs Erste, anpassen für Assets
    print("BP:", base_path)

# --- Modulverfügbarkeit (Beispiel, muss ggf. später angepasst werden) ---
fetch_epd_available = True
try:
    from src.services import fetch_epd # Dieser Import wird sich ändern, wenn fetch_epd in services landet
except ImportError:
    fetch_epd_available = False

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setApplicationName("EPD Matcher")

    # Pfad zum Icon anpassen, z.B. wenn es in src/assets/icon.ico liegt
    icon_path = os.path.join(base_path, "assets", "icon.ico") # Annahme: assets-Ordner in src/
    if not os.path.exists(icon_path): # Besserer Pfad, z.B. relativ zum Projekt-Root
        icon_path_alt = os.path.join(os.path.dirname(base_path), "assets", "icon.ico") # Annahme: assets im Projekt-Root
        if os.path.exists(icon_path_alt):
            icon_path = icon_path_alt
        else:
            print(f"WARNUNG: Icon nicht gefunden unter {icon_path} oder {icon_path_alt}")

    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    # Dies wird erst funktionieren, wenn EPDMatcherApp verschoben und importiert wurde
    # window = EPDMatcherApp(base_path=base_path) # base_path übergeben ist eine gute Idee
    # window.showMaximized()

    # if not fetch_epd_available:
    #     QMessageBox.critical(None, "Import Fehler",
    #                          f"Das Modul 'src{os.sep}fetch_epd.py' fehlt oder konnte nicht geladen werden.\nDetails abrufen funktioniert nicht.")
    # # window.show() # showMaximized reicht
    # sys.exit(app.exec())
    print("INFO: main.py gestartet. EPDMatcherApp muss noch eingebunden werden.")
    print(f"INFO: base_path ist {base_path}")
    print(f"INFO: icon_path ist {icon_path}")