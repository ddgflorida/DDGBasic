import re
from textual.app import App, ComposeResult
from textual.containers import VerticalScroll, Vertical, Horizontal
from textual.widgets import DataTable, Header, Footer, Button, Input, Label, Static, TextArea, Rule, Select

class FormRunner:
    def __init__(self, form_def, initial_data=None, nav_info=None, view_mode=None, pk_column_name='id', search_config=None, current_search_term=""):
        self.form_def = form_def
        self.initial_data = initial_data or {}
        self.nav_info = nav_info or {}
        self.view_mode = view_mode
        self.pk_column_name = pk_column_name
        self.results = {}
        # Add these new attributes to store the search info
        self.search_config = search_config or {'enabled': False}
        self.current_search_term = current_search_term

    def run(self):
        app = None
        if self.view_mode == 'grid':
            app = _ListScreen(
                self.form_def, self.initial_data, self.results, 
                self.pk_column_name, self.search_config, self.current_search_term
            )
        elif self.view_mode == 'single':
            app = _EntryScreen(
                self.form_def, self.initial_data, self.results, 
                self.nav_info, self.pk_column_name
            )
        else:
            if self.form_def.get("display_rows", 1) > 1:
                app = _ListScreen(
                    self.form_def, self.initial_data, self.results, 
                    self.pk_column_name, self.search_config, self.current_search_term
                )
            else:
                app = _EntryScreen(
                    self.form_def, self.initial_data, self.results, 
                    self.nav_info, self.pk_column_name
                )
        
        try:
            if app:
                app.run()
        except Exception as e:
            print("\n--- TUI RUNTIME ERROR ---")
            print(f"An error occurred while trying to launch the form screen: {e}")
            import traceback
            traceback.print_exc()
            print("-------------------------\n")
            
        return self.results

