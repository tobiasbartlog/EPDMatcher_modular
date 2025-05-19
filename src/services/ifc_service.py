# src/services/ifc_service.py
from typing import List, Dict, Any, Callable
from src.ifc_detectors.bbox_xyz_detector import (
    load_model_from_path,
    find_stacked_elements_by_xy_midpoint
)

class IFCService:
    def __init__(
        self,
        min_proxy_thickness: float,
        xy_tolerance: float,
        min_elements_in_stack: int
    ):
        self.min_proxy_thickness = min_proxy_thickness
        self.xy_tolerance = xy_tolerance
        self.min_elements_in_stack = min_elements_in_stack

    def analyse(
        self,
        ifc_path: str,
        message_cb: Callable[[str], None] = lambda m: None,
        progress_cb:  Callable[[int, int, str], None] = lambda c, t, s: None
    ) -> List[Dict[str, Any]]:
        """
        Lädt das IFC, filtert BuildingElementProxy nach min_proxy_thickness,
        gruppiert nach XY-Mittelpunkt mit xy_tolerance und min_elements_in_stack.
        Gibt eine Liste von „Stacks“ zurück.
        """
        message_cb(f"Starte IFC-Analyse: {ifc_path}")
        model = load_model_from_path(ifc_path, message_callback=message_cb)
        if model is None:
            message_cb("Fehler: IFC-Modell konnte nicht geladen werden.")
            return []

        stacks = find_stacked_elements_by_xy_midpoint(
            model,
            min_proxy_thickness_param=self.min_proxy_thickness,
            xy_tolerance_param=self.xy_tolerance,
            min_elements_in_stack_param=self.min_elements_in_stack,
            message_callback=message_cb,
            progress_callback=progress_cb
        )
        message_cb(f"Analyse fertig: {len(stacks)} Stapel gefunden.")
        return stacks
