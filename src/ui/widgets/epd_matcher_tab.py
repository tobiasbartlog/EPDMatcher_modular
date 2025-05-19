### src/ui/epd_matcher_tab.py

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QGroupBox, QScrollArea, QCheckBox, QPushButton, QRadioButton, QButtonGroup, QLabel
from PyQt6.QtCore import pyqtSignal

class EpdMatcherTab(QWidget):
    # Signal emitted when a match is confirmed: passes selected uuid
    match_selected = pyqtSignal(str)

    def __init__(self, epd_service, llm_service, fuzzy_search=None, parent=None):
        super().__init__(parent)
        self.epd_service = epd_service
        self.llm_service = llm_service
        self.fuzzy_search = fuzzy_search

        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        # 1) Label-Filter Group
        self.label_group = QGroupBox("2. Anwendung wählen (Filter)")
        self.label_layout = QVBoxLayout()
        # labels dynamically from epd_service.constants
        for lbl in self.epd_service.get_available_labels():
            cb = QCheckBox(lbl)
            self.label_layout.addWidget(cb)
        self.label_group.setLayout(self.label_layout)
        layout.addWidget(self.label_group)

        # 2) Spalten-Checkboxes
        self.column_group = QGroupBox("3. Spalten für erweiterten Kontext")
        self.col_layout = QVBoxLayout()
        for col in self.epd_service.get_relevant_columns():
            cb = QCheckBox(col)
            self.col_layout.addWidget(cb)
        self.column_group.setLayout(self.col_layout)
        layout.addWidget(self.column_group)

        # 3) Search button
        self.search_btn = QPushButton("4. Passende EPDs finden")
        self.search_btn.clicked.connect(self.on_search)
        layout.addWidget(self.search_btn)

        # 4) Results area (scrollable radio buttons)
        self.results_group = QGroupBox("Ergebnisse")
        self.results_layout = QVBoxLayout()
        self.results_group.setLayout(self.results_layout)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        container = QWidget()
        self.radio_area = QVBoxLayout(container)
        scroll.setWidget(container)
        self.results_layout.addWidget(scroll)
        layout.addWidget(self.results_group)

        # confirm selection
        self.confirm_btn = QPushButton("Details anzeigen")
        self.confirm_btn.clicked.connect(self.on_confirm)
        layout.addWidget(self.confirm_btn)

        self.button_group = QButtonGroup(self)

    def on_search(self):
        # gather filters
        labels = [cb.text() for cb in self.label_group.findChildren(QCheckBox) if cb.isChecked()]
        cols   = [cb.text() for cb in self.column_group.findChildren(QCheckBox) if cb.isChecked()]
        # fetch epds
        epds = self.epd_service.fetch_epds_by_labels(labels, cols)
        # call fuzzy or llm
        if self.fuzzy_search and not self.llm_service:
            results = self.fuzzy_search(self.manual_input, epds, cols)
        else:
            prompt = self._build_prompt(epds, cols)
            raw = self.llm_service.call(prompt)
            results = self.llm_service.parse_matches(raw)
        # populate radio buttons
        for rb in self.button_group.buttons():
            self.button_group.removeButton(rb)
            rb.setParent(None)
        for item in results:
            rb = QRadioButton(f"{item['name']} ({item['uuid'][:8]})")
            rb.setProperty('uuid', item['uuid'])
            self.radio_area.addWidget(rb)
            self.button_group.addButton(rb)

    def on_confirm(self):
        btn = self.button_group.checkedButton()
        if btn:
            uuid = btn.property('uuid')
            self.match_selected.emit(uuid)

    def _build_prompt(self, epds, cols):
        # basic implementation; adjust as needed
        lines = [f"UUID: {e['uuid']} | Name: {e['name']}" for e in epds]
        return "\n".join(lines)







