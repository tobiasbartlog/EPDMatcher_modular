# test_config.py
from pathlib import Path
from src.core.config_manager import ConfigManager
from src.utils.constants import CONFIG_DIR, CONFIG_PATH

# 1) Erzeuge den Manager (er legt automatisch die INI an, falls sie fehlt)
cfg = ConfigManager()

# 2) Lies Default-Werte
print("Default api_key:", cfg.api_key)
print("Default top_n :", cfg.top_n)
print("Default ifc_min_proxy_thickness:", cfg.ifc_min_proxy_thickness)

# 3) Setze mal etwas Neues
cfg.api_key = "MEIN_TEST_KEY"
cfg.top_n    = 123
cfg.ifc_xy_tolerance = 9.87

# 4) Lade eine frische Instanz, um zu prüfen, ob alles gespeichert wurde
cfg2 = ConfigManager()
print("Neuer api_key:", repr(cfg2.api_key))
print("Neues top_n :", cfg2.top_n)
print("Neues ifc_xy_tolerance:", cfg2.ifc_xy_tolerance)

# 5) Guck in die Datei, ob alles drinsteht
ini = Path(CONFIG_PATH).read_text(encoding="utf-8")
print("\n=== Inhalt von", CONFIG_PATH, "===\n", ini)

import db_setup
newdb = db_setup.get_connection()