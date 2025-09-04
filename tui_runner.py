import re
from textual.app import App, ComposeResult
from textual.containers import VerticalScroll, Vertical, Horizontal
from textual.widgets import DataTable, Header, Footer, Button, Input, Label, Static, TextArea, Rule

class FormRunner:
    def __init__(self, form_def, initial_data=None, nav_info=None, view_mode=None):
        self.form_def = form_def
        self.initial_data = initial_data or {}
        self.nav_info = nav_info or {}
        self.view_mode = view_mode  # Add this parameter
        self.results = {}

    def run(self):
        """
        Checks the form definition and launches the appropriate screen (dispatcher logic).
        """
        # Use the explicit view_mode if provided, otherwise fall back to form definition
        if self.view_mode == 'grid':
            app = _ListScreen(self.form_def, self.initial_data, self.results)
        elif self.view_mode == 'single':
            app = _EntryScreen(self.form_def, self.initial_data, self.results, self.nav_info)
        else:
            # Original logic as fallback
            if self.form_def.get("display_rows", 1) > 1:
                app = _ListScreen(self.form_def, self.initial_data, self.results)
            else:
                app = _EntryScreen(self.form_def, self.initial_data, self.results, self.nav_info)
        
        app.run()
        return self.results

# This is the original _FormScreen, renamed and updated for initial data
class _EntryScreen(App):
    """A TUI screen for single-record entry forms with validation and navigation."""

    CSS = """
    #form-container {
        padding: 1 2;
        height: auto;
    }
    #error-message {
        height: auto;
        padding: 0 1;
        background: $error;
        color: $text;
        display: none;
    }
    .form-field {
        margin-bottom: 1;
        height: 4;
    }
    .field-label {
        text-style: bold;
        margin-bottom: 0;
    }
    .heading {
        padding: 1 0;
        text-style: bold;
        text-align: center;
    }
    .textblock {
        margin-bottom: 1;
        color: $text-muted;
    }
    #nav-container {
        align: center middle;
        padding: 1 0;
    }
    #button-container {
        align: center middle;
        padding: 1 0;
    }
    Input.-invalid {
        border: thick $error;
    }
    """

    def __init__(self, form_def, initial_data, result_dict, nav_info):
        super().__init__()
        self.form_def = form_def
        self.initial_data = initial_data
        self.result_dict = result_dict
        self.nav_info = nav_info
        self.widget_map = {}
        print(f"DEBUG: EntryScreen created with initial_data: {initial_data}")
        print(f"DEBUG: EntryScreen nav_info: {nav_info}")
        print(f"DEBUG: EntryScreen buttons: {form_def.get('buttons', [])}")

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static(id="error-message")

        with VerticalScroll(id="form-container"):
            title = self.form_def.get("title", self.form_def["name"])
            yield Label(title, classes="heading")

            has_defined_fields = any(e.get("type") == "FIELD" for e in self.form_def.get("elements", []))

            if has_defined_fields:
                # Render user-defined layout
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
                            
                            if element["field_type"] == "MEMO":
                                yield TextArea(
                                    text=str(self.initial_data.get(field_name, "")),
                                    id=widget_id,
                                    disabled=is_readonly
                                )
                            else:
                                yield Input(
                                    value=str(self.initial_data.get(field_name, "")),
                                    id=widget_id,
                                    password=(element["field_type"] == "PASSWORD"),
                                    disabled=is_readonly
                                )
            elif self.initial_data:
                # Auto-generate layout with better formatting
                for field_name, value in self.initial_data.items():
                    widget_id = f"field_{field_name}"
                    self.widget_map[field_name] = widget_id
                    with Vertical(classes="form-field"):
                        yield Label(f"{field_name.title()}:", classes="field-label")
                        yield Input(
                            value=str(value),
                            id=widget_id,
                            disabled=(field_name.lower() == 'id')
                        )

        # Navigation section
        if any(self.nav_info.get(key) for key in ["has_prev", "has_next"]):
            with Horizontal(id="nav-container"):
                yield Button("◄◄ First", id="FIRST_RECORD", disabled=not self.nav_info.get("has_prev"))
                yield Button("◄ Prev", id="PREV_RECORD", disabled=not self.nav_info.get("has_prev"))
                yield Button("Next ►", id="NEXT_RECORD", disabled=not self.nav_info.get("has_next"))
                yield Button("Last ►►", id="LAST_RECORD", disabled=not self.nav_info.get("has_next"))

        # Action buttons
        with Horizontal(id="button-container"):
            for button in self.form_def.get("buttons", []):
                button_id = button["name"].lower().replace(" ", "_").replace('"', "")
                yield Button(button["name"], id=button_id)
        
        yield Footer()

    def _validate_form(self) -> bool:
        """Runs all validation rules and returns True if the form is valid."""
        error_widget = self.query_one("#error-message")
        field_elements = [e for e in self.form_def.get("elements", []) if e.get("type") == "FIELD"]

        for element in field_elements:
            field_name = element["name"]
            widget = self.query_one(f"#{self.widget_map[field_name]}")
            value = widget.value if isinstance(widget, Input) else widget.text
            validations = element.get("validations", {})

            if "required" in validations and not value.strip():
                error_widget.update(validations["required"]["message"])
                error_widget.styles.display = "block"
                return False

            if not value: continue

            if "minlength" in validations and len(value) < validations["minlength"]["value"]:
                error_widget.update(validations["minlength"]["message"])
                error_widget.styles.display = "block"
                return False

            if "maxlength" in validations and len(value) > validations["maxlength"]["value"]:
                error_widget.update(validations["maxlength"]["message"])
                error_widget.styles.display = "block"
                return False

            if "minvalue" in validations:
                try:
                    if float(value) < validations["minvalue"]["value"]:
                        error_widget.update(validations["minvalue"]["message"])
                        error_widget.styles.display = "block"
                        return False
                except (ValueError, TypeError):
                    error_widget.update(f"{element['label']} must be a number.")
                    error_widget.styles.display = "block"
                    return False

            if "pattern" in validations and not re.match(validations["pattern"]["value"], value):
                error_widget.update(validations["pattern"]["message"])
                error_widget.styles.display = "block"
                return False

            if "matches" in validations:
                other_field_name = validations["matches"]["value"]
                other_widget = self.query_one(f"#{self.widget_map[other_field_name]}")
                other_value = other_widget.value if isinstance(other_widget, Input) else other_widget.text
                if value != other_value:
                    error_widget.update(validations["matches"]["message"])
                    error_widget.styles.display = "block"
                    return False
        
        error_widget.styles.display = "none"
        return True

    def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id
        
        if button_id in ["FIRST_RECORD", "PREV_RECORD", "NEXT_RECORD", "LAST_RECORD"]:
            self.result_dict["action"] = button_id
            self.exit()
            return

        button_def = next((b for b in self.form_def["buttons"] if b["name"].lower().replace(" ", "_").replace('"', "") == button_id), None)
        if button_def:
            action = button_def.get("action")
            if action in ["SUBMIT", "INSERT", "UPDATE"]:
                if not self._validate_form():
                    return

            self.result_dict["action"] = action
            data = {}
            for field_name, widget_id in self.widget_map.items():
                widget = self.query_one(f"#{widget_id}")
                data[field_name] = widget.value if isinstance(widget, Input) else widget.text
            self.result_dict["data"] = data
            if "id" in self.initial_data:
                self.result_dict["id"] = self.initial_data["id"]
        
        self.exit()
        

