"""
The program MAKE FORM writes: a data-entry application for one table, in plain DDGBasic,
with a menu bar (Browse, Add, Edit, Delete), an entry form with one field per column,
F1 help, and messages for changes the database refuses.

build_form_program() is pure: it takes a description of the table and returns the
program's text, so it can be tested without a database.
"""
import re

_INT_TYPES = ('INT',)                                   # INTEGER, BIGINT, SMALLINT, ...
_REAL_TYPES = ('REAL', 'FLOA', 'DOUB', 'DEC', 'NUM')
MAX_FIELDS = 26                                         # two columns of 13 fields


class FormColumn:
    """One column of the table, as the form needs it.

    kind is 'text', 'int', 'real', 'date', 'bool' or 'list'; width is the text width;
    items_sql is the query of a 'list' field; auto marks a key the database numbers."""

    def __init__(self, name, kind='text', width=20, required=False, items_sql=None, hint_ref='',
                 decimals=2, digits=9, auto=False):
        self.name, self.kind, self.width, self.required = name, kind, width, required
        self.items_sql, self.hint_ref, self.auto = items_sql, hint_ref, auto
        self.decimals, self.digits = decimals, digits


def column_kind(declared_type):
    """'int', 'real', 'date', 'bool' or 'text' for a declared SQL type."""
    t = (declared_type or '').upper()
    if 'BOOL' in t:
        return 'bool'
    if t == 'DATE':
        return 'date'
    if 'TIME' in t:
        return 'text'                      # DATETIME, TIMESTAMP: typed as text
    if any(k in t for k in _INT_TYPES):
        return 'int'
    if any(k in t for k in _REAL_TYPES):
        return 'real'
    return 'text'


def decimal_places(declared_type):
    """(digits before the point, decimals) from DECIMAL(p, s), or (9, 2)."""
    m = re.search(r'\(\s*(\d+)\s*,\s*(\d+)\s*\)', declared_type or '')
    if m:
        p, s = int(m.group(1)), int(m.group(2))
        return max(1, min(p - s, 12)), min(s, 6)
    return 9, 2


def label_of(name):
    return name.replace('_', ' ').title()


def _mask(col):
    """The PICTURE of a numeric field: digits grouped with commas, like a calculator."""
    digits = '9' * (col.digits if col.kind == 'real' else 10)
    if col.kind == 'int':
        return digits
    groups = []
    while digits:
        groups.insert(0, digits[-3:])
        digits = digits[:-3]
    return ','.join(groups) + ('.' + '9' * col.decimals if col.decimals else '')


def _hint(col):
    if col.kind == 'int':
        text = 'A whole number'
    elif col.kind == 'real':
        text = 'A number: digits, then . for the decimals'
    elif col.kind == 'date':
        text = 'A date: YYYY-MM-DD'
    elif col.kind == 'bool':
        text = 'Space ticks or clears the box'
    elif col.kind == 'list':
        text = f'Space or F2 opens the list of {col.hint_ref}; a letter jumps'
    else:
        text = f'Text, up to {col.width} characters'
    return text + (' (required)' if col.required else '')


def _q(text):
    """A DDGBasic string literal."""
    return '"' + str(text).replace('"', '""') + '"'


