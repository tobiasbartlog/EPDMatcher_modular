# src/ui/widgets/stack_item_widget.py
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QCheckBox, QFrame
from PyQt6.QtCore import Qt


class StackItemWidget(QWidget):
    def __init__(self, stack_index: int, stack_info: dict, parent=None):
        super().__init__(parent)
        self.stack_index = stack_index
        self.stack_info = stack_info
        self.layer_checkboxes = []  # Liste, um die CheckBox-Instanzen zu speichern

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setSpacing(3)

        self.setStyleSheet("""
            StackItemWidget {
                border: 1px solid #cccccc;
                border-radius: 4px;
                background-color: #f0f0f0;
                padding: 3px;
            }
            QLabel {
                border: none;
                background-color: transparent;
            }
        """)

        # Titel des Stapels
        approx_mid_x = self.stack_info.get('approx_mid_x', 0.0)
        approx_mid_y = self.stack_info.get('approx_mid_y', 0.0)
        count = self.stack_info.get('count', 0)
        title_text = f"Stapel {self.stack_index + 1} (X={approx_mid_x:.2f}, Y={approx_mid_y:.2f} | {count} Elemente)"
        title_label = QLabel(f"<b>{title_text}</b>")
        main_layout.addWidget(title_label)

        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        main_layout.addWidget(line)

        elements = self.stack_info.get('elements', [])
        if not elements:
            no_elements_label = QLabel("Keine Elemente in diesem Stapel gefunden.")
            main_layout.addWidget(no_elements_label)
        else:
            for k, elem_data in enumerate(elements):
                elem_name = elem_data.get('name', 'N/A')
                elem_guid_short = elem_data.get('guid', 'N/A')[:8]  # Kürze GUID für Anzeige
                elem_min_z = elem_data.get('min_z', 0.0)
                elem_max_z = elem_data.get('max_z', 0.0)
                elem_thickness = elem_data.get('thickness_global_bbox', 0.0)

                layer_layout = QHBoxLayout()

                checkbox = QCheckBox()
                # Speichere die relevanten Daten des Layers direkt in der Checkbox
                checkbox.setProperty("layer_data", elem_data)
                self.layer_checkboxes.append(checkbox)
                layer_layout.addWidget(checkbox)

                layer_text = (f"L{k + 1}: {elem_name} (ID: {elem_guid_short}...)\n"
                              f"  Z: {elem_min_z:.3f}m bis {elem_max_z:.3f}m | D: {elem_thickness:.3f}m")
                layer_label = QLabel(layer_text)
                layer_label.setWordWrap(True)
                layer_layout.addWidget(layer_label, 1)  # Label nimmt mehr Platz

                main_layout.addLayout(layer_layout)

        self.setLayout(main_layout)

    def get_selected_layers_data(self) -> list:
        """Gibt eine Liste der Daten der ausgewählten Layer zurück."""
        selected_data = []
        for checkbox in self.layer_checkboxes:
            if checkbox.isChecked():
                selected_data.append(checkbox.property("layer_data"))
        return selected_data