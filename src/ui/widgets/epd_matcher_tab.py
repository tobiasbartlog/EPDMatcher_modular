# src/ui/widgets/epd_matcher_tab.py
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QGroupBox, QScrollArea,
                             QCheckBox, QPushButton, QRadioButton, QButtonGroup,
                             QTextEdit,  # QTextEdit für die manuelle Eingabe
                             QMessageBox, QProgressDialog, QTabWidget, QLabel)  # QTabWidget für Layer-Tabs, QLabel
from PyQt6.QtCore import pyqtSignal, QTimer, Qt
from src.services.fuzzy_service import fuzzy_search  # Importiere die Funktion direkt


class EpdMatcherTab(QWidget):
    match_selected = pyqtSignal(str)  # Signal, das die UUID des ausgewählten EPDs sendet

    def __init__(self, epd_service, llm_service, config_manager, parent=None):  # config_manager hinzugefügt
        super().__init__(parent)
        self.epd_service = epd_service
        self.llm_service = llm_service
        self.config_manager = config_manager  # config_manager speichern
        # fuzzy_search ist eine Funktion und wird direkt aufgerufen, nicht als Instanzvariable gespeichert,
        # es sei denn, du möchtest die Möglichkeit haben, die Fuzzy-Search-Implementierung zur Laufzeit auszutauschen.

        self.current_epd_search_context_title = "Manuelle Suche"  # Für Detail-Tab Kontext
        self.active_layer_search_widgets = []  # Für dynamische Layer-Tabs
        self.radio_buttons = []  # Liste für erstellte RadioButtons
        self.radio_group = QButtonGroup(self)  # ButtonGroup für exklusive Auswahl

        self.loading_dialog = None  # Für Ladeanzeige

        self._build_ui()

    def update_llm_service(self, llm_service):  # Methode zum Aktualisieren des LLM-Service von außen
        self.llm_service = llm_service
        print("EpdMatcherTab: LLM Service aktualisiert.")

    def _build_ui(self):
        main_layout = QVBoxLayout(self)

        # 1. Gruppe: Produkt- oder Materialbeschreibung (jetzt mit Tabs für Layer)
        input_group = QGroupBox("1. Produkt- oder Materialbeschreibung")
        input_group_layout = QVBoxLayout(input_group)
        self.layer_epd_search_tabs = QTabWidget()  # TabWidget für manuelle Eingabe und Layer-Suchen
        input_group_layout.addWidget(self.layer_epd_search_tabs)
        input_group.setLayout(input_group_layout)
        main_layout.addWidget(input_group)

        # Standard-Tab für manuelle Eingabe erstellen
        manual_search_tab_content = QWidget()
        manual_search_layout = QVBoxLayout(manual_search_tab_content)
        self.manual_input_box = QTextEdit()
        self.manual_input_box.setPlaceholderText(
            "Manuelle Eingabe für EPD-Suche (z.B. Asphalttragschicht AC 16 TS)\n"
            "oder wählen Sie Schichten aus der IFC Analyse (werden als neue Tabs hier erscheinen)."
        )
        self.manual_input_box.setFixedHeight(100)
        manual_search_layout.addWidget(self.manual_input_box)
        manual_search_tab_content.setLayout(manual_search_layout)
        self.layer_epd_search_tabs.addTab(manual_search_tab_content, "Manuelle Suche")

        # Suchmethode wählen (aus oldfile.py)
        method_group = QGroupBox("Suchmethode wählen")
        method_layout_h = QHBoxLayout(method_group)
        self.rb_api = QRadioButton("API Matching (LLM)")
        self.rb_fuzzy = QRadioButton("Stichwortsuche (Fuzzy)")
        self.rb_api.setChecked(True)
        method_layout_h.addWidget(self.rb_api)
        method_layout_h.addWidget(self.rb_fuzzy)
        method_group.setLayout(method_layout_h)
        main_layout.addWidget(method_group)

        # Filter-Reihe (Label-Filter und Spalten-Checkboxes)
        filter_row_layout = QHBoxLayout()

        # 2. Label-Filter Group (aus deiner epd_matcher_tab.py, angepasst)
        self.label_group_box = QGroupBox("2. Anwendung wählen (Filter)")
        self.label_checkboxes_layout = QVBoxLayout()  # Layout für die Checkboxen

        # ScrollArea für Label-Filter
        label_scroll_area = QScrollArea()
        label_scroll_area.setWidgetResizable(True)
        label_scroll_widget = QWidget()
        self.label_checkboxes_layout_scroll = QVBoxLayout(label_scroll_widget)  # Checkboxen kommen hier rein

        # Labels dynamisch aus epd_service.constants oder einer Methode in EPDService
        # In constants.py: POSSIBLE_LABELS
        from src.utils.constants import POSSIBLE_LABELS
        self.label_checkbox_widgets = {}  # Zum Speichern der Checkbox-Instanzen
        for lbl in POSSIBLE_LABELS:  # Annahme: epd_service.get_available_labels() gibt Liste zurück
            cb = QCheckBox(lbl)
            if lbl == "STRASSENBAU":  # Default-Auswahl aus oldfile.py
                cb.setChecked(True)
            self.label_checkboxes_layout_scroll.addWidget(cb)
            self.label_checkbox_widgets[lbl] = cb
        self.label_checkboxes_layout_scroll.addStretch(1)  # Damit Checkboxen nach oben rutschen
        label_scroll_widget.setLayout(self.label_checkboxes_layout_scroll)
        label_scroll_area.setWidget(label_scroll_widget)

        # Hauptlayout für die Label-GroupBox
        vbox_label_group = QVBoxLayout(self.label_group_box)
        vbox_label_group.addWidget(label_scroll_area)
        filter_row_layout.addWidget(self.label_group_box)

        # 3. Spalten-Checkboxes für erweiterten Kontext (aus deiner epd_matcher_tab.py, angepasst)
        self.column_group_box = QGroupBox("3. Spalten für erweiterten Kontext (LLM)")
        # ScrollArea für Spalten-Filter
        column_scroll_area = QScrollArea()
        column_scroll_area.setWidgetResizable(True)
        column_scroll_widget = QWidget()
        self.column_checkboxes_layout_scroll = QVBoxLayout(column_scroll_widget)  # Checkboxen kommen hier rein

        # Spalten dynamisch, z.B. aus constants.py
        from src.utils.constants import RELEVANT_COLUMNS_FOR_LLM_CONTEXT
        self.column_checkbox_widgets = {}  # Zum Speichern der Checkbox-Instanzen
        for col in RELEVANT_COLUMNS_FOR_LLM_CONTEXT:
            cb = QCheckBox(col)
            if col == "name":  # Default-Auswahl aus oldfile.py
                cb.setChecked(True)
            self.column_checkboxes_layout_scroll.addWidget(cb)
            self.column_checkbox_widgets[col] = cb
        self.column_checkboxes_layout_scroll.addStretch(1)
        column_scroll_widget.setLayout(self.column_checkboxes_layout_scroll)
        column_scroll_area.setWidget(column_scroll_widget)

        # Hauptlayout für die Column-GroupBox
        vbox_column_group = QVBoxLayout(self.column_group_box)
        vbox_column_group.addWidget(column_scroll_area)
        filter_row_layout.addWidget(self.column_group_box)

        main_layout.addLayout(filter_row_layout)

        # 4. Such-Button
        self.search_btn = QPushButton("4. Passende EPDs finden")
        self.search_btn.clicked.connect(self.find_matches_controller)  # Controller-Methode
        main_layout.addWidget(self.search_btn, alignment=Qt.AlignmentFlag.AlignCenter)

        # 5. Ergebnisse (RadioButtons in ScrollArea)
        self.results_group_box = QGroupBox("5. Vorgeschlagene EPDs (Auswahl)")
        results_group_layout = QVBoxLayout(self.results_group_box)

        self.results_scroll_area = QScrollArea()
        self.results_scroll_area.setWidgetResizable(True)
        self.match_results_container_widget = QWidget()  # Widget für die ScrollArea
        self.match_area_layout = QVBoxLayout(self.match_results_container_widget)  # Layout für RadioButtons
        self.match_area_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.match_results_container_widget.setLayout(self.match_area_layout)
        self.results_scroll_area.setWidget(self.match_results_container_widget)
        results_group_layout.addWidget(self.results_scroll_area)
        main_layout.addWidget(self.results_group_box)

        # 6. Details-Button
        self.confirm_btn = QPushButton("6. Details für Auswahl abrufen")
        self.confirm_btn.setEnabled(False)  # Initial deaktiviert
        self.confirm_btn.clicked.connect(self.on_confirm_selection)
        main_layout.addWidget(self.confirm_btn, alignment=Qt.AlignmentFlag.AlignCenter)

        self.setLayout(main_layout)

    def clear_match_radio_buttons(self):
        """Entfernt alle vorherigen RadioButtons für EPD-Matches."""
        for rb in self.radio_buttons:
            self.radio_group.removeButton(rb)
            rb.setParent(None)
            rb.deleteLater()
        self.radio_buttons.clear()
        self.confirm_btn.setEnabled(False)

    def find_matches_controller(self):
        """Diese Methode sammelt die Eingaben und startet die passende Suchfunktion."""
        self.clear_match_radio_buttons()  # Alte Ergebnisse löschen

        # Aktuellen Suchkontext und Eingabe ermitteln
        current_search_tab_index = self.layer_epd_search_tabs.currentIndex()
        self.current_epd_search_context_title = self.layer_epd_search_tabs.tabText(current_search_tab_index)

        user_input_text = ""
        if self.current_epd_search_context_title == "Manuelle Suche":
            user_input_text = self.manual_input_box.toPlainText().strip()
        else:
            # Finde das Eingabefeld für den aktiven Layer-Tab
            # Dies setzt voraus, dass handle_ifc_layers_for_search die Widgets korrekt speichert
            for layer_widget_info in self.active_layer_search_widgets:
                # Wir brauchen einen Weg, um das Widget im Tab zu identifizieren,
                # z.B. indem wir das QTextEdit direkt im Layer-Info speichern.
                # Nehmen wir an, layer_widget_info['input_widget'] ist das QTextEdit.
                # und layer_widget_info['tab_title'] ist der Titel des Tabs.
                if layer_widget_info.get('tab_title') == self.current_epd_search_context_title:
                    input_widget = layer_widget_info.get('input_widget')
                    if input_widget:
                        user_input_text = input_widget.toPlainText().strip()
                    break

        if not user_input_text:
            QMessageBox.warning(self, "Eingabe fehlt",
                                f"Bitte eine Beschreibung im Tab '{self.current_epd_search_context_title}' eingeben.")
            return

        selected_labels = [lbl for lbl, cb in self.label_checkbox_widgets.items() if cb.isChecked()]
        if not selected_labels:
            QMessageBox.warning(self, "Label fehlt", "Bitte mindestens ein Anwendungs-Label auswählen.")
            return

        # Spalten nur für LLM relevant
        selected_columns = []
        if self.rb_api.isChecked():
            selected_columns = [col for col, cb in self.column_checkbox_widgets.items() if cb.isChecked()]
            if not selected_columns:
                QMessageBox.warning(self, "Spalten fehlen",
                                    "Für das API Matching (LLM) bitte mindestens eine Spalte für den Kontext auswählen.")
                return

        # EPDs basierend auf Labels vorfiltern
        try:
            # Die EPDService.fetch_by_labels erwartet nur Label-Namen und Spalten für den SELECT
            # Die Spalten hier sind die, die für den LLM-Kontext relevant sind, plus 'uuid' und 'name'.
            # fetch_by_labels sollte immer uuid und name zurückgeben, plus die explizit angeforderten 'selected_columns'.
            cols_for_fetch = list(set(['uuid', 'name'] + selected_columns))
            pre_filtered_epds = self.epd_service.fetch_by_labels(selected_labels, cols_for_fetch)
        except Exception as e:
            QMessageBox.critical(self, "Datenbankfehler", f"Fehler beim Abrufen der EPDs: {e}")
            return

        if not pre_filtered_epds:
            QMessageBox.information(self, "Keine EPDs",
                                    "Keine EPDs für die ausgewählten Label-Filter in der Datenbank gefunden.")
            return

        # Ladeanzeige starten
        if self.loading_dialog:
            self.loading_dialog.close()
        self.loading_dialog = QProgressDialog(
            f"Suche EPDs für '{user_input_text[:30]}...' ({'LLM' if self.rb_api.isChecked() else 'Fuzzy'})...", None, 0,
            0, self)
        self.loading_dialog.setWindowModality(Qt.WindowModality.ApplicationModal)
        self.loading_dialog.setCancelButton(None)
        self.loading_dialog.setMinimumDuration(0)
        self.loading_dialog.show()
        QApplication.processEvents()  # Wichtig, damit der Dialog gezeichnet wird

        if self.rb_api.isChecked():
            # Starte LLM-Suche mit Verzögerung, damit der Lade-Dialog erscheint
            QTimer.singleShot(50,
                              lambda: self._execute_llm_search(user_input_text, pre_filtered_epds, selected_columns))
        else:  # Fuzzy Search
            # Starte Fuzzy-Suche mit Verzögerung
            QTimer.singleShot(50,
                              lambda: self._execute_fuzzy_search(user_input_text, pre_filtered_epds, selected_columns))

    def _execute_llm_search(self, user_input, epds_for_context, context_columns):
        """Führt die LLM-basierte Suche aus."""
        prompt = self._build_llm_prompt(user_input, epds_for_context, context_columns)

        try:
            raw_llm_response = self.llm_service.call(prompt)  # llm_service.call kümmert sich um Exceptions
            parsed_matches = self.llm_service.parse_matches(raw_llm_response)  # llm_service.parse_matches

            if self.loading_dialog: self.loading_dialog.close()

            if not parsed_matches and "error" in raw_llm_response.lower():  # Prüfe ob llm_service einen Fehlerstring zurückgab
                try:
                    error_data = json.loads(raw_llm_response)  # Versuche, den Fehlerstring als JSON zu parsen
                    QMessageBox.critical(self, "LLM API Fehler",
                                         f"Fehler von LLM: {error_data.get('error', raw_llm_response)}")
                except json.JSONDecodeError:
                    QMessageBox.critical(self, "LLM API Fehler", f"Fehler von LLM: {raw_llm_response}")
                return

            if not parsed_matches:
                QMessageBox.information(self, "Keine LLM-Treffer", "Das LLM hat keine passenden EPDs identifiziert.")
                return

            self._populate_match_results(parsed_matches, is_llm=True)

        except Exception as e:
            if self.loading_dialog: self.loading_dialog.close()
            QMessageBox.critical(self, "LLM Fehler", f"Ein unerwarteter Fehler bei der LLM-Suche ist aufgetreten: {e}")

    def _build_llm_prompt(self, user_input, epds, columns_for_context):
        """Erstellt den Prompt für das LLM, ähnlich zu oldfile.py build_prompt."""
        # Nimm nur top_n EPDs für den Kontext, falls die Liste sehr lang ist
        # Der ConfigManager stellt cfg.top_n bereit.
        epds_for_prompt_list = epds[:self.config_manager.top_n]

        lines = []
        for epd in epds_for_prompt_list:
            parts = [f"UUID: {epd['uuid']}", f"Name: {epd.get('name', 'N/A')}"]
            for col in columns_for_context:  # Nur die ausgewählten Kontextspalten
                value = epd.get(col)
                if value and col not in ('uuid', 'name'):  # uuid und name sind schon oben
                    parts.append(f"{col}: {str(value)[:150]}")  # Wert ggf. kürzen
            lines.append(" | ".join(parts))

        epd_context_str = "\n - ".join(lines) if lines else "Keine EPDs im direkten Kontext (Filter prüfen)."

        # Der System Prompt ist jetzt im LLMService, wir bauen nur den User-Teil
        # System Prompt aus LLMService:
        # "You are an assistant helping to match user requests to EPDs. "
        # "Respond ONLY with a valid JSON object. The object must contain "
        # "a key 'matches' which is a list of up to 3 match objects, each "
        # "with 'uuid', 'name' and 'begruendung'."

        prompt = f"""
Basierend auf der Benutzeranfrage und der folgenden Liste von EPDs (mit ihren jeweiligen UUIDs, Namen und relevanten Daten), identifiziere bitte bis zu 3 der passendsten EPDs.

Benutzeranfrage: "{user_input}"

--- Beginn VORGEFILTERTE EPD Liste ({len(epds_for_prompt_list)} Einträge) ---
 - {epd_context_str}
--- Ende VORGEFILTERTE EPD Liste ---

Bitte gib deine Antwort ausschließlich als JSON-Objekt zurück, das dem im System-Prompt beschriebenen Format entspricht (Schlüssel 'matches' mit einer Liste von Objekten, jedes mit 'uuid', 'name', 'begruendung').
"""
        return prompt

    def _execute_fuzzy_search(self, user_input, all_epds, context_columns):
        """Führt die Fuzzy-Suche aus."""
        # context_columns werden für Fuzzy-Suche verwendet, um den Suchtext pro EPD zu bauen
        try:
            # fuzzy_search(user_input, epds_list, columns_to_search_in, top_n_results, cutoff_score)
            # top_n hier aus config_manager, cutoff kann fest sein oder auch konfigurierbar
            # Die `context_columns` aus der UI sind die Spalten, die für den Suchtext relevant sind.
            # `name` sollte immer dabei sein.
            search_cols_for_fuzzy = list(set(['name'] + context_columns))

            # Die fuzzy_search Funktion erwartet eine Liste von Dicts (EPDs)
            # und eine Liste der Spaltennamen, die für den Suchtext pro EPD verwendet werden sollen.
            fuzzy_results = fuzzy_search(
                user_input=user_input,
                epds=all_epds,  # Alle vor-gefilterten EPDs
                columns=search_cols_for_fuzzy,  # Spalten für den Suchtext
                top_n=self.config_manager.top_n,  # Anzahl der gewünschten Top-Ergebnisse
                cutoff=0.4  # Mindest-Score
            )
            if self.loading_dialog: self.loading_dialog.close()

            if not fuzzy_results:
                QMessageBox.information(self, "Keine Fuzzy-Treffer",
                                        "Die Stichwortsuche hat keine passenden EPDs gefunden.")
                return

            self._populate_match_results(fuzzy_results, is_llm=False)

        except Exception as e:
            if self.loading_dialog: self.loading_dialog.close()
            QMessageBox.critical(self, "Fuzzy Search Fehler", f"Ein Fehler bei der Stichwortsuche ist aufgetreten: {e}")

    def _populate_match_results(self, results: list, is_llm: bool):
        """Füllt die RadioButton-Liste mit den Suchergebnissen."""
        self.clear_match_radio_buttons()

        if not results:
            self.match_area_layout.addWidget(QLabel("Keine Ergebnisse gefunden."))
            return

        for i, item in enumerate(results):
            uuid = item.get('uuid')
            name = item.get('name', 'N/A')

            if not uuid:  # Sicherheitshalber überspringen, falls ein Ergebnis keine UUID hat
                print(f"WARNUNG: Ergebnis ohne UUID übersprungen: {item}")
                continue

            # Hole Zusatzinfos wie Ref-Jahr, Gültigkeit, Owner aus der DB für die Anzeige
            # Dies könnte man optimieren, indem man diese Infos schon vorher holt oder EPDService eine Methode dafür hat
            display_text = f"{i + 1}. {name} ({uuid[:8]}…)"
            try:
                # epd_service.get_epd_summary(uuid) wäre ideal
                # Temporär: Direkter DB-Zugriff (sollte aber im EPDService sein)
                conn = self.epd_service.get_connection()  # Annahme: EPDService hat get_connection()
                cursor = conn.cursor()
                cursor.execute("SELECT ref_year, valid_until, owner FROM epds WHERE uuid = ?", (uuid,))
                row = cursor.fetchone()
                conn.close()
                if row:
                    ref_year, valid_until, owner = row['ref_year'], row['valid_until'], row['owner']
                    display_text = f"{i + 1}. {name} ({uuid[:8]}… | Ref: {ref_year or 'N/A'} | Bis: {valid_until or 'N/A'} | Owner: {owner or 'N/A'})"
            except Exception as db_err:
                print(f"Fehler beim Holen von Zusatzinfos für {uuid}: {db_err}")
                # display_text bleibt ohne Zusatzinfos

            if is_llm:
                reason = item.get('begruendung', 'Keine Begründung vom LLM.')
                display_text += f"\n   LLM-Begründung: {reason}"

            rb = QRadioButton(display_text)
            rb.setProperty("match_uuid", uuid)  # Speichere die volle UUID
            self.radio_group.addButton(rb)
            self.match_area_layout.addWidget(rb)
            self.radio_buttons.append(rb)

        if self.radio_buttons:
            self.confirm_btn.setEnabled(True)

    def on_confirm_selection(self):
        """Wird aufgerufen, wenn der "Details abrufen"-Button geklickt wird."""
        selected_button = self.radio_group.checkedButton()
        if selected_button:
            uuid = selected_button.property("match_uuid")
            if uuid:
                # Sende das Signal mit der UUID. MainWindow wird es an ResultsTab weiterleiten.
                self.match_selected.emit(uuid)
        else:
            QMessageBox.warning(self, "Auswahl fehlt", "Bitte wählen Sie zuerst eine EPD aus der Ergebnisliste aus.")

    # Slot für die Verbindung mit IfcAnalysisTab
    def handle_ifc_layers_for_search(self, layers_data: list):
        """
        Erstellt neue Tabs im self.layer_epd_search_tabs für jede übergebene Schicht.
        layers_data ist eine Liste von Dictionaries, jedes Dict repräsentiert eine Schicht.
        Jedes Schicht-Dict sollte mindestens 'name' und optional andere relevante Infos enthalten.
        """
        if not layers_data:
            return

        # Bestehende dynamische Schicht-Tabs entfernen (außer "Manuelle Suche")
        # Gehe rückwärts durch die Tabs, um Indexprobleme beim Entfernen zu vermeiden
        for i in range(self.layer_epd_search_tabs.count() - 1, 0, -1):
            # Prüfe, ob der Tab-Titel zu einem der aktiven Layer-Widgets gehört, um ihn sicher zu entfernen
            # oder einfach alle außer dem ersten entfernen.
            # Hier vereinfacht: Alle Tabs außer dem ersten (Manuelle Suche) entfernen.
            tab_title_to_remove = self.layer_epd_search_tabs.tabText(i)
            if tab_title_to_remove != "Manuelle Suche":
                self.layer_epd_search_tabs.removeTab(i)
                # Entferne auch das zugehörige Widget-Info aus der Tracking-Liste
                self.active_layer_search_widgets = [
                    info for info in self.active_layer_search_widgets if info.get('tab_title') != tab_title_to_remove
                ]

        first_new_tab_index = -1

        for idx, layer_data in enumerate(layers_data):
            layer_name = layer_data.get('name', f'Unbenannte Schicht {idx + 1}')
            # Eindeutiger Tab-Titel, falls Namen nicht eindeutig sind
            tab_title = f"IFC Layer: {layer_name[:30]}{'...' if len(layer_name) > 30 else ''} ({layer_data.get('guid', 'N/A')[:8]})"

            layer_tab_content = QWidget()
            layer_tab_layout = QVBoxLayout(layer_tab_content)

            # Eingabefeld für diese spezifische Schicht
            layer_input_box = QTextEdit()
            layer_input_box.setPlainText(layer_name)  # Name der Schicht als Standard-Suchbegriff
            layer_input_box.setPlaceholderText(f"Suchbegriff für EPDs zu '{layer_name}' eingeben oder anpassen.")
            layer_input_box.setFixedHeight(80)
            layer_tab_layout.addWidget(layer_input_box)

            # Optional: Weitere Infos zur Schicht anzeigen
            # info_text = f"GUID: {layer_data.get('guid', 'N/A')}\n" \
            #             f"Dicke: {layer_data.get('thickness_global_bbox', 0.0):.3f}m"
            # layer_info_label = QLabel(info_text)
            # layer_tab_layout.addWidget(layer_info_label)

            layer_tab_content.setLayout(layer_tab_layout)

            current_tab_index = self.layer_epd_search_tabs.addTab(layer_tab_content, tab_title)
            if first_new_tab_index == -1:
                first_new_tab_index = current_tab_index

            self.active_layer_search_widgets.append({
                'tab_title': tab_title,  # Wichtig für die Identifizierung
                'original_name': layer_name,
                'data': layer_data,  # Das komplette Layer-Dict
                'input_widget': layer_input_box,  # Das QTextEdit-Widget
                'tab_index': current_tab_index
            })

        if first_new_tab_index != -1:
            self.layer_epd_search_tabs.setCurrentIndex(first_new_tab_index)
            QMessageBox.information(self, "IFC Layer übernommen",
                                    f"{len(layers_data)} Layer wurden als Such-Tabs hinzugefügt.")

# Ende von src/ui/widgets/epd_matcher_tab.py