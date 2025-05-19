### src/ui/ifc_analysis_tab.py

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QTextEdit, QListWidget, QProgressDialog
from PyQt6.QtCore import pyqtSignal

class IfcAnalysisTab(QWidget):
    # Signal: list of stacks
    stacks_ready = pyqtSignal(list)

    def __init__(self, ifc_service, parent=None):
        super().__init__(parent)
        self.ifc_service = ifc_service
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        self.upload_btn = QPushButton("IFC-Datei auswählen & analysieren")
        self.upload_btn.clicked.connect(self.on_analyze)
        layout.addWidget(self.upload_btn)

        self.log = QTextEdit()
        self.log.setReadOnly(True)
        layout.addWidget(self.log)

        self.list_widget = QListWidget()
        layout.addWidget(self.list_widget)

    def on_analyze(self):
        path, _ = self.ifc_service.select_ifc_file(self)
        if not path:
            return
        self.log.clear()
        # progress dialog
        self.progress = QProgressDialog("Analysiere IFC...", None, 0, 100, self)
        self.progress.setWindowTitle("Fortschritt")
        self.progress.show()
        # call analyse
        stacks = self.ifc_service.analyse(
            path,
            message_callback=self.log.append,
            progress_callback=lambda c, t, txt: (self.progress.setLabelText(txt), self.progress.setValue(int(c/t*100)))
        )
        self.progress.close()
        self.list_widget.clear()
        for stack in stacks:
            self.list_widget.addItem(f"Stapel {stack['count']} Elemente @ ({stack['approx_mid_x']:.2f}, {stack['approx_mid_y']:.2f})")
        self.stacks_ready.emit(stacks)