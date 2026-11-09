"""
The DDGBasic IDE: a full-screen editor in the style of QBasic, started with
`ddgbasic --ide [file.bas]`.

It edits one program with syntax colouring, runs it with F5 (the program gets the
whole terminal; the IDE comes back when it ends and moves the cursor to the line of
an error), shows the built-in HELP for the keyword under the cursor with F1, and has
a menu bar (F10, or Alt and a menu's first letter) for files, editing, running,
colours and help. Under the editor, the Immediate window (F6) runs one line at a
time in a session of its own, as the REPL does. It is drawn with the same screen
layer as the text-screen statements (ddgscreen.py).
"""
import io
import os
import re
import signal
import subprocess
import sys

from ddgscreen import SCREEN, ESC, ENTER, TAB, BACKSPACE, bell

# SQL words coloured like DDGBasic's own keywords
_SQL_WORDS = {
    'SELECT', 'FROM', 'WHERE', 'GROUP', 'BY', 'ORDER', 'HAVING', 'INSERT', 'INTO', 'VALUES', 'UPDATE',
    'SET', 'DELETE', 'CREATE', 'TABLE', 'DROP', 'ALTER', 'ADD', 'COLUMN', 'JOIN', 'LEFT', 'RIGHT',
    'INNER', 'OUTER', 'ON', 'AS', 'AND', 'OR', 'NOT', 'NULL', 'IS', 'LIKE', 'IN', 'DISTINCT', 'LIMIT',
    'OFFSET', 'CASE', 'WHEN', 'THEN', 'ELSE', 'END', 'PRIMARY', 'KEY', 'FOREIGN', 'REFERENCES', 'CHECK',
    'UNIQUE', 'DEFAULT', 'INDEX', 'VIEW', 'TRIGGER', 'BEGIN', 'COMMIT', 'ROLLBACK', 'WITH', 'UNION',
    'ALL', 'EXISTS', 'BETWEEN', 'ASC', 'DESC', 'INTEGER', 'TEXT', 'REAL', 'ATTACH', 'DETACH', 'COUNT',
    'SUM', 'AVG', 'MIN', 'MAX', 'COALESCE', 'IF', 'REPLACE', 'PRAGMA', 'TRANSACTION',
}
# BASIC words that are not HELP topics of their own
_BASIC_WORDS = {
    'THEN', 'ELSE', 'ELSEIF', 'END', 'NEXT', 'TO', 'STEP', 'IN', 'EACH', 'WEND', 'LOOP', 'UNTIL',
    'WHILE', 'DO', 'FOR', 'IF', 'GOSUB', 'RETURN', 'GOTO', 'FUNCTION', 'AND', 'OR', 'NOT', 'AS',
    'REM', 'SAY', 'GET', 'PICTURE', 'VALID', 'WHEN', 'MESSAGE', 'HINT', 'LOOKUP', 'CHECKBOX', 'LIST',
    'BUTTON', 'CANCEL', 'AT', 'TITLE', 'EDIT', 'KEY', 'DETAIL', 'FREEZE', 'FORMAT', 'COLOR', 'EXIT',
    'INTO', 'CALL', 'OFF', 'ON', 'OPTIONS', 'TRUNCATE', 'APPEND', 'UPSERT', 'IGNORE', 'USING', 'RECORD',
    'SHADOW', 'DOUBLE', 'TOTAL', 'PAGE', 'VIEW', 'FILE', 'OUTPUT', 'INPUT', 'LINE', 'TRANSFORM',
    'VALIDATE', 'WITH', 'ROW', 'ENGINE', 'SQLITE', 'DUCKDB', 'MOUSE', 'THEME', 'AUTOADVANCE', 'CONFIRM',
}

# F1 on these words shows the help of the statement they belong to
_HELP_ALIASES = {
    'SAY': '@', 'GET': '@', 'PICTURE': '@', 'VALID': '@', 'MESSAGE': '@', 'HINT': '@', 'LOOKUP': '@',
    'CHECKBOX': '@', 'BUTTON': '@', 'CANCEL': '@', 'THEN': 'IF', 'ELSE': 'IF', 'ELSEIF': 'IF',
    'NEXT': 'FOR', 'STEP': 'FOR', 'TO': 'FOR', 'EACH': 'FOR EACH', 'WEND': 'WHILE', 'LOOP': 'DO',
    'UNTIL': 'DO', 'RETURN': 'GOSUB', 'DETAIL': 'BROWSE', 'FREEZE': 'BROWSE', 'RECORD': 'EDIT RECORD',
}

# Colour schemes: (background, text, keyword, string, number, comment, frame, bar fg, bar bg)
_SCHEMES = {
    'blue':  dict(bg=1, text=7, keyword=15, string=14, number=13, comment=11, frame=7, bar_fg=0, bar_bg=7),
    'black': dict(bg=0, text=7, keyword=15, string=14, number=11, comment=10, frame=7, bar_fg=0, bar_bg=7),
}

_HELP_KEYS = """F1 / Shift-F1      help on the word under the cursor / all help topics
F5                 run the program (it is saved first)
F6                 move between the editor and the Immediate window
F9                 set or clear a breakpoint on the cursor's line
F8                 step: run the program a line at a time (it starts paused on line 1)
While paused       F5 continues, F8 runs the next line, F4 shows the program's screen,
                   Run > Stop ends the program; the Immediate window sees its variables
Ctrl-C             pauses a program run with breakpoints or F8
F10, Alt+letter    the menu bar (Alt-F File, Alt-E Edit, Alt-R Run, Alt-O Options, Alt-H Help)
Ctrl-S             save                      Ctrl-O   open
Ctrl-N             new program               Alt-X    exit
Ctrl-Z             undo                      Ctrl-Y   delete the line
Ctrl-D             duplicate the line        Ctrl-G   go to a line
Ctrl-F             find                      F3       find the next one
Tab / Shift-Tab    indent / unindent         Ins      insert or overwrite
Home / End         start / end of the line   Ctrl-Home / Ctrl-End   start / end of the program
PgUp / PgDn        a screen up / down        Ctrl-Left / Ctrl-Right a word left / right
The mouse          click to move the cursor, open a menu or go to a window; the wheel scrolls
Immediate window   type a statement and press Enter: it runs at once (? x is PRINT x);
                   Up/Down recall earlier lines, PgUp/PgDn scroll, CLS clears, Esc goes back
                   (Options > Mouse off gives the terminal its own text selection back)"""


def error_location(errors):
    """The last error a program printed, as (message, line, column), or None. Runtime
    errors read "Runtime Error: ... at line 12, col 5." and lexer errors
    "Error: ... at line 2, col 5"."""
    found = re.findall(r'(?:Runtime Error|Error): (.*?) at line (\d+), col (\d+)', errors)
    if not found:
        return None
    message, line, col = found[-1]
    return message, int(line), int(col)


class DebugStop(BaseException):
    """Run > Stop while a program is paused: ends the debug run. A BaseException, like
    KeyboardInterrupt, so the program's own error handling (ON ERROR, the interpreter's
    error reporting) lets it through."""


