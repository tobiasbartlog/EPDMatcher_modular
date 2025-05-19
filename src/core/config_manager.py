# src/core/config_manager.py
from pathlib import Path
from configparser import ConfigParser
from src.utils.constants import (
    CONFIG_PATH, # Stellt sicher, dass CONFIG_PATH aus constants.py korrekt ist (z.B. HOME / "EPDMatcher_modular" / "config.ini")
    DEFAULT_TOP_N,
    DEFAULT_IFC_MIN_PROXY_THICKNESS,
    DEFAULT_IFC_XY_TOLERANCE,
    DEFAULT_IFC_MIN_ELEMENTS_IN_STACK
)

DEFAULT_OPENAI_MODEL = "gpt-3.5-turbo" # Standardmodell

class ConfigManager:
    def __init__(self):
        self.path = Path(CONFIG_PATH)
        self.cfg = ConfigParser()
        self.defaults = {
            ("openai", "api_key"): "",
            ("openai", "model"): DEFAULT_OPENAI_MODEL, # Hinzugefügt
            ("openai", "top_n_for_llm"): str(DEFAULT_TOP_N),
            ("ifc_settings", "min_proxy_thickness"): str(DEFAULT_IFC_MIN_PROXY_THICKNESS),
            ("ifc_settings", "xy_tolerance"): str(DEFAULT_IFC_XY_TOLERANCE),
            ("ifc_settings", "min_elements_in_stack"): str(DEFAULT_IFC_MIN_ELEMENTS_IN_STACK),
        }
        self._ensure_file()

    def _ensure_file(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if self.path.exists():
            self.cfg.read(self.path, encoding="utf-8")
        # Sections/Options anlegen, wenn sie fehlen
        for (sec, opt), val in self.defaults.items():
            if not self.cfg.has_section(sec):
                self.cfg.add_section(sec)
            if not self.cfg.has_option(sec, opt):
                self.cfg.set(sec, opt, val)
        self.save()  # Default-Werte persistent machen

    def save(self):
        with open(self.path, "w", encoding="utf-8") as f:
            self.cfg.write(f)

    @property
    def api_key(self) -> str:
        return self.cfg.get("openai", "api_key", fallback=self.defaults[("openai","api_key")])

    @api_key.setter
    def api_key(self, key: str):
        self.cfg.set("openai", "api_key", key)
        self.save()

    @property
    def model(self) -> str: # Hinzugefügt
        return self.cfg.get("openai", "model", fallback=self.defaults[("openai","model")])

    @model.setter # Hinzugefügt
    def model(self, model_name: str):
        self.cfg.set("openai", "model", model_name)
        self.save()

    @property
    def top_n(self) -> int:
        try:
            return self.cfg.getint("openai", "top_n_for_llm")
        except ValueError:
            return int(self.defaults[("openai","top_n_for_llm")])


    @top_n.setter
    def top_n(self, n: int):
        self.cfg.set("openai", "top_n_for_llm", str(n))
        self.save()

    @property
    def ifc_min_proxy_thickness(self) -> float:
        try:
            return self.cfg.getfloat("ifc_settings", "min_proxy_thickness")
        except ValueError:
            return float(self.defaults[("ifc_settings","min_proxy_thickness")])


    @ifc_min_proxy_thickness.setter
    def ifc_min_proxy_thickness(self, v: float):
        self.cfg.set("ifc_settings", "min_proxy_thickness", str(v))
        self.save()

    @property
    def ifc_xy_tolerance(self) -> float:
        try:
            return self.cfg.getfloat("ifc_settings", "xy_tolerance")
        except ValueError:
            return float(self.defaults[("ifc_settings","xy_tolerance")])

    @ifc_xy_tolerance.setter
    def ifc_xy_tolerance(self, v: float):
        self.cfg.set("ifc_settings", "xy_tolerance", str(v))
        self.save()

    @property
    def ifc_min_elements_in_stack(self) -> int:
        try:
            return self.cfg.getint("ifc_settings", "min_elements_in_stack")
        except ValueError:
            return int(self.defaults[("ifc_settings","min_elements_in_stack")])

    @ifc_min_elements_in_stack.setter
    def ifc_min_elements_in_stack(self, v: int):
        self.cfg.set("ifc_settings", "min_elements_in_stack", str(v))
        self.save()