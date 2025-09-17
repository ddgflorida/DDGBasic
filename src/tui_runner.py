import re
from textual.app import App, ComposeResult
from textual.containers import VerticalScroll, Vertical, Horizontal
from textual.widgets import DataTable, Header, Footer, Button, Input, Label, Static, TextArea, Rule, Select

class FormRunner:
    def __init__(self, form_def, initial_data=None, nav_info=None, view_mode=None, pk_column_name='id'):
        self.form_def = form_def
        self.initial_data = initial_data or {}
        self.nav_info = nav_info or {}
        self.view_mode = view_mode  # Add this parameter
        self.pk_column_name = pk_column_name
        self.results = {}

    def run(self):
        """
        Checks the form definition and launches the appropriate screen (dispatcher logic).
        """
        # Use the explicit view_mode if provided, otherwise fall back to form definition
        if self.view_mode == 'grid':
            # Add self.pk_column_name to the call
            app = _ListScreen(self.form_def, self.initial_data, self.results, self.pk_column_name)
        elif self.view_mode == 'single':
            # Add self.pk_column_name to the call
            app = _EntryScreen(self.form_def, self.initial_data, self.results, self.nav_info, self.pk_column_name)
        else:
            # Original logic as fallback
            if self.form_def.get("display_rows", 1) > 1:
                # Add self.pk_column_name to the call
                app = _ListScreen(self.form_def, self.initial_data, self.results, self.pk_column_name)
            else:
                # Add self.pk_column_name to the call
                app = _EntryScreen(self.form_def, self.initial_data, self.results, self.nav_info, self.pk_column_name)
        
        app.run()
        return self.results