# This is the original _FormScreen, renamed and updated for initial data
class _EntryScreen(App):
    """A TUI screen for single-record entry forms with validation and navigation."""
    CSS = """
    Screen { background: $surface; }
    #form-container { padding: 1 2; height: auto; }
    #error-message { height: auto; padding: 1 2; background: $error; color: $text; text-style: bold; display: none; }
    .form-field { margin-bottom: 1; height: auto; }
    .field-label { text-style: bold; color: $accent; margin-bottom: 0; height: 1; }
    .heading { padding: 0; text-style: bold; text-align: center; color: $primary; margin-bottom: 1; height: auto; }
    .textblock { margin-bottom: 1; padding: 1; color: $text-muted; background: $surface-lighten-1; border: solid $surface-lighten-2; text-style: italic; }
    #nav-container { align: center middle; padding: 1; margin: 1 0; background: $surface-lighten-1; border: solid $accent; }
    #button-container { align: center middle; padding: 1; margin: 1 0; background: $surface-lighten-1; border: solid $accent; height: auto; min-height: 5; }
    Input { height: 3; border: solid $surface-lighten-2; background: $surface; padding: 0 1; margin-top: 0; }
    Input:focus { border: solid $primary; background: $surface-lighten-1; }
    Input.-invalid { border: thick $error; background: $error 10%; }
    Input:disabled { background: $surface-darken-1; color: $text-muted; }
    TextArea { height: 6; border: solid $surface-lighten-2; background: $surface; padding: 1; margin-top: 0; }
    TextArea:focus { border: solid $primary; background: $surface-lighten-1; }
    TextArea:disabled { background: $surface-darken-1; color: $text-muted; }
    Button { margin: 0 1; height: 3; min-width: 10; border: solid $accent; background: $primary; color: $surface; text-style: bold; content-align: center middle; }
    Button:hover { background: $accent; border: solid $primary; }
    Button:disabled { background: $surface-darken-1; color: $text-muted; border: solid $surface-lighten-1; }
    Button.-neutral { background: $surface-lighten-2; color: $text; border: solid $surface-lighten-3; }
    Button.-neutral:hover { background: $surface-lighten-3; border: solid $accent; }
    Button.-success { background: $success; color: $surface; border: solid $success; }
    Button.-success:hover { background: $success-lighten-1; border: solid $success; }
    Rule { margin: 1 0; color: $accent; }
    .lookup-field { layout: horizontal; height: auto; }
    .lookup-field Input { width: 1fr; }
    .lookup-button { min-width: 5; width: 5; margin-left: 1; height: 3; }
    .-hidden { display: none; }
    """

    def __init__(self, form_def, initial_data, result_dict, nav_info, pk_column_name):
        super().__init__()
        self.form_def = form_def
        self.initial_data = initial_data
        self.result_dict = result_dict
        self.nav_info = nav_info
        self.pk_column_name = pk_column_name
        self.widget_map = {}
        
        form_title = self.form_def.get("title", self.form_def.get("name", "Data Entry"))
        self.title = f"Entry View: {form_title}"

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static(id="error-message")

        with VerticalScroll(id="form-container"):
            has_defined_fields = any(e.get("type") == "FIELD" for e in self.form_def.get("elements", []))

            if has_defined_fields:
                for element in self.form_def.get("elements", []):
                    if element["type"] == "HEADING":
                        yield Label(element["text"], classes="heading")
                    elif element["type"] == "TEXTBLOCK":
                        yield Label(element["text"], classes="textblock")
                    elif element["type"] == "SEPARATOR":
                        yield Rule()
                    elif element["type"] == "FIELD":
                        field_name = element["name"]
                        widget_id = f"field_{field_name}"
                        self.widget_map[field_name] = widget_id
                        
                        with Vertical(classes="form-field"):
                            yield Label(f"{element['label']}:", classes="field-label")
                            is_readonly = element.get("readonly", False)
                            initial_value = self.initial_data.get(field_name)
                            lookup_config = element.get("lookup")

                            if lookup_config:
                                display_field = lookup_config.get("display")
                                display_widget_id = f"display_{field_name}"
                                display_value = self.initial_data.get(display_field, "")
                                if not display_value and initial_value:
                                    display_value = f"<{initial_value}>"

                                with Horizontal(classes="lookup-field"):
                                    yield Input(value=str(display_value), id=display_widget_id, disabled=True)
                                    yield Button("[...]", id=f"lookup_{field_name}", classes="lookup-button")
                                
                                yield Input(value=str(initial_value or ""), id=widget_id, classes="-hidden")

                            elif element.get("field_type") == "CHOICE":
                                choices = element.get("choices", [])
                                options = [(str(item), item) for item in choices]
                                if initial_value is not None and initial_value in choices:
                                    yield Select(options, value=initial_value, id=widget_id, disabled=is_readonly)
                                else:
                                    yield Select(options, id=widget_id, disabled=is_readonly)
                            
                            elif element.get("field_type") == "MEMO":
                                yield TextArea(text=str(initial_value or ""), id=widget_id, disabled=is_readonly)
                            
                            else: # Standard Input
                                yield Input(
                                    value=str(initial_value or ""),
                                    id=widget_id,
                                    password=(element.get("field_type") == "PASSWORD"),
                                    disabled=is_readonly
                                )
            elif self.initial_data:
                for field_name, value in self.initial_data.items():
                    widget_id = f"field_{field_name}"
                    self.widget_map[field_name] = widget_id
                    with Vertical(classes="form-field"):
                        yield Label(f"{field_name.title()}:", classes="field-label")
                        yield Input(value=str(value or ""), id=widget_id, disabled=(field_name.lower() == 'id'))

        if any(self.nav_info.get(key) for key in ["has_prev", "has_next"]):
            with Horizontal(id="nav-container"):
                yield Button("◄◄ First", id="FIRST_RECORD", disabled=not self.nav_info.get("has_prev"))
                yield Button("◄ Prev", id="PREV_RECORD", disabled=not self.nav_info.get("has_prev"))
                yield Button("Next ►", id="NEXT_RECORD", disabled=not self.nav_info.get("has_next"))
                yield Button("Last ►►", id="LAST_RECORD", disabled=not self.nav_info.get("has_next"))

        contextual_buttons = self._get_contextual_buttons('single')

        with Horizontal(id="button-container"):
            for button in contextual_buttons:
                safe_name = re.sub(r'[^a-zA-Z0-9_ -]', '', button["name"])
                button_id = safe_name.lower().replace(" ", "_")
                action = button.get("action", "").upper()
                css_classes = ["-success" if action in ["SAVE", "UPDATE", "SUBMIT"] else "-neutral" if action in ["CANCEL", "CLOSE", "VIEW_GRID"] else ""]
                yield Button(button["name"], id=button_id, classes=" ".join(css_classes))
        
        yield Footer()

    def _get_form_data(self) -> dict:
        data = {}
        for field_name, widget_id in self.widget_map.items():
            try:
                widget = self.query_one(f"#{widget_id}")
                if isinstance(widget, Select): data[field_name] = widget.value
                elif isinstance(widget, TextArea): data[field_name] = widget.text
                else: data[field_name] = widget.value
            except Exception:
                data[field_name] = self.initial_data.get(field_name)
        return data

    def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = str(event.button.id)

        if button_id.startswith("lookup_"):
            field_name = button_id.replace("lookup_", "")
            self.result_dict["action"] = "RUN_LOOKUP"
            self.result_dict["lookup_field"] = field_name
            self.result_dict["data"] = self._get_form_data() # Save current state
            self.exit()
            return

        if button_id in ["FIRST_RECORD", "PREV_RECORD", "NEXT_RECORD", "LAST_RECORD"]:
            self.result_dict["action"] = button_id
            self.exit()
            return
        
        print("\n--- TUI DEBUG: on_button_pressed in _EntryScreen ---")
        print(f"Button ID from click event: '{button_id}'")

        button_def = None
        for b in self.form_def.get("buttons", []):
            # This is the sanitizing logic from your version of the code
            sanitized_name = re.sub(r'[^a-zA-Z0-9_]', '', b["name"].lower().replace(" ", "_"))
            
            print(f"Comparing with form button '{b['name']}', sanitized to '{sanitized_name}'")
            
            if sanitized_name == button_id:
                button_def = b
                print(f"MATCH FOUND! Action is '{button_def.get('action')}'")
                break
        
        if not button_def:
            print("MATCH NOT FOUND! The button's action will not be set.")
        print("---------------------------------------------------\n")

        button_def = None
        for b in self.form_def.get("buttons", []):
            # This is the sanitizing logic from your version of the code
            sanitized_name = re.sub(r'[^a-zA-Z0-9_]', '', b["name"].lower().replace(" ", "_"))
            
            print(f"Comparing with form button '{b['name']}', sanitized to '{sanitized_name}'")
            
            if sanitized_name == button_id:
                button_def = b
                print(f"MATCH FOUND! Action is '{button_def.get('action')}'")
                break
        if button_def:
            action = button_def.get("action")
            if action in ["SUBMIT", "INSERT", "UPDATE"]:
                if not self._validate_form(): return

            self.result_dict["action"] = action
            self.result_dict["data"] = self._get_form_data()
            
            pk_value = None
            for key, value in self.initial_data.items():
                if key.lower() == self.pk_column_name.lower(): pk_value = value; break
            self.result_dict["pk"] = pk_value
        
        self.exit()
    
    def _validate_form(self) -> bool:
        error_widget = self.query_one("#error-message")
        field_elements = [e for e in self.form_def.get("elements", []) if e.get("type") == "FIELD"]

        for element in field_elements:
            field_name = element["name"]
            widget = self.query_one(f"#{self.widget_map[field_name]}")
            value = ""
            if isinstance(widget, Select): value = widget.value
            elif isinstance(widget, TextArea): value = widget.text
            else: value = widget.value
            validations = element.get("validations", {})

            if "required" in validations and not str(value).strip():
                error_widget.update(validations["required"]["message"]); error_widget.styles.display = "block"; return False
            if not value: continue
            if "minlength" in validations and len(str(value)) < validations["minlength"]["value"]:
                error_widget.update(validations["minlength"]["message"]); error_widget.styles.display = "block"; return False
            if "maxlength" in validations and len(str(value)) > validations["maxlength"]["value"]:
                error_widget.update(validations["maxlength"]["message"]); error_widget.styles.display = "block"; return False
            if "minvalue" in validations:
                try:
                    if float(value) < validations["minvalue"]["value"]:
                        error_widget.update(validations["minvalue"]["message"]); error_widget.styles.display = "block"; return False
                except (ValueError, TypeError):
                    error_widget.update(f"{element['label']} must be a number."); error_widget.styles.display = "block"; return False
            if "pattern" in validations and not re.match(validations["pattern"]["value"], str(value)):
                error_widget.update(validations["pattern"]["message"]); error_widget.styles.display = "block"; return False
            if "matches" in validations:
                other_field_name = validations["matches"]["value"]
                other_widget = self.query_one(f"#{self.widget_map[other_field_name]}")
                other_value = other_widget.value if isinstance(other_widget, Input) else other_widget.text
                if value != other_value:
                    error_widget.update(validations["matches"]["message"]); error_widget.styles.display = "block"; return False
        
        error_widget.styles.display = "none"
        return True
    
    def _get_contextual_buttons(self, current_view_mode):
        buttons = self.form_def.get("buttons", [])
        contextual_buttons = []
        for button in buttons:
            action = button.get("action", "").upper()
            button_added = False
            if action in ['CLOSE', 'EXIT', 'HELP']:
                contextual_buttons.append(button); button_added = True
            if not button_added:
                if current_view_mode == 'grid':
                    if action in ['VIEW_SINGLE', 'EDIT', 'NEW', 'DELETE', 'REFRESH', 'EDIT_DETAILS', 'SELECT']:
                        contextual_buttons.append(button)
                elif current_view_mode == 'single':
                    if action in ['VIEW_GRID', 'UPDATE', 'SAVE', 'SUBMIT', 'CANCEL', 'DELETE', 'BACK_TO_GRID']:
                        contextual_buttons.append(button)
        return contextual_buttons    

