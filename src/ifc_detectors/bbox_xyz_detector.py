# src/bbox_xyz_detector.py
import os
import sys
from collections import defaultdict
# Counter ist hier nicht mehr direkt für Top-N verwendet, kann ggf. entfernt werden, wenn nirgends sonst genutzt
# import math # Wird nicht verwendet, kann entfernt werden
import json  # Nur wenn Speichern noch eine Option sein soll (für GUI-Integration meist nicht hier)

import ifcopenshell
import ifcopenshell.geom
import numpy as np

# --- PythonOCC Imports ---
# Diese bleiben, falls ifcopenshell.geom.create_shape sie implizit für bestimmte Geometrien benötigt.
# Wenn nicht, könnten sie theoretisch auch entfernt werden, aber sicherheitshalber hier belassen.
try:
    from OCC.Core import gp
    from OCC.Core import BRepAlgoAPI, BRepPrimAPI, BRepBuilderAPI
    from OCC.Core import TopoDS, TopExp, TopAbs
    from OCC.Core import Bnd
    from OCC.Core import BRepBndLib
except ImportError as e:
    # Für ein Modul ist print() hier weniger ideal, besser wäre es, wenn die GUI
    # prüft, ob der Import von identstreetlayers selbst fehlschlägt.
    # Aber für den Moment belassen wir es, um die Struktur nicht zu stark zu ändern.
    print(f"WARNUNG (bbox_xyz_detector.py): pythonocc-core konnte nicht importiert werden: {e}")
    # sys.exit(1) # Ein Modul sollte nicht sys.exit() aufrufen
except Exception as e_general:
    print(f"WARNUNG (bbox_xyz_detector.py): Unerwarteter Fehler beim Importieren von PythonOCC: {e_general}")

# ———————— Standard-Konfigurationswerte (dienen als Defaults für Funktionsparameter) ————————
# Diese globalen Konstanten werden NICHT mehr direkt in den Funktionen unten verwendet,
# sondern dienen als Referenz oder Default-Werte in der GUI oder beim direkten Aufruf.
DEFAULT_MIN_PROXY_THICKNESS = 0.01
DEFAULT_XY_TOLERANCE = 0.5
DEFAULT_MIN_ELEMENTS_IN_STACK_COLUMN = 4


# IFC_FILE_PATH und OUTPUT_JSON_FILE werden hier nicht mehr benötigt.
# ——————————————————————————————————————————————————————————————————————————————————————

def load_model_from_path(path: str, message_callback=None) -> ifcopenshell.file | None:
    """
    Lädt ein IFC-Modell vom gegebenen Pfad.
    Gibt das ifcopenshell.file Objekt zurück oder None bei Fehlern.
    """
    if message_callback:
        message_callback(f"Lade IFC-Modell von: {os.path.basename(path)}...")
    if not os.path.isfile(path):
        if message_callback:
            message_callback(f"FEHLER: Datei nicht gefunden: {path}")
        # raise FileNotFoundError(f"Datei nicht gefunden: {path}") # Besser None zurückgeben für GUI
        return None
    try:
        model = ifcopenshell.open(path)
        if message_callback:
            message_callback("IFC-Modell erfolgreich geladen.")
        return model
    except Exception as e:
        if message_callback:
            message_callback(f"FEHLER beim Öffnen der IFC-Datei: {e}")
        return None


def get_element_bbox_details(proxy_element):
    """
    Ermittelt Bounding-Box-Details für ein gegebenes IfcBuildingElementProxy.
    Unverändert von Ihrer Version.
    """
    settings = ifcopenshell.geom.settings()
    try:
        shape_result = ifcopenshell.geom.create_shape(settings, proxy_element)
        if not shape_result or not hasattr(shape_result, 'geometry') or \
                not shape_result.geometry or not hasattr(shape_result.geometry, 'verts') or \
                not shape_result.geometry.verts:
            return None

        verts_data = shape_result.geometry.verts
        if not isinstance(verts_data, (list, tuple)) or not verts_data or \
                not all(isinstance(v, (int, float)) for v in verts_data) or \
                len(verts_data) % 3 != 0:
            return None

        verts = np.array(verts_data, dtype=float).reshape(-1, 3)
        if np.isnan(verts).any(): return None

        min_coords = np.min(verts, axis=0)
        max_coords = np.max(verts, axis=0)
        min_x, min_y, min_z = min_coords[0], min_coords[1], min_coords[2]
        max_x, max_y, max_z = max_coords[0], max_coords[1], max_coords[2]

        if not (max_x >= min_x and max_y >= min_y and max_z >= min_z): return None

        thickness_global_bbox = max_z - min_z
        name = proxy_element.ObjectType or proxy_element.Name or proxy_element.LongName or "<kein Name>"

        return {
            'guid': proxy_element.GlobalId, 'name': name, 'ifc_class': proxy_element.is_a(),
            'min_x': min_x, 'max_x': max_x, 'min_y': min_y, 'max_y': max_y,
            'min_z': min_z, 'max_z': max_z, 'thickness_global_bbox': thickness_global_bbox,
            'mid_x': (min_x + max_x) / 2.0, 'mid_y': (min_y + max_y) / 2.0
        }
    except Exception:
        # Im Modulbetrieb ist es oft besser, hier keinen print zu haben,
        # sondern den Fehler ggf. weiter oben zu behandeln oder None zurückzugeben.
        return None


