# core/db_setup.py
import sqlite3
from pathlib import Path

def get_connection(db_path: str) -> sqlite3.Connection:
    """
    Öffnet eine SQLite-Verbindung mit Foreign-Keys und Row-Factory.
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def init_db(db_path: str):
    """
    Legt nötige Tabellen an (falls noch nicht vorhanden):
      - epds
      - epd_environmental_indicators
    """
    # sicherstellen, dass der Pfad existiert
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    conn = get_connection(db_path)
    cur = conn.cursor()

    # --- Tabelle epds (Grundschema, bitte ggf. anpassen) ---
    cur.execute("""
    CREATE TABLE IF NOT EXISTS epds (
        uuid TEXT PRIMARY KEY,
        name TEXT,
        classification_path TEXT,
        owner TEXT,
        compliance TEXT,
        data_sources TEXT,
        sub_type TEXT,
        general_comment_de TEXT,
        tech_desc_de TEXT,
        tech_app_de TEXT,
        use_advice_de TEXT,
        ref_year INTEGER,
        valid_until TEXT,
        application_labels TEXT
    )
    """)

    # --- Tabelle für die JSON-Umweltdaten ---
    cur.execute("""
    CREATE TABLE IF NOT EXISTS epd_environmental_indicators (
        uuid TEXT PRIMARY KEY,
        lcia_results_json TEXT,
        key_flows_json TEXT,
        biogenic_carbon_json TEXT,
        last_updated TEXT,
        FOREIGN KEY (uuid) REFERENCES epds(uuid) ON DELETE CASCADE
    )
    """)

    conn.commit()
    conn.close()