class _ListScreen(App):
    """A TUI screen for displaying data grids."""

    def __init__(self, form_def, initial_data, result_dict):
        super().__init__()
        self.form_def = form_def
        self.initial_data = initial_data
        self.result_dict = result_dict
        self.selected_row_index = 0  # Track selection manually

    def compose(self) -> ComposeResult:
        """Create the child widgets for the grid view."""
        yield Header()
        yield DataTable(id="data-table")
        with Horizontal(id="button-container"):
             for button in self.form_def.get("buttons", []):
                button_id = button["name"].lower().replace(" ", "_").replace('"', "")
                yield Button(button["name"], id=button_id)
        yield Footer()

    def on_mount(self) -> None:
        """Called when the app is first mounted to populate the table."""
        table = self.query_one(DataTable)
        rows = self.initial_data.get("rows", [])
        
        has_defined_fields = any(e.get("type") == "FIELD" for e in self.form_def.get("elements", []))
        headers = []
        if has_defined_fields:
            for element in self.form_def.get("elements", []):
                if element.get("type") == "FIELD":
                    headers.append(element.get("label", element["name"]))
        else:
            headers = self.initial_data.get("headers", [])
        
        if headers:
            table.add_columns(*headers)
        if rows:
            # Ensure all rows have the same number of columns as headers
            filtered_rows = []
            for row in rows:
                if len(row) >= len(headers):
                    filtered_rows.append(row[:len(headers)])
                else:
                    # Pad short rows with empty strings
                    padded_row = list(row) + [''] * (len(headers) - len(row))
                    filtered_rows.append(padded_row)
            
            if filtered_rows:
                table.add_rows(filtered_rows)

    def on_data_table_row_selected(self, event) -> None:
        """Track which row is selected when user clicks on it."""
        try:
            table = self.query_one(DataTable)
            self.selected_row_index = table.get_row_index(event.row_key)
        except Exception:
            self.selected_row_index = 0

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events."""
        button_id = event.button.id
        print(f"DEBUG: Button pressed with ID: '{button_id}'")
        
        button_def = next((
            b for b in self.form_def["buttons"] 
            if b["name"].lower().replace(" ", "_").replace('"', "") == button_id
        ), None)
        
        print(f"DEBUG: Found button_def: {button_def}")

        if button_def:
            action = button_def.get("action")
            print(f"DEBUG: Action from button_def: '{action}'")
            self.result_dict["action"] = action
            
            # Use our manually tracked selection instead of cursor
            rows = self.initial_data.get("rows", [])
            if rows and 0 <= self.selected_row_index < len(rows):
                row_data = rows[self.selected_row_index]
                original_headers = self.initial_data.get("headers", [])
                if original_headers and len(row_data) >= len(original_headers):
                    row_dict = dict(zip(original_headers, row_data))
                    self.result_dict["selected_id"] = row_dict.get("id")
                    print(f"DEBUG: Selected ID: {self.result_dict.get('selected_id')}")

            if action == "OPENFORM" and button_def.get("args"):
                self.result_dict["target_form"] = button_def["args"][0]
        else:
            print(f"DEBUG: No button definition found for ID '{button_id}'")
            print(f"DEBUG: Available buttons: {self.form_def.get('buttons', [])}")

        print(f"DEBUG: Final result_dict: {self.result_dict}")
        self.exit()