def find_stacked_elements_by_xy_midpoint(
        model: ifcopenshell.file,
        min_proxy_thickness_param: float,
        xy_tolerance_param: float,
        min_elements_in_stack_param: int,
        message_callback=None,
        progress_callback=None
) -> list:
    """
    Analysiert das IFC-Modell und findet gestapelte IfcBuildingElementProxy-Elemente.
    Verwendet übergebene Parameter für die Konfiguration.
    """
    if message_callback:
        message_callback("1. Sammle Bounding-Box Details aller IfcBuildingElementProxy-Elemente...")

    element_data_list = []
    processed_count = 0
    # Es ist effizienter, by_type einmal aufzurufen und dann zu iterieren.
    all_proxies = list(model.by_type("IfcBuildingElementProxy"))
    total_proxies = len(all_proxies)

    if total_proxies == 0:
        if message_callback:
            message_callback("  Keine IfcBuildingElementProxy-Elemente im Modell gefunden.")
        return []

    if progress_callback:  # Initialer Fortschritt
        progress_callback(0, total_proxies, f"Sammle BBox (0/{total_proxies})")

    for i, proxy in enumerate(all_proxies):
        processed_count += 1
        if progress_callback and (processed_count % 20 == 0 or processed_count == total_proxies):
            # Fortschritt an die GUI melden
            progress_callback(processed_count, total_proxies,
                              f"Verarbeite Proxy {processed_count}/{total_proxies} (BBox)")

        details = get_element_bbox_details(proxy)  # Ihre bestehende Funktion
        # Verwende die übergebenen Parameter
        if details and details['thickness_global_bbox'] >= min_proxy_thickness_param:
            element_data_list.append(details)

    if message_callback:
        message_callback(
            f"  {len(element_data_list)} Proxies nach Dickenfilter (>= {min_proxy_thickness_param * 1000:.0f}mm)."
        )
    if not element_data_list:
        return []

    if message_callback:
        message_callback(
            f"\n2. Gruppiere Elemente nach XY-Mittelpunkt (Toleranz: {xy_tolerance_param * 1000:.0f}mm)...")
    if progress_callback:  # Fortschritt für Gruppierung
        progress_callback(0, 1, "Gruppiere Elemente...")  # Einfacher Fortschritt (1 Schritt)

    grouped_by_xy_midpoint = defaultdict(list)
    for data_item in element_data_list:  # data umbenannt zu data_item, um Konflikt mit Modul 'data' zu vermeiden
        # Verwende die übergebenen Parameter
        key_x = round(data_item['mid_x'] / xy_tolerance_param)
        key_y = round(data_item['mid_y'] / xy_tolerance_param)
        grouped_by_xy_midpoint[(key_x, key_y)].append(data_item)

    if progress_callback:  # Fortschritt für Gruppierung abgeschlossen
        progress_callback(1, 1, "Gruppierung abgeschlossen.")

    if message_callback:
        message_callback("\n3. Filtere und sortiere gefundene vertikale Elementstapel...")
    if progress_callback:  # Fortschritt für Filterung
        progress_callback(0, 1, "Filtere Stapel...")

    output_stacks_data = []  # Umbenannt von output_stacks_for_json, da wir hier nur Daten zurückgeben

    sorted_group_keys = sorted(grouped_by_xy_midpoint.keys(),
                               key=lambda k: len(grouped_by_xy_midpoint[k]),
                               reverse=True)

    for key_val in sorted_group_keys:  # key umbenannt zu key_val
        elements_in_group_details = grouped_by_xy_midpoint[key_val]
        # Verwende die übergebenen Parameter
        if len(elements_in_group_details) >= min_elements_in_stack_param:
            elements_in_group_details.sort(key=lambda d: d['min_z'])

            approx_mid_x = key_val[0] * xy_tolerance_param
            approx_mid_y = key_val[1] * xy_tolerance_param

            serializable_elements = []
            for elem_data in elements_in_group_details:
                serializable_elements.append({
                    'guid': elem_data['guid'],
                    'name': elem_data['name'],
                    'ifc_class': elem_data['ifc_class'],
                    'min_z': elem_data['min_z'],
                    'max_z': elem_data['max_z'],
                    'thickness_global_bbox': elem_data['thickness_global_bbox']
                })

            output_stacks_data.append({
                'approx_mid_x': approx_mid_x,
                'approx_mid_y': approx_mid_y,
                'elements': serializable_elements,
                'count': len(serializable_elements)
            })

    if progress_callback:  # Fortschritt für Filterung abgeschlossen
        progress_callback(1, 1, "Filterung abgeschlossen.")

    if message_callback:
        message_callback(f"  Analyse abgeschlossen. {len(output_stacks_data)} Stapel-Kandidaten gefunden.")
    return output_stacks_data