# This is the original _FormScreen, renamed and updated for initial data
class _EntryScreen(App):
    """A TUI screen for single-record entry forms with validation and navigation."""
    CSS = """
    Screen {
        background: $surface;
    }

    #form-container {
        padding: 1 2;
        height: auto;
    }

    #error-message {
        height: auto;
        padding: 1 2;
        background: $error;
        color: $text;
        text-style: bold;
        display: none;
    }

    .form-field {
        margin-bottom: 1;
        height: auto;
    }

    .field-label {
        text-style: bold;
        color: $accent;
        margin-bottom: 0;
        height: 1;
    }

    .heading {
        padding: 0;
        text-style: bold;
        text-align: center;
        color: $primary;
        margin-bottom: 1;
        height: auto;
    }

    .textblock {
        margin-bottom: 1;
        padding: 1;
        color: $text-muted;
        background: $surface-lighten-1;
        border: solid $surface-lighten-2;
        text-style: italic;
    }

    #nav-container {
        align: center middle;
        padding: 1;
        margin: 1 0;
        background: $surface-lighten-1;
        border: solid $accent;
    }

    #button-container {
        align: center middle;
        padding: 1;
        margin: 1 0;
        background: $warning;
        border: solid $accent;
        height: auto;
        min-height: 5;
    }

    Input {
        height: 3;
        border: solid $surface-lighten-2;
        background: $surface;
        padding: 0 1;
        margin-top: 0;
    }

    Input:focus {
        border: solid $primary;
        background: $surface-lighten-1;
    }

    Input.-invalid {
        border: thick $error;
        background: $error 10%;
    }

    Input:disabled {
        background: $surface-darken-1;
        color: $text-muted;
    }

    TextArea {
        height: 6;
        border: solid $surface-lighten-2;
        background: $surface;
        padding: 1;
        margin-top: 0;
    }

    TextArea:focus {
        border: solid $primary;
        background: $surface-lighten-1;
    }

    TextArea:disabled {
        background: $surface-darken-1;
        color: $text-muted;
    }

    Button {
        margin: 0 1;
        height: 3;
        min-width: 10;
        border: solid $accent;
        background: $primary;
        color: $surface;
        text-style: bold;
        content-align: center middle;
    }

    Button:hover {
        background: $accent;
        border: solid $primary;
    }

    Button:disabled {
        background: $surface-darken-1;
        color: $text-muted;
        border: solid $surface-lighten-1;
    }

    Rule {
        margin: 1 0;
        color: $accent;
    }
    """

    def __init__(self, form_def, initial_data, result_dict, nav_info, pk_column_name):
        super().__init__()
        self.form_def = form_def
        self.initial_data = initial_data
        self.result_dict = result_dict
        self.nav_info = nav_info
        self.pk_column_name = pk_column_name
        self.widget_map = {}
        
        # This is the corrected title logic
        form_title = self.form_def.get("name", "Data Entry")
        heading_element = next((el for el in self.form_def.get("elements", []) if el.get("type") == "HEADING"), None)
        form_title = self.form_def.get("title", self.form_def.get("name", "Data Entry"))
        self.title = f"Entry View: {form_title}"
        print(f"DEBUG: EntryScreen created with initial_data: {initial_data}")
        print(f"DEBUG: EntryScreen nav_info: {nav_info}")
        print(f"DEBUG: EntryScreen buttons: {form_def.get('buttons', [])}")

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static(id="error-message")

        with VerticalScroll(id="form-container"):
            #title = self.form_def.get("title", self.form_def["name"])
            #yield Label(title, classes="heading")

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
                            
                            if element["field_type"] == "CHOICE":
                                choices = element.get("choices", [])
                                options = [(str(item), item) for item in choices]
                                initial_value = self.initial_data.get(field_name)

                                # Only pass the 'value' argument if we have an initial value
                                # and that value is actually one of the valid options.
                                if initial_value is not None and initial_value in choices:
                                    yield Select(
                                        options,
                                        value=initial_value,
                                        id=widget_id,
                                        disabled=is_readonly
                                    )
                                else:
                                    # Otherwise, let the Select widget use its own default.
                                    yield Select(
                                        options,
                                        id=widget_id,
                                        disabled=is_readonly
                                    )
                            elif element["field_type"] == "MEMO":
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
            value = ""
            if isinstance(widget, Select):
                value = widget.value
            elif isinstance(widget, TextArea):
                value = widget.text
            else: # Input
                value = widget.value
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

        # Part 1: Handle the special navigation buttons first.
        if button_id in ["FIRST_RECORD", "PREV_RECORD", "NEXT_RECORD", "LAST_RECORD"]:
            self.result_dict["action"] = button_id
            self.exit()
            return

        # Part 2: Handle the action buttons defined in the FORM.
        button_def = next((
            b for b in self.form_def["buttons"]
            if re.sub(r'[^a-zA-Z0-9_]', '', b["name"].lower().replace(" ", "_")) == button_id
        ), None)
        
        if button_def:
            action = button_def.get("action")
            if action in ["SUBMIT", "INSERT", "UPDATE"]:
                if not self._validate_form():
                    return

            self.result_dict["action"] = action
            
            data = {}
            for field_name, widget_id in self.widget_map.items():
                widget = self.query_one(f"#{widget_id}")
                if isinstance(widget, Select):
                    data[field_name] = widget.value
                elif isinstance(widget, TextArea):
                    data[field_name] = widget.text
                else: # This handles Input widgets
                    data[field_name] = widget.value
            self.result_dict["data"] = data
            
            pk_value = None
            for key, value in self.initial_data.items():
                if key.lower() == self.pk_column_name.lower():
                    pk_value = value
                    break
            self.result_dict["pk"] = pk_value # Using "pk" as the key
        
        self.exit()
        

