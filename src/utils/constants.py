from pathlib import Path
from os import getenv

# --- Pfade ---
HOME = Path(getenv("APPDATA") or Path.home())
CONFIG_DIR = HOME / "EPDMatcher_modular"
CONFIG_PATH = CONFIG_DIR / "config.ini"

# --- Datenbank ---
DB_FILE = "oekobaudat_epds.db"
LABELS_COLUMN_NAME = "application_labels"
INDICATORS_TABLE_NAME = "epd_environmental_indicators"

# --- EPD-Filter ---
POSSIBLE_LABELS = [
    "STRASSENBAU", "HOCHBAU_TRAGWERK", "HOCHBAU_FASSADE", "HOCHBAU_DACH",
    "HOCHBAU_INNENAUSBAU", "TIEFBAU", "BRUECKENBAU", "TGA_HAUSTECHNIK",
    "DAEMMSTOFFE", "ABDICHTUNG_BAUWERK", "LANDSCHAFTSBAU_AUSSENANLAGEN",
    "INDUSTRIE_ANLAGENBAU", "MOEBEL_INNENEINRICHTUNG", "SONSTIGES_UNKLAR"
]
RELEVANT_COLUMNS_FOR_LLM_CONTEXT = [
    "name", "classification_path", "owner", "compliance", "data_sources", "sub_type",
    "general_comment_de", "tech_desc_de", "tech_app_de", "use_advice_de"
]


# --- Default-Konfiguration für ConfigManager ---
DEFAULT_TOP_N = 70
DEFAULT_IFC_MIN_PROXY_THICKNESS = 0.01
DEFAULT_IFC_XY_TOLERANCE = 0.5
DEFAULT_IFC_MIN_ELEMENTS_IN_STACK = 4