def build_form_program(table, columns, key, engine, database, title="", made_on="",
                       quote=lambda name: name):
    """The program's text.

    table     the table's name           columns  FormColumn list, in table order
    key       the column that identifies a row, or 'rowid' (SQLite tables without one)
    engine    'sqlite' or 'duckdb'       database the file the program opens
    quote     quote(name) gives a column or table name as SQL needs it"""
    title = title or label_of(table)
    singular = title[:-1] if title.endswith('s') and len(title) > 3 else title
    t_sql = quote(table)
    fields = [c for c in columns if not c.auto]
    if not fields:
        raise ValueError(f"MAKE FORM: the table {table} has no columns to edit.")
    if len(fields) > MAX_FIELDS:
        raise ValueError(f"MAKE FORM: {table} has {len(fields)} columns; a form holds at most {MAX_FIELDS}. "
                         "Make a view or a narrower table, or build the form by hand.")
    key_name = 'row_id' if key == 'rowid' else key
    key_sql = 'rowid' if key == 'rowid' else quote(key)
    shown = [c for c in columns if c.name != key and c.kind not in ('bool',)][:3]
    if not shown:
        shown = [c for c in columns if c.name != key][:1]
    first = shown[0].name if shown else key_name
    lines = []
    add = lines.append

    # --- header ------------------------------------------------------
    add('REM ' + '=' * 67)
    add(f'REM {title}: a data-entry program for the table {table}.')
    add(f'REM Made by MAKE FORM{" on " + made_on if made_on else ""}. It is plain DDGBasic: change it freely.')
    add('REM F1 shows the keys. Browse edits the table as a grid; Add, Edit and Delete use the form.')
    add('REM ' + '=' * 67)
    add(f'DATABASE ENGINE {engine.upper()}')
    add(f'DATABASE OPEN {_q(database)}')
    add('SET SQL_FATAL_ERRORS OFF')
    add('REM (a change the database refuses sets ERR and ERRMSG$, and is shown with ALERT)')
    add('')
    help_lines = ['F1           This help, from anywhere',
                  'Menu bar     Left/Right move, Enter or a letter opens a menu',
                  'Grid         Enter edits a cell, Ins adds a row, Del deletes,',
                  '             click a heading or press F3 to sort',
                  'Pick list    Type to jump to a row, Enter chooses',
                  'Form         Tab/Enter next field, Space or F2 opens a list or',
                  '             ticks a box, Ctrl-Y clears a field, Esc cancels']
    add(f'keys$ = {_q(help_lines[0])} + CHR$(10)')
    for n, text in enumerate(help_lines[1:], 1):
        add(f'keys$ = keys$ + {_q(text)}' + (' + CHR$(10)' if n < len(help_lines) - 1 else ''))
    add('FUNCTION show_help()')
    add('    VIEW keys$ AT 6, 8, 16, 74 TITLE "Keys (Esc closes)"')
    add('END FUNCTION')
    add('ON KEY "F1" CALL show_help')
    add('')

    # --- main loop ---------------------------------------------------
    add('SET THEME "classic"                REM or default, norton, green, amber, paper, mono')
    add('DO')
    add('    GOSUB desktop')
    menu = re.sub(r'[^A-Za-z0-9 ]', '', title).strip() or 'Records'
    add(f'    choice$ = MENUBAR$("File:Quit", "{menu}:Browse|Add|Edit|Delete", "Help:Keys")')
    add(f'    IF choice$ = "{menu}.Browse" THEN GOSUB browse_records')
    add(f'    IF choice$ = "{menu}.Add" THEN GOSUB add_record')
    add(f'    IF choice$ = "{menu}.Edit" THEN GOSUB edit_record')
    add(f'    IF choice$ = "{menu}.Delete" THEN GOSUB delete_record')
    add('    IF choice$ = "Help.Keys" THEN x = show_help()')
    add('LOOP UNTIL choice$ = "File.Quit" OR choice$ = ""')
    add('SET THEME "default"')
    add('CLS')
    add('END')
    add('')

    add('desktop:')
    add('    CLS')
    add(f'    BOX 2, 1, 23, 80, {_q(title.upper())} DOUBLE')
    add(f'    @ 4, 4 SAY LTRIM$(STR$((SELECT COUNT(*) FROM {t_sql}))) & " records in {table}."')
    add(f'    @ 6, 4 SAY "{menu}: Browse, Add, Edit or Delete.   F1: keys."')
    add('    @ 24, 2 SAY "F1 help  Arrows move  Enter chooses  Esc goes back  Letters are hot keys"')
    add('    RETURN')
    add('')

    # --- browse --------------------------------------------------------
    add('browse_records:')
    add('    REM The whole table as a grid: changes are saved as they are made')
    if key == 'rowid':
        add(f'    BROWSE {_q(table)} EDIT AT 3, 3, 21, 78 TITLE "{title} (Enter edits, Ins adds, Del deletes, F3 sorts)"')
    else:
        add(f'    BROWSE (SELECT * FROM {t_sql} ORDER BY {quote(first) if first != key_name else key_sql}) '
            f'EDIT KEY {_q(key)} _')
        add(f'        AT 3, 3, 21, 78 TITLE "{title} (Enter edits, Ins adds, Del deletes, F3 sorts)"')
    add('    RETURN')
    add('')

    # --- pick ------------------------------------------------------------
    pick_cols = [quote(c.name) for c in shown if c.name != key]
    key_col = f'rowid AS row_id' if key == 'rowid' else quote(key)
    add('pick_record:')
    add('    REM Choose a row: p gets it, or an empty hash after Esc. Typing jumps to a row.')
    add(f'    BROWSE (SELECT {", ".join(pick_cols + [key_col])} FROM {t_sql} ORDER BY {quote(first) if pick_cols else key_sql}) _')
    add(f'        AT 3, 3, 21, 78 TITLE "Pick a {singular.lower()} (type to find)" INTO p')
    add('    RETURN')
    add('')

    # --- the form --------------------------------------------------------
    per_column = 13
    two = len(fields) > per_column
    label_w = max(len(label_of(c.name)) for c in fields)
    rows_used = min(len(fields), per_column)
    top, bottom = 3, 3 + rows_used + 6
    left, right = (2, 79) if two else (6, 75)
    field_room = (right - left - 6) // (2 if two else 1) - label_w - 5
    add('form:')
    add('    REM The entry form for the hash r. BUTTON$ says how it ended ("Save" or "").')
    add('    saved$ = SAVESCREEN()')
    add(f'    BOX {top}, {left}, {bottom}, {right}, form_title$ SHADOW')
    for n, c in enumerate(fields):
        row = top + 2 + (n % per_column)
        col = left + 3 + (n // per_column) * ((right - left) // 2)
        say = _q(label_of(c.name).ljust(label_w) + ' : ')
        target = f'r.{c.name}'
        parts = [f'    @ {row}, {col} SAY {say} GET {target}']
        if c.kind == 'text':
            parts.append(f'PICTURE "@S{max(1, min(c.width, field_room))}"')
        elif c.kind in ('int', 'real'):
            parts.append(f'PICTURE "{_mask(c)}"')
        elif c.kind == 'date':
            parts.append('PICTURE "@D"')
        elif c.kind == 'bool':
            parts.append('CHECKBOX')
        elif c.kind == 'list':
            parts.append(f'LIST ({c.items_sql})')
        if c.required and c.kind in ('text', 'date', 'list'):
            # Numbers and check boxes are left out: 0 and "no" are real values for a NOT NULL column
            parts.append(f'REQUIRED MESSAGE {_q(label_of(c.name) + " is required")}')
        line = ' '.join(parts)
        hint = f'HINT {_q(_hint(c))}'
        if len(line) + len(hint) + 1 > 118:
            add(line + ' _')
            add('        ' + hint)
        else:
            add(line + ' ' + hint)
    add(f'    @ {bottom - 2}, {left + 3} BUTTON "Save"')
    add(f'    @ {bottom - 2}, {left + 13} BUTTON "Cancel" CANCEL')
    add('    READ')
    add('    RESTSCREEN saved$')
    add('    RETURN')
    add('')

    def value_sql(c):
        bind = f':r.{c.name}'
        return f'({bind} <> 0)' if c.kind == 'bool' else bind

    # --- add -----------------------------------------------------------------
    add('add_record:')
    blanks = []
    for c in fields:
        blanks.append(f'r.{c.name} = ' + ('0' if c.kind in ('int', 'real', 'bool') else '""'))
    for n in range(0, len(blanks), 4):
        add('    ' + ' : '.join(blanks[n:n + 4]))
    add(f'    form_title$ = {_q("New " + singular.lower())}')
    add('    DO')
    add('        GOSUB form')
    add('        IF BUTTON$ <> "Save" THEN EXIT DO')
    add(f'        INSERT INTO {t_sql} ({", ".join(quote(c.name) for c in fields)})')
    add(f'            VALUES ({", ".join(value_sql(c) for c in fields)});')
    add('        IF ERR = 0 THEN EXIT DO')
    add('        x = ALERT("Not saved;" & ERRMSG$)')
    add('    LOOP')
    add('    RETURN')
    add('')

    # --- edit -----------------------------------------------------------------
    def select_expr(c):
        if c.kind in ('int', 'real', 'bool'):
            zero = 'false' if c.kind == 'bool' and engine == 'duckdb' else '0'
            return f'COALESCE({quote(c.name)}, {zero}) AS {quote(c.name)}'
        return quote(c.name)

    add('edit_record:')
    add('    GOSUB pick_record')
    add('    IF LASTKEY$ = CHR$(27) THEN RETURN')
    add(f'    FOR r IN (SELECT {", ".join(select_expr(c) for c in fields)} FROM {t_sql} WHERE {key_sql} = :p.{key_name})')
    add(f'        form_title$ = {_q("Edit " + singular.lower())}')
    add('        DO')
    add('            GOSUB form')
    add('            IF BUTTON$ <> "Save" THEN EXIT DO')
    sets = [f'{quote(c.name)} = {value_sql(c)}' for c in fields]
    add(f'            UPDATE {t_sql} SET {sets[0]}' + (',' if len(sets) > 1 else ''))
    for n, s in enumerate(sets[1:], 1):
        add(f'                {s}' + (',' if n < len(sets) - 1 else ''))
    add(f'                WHERE {key_sql} = :p.{key_name};')
    add('            IF ERR = 0 THEN EXIT DO')
    add('            x = ALERT("Not saved;" & ERRMSG$)')
    add('        LOOP')
    add('    NEXT')
    add('    RETURN')
    add('')

    # --- delete --------------------------------------------------------------
    add('delete_record:')
    add('    GOSUB pick_record')
    add('    IF LASTKEY$ = CHR$(27) THEN RETURN')
    add(f'    IF ALERT("Delete " & p.{first} & "?", "No", "Yes") = 2 THEN')
    add(f'        DELETE FROM {t_sql} WHERE {key_sql} = :p.{key_name};')
    add('        IF ERR THEN x = ALERT("Not deleted;" & ERRMSG$)')
    add('    END IF')
    add('    RETURN')
    return '\n'.join(lines) + '\n'