# Der folgende Block wird nur ausgeführt, wenn das Skript direkt gestartet wird.
# Für den Import als Modul wird er ignoriert. Sie können ihn für Tests belassen
# oder entfernen/auskommentieren.
if __name__ == "__main__":
    print("Starte bbox_xyz_detector.py als eigenständiges Skript für Tests...")


    # Beispielhafte Test-Callbacks
    def console_message_callback(message):
        print(f"[MSG] {message}")


    def console_progress_callback(current, total, status_text):
        print(f"[PROG] {status_text} - {current}/{total}")


    # Testpfad (bitte anpassen, falls notwendig für direkte Tests)
    TEST_IFC_FILE_PATH = r"C:\Users\Arbeit\PycharmProjects\FullSusInfraEPDMatcher\ifcfile.ifc"  # Oder ein anderer Testpfad
    TEST_OUTPUT_JSON_FILE = "test_candidate_stacks_direct.json"

    console_message_callback(f"Lade IFC für Test: {TEST_IFC_FILE_PATH}")
    model = load_model_from_path(TEST_IFC_FILE_PATH, message_callback=console_message_callback)

    if model:
        console_message_callback("Starte Stapel-Analyse mit Standardparametern für Test...")
        candidate_stacks = find_stacked_elements_by_xy_midpoint(
            model,
            min_proxy_thickness_param=DEFAULT_MIN_PROXY_THICKNESS,
            xy_tolerance_param=DEFAULT_XY_TOLERANCE,
            min_elements_in_stack_param=DEFAULT_MIN_ELEMENTS_IN_STACK_COLUMN,
            message_callback=console_message_callback,
            progress_callback=console_progress_callback
        )

        if not candidate_stacks:
            console_message_callback("\nKeine Stapel-Kandidaten im Test gefunden.")
        else:
            console_message_callback(
                f"\n{len(candidate_stacks)} Stapel-Kandidaten im Test gefunden."
            )
            # Optionale Ausgabe der Stapel in der Konsole
            for i, stack_info in enumerate(candidate_stacks, 1):
                console_message_callback(
                    f"\nStapel {i} (ca. X={stack_info['approx_mid_x']:.2f}, Y={stack_info['approx_mid_y']:.2f}; {stack_info['count']} Elemente):"
                )
                for elem_data in reversed(stack_info['elements']):
                    console_message_callback(
                        f"  - {elem_data['guid']} | {elem_data['name']:<50} | min_Z: {elem_data['min_z']:.3f}"
                    )

            # Optional: Testweise Speicherung in JSON
            try:
                with open(TEST_OUTPUT_JSON_FILE, 'w', encoding='utf-8') as f:
                    json.dump(candidate_stacks, f, indent=4, ensure_ascii=False)
                console_message_callback(f"\nTest-Kandidaten-Stapel wurden in '{TEST_OUTPUT_JSON_FILE}' gespeichert.")
            except Exception as e:
                console_message_callback(f"\nFehler beim Speichern der Test-Kandidaten-Stapel: {e}")
    else:
        console_message_callback("Test-IFC-Modell konnte nicht geladen werden.")