class _ListScreen(App):
    """A TUI screen for displaying data grids."""
    
    CSS = """
        Screen {
            background: $surface;
        }
        
        .header-info {
            height: 1;
            margin: 0;
            padding: 0 1;
            background: $primary;
            color: $text;
            border: solid $accent;
        }
        
        .controls {
            height: 6;
            margin: 0;
            padding: 1;
            background: $surface-lighten-1;
            border: solid $accent;
            align: center middle;
        }
        
        .prompt-text {
            text-style: bold;
            color: $accent;
            margin: 0 1 0 0;
            width: auto;
        }
        
        .help-text {
            color: $text-muted;
            text-style: italic;
            margin-bottom: 0;
        }
        
        #file-input {
            width: 50;
            height: 4;
            border: solid $accent;
        }
        
        DataTable {
            margin: 0;
            border: solid $accent;
            height: 1fr;
        }
        
        Input {
            margin: 0 1;
            height: 4;
            border: solid $accent;
            background: $surface;
        }
        
        Input:focus {
            border: solid $primary;
            background: $surface-lighten-1;
        }
        
        Button {
            margin: 0 1;
            height: 3;
            min-width: 10;
            color: auto !important;
            text-style: bold;
        }
        
        Button.-primary {
            background: $primary;
        }
        
        Button.-success {
            background: $success;
        }
        
        Button.-warning {
            background: $warning;
        }
        
        Button:hover {
            text-style: bold reverse;
        }
        """
    

    def __init__(self, form_def, initial_data, result_dict, pk_column_name):
        super().__init__()
        self.form_def = form_def
        self.initial_data = initial_data
        self.result_dict = result_dict
        self.pk_column_name = pk_column_name

        # --- START OF NEW LOGIC ---
        # Find the HEADING text from the form's elements to use as the title.
        form_title = self.form_def.get("name", "Data Grid") # Fallback title
        
        heading_element = next((el for el in self.form_def.get("elements", []) if el.get("type") == "HEADING"), None)
        if heading_element:
            form_title = heading_element.get("text", form_title)

        self.title = f"List View: {form_title}"

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
        all_rows = self.initial_data.get("rows", [])
        
        # This is the full list of columns from the SQL query (e.g., ['id', 'last_name', ...])
        source_headers = self.initial_data.get("headers", [])
        if not source_headers:
            return # Cannot proceed without knowing the source column names
            
        has_defined_fields = any(e.get("type") == "FIELD" for e in self.form_def.get("elements", []))

        display_headers_for_ui = []    # The user-friendly labels for the UI
        field_names_from_source = []   # The actual column names to pull data from
        
        if has_defined_fields:
            for element in self.form_def.get("elements", []):
                if element.get("type") == "FIELD":
                    display_headers_for_ui.append(element.get("label", element["name"]))
                    field_names_from_source.append(element["name"])
        else:
            # Fallback if no fields are defined (use all source headers)
            display_headers_for_ui = source_headers
            field_names_from_source = source_headers
            
        if not display_headers_for_ui:
            return

        # --- START OF FIX ---
        # Create a mapping from the source column names to their index (e.g., {'id': 0, 'last_name': 1, ...})
        try:
            source_header_map = {header_name.lower(): i for i, header_name in enumerate(source_headers)}
            # Find the correct index in the source data for each field we want to display
            display_indices = [source_header_map[field_name.lower()] for field_name in field_names_from_source]
        except KeyError as e:
            # This error happens if a FIELD name in the form doesn't exist in the SOURCE query
            self.exit(f"Form Error: FIELD '{e.args[0]}' not found in SOURCE query columns.")
            return

        # Build the rows for display using only the data from the correctly mapped indices
        display_rows = []
        for row in all_rows:
            display_row = [row[i] for i in display_indices]
            display_rows.append(display_row)
        # --- END OF FIX ---

        table.add_columns(*display_headers_for_ui)
        if display_rows:
            table.add_rows(display_rows)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events."""
        button_id = event.button.id
        
        button_def = next((
            b for b in self.form_def["buttons"] 
            if re.sub(r'[^a-zA-Z0-9_]', '', b["name"].lower().replace(" ", "_")) == button_id
        ), None)

        if button_def:
            action = button_def.get("action")
            self.result_dict["action"] = action
            
            # Get the table widget and its current cursor position directly.
            table = self.query_one(DataTable)
            selected_row_index = table.cursor_row

            rows = self.initial_data.get("rows", [])
            
            # Use the real-time cursor position for the selection.
            if rows and selected_row_index is not None and 0 <= selected_row_index < len(rows):
                row_data = rows[selected_row_index]
                original_headers = self.initial_data.get("headers", [])
                
                if original_headers and len(row_data) >= len(original_headers):
                    row_dict = dict(zip(original_headers, row_data))
                    
                    pk_value = None
                    for key, value in row_dict.items():
                        if key.lower() == self.pk_column_name.lower():
                            pk_value = value
                            break
                    self.result_dict["selected_id"] = pk_value

            if action == "OPENFORM" and button_def.get("args"):
                self.result_dict["target_form"] = button_def["args"][0]
        
        self.exit()
        
