# src/services/epd_service.py

from typing import List, Dict, Any
import json
import datetime

from src.core.db_setup import get_connection
from src.utils.constants import DB_FILE, LABELS_COLUMN_NAME

class EPDService:
    def __init__(self, db_path: str = DB_FILE):
        self.db_path = db_path

    def fetch_by_labels(
        self, labels: List[str], columns: List[str]
    ) -> List[Dict[str, Any]]:
        """
        Liefert alle EPDs, deren application_labels eines der labels enthält.
        Gibt nur uuid, name und die explizit gewünschten Spalten zurück.
        """
        with get_connection(self.db_path) as conn:
            cur = conn.cursor()

            # valid columns prüfen
            cur.execute("PRAGMA table_info(epds)")
            valid = {r["name"] for r in cur.fetchall()}
            cols = ["uuid", "name"] + [c for c in columns if c in valid]
            cols_sql = ", ".join(f'"{c}"' for c in cols)

            if not labels:
                return []  # oder raise ValueError

            where = " OR ".join(f'"{LABELS_COLUMN_NAME}" LIKE ?' for _ in labels)
            params = [f"%{lbl}%" for lbl in labels]

            cur.execute(f"SELECT {cols_sql} FROM epds WHERE {where}", params)
            return [dict(r) for r in cur.fetchall()]

    def get_details(self, uuid: str) -> Dict[str, Any]:
        """
        Lädt ein EPD komplett plus evtl. zugehörige Umwelt-JSON.
        """
        with get_connection(self.db_path) as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM epds WHERE uuid = ?", (uuid,))
            row = cur.fetchone()
            if row is None:
                raise KeyError(f"EPD {uuid} nicht gefunden.")
            epd = dict(row)

            # Environmental-Daten
            cur.execute(
                "SELECT lcia_results_json, key_flows_json, biogenic_carbon_json, last_updated "
                "FROM epd_environmental_indicators WHERE uuid = ?", (uuid,)
            )
            env = cur.fetchone()
            if env:
                epd["environmental"] = {
                    "LCIA Results": json.loads(env["lcia_results_json"]),
                    "Key Flows":   json.loads(env["key_flows_json"]),
                    "Biogenic Carbon": json.loads(env["biogenic_carbon_json"]),
                    "last_updated": env["last_updated"],
                }
            return epd

    def save_environmental(
            self,
            uuid: str,
            lcia: dict,
            key_flows: dict,
            biogenic: dict
    ) -> None:
        """
        Legt die Umweltdaten für ein EPD an oder ersetzt sie (INSERT OR REPLACE).
        """
        if not uuid:
            raise ValueError("UUID darf nicht leer sein")

        now = datetime.now().isoformat()
        lcia_js = json.dumps(lcia, ensure_ascii=False)
        flows_js = json.dumps(key_flows, ensure_ascii=False)
        bio_js = json.dumps(biogenic, ensure_ascii=False)

        with get_connection(self.db_path) as conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT OR REPLACE INTO epd_environmental_indicators
                (uuid, lcia_results_json, key_flows_json, biogenic_carbon_json, last_updated)
                VALUES (?, ?, ?, ?, ?)
            """, (uuid, lcia_js, flows_js, bio_js, now))
            conn.commit()