class _ListScreen(App):
    """A TUI screen for displaying data grids."""
    CSS = """
        Screen { background: $surface; }
        .header-info { height: 1; margin: 0; padding: 0 1; background: $primary; color: $text; border: solid $accent; }
        .controls { height: auto; min-height: 5; margin: 0; padding: 1; background: $surface-lighten-1; border: solid $accent; align: center middle; }
        .prompt-text { text-style: bold; color: $accent; margin: 0 1 0 0; width: auto; }
        #search-input { width: 1fr; }
        DataTable { margin: 0; border: solid $accent; height: 1fr; }
        Input { margin: 0 1; height: 3; border: solid $accent; background: $surface; }
        Input:focus { border: solid $primary; background: $surface-lighten-1; }
        Button { margin: 0 1; height: 3; min-width: 10; color: auto !important; text-style: bold; }
        Button:hover { text-style: bold reverse; }
        #button-container { align: center middle; padding: 1; margin: 1 0; background: $surface-lighten-1; border: solid $accent; height: auto; min-height: 5; }
    """

    def __init__(self, form_def, initial_data, result_dict, pk_column_name, search_config, current_search_term):
        super().__init__()
        self.form_def = form_def
        self.initial_data = initial_data
        self.result_dict = result_dict
        self.pk_column_name = pk_column_name
        self.search_config = search_config
        self.current_search_term = current_search_term

        form_title = self.form_def.get("name", "Data Grid")
        heading_element = next((el for el in self.form_def.get("elements", []) if el.get("type") == "HEADING"), None)
        if heading_element: form_title = heading_element.get("text", form_title)
        
        record_count = len(self.initial_data.get("rows", []))
        self.title = f"List View: {form_title} ({record_count} records)"

    def compose(self) -> ComposeResult:
        yield Header()
        
        if self.search_config.get('enabled'):
            with Horizontal(classes="controls"):
                yield Label("Search:", classes="prompt-text")
                yield Input(id="search-input", value=self.current_search_term, placeholder="Type and press Enter...")
        
        yield DataTable(id="data-table")
        
        contextual_buttons = self._get_contextual_buttons('grid')
        with Horizontal(id="button-container"):
             for button in contextual_buttons:
                button_id = button["name"].lower().replace(" ", "_").replace('"', "")
                yield Button(button["name"], id=button_id)
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one(DataTable)
        all_rows = self.initial_data.get("rows", [])
        source_headers = self.initial_data.get("headers", [])
        if not source_headers: return

        has_defined_fields = any(e.get("type") == "FIELD" for e in self.form_def.get("elements", []))
        display_headers_for_ui, field_names_from_source = [], []
        
        if has_defined_fields:
            source_header_map = {header.lower(): header for header in source_headers}
            for element in self.form_def.get("elements", []):
                if element.get("type") == "FIELD":
                    field_name = element["name"]
                    if field_name.lower() in source_header_map:
                        display_headers_for_ui.append(element.get("label", element["name"]))
                        field_names_from_source.append(source_header_map[field_name.lower()])
        else:
            display_headers_for_ui = [h for h in source_headers if h.lower() != 'rowid']
            field_names_from_source = [h for h in source_headers if h.lower() != 'rowid']

        if not display_headers_for_ui: return

        try:
            source_header_map = {header_name.lower(): i for i, header_name in enumerate(source_headers)}
            display_indices = [source_header_map[field_name.lower()] for field_name in field_names_from_source]
        except KeyError as e:
            self.exit(f"Form Error: FIELD '{e.args[0]}' not found in SOURCE query columns.")
            return

        display_rows = [[row[i] for i in display_indices] for row in all_rows]
        table.add_columns(*display_headers_for_ui)
        if display_rows: table.add_rows(display_rows)

        if self.search_config.get('enabled'):
            self.query_one("#search-input").focus()
        else:
            table.focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle the user pressing Enter in the search input."""
        if event.input.id == "search-input":
            self.result_dict["action"] = "SEARCH"
            self.result_dict["search_term"] = event.value
            self.exit()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if self.search_config.get('enabled'):
            self.result_dict["search_term"] = self.query_one("#search-input").value
        
        button_id = event.button.id
        button_def = next((b for b in self.form_def.get("buttons", []) if re.sub(r'[^a-zA-Z0-9_]', '', b["name"].lower().replace(" ", "_")) == button_id), None)

        if button_def:
            self.result_dict["action"] = button_def.get("action")
            table = self.query_one(DataTable)
            selected_row_index = table.cursor_row
            rows = self.initial_data.get("rows", [])
            original_headers = self.initial_data.get("headers", [])
            
            if rows and selected_row_index is not None and 0 <= selected_row_index < len(rows):
                row_data = rows[selected_row_index]
                if original_headers:
                    row_dict = dict(zip(original_headers, row_data))
                    pk_value = None
                    for key, value in row_dict.items():
                        if key.lower() == self.pk_column_name.lower():
                            pk_value = value
                            break
                    if pk_value is None and row_data: pk_value = row_data[0]
                    self.result_dict["selected_id"] = pk_value
        self.exit()

    def _get_contextual_buttons(self, current_view_mode):
        buttons = self.form_def.get("buttons", [])
        contextual_buttons = []
        for button in buttons:
            action = button.get("action", "").upper()
            button_added = False
            if action in ['CLOSE', 'EXIT', 'HELP']:
                contextual_buttons.append(button); button_added = True
            if not button_added:
                if current_view_mode == 'grid':
                    if action in ['VIEW_SINGLE', 'EDIT', 'NEW', 'DELETE', 'REFRESH', 'EDIT_DETAILS', 'SELECT']:
                        contextual_buttons.append(button)
                elif current_view_mode == 'single':
                    if action in ['VIEW_GRID', 'UPDATE', 'SAVE', 'CANCEL', 'DELETE', 'BACK_TO_GRID']:
                        contextual_buttons.append(button)
        return contextual_buttons