class Editor:
    IMMEDIATE_HEIGHT = 6                      # the Immediate window's rows, its input line included

    def __init__(self, path, runner, help_topics, get_help, new_session=None, new_program=None):
        self.runner = runner                  # the command that runs a .bas file
        self.new_session = new_session        # makes the interpreter of the Immediate window
        self.new_program = new_program        # new_program(source, folder): an interpreter to debug
        self.help_topics = help_topics        # HELP topic names
        self.get_help = get_help              # get_help(topic) -> {'desc', 'syntax', 'examples'} or None
        self.keywords = set(_SQL_WORDS) | _BASIC_WORDS
        for topic in help_topics:
            for word in topic.split():
                if re.fullmatch(r'[A-Z_][A-Z0-9_]*\$?', word):
                    self.keywords.add(word)
        self.scheme = _SCHEMES['blue']
        self.path = None
        self.lines = ['']
        self.newline = '\r\n' if os.name == 'nt' else '\n'
        self.row = self.col = 0               # the cursor, in the text
        self.top = self.left = 0              # the first line and column shown
        self.modified = False
        self.insert = True
        self.undo = []
        self.last_edit = None                 # (kind, row): typing on one line is one undo step
        self.find_text = ''
        self.message = ''
        # The Immediate window
        self.session = None                   # its interpreter, made on first use
        self.show_immediate = new_session is not None
        self.focus = 'editor'                 # or 'immediate'
        self.imm_lines = []                   # what it has shown: typed lines and their output
        self.imm_text, self.imm_pos = '', 0   # the line being typed
        self.imm_history, self.imm_recall = [], None
        self.imm_scroll = 0                   # lines scrolled back from the newest
        # The debugger
        self.breakpoints = set()              # line indexes (from 0)
        self.program = None                   # the interpreter of a debug run
        self.paused_row = None                # the line it is paused on
        self.debug_mode = 'run'               # 'run' to the next breakpoint, or 'step'
        self.pause_requested = False          # Ctrl-C during a debug run
        if path:
            self.load(path)

    # --- files ---------------------------------------------------------------------
    def load(self, path):
        self.path = os.path.abspath(path)
        if os.path.exists(self.path):
            with open(self.path, encoding='utf-8', errors='replace', newline='') as f:
                text = f.read()
            self.newline = '\r\n' if '\r\n' in text else '\n'
            self.lines = [line.expandtabs(4) for line in text.replace('\r\n', '\n').split('\n')]
            if len(self.lines) > 1 and self.lines[-1] == '':
                self.lines.pop()                # the file's last newline
            self.message = f'{os.path.basename(self.path)}: {len(self.lines)} lines'
        else:
            self.lines = ['']
            self.message = f'{os.path.basename(self.path)} is a new file'
        self.row = self.col = self.top = self.left = 0
        self.modified = False
        self.undo = []
        self.breakpoints = set()

    def save(self, path=None):
        path = path or self.path
        if not path:
            return self.save_as()
        try:
            with open(path, 'w', encoding='utf-8', newline='') as f:
                f.write(self.newline.join(self.lines) + self.newline)
        except OSError as e:
            SCREEN.alert(f'Not saved;{e}', ['OK'])
            return False
        self.path = os.path.abspath(path)
        self.modified = False
        self.message = f'Saved {os.path.basename(self.path)}'
        return True

    def save_as(self):
        default = os.path.basename(self.path) if self.path else 'program.bas'
        name = self.prompt('Save As', 'File name:', default)
        if not name:
            return False
        if not os.path.splitext(name)[1]:
            name += '.bas'
        folder = os.path.dirname(self.path) if self.path else os.getcwd()
        path = os.path.abspath(os.path.join(folder, os.path.expanduser(name)))
        if os.path.exists(path) and path != self.path:
            if SCREEN.alert(f'{os.path.basename(path)} already exists.;Replace it?', ['No', 'Yes']) != 2:
                return False
        return self.save(path)

    def keep_changes(self):
        """Before the program is closed: True to go on (saved or discarded), False to stay."""
        if not self.modified:
            return True
        name = os.path.basename(self.path) if self.path else 'Untitled'
        choice = SCREEN.alert(f'Save the changes to {name}?', ['Yes', 'No', 'Cancel'])
        if choice == 1:
            return self.save()
        return choice == 2

    def open_file(self):
        if not self.keep_changes():
            return
        folder = os.path.dirname(self.path) if self.path else os.getcwd()
        names = sorted((n for n in os.listdir(folder) if n.lower().endswith('.bas')), key=str.lower)
        rows = [['(type a name)', '', '']]
        for name in names:
            full = os.path.join(folder, name)
            try:
                with open(full, encoding='utf-8', errors='replace') as f:
                    count = sum(1 for _ in f)
            except OSError:
                count = ''
            rows.append([name, count, os.path.getsize(full)])
        rows_on, cols_on = SCREEN.size()
        chosen = SCREEN.browse(['File', 'Lines', 'Bytes'], rows, (3, 8, rows_on - 3, cols_on - 8),
                               f'Open: {folder}', shadow=True)
        if chosen < 0:
            return
        if chosen == 0:
            name = self.prompt('Open', 'File name:', '')
            if not name:
                return
            path = os.path.join(folder, os.path.expanduser(name))
        else:
            path = os.path.join(folder, rows[chosen][0])
        self.load(path)

    def new_file(self):
        if not self.keep_changes():
            return
        self.path = None
        self.lines = ['']
        self.row = self.col = self.top = self.left = 0
        self.modified = False
        self.undo = []
        self.message = 'New program'

    # --- small dialogs -------------------------------------------------------------------
    def prompt(self, title, label, default=''):
        """A one-line input box. Returns the text, or None for Esc."""
        rows, cols = SCREEN.size()
        width = min(60, cols - 6)
        top, left = rows // 2 - 2, (cols - width) // 2
        under = SCREEN.popup(top, left, top + 4, left + width, title, double=True)
        text, pos = default, len(default)
        field = width - len(label) - 5
        try:
            while True:
                shown = text[max(0, pos - field + 1):][:field]
                SCREEN._w(SCREEN._put(top + 2, left + 2, label + ' ', SCREEN.fg, SCREEN.bg) +
                          SCREEN._put(top + 2, left + 3 + len(label), shown.ljust(field), 0, 7) +
                          f'\x1b[{top + 2};{left + 3 + len(label) + min(pos, field - 1)}H\x1b[?25h')
                key = SCREEN.keys.read_key()
                if key in (None, ESC):
                    return None
                if key == ENTER:
                    return text.strip()
                if key == BACKSPACE and pos > 0:
                    text, pos = text[:pos - 1] + text[pos:], pos - 1
                elif key == 'DEL':
                    text = text[:pos] + text[pos + 1:]
                elif key == 'LEFT':
                    pos = max(0, pos - 1)
                elif key == 'RIGHT':
                    pos = min(len(text), pos + 1)
                elif key == 'HOME':
                    pos = 0
                elif key == 'END':
                    pos = len(text)
                elif key and len(key) == 1 and key.isprintable():
                    text, pos = text[:pos] + key + text[pos:], pos + 1
        finally:
            SCREEN.restore_saved(under)

    # --- help ---------------------------------------------------------------------------
    def word_at_cursor(self):
        line = self.lines[self.row]
        for m in re.finditer(r'[A-Za-z_@][A-Za-z0-9_]*\$?|@', line):
            if m.start() <= self.col <= m.end():
                return m.start(), m.group()
        return None, ''

    def help_topic_at_cursor(self, line=None, col=None):
        """The HELP topic for the word under the cursor (of the editor, or of the given line
        and column), trying two-word topics (ON KEY, SET THEME, MAKE FORM) with the word
        before and after it too."""
        if line is None:
            line, col = self.lines[self.row], self.col
        start, word = None, ''
        for m in re.finditer(r'[A-Za-z_@][A-Za-z0-9_]*\$?|@', line):
            if m.start() <= col <= m.end():
                start, word = m.start(), m.group()
                break
        if not word:
            return None
        words = [(m.start(), m.group().upper()) for m in re.finditer(r'[A-Za-z_@][A-Za-z0-9_]*\$?|@', line)]
        i = next((n for n, (s, _) in enumerate(words) if s == start), None)
        topics = set(self.help_topics)
        if i is not None:
            for a, b in ((i - 1, i), (i, i + 1)):
                if 0 <= a and b < len(words) and f'{words[a][1]} {words[b][1]}' in topics:
                    return f'{words[a][1]} {words[b][1]}'
        upper = word.upper()
        if upper in topics:
            return upper
        if upper in _HELP_ALIASES and _HELP_ALIASES[upper] in topics:
            return _HELP_ALIASES[upper]
        if upper.endswith('$') and upper[:-1] in topics:
            return upper[:-1]
        if upper + '$' in topics:
            return upper + '$'
        return None

    def show_help(self, topic):
        info = self.get_help(topic)
        if not info:
            SCREEN.alert(f'There is no help for {topic}.', ['OK'])
            return
        text = f"{topic}\n\n{info['desc']}\n\nSyntax:\n  " + info['syntax'].replace('\n', '\n  ')
        if info.get('examples'):
            text += '\n\nExamples:\n' + '\n'.join('  ' + e.replace('\n', '\n  ') for e in info['examples'])
        rows, cols = SCREEN.size()
        SCREEN.view(self.wrap(text, cols - 10), (3, 4, rows - 3, cols - 3), f'Help: {topic}  (Esc closes)')

    def help_topics_list(self):
        rows, cols = SCREEN.size()
        topics = sorted(self.help_topics)
        chosen = SCREEN.browse(['Topic (type to find)'], [[t] for t in topics], (3, 10, rows - 3, cols - 10),
                               'Help topics', shadow=True)
        if chosen >= 0:
            self.show_help(topics[chosen])

    @staticmethod
    def wrap(text, width):
        out = []
        for line in text.split('\n'):
            indent = len(line) - len(line.lstrip())
            while len(line) > width:
                cut = line.rfind(' ', indent + 1, width)
                cut = cut if cut > indent else width
                out.append(line[:cut])
                line = ' ' * indent + line[cut:].lstrip()
            out.append(line)
        return '\n'.join(out)

    # --- running ----------------------------------------------------------------------
    def run(self):
        if not self.path or self.modified:
            if not self.save():
                return
        SCREEN.restore()                                    # the program gets a normal terminal
        sys.stdout.write('\x1b[0m\x1b[2J\x1b[H')
        sys.stdout.flush()
        folder, name = os.path.split(self.path)
        try:
            # The program runs in its own folder, so its relative file names work; its
            # errors are collected to find the line, and shown after it ends.
            done = subprocess.run(self.runner + [name], cwd=folder, stderr=subprocess.PIPE)
            errors = done.stderr.decode('utf-8', errors='replace')
            status = done.returncode
        except KeyboardInterrupt:
            errors, status = '', 130
        except OSError as e:
            errors, status = f'Could not run the program: {e}\n', 1
        sys.stdout.write('\x1b[0m\x1b[?25h')
        if errors:
            sys.stdout.write(errors if errors.endswith('\n') else errors + '\n')
        outcome = 'finished' if status == 0 else ('stopped (Ctrl-C)' if status == 130 else 'stopped with an error')
        sys.stdout.write(f'\n The program {outcome}. Press any key to return to the IDE.')
        sys.stdout.flush()
        SCREEN.keys.read_key()
        self.repaint()
        # Go to the error
        found = error_location(errors) if status != 0 else None
        if found:
            text, line, col = found
            self.row = max(0, min(line - 1, len(self.lines) - 1))
            self.col = max(0, min(col - 1, len(self.lines[self.row])))
            self.scroll_to_cursor()
            self.draw()
            SCREEN.alert(f'Line {line}:;{text[:200]}', ['OK'])
            self.message = f'Error on line {line}: {text[:120]}'

    # --- the debugger: breakpoints, stepping --------------------------------------------
    def toggle_breakpoint(self):
        if self.row in self.breakpoints:
            self.breakpoints.discard(self.row)
            self.message = f'Breakpoint on line {self.row + 1} cleared'
        else:
            self.breakpoints.add(self.row)
            self.message = f'Breakpoint on line {self.row + 1}: F5 runs to it'

    def debug(self, step):
        """Runs the program inside the IDE, stopping at breakpoints (and, with step, on its
        first line). The program uses the whole screen; at a stop the IDE comes back with
        the line highlighted. The editor's text is run as it is, saved or not."""
        if self.new_program is None:
            bell()
            return
        folder = os.path.dirname(self.path) if self.path else os.getcwd()
        source = '\n'.join(self.lines) + '\n'
        try:
            program = self.new_program(source, folder)
        except Exception as e:                       # the lexer refused the program
            found = error_location(f'Error: {e}')
            self.message = f'Error: {e}'.split('\n')[0][:150]
            if found:
                self.row = max(0, min(found[1] - 1, len(self.lines) - 1))
                self.col = max(0, found[2] - 1)
            return
        self.program, self.debug_mode, self.pause_requested = program, 'step' if step else 'run', False
        program.line_hook = self.on_line
        ide_colours = (SCREEN.fg, SCREEN.bg, SCREEN.field_fg, SCREEN.field_bg)
        mouse, hotkeys, hotkey_call = SCREEN.keys.mouse_wanted, dict(SCREEN.keys.hotkeys), SCREEN.hotkey_call
        errors = io.StringIO()

        class Tee:                                   # errors go to the screen and are kept
            def write(self, text):
                errors.write(text)
                return saved_stderr.write(text)

            def flush(self):
                saved_stderr.flush()

        saved_stderr, here = sys.stderr, os.getcwd()
        previous_sigint = signal.getsignal(signal.SIGINT)

        def on_ctrl_c(signum, frame):
            self.pause_requested = True              # pause before the next line

        self.start_program_screen()
        status = None
        try:
            signal.signal(signal.SIGINT, on_ctrl_c)
            sys.stderr = Tee()
            os.chdir(folder)
            program.run()
            status = program.exit_code
        except DebugStop:
            status = 'stopped'
        except KeyboardInterrupt:
            status = 130
        except Exception as e:
            sys.stderr.write(f'Error: {e}\n')
            status = 1
        finally:
            signal.signal(signal.SIGINT, previous_sigint)
            sys.stderr = saved_stderr
            os.chdir(here)
            try:
                program.close()
            except Exception:
                pass
            self.program, self.paused_row = None, None
            SCREEN.keys.hotkeys, SCREEN.hotkey_call = hotkeys, hotkey_call   # the program's ON KEYs end with it
            SCREEN.keys.set_mouse(mouse)
            SCREEN.gets = []
            SCREEN.fg, SCREEN.bg, SCREEN.field_fg, SCREEN.field_bg = ide_colours
        if status != 'stopped':
            SCREEN.keys.raw_off()
            outcome = 'finished' if status == 0 else ('stopped (Ctrl-C)' if status == 130 else 'stopped with an error')
            sys.stdout.write(f'\x1b[0m\x1b[?25h\n The program {outcome}. Press any key to return to the IDE.')
            sys.stdout.flush()
            SCREEN.keys.read_key()
        self.repaint()
        found = error_location(errors.getvalue()) if status not in (0, 'stopped') else None
        if found:
            text, line, col = found
            self.row = max(0, min(line - 1, len(self.lines) - 1))
            self.col = max(0, min(col - 1, len(self.lines[self.row])))
            self.scroll_to_cursor()
            self.draw()
            SCREEN.alert(f'Line {line}:;{text[:200]}', ['OK'])
            self.message = f'Error on line {line}: {text[:120]}'
        elif status == 'stopped':
            self.message = 'The program was stopped'

    def start_program_screen(self):
        """A clear screen in the default colours for the program, as when it runs on its own."""
        SCREEN.color(7, 0, 0, 7)
        SCREEN.keys.raw_off()
        SCREEN.cells = SCREEN._blank(SCREEN.rows, SCREEN.cols, 7, 0)
        SCREEN.cur_row = SCREEN.cur_col = 1
        sys.stdout.write('\x1b[0m\x1b[2J\x1b[H\x1b[?25h')
        sys.stdout.flush()

    def on_line(self, program, line):
        """The interpreter's line hook: pauses at a breakpoint, when stepping, or after Ctrl-C."""
        row = line - 1
        if self.debug_mode == 'step' or row in self.breakpoints or self.pause_requested:
            self.pause_requested = False
            self.pause(row)

    def pause(self, row):
        """The program stops before line row: the IDE comes back with the line highlighted,
        until F5 (continue), F8 (step) or Run > Stop."""
        program_screen = SCREEN.save()
        program_colours = (SCREEN.fg, SCREEN.bg, SCREEN.field_fg, SCREEN.field_bg)
        program_gets, program_hotkeys = SCREEN.gets, dict(SCREEN.keys.hotkeys)
        SCREEN.gets, SCREEN.keys.hotkeys = [], {}
        SCREEN.color(15, self.scheme['bg'], self.scheme['bar_fg'], self.scheme['bar_bg'])
        self.paused_row, self.row, self.col, self.focus = row, row, 0, 'editor'
        self.message = f'Paused before line {row + 1}: F8=step  F5=continue  F4=output  Run>Stop'
        self.repaint()
        try:
            while True:
                self.draw()
                try:
                    key = SCREEN.keys.read_key()
                except KeyboardInterrupt:
                    continue
                if key is None:
                    raise DebugStop()
                if key in ('F5', 'F8'):
                    self.debug_mode = 'step' if key == 'F8' else 'run'
                    break
                if key == 'F4':
                    self.show_output(program_screen)
                    continue
                result = self.handle_key(key)
                if result in ('continue', 'step'):
                    self.debug_mode = 'step' if result == 'step' else 'run'
                    break
                if result in ('stop', 'quit'):
                    raise DebugStop()
        finally:
            self.paused_row = None
            SCREEN.gets, SCREEN.keys.hotkeys = program_gets, program_hotkeys
            SCREEN.fg, SCREEN.bg, SCREEN.field_fg, SCREEN.field_bg = program_colours
        # Back to the program: its screen as it left it
        SCREEN.keys.raw_off()
        sys.stdout.write('\x1b[0m\x1b[2J')
        SCREEN.restore_saved(program_screen)
        SCREEN._w(SCREEN._normal())

    def show_output(self, program_screen):
        """F4 while paused: the program's screen, until a key is pressed."""
        sys.stdout.write('\x1b[0m\x1b[2J')
        SCREEN.restore_saved(program_screen)
        SCREEN._w('\x1b[?25l')
        SCREEN.keys.read_key()
        self.repaint()

    # --- editing ---------------------------------------------------------------------
    def remember(self, kind):
        """Saves an undo point before a change, unless it continues the last one
        (typing on the same line is one step)."""
        if kind in ('type', 'delete') and self.last_edit == (kind, self.row):
            return
        self.undo.append((list(self.lines), self.row, self.col, set(self.breakpoints)))
        if len(self.undo) > 500:
            self.undo.pop(0)
        self.last_edit = (kind, self.row)
        self.modified = True

    def do_undo(self):
        if not self.undo:
            bell()
            self.message = 'Nothing to undo'
            return
        self.lines, self.row, self.col, self.breakpoints = self.undo.pop()
        self.last_edit = None
        self.modified = True

    def line_inserted(self, at):
        """A line was inserted at index at: the breakpoints below it move down."""
        self.breakpoints = {b + 1 if b >= at else b for b in self.breakpoints}

    def line_removed(self, at):
        """The line at index at was removed: its breakpoint goes, the ones below move up."""
        self.breakpoints = {b - 1 if b > at else b for b in self.breakpoints if b != at}

    def type_char(self, ch):
        self.remember('type')
        line = self.lines[self.row]
        if self.insert or self.col >= len(line):
            self.lines[self.row] = line[:self.col] + ch + line[self.col:]
        else:
            self.lines[self.row] = line[:self.col] + ch + line[self.col + 1:]
        self.col += 1

    def enter(self):
        self.remember('enter')
        line = self.lines[self.row]
        indent = len(line) - len(line.lstrip(' '))
        indent = min(indent, self.col)
        self.lines[self.row] = line[:self.col]
        self.lines.insert(self.row + 1, ' ' * indent + line[self.col:].lstrip(' ') if self.col < len(line) else ' ' * indent)
        # Enter at the start of a line pushes the line (and its breakpoint) down
        self.line_inserted(self.row if self.col == 0 and line.strip() else self.row + 1)
        self.row, self.col = self.row + 1, indent

    def backspace(self):
        if self.col > 0:
            self.remember('delete')
            line = self.lines[self.row]
            # In leading spaces, go back to the previous indent stop
            if line[:self.col].strip() == '' and self.col % 4 == 0 and self.col >= 4:
                self.lines[self.row] = line[:self.col - 4] + line[self.col:]
                self.col -= 4
            else:
                self.lines[self.row] = line[:self.col - 1] + line[self.col:]
                self.col -= 1
        elif self.row > 0:
            self.remember('join')
            self.col = len(self.lines[self.row - 1])
            self.lines[self.row - 1] += self.lines.pop(self.row)
            self.line_removed(self.row)
            self.row -= 1

    def delete(self):
        line = self.lines[self.row]
        if self.col < len(line):
            self.remember('delete')
            self.lines[self.row] = line[:self.col] + line[self.col + 1:]
        elif self.row + 1 < len(self.lines):
            self.remember('join')
            self.lines[self.row] = line.ljust(self.col) + self.lines.pop(self.row + 1)
            self.line_removed(self.row + 1)

    def tab(self, back=False):
        self.remember('indent')
        line = self.lines[self.row]
        if back:
            spaces = min(4, len(line) - len(line.lstrip(' ')))
            self.lines[self.row] = line[spaces:]
            self.col = max(0, self.col - spaces)
        else:
            n = 4 - self.col % 4
            self.lines[self.row] = line[:self.col] + ' ' * n + line[self.col:]
            self.col += n

    def delete_line(self):
        self.remember('line')
        if len(self.lines) == 1:
            self.lines = ['']
            self.breakpoints = set()
        else:
            self.lines.pop(self.row)
            self.line_removed(self.row)
            self.row = min(self.row, len(self.lines) - 1)
        self.col = min(self.col, len(self.lines[self.row]))

    def duplicate_line(self):
        self.remember('line')
        self.lines.insert(self.row + 1, self.lines[self.row])
        self.line_inserted(self.row + 1)
        self.row += 1

    def find(self, again=False):
        if not again or not self.find_text:
            text = self.prompt('Find', 'Find:', self.find_text)
            if not text:
                return
            self.find_text = text
        want = self.find_text.lower()
        n = len(self.lines)
        for k in range(n + 1):
            r = (self.row + k) % n
            start = self.col + 1 if k == 0 else 0
            at = self.lines[r].lower().find(want, start) if k < n or start == 0 else -1
            if at >= 0 and not (k == n and at >= self.col + 1):
                self.row, self.col = r, at
                self.message = f'Found "{self.find_text}"'
                return
        bell()
        self.message = f'"{self.find_text}" was not found'

    def go_to_line(self):
        text = self.prompt('Go to line', 'Line number:', str(self.row + 1))
        if text and text.isdigit():
            self.row = max(0, min(int(text) - 1, len(self.lines) - 1))
            self.col = 0

    def word_move(self, direction):
        line = self.lines[self.row]
        if direction < 0:
            if self.col == 0 and self.row > 0:
                self.row -= 1
                self.col = len(self.lines[self.row])
                return
            c = self.col
            while c > 0 and not line[c - 1].isalnum():
                c -= 1
            while c > 0 and line[c - 1].isalnum():
                c -= 1
            self.col = c
        else:
            if self.col >= len(line) and self.row + 1 < len(self.lines):
                self.row += 1
                self.col = 0
                return
            c = self.col
            while c < len(line) and line[c].isalnum():
                c += 1
            while c < len(line) and not line[c].isalnum():
                c += 1
            self.col = c

    # --- the Immediate window -------------------------------------------------------------
    def execute_immediate(self, text):
        """Runs one line in the Immediate window's session and adds it and its output to the
        window. ? x is PRINT x; CLS clears the window. Returns the output lines."""
        line = text.strip()
        if not line:
            return []
        if line.upper() == 'CLS':
            self.imm_lines, self.imm_scroll = [], 0
            return []
        if re.match(r'(?i)(LINE\s+)?INPUT\b(?!\s*#)', line):
            out = ["INPUT can't be used here: the Immediate window has no keyboard prompt."]
        else:
            code = 'PRINT ' + line[1:] if line.startswith('?') else line
            paused = self.program if self.paused_row is not None else None
            if paused is None and self.session is None:
                self.session = self.new_session()
            session = paused or self.session
            if paused is not None:
                # repl_execute replaces the token stream: keep the paused program's place
                kept = (paused.tokens, paused.token_index, paused.labels, paused.jump_map,
                        list(paused.gosub_stack), paused.program_terminated, paused.line_hook)
                paused.line_hook = None
            buffer, saved = io.StringIO(), (sys.stdout, sys.stderr)
            here = os.getcwd()
            colours = (SCREEN.fg, SCREEN.bg, SCREEN.field_fg, SCREEN.field_bg)
            try:
                sys.stdout = sys.stderr = buffer          # what the line prints goes to the window
                if self.path:
                    os.chdir(os.path.dirname(self.path))  # file names are relative to the program
                session.repl_execute(code)
            except KeyboardInterrupt:
                buffer.write('Interrupted.\n')
            finally:
                sys.stdout, sys.stderr = saved
                if paused is not None:
                    (paused.tokens, paused.token_index, paused.labels, paused.jump_map,
                     paused.gosub_stack, paused.program_terminated, paused.line_hook) = kept
                os.chdir(here)
                SCREEN.fg, SCREEN.bg, SCREEN.field_fg, SCREEN.field_bg = colours   # a COLOR in the line
                SCREEN.gets = []                                                 # a GET in the line
            # Screen statements in the line drew with escape codes; keep only their text
            text_out = re.sub(r'\x1b\[[0-9;?<]*[A-Za-z]', '', buffer.getvalue()).replace('\r', '')
            out = [l.expandtabs(8) for l in text_out.rstrip('\n').split('\n')] if text_out.strip() else []
            # An error: just its message (its position in a one-line program means nothing here)
            for n, l in enumerate(out):
                if l.startswith('REPL Error: '):
                    message = re.sub(r' at line \d+, col \d+\.?$', '', l[len('REPL Error: '):])
                    out = out[:n] + ['Error: ' + message]
                    break
        self.imm_lines.extend(['> ' + line] + out)
        del self.imm_lines[:-1000]
        if not self.imm_history or self.imm_history[-1] != line:
            self.imm_history.append(line)
        self.imm_recall, self.imm_scroll = None, 0
        return out

    def immediate_key(self, key):
        """A key typed in the Immediate window."""
        text, pos = self.imm_text, self.imm_pos
        if key == ENTER:
            self.execute_immediate(text)
            self.imm_text, self.imm_pos = '', 0
            self.repaint()                                # in case the line drew on the screen
            return
        if key in (ESC, 'F6'):
            self.focus = 'editor'
        elif key == BACKSPACE and pos > 0:
            self.imm_text, self.imm_pos = text[:pos - 1] + text[pos:], pos - 1
        elif key == 'DEL':
            self.imm_text = text[:pos] + text[pos + 1:]
        elif key == 'LEFT':
            self.imm_pos = max(0, pos - 1)
        elif key == 'RIGHT':
            self.imm_pos = min(len(text), pos + 1)
        elif key == 'HOME':
            self.imm_pos = 0
        elif key == 'END':
            self.imm_pos = len(text)
        elif key in ('UP', 'DOWN') and self.imm_history:
            n = len(self.imm_history)
            i = self.imm_recall if self.imm_recall is not None else n
            i = max(0, i - 1) if key == 'UP' else i + 1
            if i >= n:
                self.imm_recall, self.imm_text = None, ''
            else:
                self.imm_recall, self.imm_text = i, self.imm_history[i]
            self.imm_pos = len(self.imm_text)
        elif key in ('PGUP', 'PGDN', 'WHEELUP', 'WHEELDOWN'):
            step = self.IMMEDIATE_HEIGHT - 1 if key in ('PGUP', 'PGDN') else 3
            back = key in ('PGUP', 'WHEELUP')
            most = max(0, len(self.imm_lines) - (self.IMMEDIATE_HEIGHT - 1))
            self.imm_scroll = max(0, min(most, self.imm_scroll + (step if back else -step)))
        elif len(key) == 1 and key.isprintable():
            self.imm_text, self.imm_pos = text[:pos] + key + text[pos:], pos + 1
        else:
            bell()

    # --- drawing ---------------------------------------------------------------------
    def area(self):
        rows, cols = SCREEN.size()
        last = rows - 2 - (self.IMMEDIATE_HEIGHT + 1 if self.show_immediate else 0)
        return 3, last, cols - 2              # first and last text row, text width

    def draw_immediate(self, rows, cols):
        """The Immediate window: a title line, the newest lines, and the line being typed."""
        s = self.scheme
        first, last, width = self.area()
        title = ' Immediate ' if self.focus != 'immediate' else ' Immediate  (F6 or Esc: back to the editor) '
        bar = '─' * (cols - 2)
        start = max(0, (cols - 2 - len(title)) // 2)
        bar = bar[:start] + title + bar[start + len(title):]
        out = [SCREEN._put(last + 1, 1, '├' + bar[:cols - 2] + '┤', s['frame'], s['bg'])]
        shown = self.IMMEDIATE_HEIGHT - 1
        end = len(self.imm_lines) - self.imm_scroll
        lines = self.imm_lines[max(0, end - shown):end]
        lines = [''] * (shown - len(lines)) + lines
        for n, text in enumerate(lines):
            row = last + 2 + n
            colour = s['keyword'] if text.startswith('> ') else s['text']
            out.append(SCREEN._put(row, 1, '│', s['frame'], s['bg']))
            out.append(SCREEN._put(row, 2, text[:width].ljust(width), colour, s['bg']))
            out.append(SCREEN._put(row, cols, '│', s['frame'], s['bg']))
        row = last + 2 + shown
        typed = '> ' + self.imm_text
        offset = max(0, len(typed) - width + 1) if self.imm_pos + 2 >= width else 0
        out.append(SCREEN._put(row, 1, '│', s['frame'], s['bg']))
        out.append(SCREEN._put(row, 2, typed[offset:offset + width].ljust(width), s['keyword'], s['bg']))
        out.append(SCREEN._put(row, cols, '│', s['frame'], s['bg']))
        return ''.join(out), row, 2 + 2 + self.imm_pos - offset

    def scroll_to_cursor(self):
        first, last, width = self.area()
        height = last - first + 1
        if self.row < self.top:
            self.top = self.row
        elif self.row >= self.top + height:
            self.top = self.row - height + 1
        if self.col < self.left:
            self.left = max(0, self.col - 8)
        elif self.col >= self.left + width:
            self.left = self.col - width + 8

    def colours_of(self, line):
        """The colour of each character of a line."""
        s = self.scheme
        out = [s['text']] * len(line)

        def paint(a, b, colour):
            for i in range(a, min(b, len(line))):
                out[i] = colour

        i, statement_start = 0, True
        while i < len(line):
            ch = line[i]
            if ch in '"`\'':
                j = i + 1
                while j < len(line):
                    if line[j] == ch:
                        if ch == '"' and j + 1 < len(line) and line[j + 1] == '"':
                            j += 2
                            continue
                        break
                    j += 1
                paint(i, j + 1, s['string'])
                i, statement_start = j + 1, False
                continue
            if line.startswith('--', i):
                paint(i, len(line), s['comment'])
                break
            m = re.match(r'[A-Za-z_][A-Za-z0-9_]*\$?', line[i:])
            if m:
                word = m.group()
                if word.upper() == 'REM' and statement_start:
                    paint(i, len(line), s['comment'])
                    break
                # A word after a . is a field (c.name), not a keyword
                if word.upper() in self.keywords and not (i > 0 and line[i - 1] == '.'):
                    paint(i, i + len(word), s['keyword'])
                i += len(word)
                statement_start = False
                continue
            m = re.match(r'\d+(\.\d+)?([eE][+-]?\d+)?|\.\d+', line[i:])
            if m:
                paint(i, i + len(m.group()), s['number'])
                i += len(m.group())
                statement_start = False
                continue
            if ch == ':':
                statement_start = True
            elif not ch.isspace():
                statement_start = False
            i += 1
        return out

    def draw_line(self, screen_row, text_row, width):
        s = self.scheme
        if text_row >= len(self.lines):
            return SCREEN._put(screen_row, 2, ' ' * width, s['text'], s['bg'])
        line = self.lines[text_row]
        shown = line[self.left:self.left + width]
        if text_row == self.paused_row:          # the line the program is paused before
            return SCREEN._put(screen_row, 2, shown.ljust(width), 0, 7)
        if text_row in self.breakpoints:
            return SCREEN._put(screen_row, 2, shown.ljust(width), 15, 4)
        colours = self.colours_of(line)[self.left:self.left + width]
        out, start = [], 0
        for k in range(1, len(shown) + 1):
            if k == len(shown) or colours[k] != colours[start]:
                out.append(SCREEN._put(screen_row, 2 + start, shown[start:k], colours[start], s['bg']))
                start = k
        if len(shown) < width:
            out.append(SCREEN._put(screen_row, 2 + len(shown), ' ' * (width - len(shown)), s['text'], s['bg']))
        return ''.join(out)

    def title(self):
        name = os.path.basename(self.path) if self.path else 'Untitled'
        return name + (' *' if self.modified else '')

    def draw_menu_bar(self):
        s = self.scheme
        rows, cols = SCREEN.size()
        out = [SCREEN._put(1, 1, ' ' * cols, s['bar_fg'], s['bar_bg'])]
        x = 2
        for name in ('File', 'Edit', 'Run', 'Options', 'Help'):
            out.append(SCREEN._put(1, x, ' ' + name + ' ', s['bar_fg'], s['bar_bg']))
            x += len(name) + 3
        return ''.join(out)

    def draw(self):
        s = self.scheme
        rows, cols = SCREEN.size()
        first, last, width = self.area()
        self.scroll_to_cursor()
        out = [self.draw_menu_bar()]
        title = f' {self.title()} '
        bar = '─' * (cols - 2)
        start = max(0, (cols - 2 - len(title)) // 2)
        bar = bar[:start] + title + bar[start + len(title):]
        tl, tr, bl, br, _, _ = SCREEN.frame_chars()     # rounded corners in the modern style
        out.append(SCREEN._put(2, 1, tl + bar[:cols - 2] + tr, s['frame'], s['bg']))
        for n, screen_row in enumerate(range(first, last + 1)):
            out.append(SCREEN._put(screen_row, 1, '│', s['frame'], s['bg']))
            out.append(self.draw_line(screen_row, self.top + n, width))
            out.append(SCREEN._put(screen_row, cols, '│', s['frame'], s['bg']))
        cursor_row = first + self.row - self.top
        cursor_col = 2 + self.col - self.left
        if self.show_immediate:
            pane, input_row, input_col = self.draw_immediate(rows, cols)
            out.append(pane)
            if self.focus == 'immediate':
                cursor_row, cursor_col = input_row, input_col
        out.append(SCREEN._put(rows - 1, 1, bl + '─' * (cols - 2) + br, s['frame'], s['bg']))
        position = f'Ln {self.row + 1}  Col {self.col + 1}  {"Ins" if self.insert else "Ovr"} '
        if self.focus == 'immediate':
            hint = 'Enter runs the line  ? x prints x  Up=recall  F6=editor'
        else:
            hint = 'F1=Help  F5=Run  F6=Immediate  F10=Menu  Ctrl-S=Save  Alt-X=Exit'
        left = ' ' + (self.message or hint)
        status = left[:cols - len(position) - 1].ljust(cols - len(position) - 1) + position
        out.append(SCREEN._put(rows, 1, status[:cols - 1], s['bar_fg'], s['bar_bg']))
        SCREEN._w(''.join(out) + SCREEN._normal() + f'\x1b[{cursor_row};{cursor_col}H\x1b[?25h')

    def set_scheme(self, name):
        """The editor's colours; dialogs, menus and help windows follow the background."""
        self.scheme = _SCHEMES[name]
        SCREEN.color(15, self.scheme['bg'], self.scheme['bar_fg'], self.scheme['bar_bg'])
        self.repaint()

    def repaint(self):
        SCREEN._w('\x1b[0m\x1b[2J')
        SCREEN.rows, SCREEN.cols = SCREEN.size()
        SCREEN.cells = SCREEN._blank(SCREEN.rows, SCREEN.cols, 7, 0)
        self.draw()

    # --- the menu bar ----------------------------------------------------------------------
    MENUS = [
        ('File', ['New            Ctrl-N', 'Open...        Ctrl-O', 'Save           Ctrl-S',
                  'Save As...', '-', 'Exit           Alt-X']),
        ('Edit', ['Undo           Ctrl-Z', '-', 'Delete line    Ctrl-Y', 'Duplicate line Ctrl-D', '-',
                  'Find...        Ctrl-F', 'Find next      F3', 'Go to line...  Ctrl-G']),
        ('Run', ['Start/Continue F5', 'Step           F8', 'Breakpoint     F9', 'Clear breakpoints',
                 'Stop', '-', 'Output screen  F4']),
        ('Options', ['Default colours', 'Black screen', '-', 'Mouse on', 'Mouse off', '-', 'Immediate window   F6']),
        ('Help', ['Help on word   F1', 'Topics...      Shift-F1', 'Keys', '-', 'About']),
    ]

    @staticmethod
    def command_name(menu, item):
        """The command of a menu item: 'Run.Start/Continue' for Run's 'Start/Continue  F5'
        (the shortcut at the end is not part of it)."""
        item = re.sub(r'\s+(F\d+|(Ctrl|Alt|Shift)-\S+)$', '', item.strip())
        return f'{menu}.{item.strip()}'

    def menu(self, first_letter=None):
        if first_letter:
            SCREEN.keys.pending.insert(0, first_letter)
        choice = SCREEN.menubar(self.MENUS, leave_easily=True)
        if not choice:
            return None
        menu, item = choice.split('.', 1)
        return self.command_name(menu, item)

    def command(self, name):
        """Runs a menu command; returns False to leave the IDE."""
        if name == 'File.New':
            self.new_file()
        elif name == 'File.Open...':
            self.open_file()
        elif name == 'File.Save':
            self.save()
        elif name == 'File.Save As...':
            self.save_as()
        elif name == 'File.Exit':
            if self.paused_row is not None:
                return 'stop'                    # leave the paused program first
            return 'quit' if self.keep_changes() else True
        elif name == 'Edit.Undo':
            self.do_undo()
        elif name == 'Edit.Delete line':
            self.delete_line()
        elif name == 'Edit.Duplicate line':
            self.duplicate_line()
        elif name == 'Edit.Find...':
            self.find()
        elif name == 'Edit.Find next':
            self.find(again=True)
        elif name == 'Edit.Go to line...':
            self.go_to_line()
        elif name == 'Run.Start/Continue':
            if self.paused_row is not None:
                return 'continue'
            if self.breakpoints:
                self.debug(step=False)           # breakpoints: run inside the IDE to stop at them
            else:
                self.run()
        elif name == 'Run.Step':
            if self.paused_row is not None:
                return 'step'
            self.debug(step=True)
        elif name == 'Run.Breakpoint':
            self.toggle_breakpoint()
        elif name == 'Run.Clear breakpoints':
            self.breakpoints = set()
            self.message = 'All breakpoints cleared'
        elif name == 'Run.Stop':
            if self.paused_row is None:
                bell()
                self.message = 'No program is paused'
            else:
                return 'stop'
        elif name == 'Run.Output screen':
            bell()
            self.message = 'F4 shows the program\'s screen while it is paused'
        elif name == 'Options.Default colours':
            self.set_scheme('blue')
        elif name == 'Options.Black screen':
            self.set_scheme('black')
        elif name == 'Options.Immediate window':
            if self.new_session is None:
                bell()
            elif self.show_immediate and self.focus == 'editor':
                self.show_immediate = False       # hide it, giving the editor the room
            else:
                self.show_immediate, self.focus = True, 'immediate'
            self.repaint()
        elif name in ('Options.Mouse on', 'Options.Mouse off'):
            SCREEN.keys.set_mouse(name.endswith('on'))
            self.message = 'The mouse is ' + ('on' if name.endswith('on') else 'off')
        elif name == 'Help.Help on word':
            topic = self.help_topic_at_cursor(self.imm_text, self.imm_pos) if self.focus == 'immediate' \
                else self.help_topic_at_cursor()
            if topic:
                self.show_help(topic)
            else:
                self.help_topics_list()
        elif name == 'Help.Topics...':
            self.help_topics_list()
        elif name == 'Help.Keys':
            rows, cols = SCREEN.size()
            SCREEN.view(_HELP_KEYS, (4, 3, rows - 4, cols - 2), 'Keys  (Esc closes)')
        elif name == 'Help.About':
            SCREEN.alert('DDGBasic IDE;A BASIC with SQLite and DuckDB built in.;Press F1 on any keyword for its help.',
                         ['OK'])
        return True

    # Every command a menu item or a key can give (tests/ide_check.py checks the menus against it)
    COMMANDS = {
        'File.New', 'File.Open...', 'File.Save', 'File.Save As...', 'File.Exit',
        'Edit.Undo', 'Edit.Delete line', 'Edit.Duplicate line', 'Edit.Find...', 'Edit.Find next',
        'Edit.Go to line...', 'Run.Start/Continue', 'Run.Step', 'Run.Breakpoint', 'Run.Clear breakpoints',
        'Run.Stop', 'Run.Output screen', 'Options.Default colours', 'Options.Black screen', 'Options.Mouse on',
        'Options.Mouse off', 'Options.Immediate window', 'Help.Help on word', 'Help.Topics...', 'Help.Keys',
        'Help.About',
    }

    # --- the main loop ---------------------------------------------------------------------
    KEY_COMMANDS = {
        '\x0e': 'File.New', '\x0f': 'File.Open...', '\x13': 'File.Save', '\x1a': 'Edit.Undo',
        '\x19': 'Edit.Delete line', '\x04': 'Edit.Duplicate line', '\x06': 'Edit.Find...',
        'F3': 'Edit.Find next', '\x07': 'Edit.Go to line...', 'F5': 'Run.Start/Continue', 'F8': 'Run.Step',
        'F9': 'Run.Breakpoint', 'F1': 'Help.Help on word',
        'ALT-X': 'File.Exit', '\x11': 'File.Exit',
    }

    # Commands that change the text, refused while a program is paused
    EDIT_COMMANDS = ('Edit.Undo', 'Edit.Delete line', 'Edit.Duplicate line', 'File.New', 'File.Open...')

    def loop(self):
        SCREEN.keys.block_suspend = True
        SCREEN.keys.raw_off()                    # take the new setting on the next key
        self.set_scheme('blue')
        while True:
            self.draw()
            try:
                key = SCREEN.keys.read_key()
            except KeyboardInterrupt:
                self.message = 'Ctrl-C does nothing here: Alt-X (or File > Exit) leaves the IDE'
                continue
            if key is None:
                return
            if self.handle_key(key) == 'quit':
                return

    def handle_key(self, key):
        """One key, in the editor or the Immediate window. Returns 'quit' to leave the IDE,
        or, while a program is paused, 'continue', 'step' or 'stop'."""
        if key == '':
            return None
        paused = self.paused_row is not None
        if not paused or not self.message.startswith('Paused'):
            self.message = ''
        name = self.KEY_COMMANDS.get(key)
        if key == 'F10' or (key.startswith('ALT-') and key != 'ALT-X'):
            letter = key[4:] if key.startswith('ALT-') else None
            name = self.menu(letter)
            if name is None:
                return None
        if key == 'SHIFT-F1':
            name = 'Help.Topics...'
        if key == 'F6' and self.new_session is not None:
            if self.focus == 'editor':
                self.show_immediate, self.focus = True, 'immediate'
                self.repaint()
            else:
                self.focus = 'editor'
            return None
        if paused and name in self.EDIT_COMMANDS:
            bell()
            self.message = 'The program is paused: Run > Stop (or F5 to the end) before changing it'
            return None
        if self.focus == 'immediate' and name in ('Edit.Undo', 'Edit.Delete line', 'Edit.Duplicate line',
                                                 'Edit.Go to line...', 'Run.Breakpoint'):
            bell()                               # editor commands: not while typing in the Immediate window
            return None
        if name:
            result = self.command(name)
            if result in ('quit', 'continue', 'step', 'stop'):
                return result
            return None
        first, last, width = self.area()
        if key in ('CLICK', 'WHEELUP', 'WHEELDOWN') and self.show_immediate:
            r = SCREEN.keys.mouse_row
            in_pane = last + 1 < r < SCREEN.size()[0] - 1
            if key == 'CLICK' and in_pane:
                self.focus = 'immediate'
                return None
            if key == 'CLICK' and first <= r <= last:
                self.focus = 'editor'
            if key != 'CLICK' and in_pane:
                self.immediate_key(key)
                return None
        if self.focus == 'immediate' and key != 'CLICK':
            self.immediate_key(key)
            return None
        if paused and (key in (ENTER, BACKSPACE, 'DEL', TAB, 'BTAB') or (len(key) == 1 and key.isprintable())):
            bell()
            self.message = 'The program is paused: Run > Stop (or F5 to the end) before changing it'
            return None
        height = last - first + 1
        line = self.lines[self.row]
        if key in ('UP', 'DOWN', 'PGUP', 'PGDN', 'LEFT', 'RIGHT', 'HOME', 'END', 'CTRL-HOME',
                   'CTRL-END', 'CTRL-LEFT', 'CTRL-RIGHT', 'CLICK', 'WHEELUP', 'WHEELDOWN'):
            self.last_edit = None
        if key == 'UP':
            self.row = max(0, self.row - 1)
        elif key == 'DOWN':
            self.row = min(len(self.lines) - 1, self.row + 1)
        elif key == 'PGUP':
            self.row = max(0, self.row - height)
            self.top = max(0, self.top - height)
        elif key == 'PGDN':
            self.row = min(len(self.lines) - 1, self.row + height)
            self.top = min(max(0, len(self.lines) - height), self.top + height)
        elif key == 'LEFT':
            if self.col > 0:
                self.col -= 1
            elif self.row > 0:
                self.row -= 1
                self.col = len(self.lines[self.row])
        elif key == 'RIGHT':
            if self.col < len(line):
                self.col += 1
            elif self.row + 1 < len(self.lines):
                self.row, self.col = self.row + 1, 0
        elif key == 'HOME':
            indent = len(line) - len(line.lstrip(' '))
            self.col = 0 if self.col == indent else indent
        elif key == 'END':
            self.col = len(line)
        elif key == 'CTRL-HOME':
            self.row = self.col = 0
        elif key == 'CTRL-END':
            self.row = len(self.lines) - 1
            self.col = len(self.lines[self.row])
        elif key in ('CTRL-LEFT', 'CTRL-RIGHT'):
            self.word_move(-1 if key == 'CTRL-LEFT' else 1)
        elif key == 'CLICK':
            r, c = SCREEN.keys.mouse_row, SCREEN.keys.mouse_col
            if first <= r <= last:
                self.row = min(len(self.lines) - 1, self.top + r - first)
                self.col = max(0, self.left + c - 2)
            elif r == 1:
                # A click on the menu bar: hand the same click to the menu bar, which opens
                # the menu under it
                SCREEN.keys.pending[0:0] = list(f'\x1b[<0;{c};1M')
                name = self.menu()
                if name:
                    result = self.command(name)
                    if result in ('quit', 'continue', 'step', 'stop'):
                        return result
        elif key in ('WHEELUP', 'WHEELDOWN'):
            step = -3 if key == 'WHEELUP' else 3
            self.top = max(0, min(self.top + step, max(0, len(self.lines) - height)))
            self.row = max(self.top, min(self.row, self.top + height - 1, len(self.lines) - 1))
        elif key == 'INS':
            self.insert = not self.insert
        elif key == ENTER:
            self.enter()
        elif key == BACKSPACE:
            self.backspace()
        elif key == 'DEL':
            self.delete()
        elif key == TAB:
            self.tab()
        elif key == 'BTAB':
            self.tab(back=True)
        elif len(key) == 1 and key.isprintable():
            self.type_char(key)
        elif key == ESC:
            pass
        else:
            bell()
        self.col = min(self.col, len(self.lines[self.row]))
        return None


def run_ide(path, runner, help_topics, get_help, new_session=None, new_program=None):
    """Opens the IDE on path (or a new program) and returns when the user leaves it.
    new_session() makes the interpreter of the Immediate window; new_program(source,
    folder) makes one for a debug run."""
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        print("The IDE needs an interactive terminal.", file=sys.stderr)
        return 1
    editor = Editor(path, runner, help_topics, get_help, new_session, new_program)
    mouse_before = SCREEN.keys.mouse_wanted
    SCREEN.keys.set_mouse(True)              # off by default on Windows; the IDE wants clicks
    try:
        editor.loop()
    finally:
        SCREEN.keys.set_mouse(mouse_before)
        SCREEN.keys.block_suspend = False
        if editor.session is not None:
            try:
                editor.session.close()
            except Exception:
                pass
        SCREEN.restore()
        sys.stdout.write('\x1b[0m\x1b[2J\x1b[H')
        sys.stdout.flush()
    return 0
