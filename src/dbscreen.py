"""
Text-mode screen support for DbBasic, in the style of 1990s BASIC and xBase:
cursor positioning, colours, boxes, @ SAY/GET entry fields edited with READ,
light-bar menus and a scrolling query browser.

Everything is drawn with ANSI escape sequences written to stdout, so PRINT
keeps working in between. Keys are read one at a time from the terminal
(cbreak mode on macOS/Linux, msvcrt on Windows). When stdin is not a
terminal, keys are read from it as a stream, so scripts can be tested with
scripted keystrokes.

Rows and columns are 1-based: (1, 1) is the top-left corner, as in LOCATE.
"""
import atexit
import json
import os
import re
import shutil
import sys
import time

# QBasic colour numbers 0-15 -> ANSI colour (0-7); 8-15 are the bright versions
_ANSI = [0, 4, 2, 6, 1, 5, 3, 7]

# Key names returned for keys that are not characters
_CSI_KEYS = {
    'A': 'UP', 'B': 'DOWN', 'C': 'RIGHT', 'D': 'LEFT', 'H': 'HOME', 'F': 'END', 'Z': 'BTAB',
    '1~': 'HOME', '7~': 'HOME', '4~': 'END', '8~': 'END', '2~': 'INS', '3~': 'DEL',
    '5~': 'PGUP', '6~': 'PGDN',
    '11~': 'F1', '12~': 'F2', '13~': 'F3', '14~': 'F4', '15~': 'F5', '17~': 'F6',
    '18~': 'F7', '19~': 'F8', '20~': 'F9', '21~': 'F10', '23~': 'F11', '24~': 'F12',
}
_SS3_KEYS = {'P': 'F1', 'Q': 'F2', 'R': 'F3', 'S': 'F4', 'A': 'UP', 'B': 'DOWN',
             'C': 'RIGHT', 'D': 'LEFT', 'H': 'HOME', 'F': 'END'}
_WIN_KEYS = {'H': 'UP', 'P': 'DOWN', 'K': 'LEFT', 'M': 'RIGHT', 'G': 'HOME', 'O': 'END',
             'R': 'INS', 'S': 'DEL', 'I': 'PGUP', 'Q': 'PGDN', '\x0f': 'BTAB',
             ';': 'F1', '<': 'F2', '=': 'F3', '>': 'F4', '?': 'F5', '@': 'F6',
             'A': 'F7', 'B': 'F8', 'C': 'F9', 'D': 'F10', '\x85': 'F11', '\x86': 'F12'}

ENTER, ESC, TAB, BACKSPACE = '\r', '\x1b', '\t', '\x08'

SAVED_PREFIX = '\x00SCREEN:'   # marks a string made by SAVESCREEN


class ScreenError(Exception):
    pass


class KeyReader:
    """Reads single keys. Characters come back as themselves (Enter is CHR$(13),
    Esc CHR$(27), Tab CHR$(9), Backspace CHR$(8)); other keys as names such as
    'UP', 'PGDN' or 'F1'."""

    def __init__(self):
        self.pending = []
        self.is_tty = sys.stdin.isatty()
        self.windows = os.name == 'nt'
        self._saved_mode = None

    # --- terminal mode (macOS/Linux) -----------------------------------
    def raw_on(self):
        """Stop the terminal echoing and buffering keys until raw_off()."""
        if self.is_tty and not self.windows and self._saved_mode is None:
            import termios
            fd = sys.stdin.fileno()
            self._saved_mode = termios.tcgetattr(fd)
            mode = termios.tcgetattr(fd)
            mode[3] &= ~(termios.ECHO | termios.ICANON)     # no echo, a key at a time
            mode[0] &= ~termios.IXON                        # Ctrl-S / Ctrl-Q reach the program
            mode[6][termios.VMIN], mode[6][termios.VTIME] = 1, 0
            # Let Ctrl-Y, Ctrl-V and Ctrl-O through (on macOS Ctrl-Y would suspend the program).
            # Ctrl-C still stops it.
            try:
                disabled = os.fpathconf(fd, 'PC_VDISABLE')
            except (OSError, ValueError):
                disabled = 0
            slots = [getattr(termios, n) for n in ('VDSUSP', 'VLNEXT', 'VDISCARD') if hasattr(termios, n)]
            if sys.platform == 'darwin' and not hasattr(termios, 'VDSUSP'):
                slots.append(11)                            # VDSUSP in <sys/termios.h>
            for slot in slots:
                mode[6][slot] = bytes([disabled]) if isinstance(mode[6][slot], bytes) else disabled
            termios.tcsetattr(fd, termios.TCSANOW, mode)    # TCSAFLUSH would drop keys typed ahead

    def raw_off(self):
        if self._saved_mode is not None:
            import termios
            termios.tcsetattr(sys.stdin.fileno(), termios.TCSADRAIN, self._saved_mode)
            self._saved_mode = None

    # --- reading -------------------------------------------------------
    def _read_char(self, timeout=None):
        """One character, or None when the timeout passes or input has ended."""
        if self.pending:
            return self.pending.pop(0)
        if not self.is_tty:
            ch = sys.stdin.read(1)
            return ch or None
        if self.windows:
            import msvcrt
            if timeout is not None:
                deadline = time.time() + timeout
                while not msvcrt.kbhit():
                    if time.time() >= deadline:
                        return None
                    time.sleep(0.01)
            return msvcrt.getwch()
        import select
        self.raw_on()
        fd = sys.stdin.fileno()
        ready, _, _ = select.select([fd], [], [], timeout)
        if not ready:
            return None
        first = os.read(fd, 1)
        if not first:
            return None
        # Complete a UTF-8 character
        extra = 0
        if first[0] >= 0xF0: extra = 3
        elif first[0] >= 0xE0: extra = 2
        elif first[0] >= 0xC0: extra = 1
        data = first + (os.read(fd, extra) if extra else b'')
        return data.decode('utf-8', errors='replace')

    def read_key(self, timeout=None):
        """The next key, waiting up to timeout seconds (None waits forever).
        Returns '' if no key arrives in time, or None when input has ended."""
        ch = self._read_char(timeout)
        if ch is None:
            return '' if (timeout is not None and self.is_tty) else None
        if self.windows and self.is_tty and ch in ('\x00', '\xe0'):
            return _WIN_KEYS.get(self._read_char() or '', '')
        if ch == '\x1b':
            nxt = self._read_char(0.05)
            if nxt == '[':
                seq = ''
                while True:
                    c = self._read_char(0.05)
                    if c is None:
                        break
                    seq += c
                    if '@' <= c <= '~':
                        break
                return _CSI_KEYS.get(seq, '')
            if nxt == 'O':
                return _SS3_KEYS.get(self._read_char(0.05) or '', '')
            if nxt is not None:
                self.pending.insert(0, nxt)
            return ESC
        if ch in ('\n', '\r'):
            return ENTER
        if ch in ('\x7f', '\x08'):
            return BACKSPACE
        return ch


class Field:
    """One GET entry field."""

    def __init__(self, row, col, var_name, value, picture, valid, numeric):
        self.row, self.col = row, col
        self.var_name, self.valid = var_name, valid
        self.numeric = numeric
        self.upper = False
        width = None
        template = picture or ''
        if template.startswith('@'):
            funcs, _, template = template[1:].partition(' ')
            funcs = funcs.upper()
            self.upper = '!' in funcs
            m = re.search(r'S(\d+)', funcs)
            if m:
                width = int(m.group(1))
        self.template = '' if numeric else template
        self.mask = template if numeric else ''
        if self.template:
            width = len(self.template)
        elif width is None:
            width = len(template) if (numeric and template) else (10 if numeric else max(len(value), 20))
        self.width = width
        self.buffer = self._initial_buffer(value)

    def _editable(self, i):
        return not self.template or self.template[i] in '9#ANX!'

    def _accepts(self, i, ch):
        if self.numeric:
            return ch.isdigit() or ch in '.-+,'
        if not self.template:
            return ch.isprintable()
        m = self.template[i]
        if m == '9': return ch.isdigit()
        if m == '#': return ch.isdigit() or ch in ' +-'
        if m == 'A': return ch.isalpha()
        if m == 'N': return ch.isalnum()
        return ch.isprintable()

    def _initial_buffer(self, value):
        if self.numeric:
            text = format_number(value)
            return list(text[:self.width].ljust(self.width))
        text = str(value)
        if not self.template:
            return list(text[:self.width].ljust(self.width))
        if len(text) == len(self.template):
            return list(text)
        chars = iter(c for c in text)
        return [next(chars, ' ') if self._editable(i) else self.template[i] for i in range(self.width)]

    def text(self):
        """The field's value as it should be stored."""
        raw = ''.join(self.buffer)
        if self.template and all(raw[i] == ' ' for i in range(self.width) if self._editable(i)):
            return ''
        return raw.rstrip()

    def value(self):
        """The typed value, converted for a numeric field. Raises ValueError."""
        text = self.text()
        if not self.numeric:
            return text
        text = text.replace(',', '').strip()
        return float(text) if text else 0.0

    def first_pos(self):
        return next((i for i in range(self.width) if self._editable(i)), 0)

    def _step(self, pos, direction):
        i = pos + direction
        while 0 <= i < self.width and not self._editable(i):
            i += direction
        return i if 0 <= i < self.width else pos

    def last_pos(self):
        return next((i for i in range(self.width - 1, -1, -1) if self._editable(i)), self.width - 1)

    def edit_key(self, key, pos, insert):
        """Applies an editing key; returns the new cursor position. Sets self.filled when
        a character was typed into the field's last position (for SET AUTOADVANCE)."""
        self.filled = False
        if key == 'LEFT':
            return self._step(pos, -1)
        if key == 'RIGHT':
            return self._step(pos, 1)
        if key == 'HOME':
            return self.first_pos()
        if key == 'END':
            end = len(''.join(self.buffer).rstrip())
            return min(end, self.width - 1)
        if key == '\x19':                      # Ctrl-Y clears the field
            self.buffer = [' ' if self._editable(i) else self.template[i] for i in range(self.width)]
            return self.first_pos()
        if key == BACKSPACE:
            prev = self._step(pos, -1)
            if prev == pos and (pos == self.first_pos()):
                return pos
            pos = prev
            key = 'DEL'
        if key == 'DEL':
            if self.template:
                self.buffer[pos] = ' '
            else:
                del self.buffer[pos]
                self.buffer.append(' ')
            return pos
        if len(key) == 1 and key.isprintable():
            if not self._accepts(pos, key):
                bell()
                return pos
            if self.upper or (self.template and self.template[pos] == '!'):
                key = key.upper()
            if insert and not self.template:
                if self.buffer[-1] != ' ':
                    bell()
                    return pos
                self.buffer.insert(pos, key)
                self.buffer.pop()
            else:
                self.buffer[pos] = key
            self.filled = pos == self.last_pos()
            return self._step(pos, 1) if pos < self.width - 1 else pos
        return pos


def format_number(value):
    """A number as PRINT shows it, without the leading space."""
    try:
        f = float(value)
    except (TypeError, ValueError):
        return str(value)
    return str(int(f)) if f == int(f) and abs(f) < 1e15 else repr(f)


def bell():
    sys.stdout.write('\a')
    sys.stdout.flush()


class Screen:
    def __init__(self):
        self.keys = KeyReader()
        self.fg, self.bg = 7, 0
        self.field_fg, self.field_bg = 0, 7
        self.gets = []
        self.last_key = ''
        self.used = False
        self.auto_advance = False   # SET AUTOADVANCE ON: filling a field moves to the next one
        # A copy of what is on the screen, one (char, fg, bg) cell per position, so that
        # SAVESCREEN, MENU and BROWSE can put back what they cover (ANSI can't read it back)
        self.rows, self.cols = self.size()
        self.cells = self._blank(self.rows, self.cols, 7, 0)
        self.cur_row, self.cur_col = 1, 1

    # --- output helpers ------------------------------------------------
    def _activate(self):
        if self.used:
            return
        self.used = True
        if os.name == 'nt':
            try:   # let the Windows console interpret ANSI sequences
                import ctypes
                k32 = ctypes.windll.kernel32
                handle = k32.GetStdHandle(-11)
                mode = ctypes.c_uint32()
                if k32.GetConsoleMode(handle, ctypes.byref(mode)):
                    k32.SetConsoleMode(handle, mode.value | 0x0004)
            except Exception:
                pass
        atexit.register(self.restore)

    def restore(self):
        """Puts the terminal back as it was: normal colours, cursor shown, keys echoed."""
        self.keys.raw_off()
        if self.used:
            sys.stdout.write('\x1b[0m\x1b[?25h')
            sys.stdout.flush()

    def _w(self, text):
        self._activate()
        sys.stdout.write(text)
        sys.stdout.flush()

    @staticmethod
    def _sgr(fg, bg):
        fg_code = (90 if fg >= 8 else 30) + _ANSI[fg % 8]
        bg_code = (100 if bg >= 8 else 40) + _ANSI[bg % 8]
        return f'\x1b[0;{fg_code};{bg_code}m'

    def _normal(self):
        return self._sgr(self.fg, self.bg)

    def _field_colour(self):
        return self._sgr(self.field_fg, self.field_bg)

    @staticmethod
    def size():
        cols, rows = shutil.get_terminal_size((80, 24))
        return rows, cols

    @staticmethod
    def _blank(rows, cols, fg, bg):
        return [[(' ', fg, bg) for _ in range(cols)] for _ in range(rows)]

    def _put(self, row, col, text, fg, bg):
        """Records text in the screen copy and returns the ANSI output that draws it."""
        r = row - 1
        if 0 <= r < self.rows:
            line = self.cells[r]
            for i, ch in enumerate(text):
                c = col - 1 + i
                if 0 <= c < self.cols:
                    line[c] = (ch, fg, bg)
        self.cur_row, self.cur_col = row, col + len(text)
        return f'\x1b[{row};{col}H' + self._sgr(fg, bg) + text

    def track(self, text, emit=True):
        """PRINT and INPUT text written at the cursor: kept in the screen copy, following the
        terminal's newlines, tab stops, line wrap and scrolling. emit=False only records it."""
        for ch in text:
            if ch == '\n':
                self._newline()
            elif ch == '\r':
                self.cur_col = 1
            elif ch == '\t':
                self.cur_col = min(((self.cur_col - 1) // 8 + 1) * 8 + 1, self.cols)
            elif ch == '\a' or not ch.isprintable():
                continue
            else:
                if self.cur_col > self.cols:
                    self._newline()
                if 1 <= self.cur_row <= self.rows:
                    self.cells[self.cur_row - 1][self.cur_col - 1] = (ch, self.fg, self.bg)
                self.cur_col += 1
        if emit:
            self._w(text)

    def _newline(self):
        self.cur_col = 1
        if self.cur_row >= self.rows:
            self.cells.pop(0)
            self.cells.append([(' ', self.fg, self.bg) for _ in range(self.cols)])
        else:
            self.cur_row += 1

    def _draw_cells(self, r1, c1, block):
        """ANSI output for a block of cells with its top-left corner at r1, c1."""
        out = []
        for n, line in enumerate(block):
            out.append(f'\x1b[{r1 + n};{c1}H')
            colour = None
            for ch, fg, bg in line:
                if (fg, bg) != colour:
                    out.append(self._sgr(fg, bg))
                    colour = (fg, bg)
                out.append(ch)
            row = r1 + n - 1
            if 0 <= row < self.rows:
                for i, cell in enumerate(line):
                    if 0 <= c1 - 1 + i < self.cols:
                        self.cells[row][c1 - 1 + i] = cell
        return ''.join(out)

    def save(self, r1=None, c1=None, r2=None, c2=None):
        """SAVESCREEN: the area's contents and the cursor, as a string RESTSCREEN can put back."""
        r1, c1 = r1 or 1, c1 or 1
        r2, c2 = r2 or self.rows, c2 or self.cols
        r1, c1 = max(1, r1), max(1, c1)
        r2, c2 = min(self.rows, r2), min(self.cols, c2)
        if r2 < r1 or c2 < c1:
            raise ScreenError("SAVESCREEN area is empty.")
        block = [self.cells[r][c1 - 1:c2] for r in range(r1 - 1, r2)]
        return SAVED_PREFIX + json.dumps({'at': [r1, c1], 'cursor': [self.cur_row, self.cur_col],
                                          'cells': [[list(cell) for cell in line] for line in block]},
                                         ensure_ascii=False, separators=(',', ':'))

    def restore_saved(self, saved):
        """RESTSCREEN: puts back an area saved by SAVESCREEN, and the cursor."""
        if not isinstance(saved, str) or not saved.startswith(SAVED_PREFIX):
            raise ScreenError("RESTSCREEN needs a value returned by SAVESCREEN.")
        try:
            data = json.loads(saved[len(SAVED_PREFIX):])
            r1, c1 = data['at']
            block = [[tuple(cell) for cell in line] for line in data['cells']]
        except (ValueError, KeyError, TypeError):
            raise ScreenError("RESTSCREEN needs a value returned by SAVESCREEN.")
        row, col = data.get('cursor', [r1, c1])
        self._w(self._draw_cells(r1, c1, block) + self._normal() + f'\x1b[{row};{col}H')
        self.cur_row, self.cur_col = row, col

    # --- statements ----------------------------------------------------
    def color(self, fg=None, bg=None, field_fg=None, field_bg=None):
        for v in (fg, bg, field_fg, field_bg):
            if v is not None and not 0 <= v <= 15:
                raise ScreenError("COLOR values must be 0 to 15.")
        if fg is not None: self.fg = fg
        if bg is not None: self.bg = bg
        if field_fg is not None: self.field_fg = field_fg
        if field_bg is not None: self.field_bg = field_bg
        self._w(self._normal())

    def cls(self):
        self.gets = []
        self.rows, self.cols = self.size()     # the terminal may have been resized
        self.cells = self._blank(self.rows, self.cols, self.fg, self.bg)
        self.cur_row, self.cur_col = 1, 1
        self._w(self._normal() + '\x1b[2J\x1b[H')

    def locate(self, row, col):
        self.cur_row, self.cur_col = max(1, row), max(1, col)
        self._w(f'\x1b[{self.cur_row};{self.cur_col}H')

    def say(self, row, col, text):
        self._w(self._put(row, col, text, self.fg, self.bg))

    def box(self, r1, c1, r2, c2, title='', double=False):
        if r2 - r1 < 1 or c2 - c1 < 1:
            raise ScreenError("BOX needs a bottom-right corner below and to the right of the top-left corner.")
        tl, tr, bl, br, h, v = ('╔', '╗', '╚', '╝', '═', '║') if double else ('┌', '┐', '└', '┘', '─', '│')
        inner = c2 - c1 - 1
        top = h * inner
        if title:
            label = f' {title} '[:inner]
            start = (inner - len(label)) // 2
            top = top[:start] + label + top[start + len(label):]
        out = [self._put(r1, c1, tl + top + tr, self.fg, self.bg)]
        for r in range(r1 + 1, r2):
            out.append(self._put(r, c1, v + ' ' * inner + v, self.fg, self.bg))
        out.append(self._put(r2, c1, bl + h * inner + br, self.fg, self.bg))
        self._w(''.join(out))

    # --- GET / READ ----------------------------------------------------
    def add_get(self, row, col, var_name, value, picture, valid, numeric, target=None,
                message=None, when=None, lookup=None):
        field = Field(row, col, var_name, value, picture, valid, numeric)
        field.target = target       # where READ stores the value (the interpreter's description)
        field.message, field.when, field.lookup = message, when, lookup
        self.gets.append(field)
        self._draw_field(field)
        return field

    def _draw_field(self, field, cursor=None):
        out = self._put(field.row, field.col, ''.join(field.buffer), self.field_fg, self.field_bg)
        if cursor is not None:
            out += f'\x1b[{field.row};{field.col + cursor}H'
        self._w(out + ('' if cursor is not None else self._normal()))

    def read(self, assign, check_valid, current_values, check_when=None, lookup=None):
        """Edits the pending GET fields. assign(field, value) stores a field's value,
        check_valid(field) evaluates its VALID condition, check_when(field) its WHEN
        condition, and current_values(fields) returns their values. lookup(field) returns
        (columns, rows) for a field with LOOKUP. Esc puts back the values the fields had
        when READ started. Returns the key that ended it."""
        fields, self.gets = self.gets, []
        if not fields:
            return ''
        saved = current_values(fields)

        def allowed(i):
            f = fields[i]
            return getattr(f, 'when', None) is None or check_when is None or check_when(f)

        def step(i, direction):
            """The next field in a direction whose WHEN allows it, or None."""
            i += direction
            while 0 <= i < len(fields):
                if allowed(i):
                    return i
                i += direction
            return None

        index = step(-1, 1)
        if index is None:                      # every field is switched off by WHEN
            self.last_key = ENTER
            return ENTER
        insert = True
        pos = fields[index].first_pos()
        fresh = True        # the first key typed into a numeric field replaces its value
        message_under = None
        self._w('\x1b[?25h')
        try:
            while True:
                field = fields[index]
                self._draw_field(field, pos)
                key = self.keys.read_key()
                if key is None:            # input ended: give up as if Esc was pressed
                    key = ESC
                if message_under:          # a VALID message stays up until the next key
                    self.restore_saved(message_under)
                    message_under = None
                self.last_key = key
                if key == ESC:
                    for f, value in zip(fields, saved):
                        assign(f, value)
                        f.buffer = f._initial_buffer(value)
                        self._draw_field(f)
                    return key
                if key == 'F2' and getattr(field, 'lookup', None) is not None and lookup:
                    if self._pick(field, lookup) is not None:
                        pos = field.first_pos()
                    continue
                if key in (ENTER, TAB, 'DOWN', 'UP', 'BTAB', 'PGDN', 'PGUP', '\x17'):
                    try:
                        value = field.value()
                    except ValueError:
                        bell()
                        continue
                    if getattr(field, 'lookup', None) is not None and lookup and str(value).strip() \
                            and not self._in_lookup(field, value, lookup):
                        # Not an allowed value: offer the list, starting at the closest match
                        if self._pick(field, lookup, value) is None:
                            bell()
                            continue
                        value = field.value()
                    assign(field, value)
                    if field.valid is not None and not check_valid(field):
                        bell()
                        if getattr(field, 'message', None):
                            message_under = self._show_message(field.message)
                        continue
                    self._draw_field(field)
                    if key in ('PGDN', 'PGUP', '\x17'):
                        return key
                    nxt = step(index, -1 if key in ('UP', 'BTAB') else 1)
                    if nxt is None:
                        if key in (ENTER, TAB, 'DOWN'):
                            return key         # past the last field
                        nxt = index            # already at the first field
                    index = nxt
                    pos = fields[index].first_pos()
                    fresh = True
                    continue
                if key == 'INS':
                    insert = not insert
                    continue
                if fresh and field.numeric and len(key) == 1 and key.isprintable():
                    field.buffer = [' '] * field.width
                    pos = 0
                fresh = False
                pos = field.edit_key(key, pos, insert)
                if self.auto_advance and getattr(field, 'filled', False):
                    # The field is full: go on as if Enter had been pressed
                    self.keys.pending.insert(0, ENTER)
        finally:
            if message_under:
                self.restore_saved(message_under)
            self._w(self._normal())

    def _show_message(self, text):
        """Shows a message on the bottom line; returns what it covered, for restore_saved."""
        under = self.save(self.rows, 1, self.rows, self.cols)
        self._w(self._put(self.rows, 1, (' ' + str(text))[:self.cols].ljust(self.cols), self.field_fg, self.field_bg)
                + self._normal())
        return under

    @staticmethod
    def _matches(a, b):
        return str(a).strip().upper() == str(b).strip().upper()

    def _in_lookup(self, field, value, lookup):
        columns, rows = lookup(field)
        if isinstance(value, float) and value == int(value):
            value = int(value)
        return any(self._matches(row[0], value) for row in rows)

    def _pick(self, field, lookup, typed=''):
        """Opens the LOOKUP list under the field. Fills the field with the first column of
        the chosen row and returns that value, or returns None for Esc."""
        columns, rows = lookup(field)
        if not rows:
            bell()
            return None
        typed = str(typed).strip().upper()
        start = next((i for i, r in enumerate(rows) if typed and str(r[0]).upper().startswith(typed)), 0)
        width = min(self.cols, max(24, 4 + sum(min(30, max(len(str(c)), max(len(str(r[i])) for r in rows))) + 3
                                                for i, c in enumerate(columns))))
        height = min(len(rows), 10) + 5
        top = field.row + 1 if field.row + height <= self.rows else max(1, field.row - height)
        left = max(1, min(field.col, self.cols - width + 1))
        chosen = self.browse(columns, [list(r) for r in rows], (top, left, top + height - 1, left + width - 1),
                             'Choose', start=start)
        if chosen < 0:
            return None
        value = rows[chosen][0]
        if isinstance(value, float) and value == int(value):
            value = int(value)
        field.buffer = field._initial_buffer('' if value is None else value)
        self._draw_field(field)
        return value

    # --- MENUBAR -------------------------------------------------------
    def menubar(self, menus, row=1):
        """A menu bar across the screen with pull-down menus. menus is a list of
        (title, [items]); an item '-' is a separator. Returns "Title.Item", "Title" for
        a title with no items, or "" for Esc. The bar stays drawn; the pull-downs don't."""
        if not menus:
            raise ScreenError("MENUBAR needs at least one menu.")
        positions, x = [], 2
        for title, _ in menus:
            positions.append(x)
            x += len(title) + 3
        current, opened, item = 0, False, 0
        underneath = None
        cursor = (self.cur_row, self.cur_col)   # put back afterwards, so PRINT carries on where it was

        def selectable(items, i):
            return items[i].strip() != '-'

        def first_item(items):
            return next((i for i in range(len(items)) if selectable(items, i)), 0)

        def draw_bar():
            out = [self._put(row, 1, ' ' * self.cols, self.field_fg, self.field_bg)]
            for n, (title, _) in enumerate(menus):
                fg, bg = (self.fg, self.bg) if n == current else (self.field_fg, self.field_bg)
                out.append(self._put(row, positions[n] - 1, f' {title} ', fg, bg))
            self._w(''.join(out) + self._normal())

        def dropdown_area(n):
            items = menus[n][1]
            width = max(len(i) for i in items) + 2
            left = max(1, min(positions[n] - 1, self.cols - width - 1))
            return row + 1, left, row + 2 + len(items), left + width + 1

        def draw_dropdown():
            items = menus[current][1]
            top, left, bottom, right = dropdown_area(current)
            self.box(top, left, bottom, right)
            width = right - left - 1
            out = []
            for n, text in enumerate(items):
                if not selectable(items, n):
                    out.append(self._put(top + 1 + n, left, '├' + '─' * width + '┤', self.fg, self.bg))
                    continue
                fg, bg = (self.field_fg, self.field_bg) if n == item else (self.fg, self.bg)
                out.append(self._put(top + 1 + n, left + 1, (' ' + text).ljust(width), fg, bg))
            self._w(''.join(out) + self._normal())

        def open_menu():
            nonlocal opened, item, underneath
            close_menu()
            if menus[current][1]:
                underneath = self.save(*dropdown_area(current))
                opened, item = True, first_item(menus[current][1])
            else:
                opened = False

        def close_menu():
            nonlocal opened, underneath
            if underneath:
                self.restore_saved(underneath)
                underneath = None
            opened = False

        def move(items, i, direction):
            for _ in range(len(items)):
                i = (i + direction) % len(items)
                if selectable(items, i):
                    return i
            return i

        self._w('\x1b[?25l')
        try:
            while True:
                draw_bar()
                if opened:
                    draw_dropdown()
                key = self.keys.read_key()
                if key is None:
                    key = ESC
                self.last_key = key
                title, items = menus[current]
                if not opened:
                    if key == ESC:
                        return ''
                    if key in ('RIGHT', TAB):
                        current = (current + 1) % len(menus)
                    elif key in ('LEFT', 'BTAB'):
                        current = (current - 1) % len(menus)
                    elif key in (ENTER, 'DOWN'):
                        if not items:
                            return title
                        open_menu()
                    elif len(key) == 1:
                        hits = [n for n, (t, _) in enumerate(menus) if t.strip()[:1].upper() == key.upper()]
                        if hits:
                            current = hits[0]
                            if not menus[current][1]:
                                return menus[current][0]
                            open_menu()
                    continue
                if key == ESC:
                    close_menu()
                elif key == 'DOWN':
                    item = move(items, item, 1)
                elif key == 'UP':
                    item = move(items, item, -1)
                elif key == 'HOME':
                    item = first_item(items)
                elif key == 'END':
                    item = move(items, 0, -1)
                elif key in ('RIGHT', 'LEFT', TAB, 'BTAB'):
                    current = (current + (1 if key in ('RIGHT', TAB) else -1)) % len(menus)
                    open_menu()
                elif key == ENTER:
                    return f'{title}.{items[item].strip()}'
                elif len(key) == 1:
                    hits = [n for n, text in enumerate(items)
                            if selectable(items, n) and text.strip()[:1].upper() == key.upper()]
                    if hits:
                        return f'{title}.{items[hits[0]].strip()}'
        finally:
            close_menu()
            draw_bar_final = [self._put(row, 1, ' ' * self.cols, self.field_fg, self.field_bg)]
            for n, (title, _) in enumerate(menus):
                draw_bar_final.append(self._put(row, positions[n] - 1, f' {title} ', self.field_fg, self.field_bg))
            self.cur_row, self.cur_col = cursor
            self._w(''.join(draw_bar_final) + self._normal() + f'\x1b[{cursor[0]};{cursor[1]}H' + '\x1b[?25h')

    # --- ALERT ---------------------------------------------------------
    def alert(self, message, buttons):
        """A centred message box with buttons. Returns the chosen button (from 1), or 0 for Esc.
        A ';' in the message starts a new line."""
        buttons = [str(b) for b in buttons] or ['OK']
        lines = str(message).split(';')
        labels = [f' {b} ' for b in buttons]
        bar = '  '.join(labels)
        inner = min(self.cols - 2, max(max(len(line) for line in lines), len(bar), 16) + 4)
        height = len(lines) + 4
        top = max(1, (self.rows - height) // 2 + 1)
        left = max(1, (self.cols - inner - 2) // 2 + 1)
        bottom, right = top + height - 1, left + inner + 1
        underneath = self.save(top, left, min(bottom, self.rows), min(right, self.cols))
        self.box(top, left, bottom, right, double=True)
        for n, line in enumerate(lines):
            self._w(self._put(top + 1 + n, left + 1, line.strip()[:inner].center(inner), self.fg, self.bg))
        choice = 0
        self._w('\x1b[?25l')
        try:
            while True:
                col = left + 1 + (inner - len(bar)) // 2
                out = []
                for n, label in enumerate(labels):
                    fg, bg = (self.field_fg, self.field_bg) if n == choice else (self.fg, self.bg)
                    out.append(self._put(bottom - 1, col, label, fg, bg))
                    col += len(label) + 2
                self._w(''.join(out) + self._normal())
                key = self.keys.read_key()
                if key is None:
                    key = ESC
                self.last_key = key
                if key == ESC:
                    return 0
                if key == ENTER:
                    return choice + 1
                if key in ('RIGHT', TAB, 'DOWN'):
                    choice = (choice + 1) % len(labels)
                elif key in ('LEFT', 'BTAB', 'UP'):
                    choice = (choice - 1) % len(labels)
                elif len(key) == 1:
                    hits = [n for n, b in enumerate(buttons) if b.strip()[:1].upper() == key.upper()]
                    if hits:
                        return hits[0] + 1
        finally:
            self.restore_saved(underneath)
            self._w('\x1b[?25h')

    # --- MENU ----------------------------------------------------------
    def menu(self, row, col, items):
        """A boxed light-bar menu. Returns the chosen item number (1-based), or 0 for Esc."""
        if not items:
            raise ScreenError("MENU needs at least one item.")
        items = [str(i) for i in items]
        width = max(len(i) for i in items) + 2
        underneath = self.save(row, col, row + len(items) + 1, col + width + 1)
        self.box(row, col, row + len(items) + 1, col + width + 1)
        choice = 0
        self._w('\x1b[?25l')
        try:
            while True:
                for n, item in enumerate(items):
                    fg, bg = (self.field_fg, self.field_bg) if n == choice else (self.fg, self.bg)
                    self._w(self._put(row + 1 + n, col + 1, ' ' + item.ljust(width - 1), fg, bg) + self._normal())
                key = self.keys.read_key()
                if key is None:
                    key = ESC
                self.last_key = key
                if key == ESC:
                    return 0
                if key == ENTER:
                    return choice + 1
                if key in ('DOWN', 'RIGHT', TAB):
                    choice = (choice + 1) % len(items)
                elif key in ('UP', 'LEFT', 'BTAB'):
                    choice = (choice - 1) % len(items)
                elif key in ('HOME', 'PGUP'):
                    choice = 0
                elif key in ('END', 'PGDN'):
                    choice = len(items) - 1
                elif len(key) == 1:
                    hits = [n for n, item in enumerate(items) if item.strip()[:1].upper() == key.upper()]
                    if hits:
                        return hits[0] + 1
        finally:
            self.restore_saved(underneath)       # put back what the menu covered
            self._w('\x1b[?25h')

    # --- BROWSE --------------------------------------------------------
    def browse(self, columns, rows, area=None, title='', save=None, hidden=(), locked=(), add=None, delete=None, start=0):
        """A scrolling grid. Returns the index of the chosen row, or -1 for Esc.

        With save, the grid is editable: Left/Right move between cells, Enter (or typing)
        edits the current cell, and save(row_index, col_index, value) stores the new value,
        returning an error message or None. Columns in hidden are not shown; columns in
        locked can't be edited. rows is updated in place with the saved values.

        With add, Ins calls add(), which inserts a row, reloads rows in place and returns the
        index of the new row (or None if it isn't known), or False when cancelled. With delete,
        Del asks for confirmation and calls delete(row_index), which returns an error or None."""
        screen_rows, screen_cols = self.size()
        r1, c1, r2, c2 = area or (1, 1, screen_rows, screen_cols)
        if r2 - r1 < 4 or c2 - c1 < 10:
            raise ScreenError("BROWSE area is too small.")
        visible = [i for i in range(len(columns)) if i not in hidden]
        if not visible:
            raise ScreenError("BROWSE has no columns to show.")

        def show(v):
            if v is None:
                return ''
            return format_number(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else str(v)

        def layout():
            cells = [[show(v) for v in row] for row in rows]
            widths = [min(30, max([len(str(c))] + [len(r[i]) for r in cells])) for i, c in enumerate(columns)]
            return cells, widths

        cells, widths = layout()
        page = r2 - r1 - 4                     # rows between the header line and the status line
        inner = c2 - c1 - 1
        top, current, first_col, cur_col = 0, 0, 0, 0   # cur_col indexes visible[]
        if 0 < start < len(rows):
            current = start
            top = max(0, start - (page - 1))
        message = ''
        underneath = self.save(r1, c1, r2, c2)
        self.box(r1, c1, r2, c2, title)
        self._w('\x1b[?25l')

        def line(values):
            text = ' │ '.join(str(values[i])[:widths[i]].ljust(widths[i]) for i in visible[first_col:])
            return (' ' + text)[:inner].ljust(inner)

        def cell_offset(n):
            """Column within the grid where visible column n starts."""
            return 1 + sum(widths[i] + 3 for i in visible[first_col:n])

        def edit_cell(screen_row, n, first_key):
            ci = visible[n]
            raw = rows[current][ci]
            numeric = isinstance(raw, (int, float)) and not isinstance(raw, bool)
            offset = cell_offset(n)
            width = max(1, min(max(widths[ci], len(show(raw)), 10), inner - offset))
            field = Field(screen_row, c1 + 1 + offset, '', '' if raw is None else raw, f'@S{width}', None, numeric)
            pos, insert = field.first_pos(), True
            if first_key:                      # typing starts a new value, as in a spreadsheet
                field.buffer = [' '] * field.width
                pos = field.edit_key(first_key, 0, insert)
            self._w('\x1b[?25h')
            try:
                while True:
                    self._draw_field(field, pos)
                    key = self.keys.read_key()
                    if key is None:
                        key = ESC
                    if key == ESC:
                        return None, key
                    if key in (ENTER, TAB, 'UP', 'DOWN'):
                        if numeric and not field.text().strip():
                            return ('', None), key
                        try:
                            value = field.value()
                        except ValueError:
                            bell()
                            continue
                        if numeric and value == int(value):
                            value = int(value)
                        return ('', value), key
                    if key == 'INS':
                        insert = not insert
                        continue
                    pos = field.edit_key(key, pos, insert)
            finally:
                self._w('\x1b[?25l')

        try:
            while True:
                # keep the current cell in view
                if save:
                    while first_col < cur_col and cell_offset(cur_col) + widths[visible[cur_col]] > inner:
                        first_col += 1
                    first_col = min(first_col, cur_col)
                out = [self._put(r1 + 1, c1 + 1, line(columns), self.fg, self.bg),
                       self._put(r1 + 2, c1 + 1, '─' * inner, self.fg, self.bg)]
                for n in range(page):
                    i = top + n
                    fg, bg = (self.field_fg, self.field_bg) if i == current else (self.fg, self.bg)
                    text = line(cells[i]) if i < len(cells) else ' ' * inner
                    out.append(self._put(r1 + 3 + n, c1 + 1, text, fg, bg))
                    if save and i == current:   # the current cell in reverse
                        off = cell_offset(cur_col)
                        ci = visible[cur_col]
                        cell_text = text[off:off + widths[ci]]
                        out.append(self._put(r1 + 3 + n, c1 + 1 + off, cell_text, self.field_bg, self.field_fg))
                if message:
                    status = ' ' + message
                elif save:
                    extra = ('  Ins=add' if add else '') + ('  Del=delete' if delete else '')
                    status = f' {current + 1 if cells else 0} of {len(cells)}   Enter=edit{extra}  Esc=done'
                else:
                    status = f' {current + 1 if cells else 0} of {len(cells)}   Enter=select  Esc=cancel  ←→=columns'
                message = ''
                out.append(self._put(r2 - 1, c1 + 1, status[:inner].ljust(inner), self.fg, self.bg))
                self._w(''.join(out) + self._normal())
                key = self.keys.read_key()
                if key is None:
                    key = ESC
                self.last_key = key
                if key == ESC:
                    return -1
                if save and add and key == 'INS':
                    new_index = add()
                    if new_index is not False:
                        cells, widths = layout()
                        if new_index is not None:
                            current = new_index
                        current = min(current, len(cells) - 1)
                        cur_col = 0
                    continue
                if save and delete and key == 'DEL' and cells:
                    self._w(self._put(r2 - 1, c1 + 1, ' Delete this row? (Y/N)'[:inner].ljust(inner), self.fg, self.bg))
                    answer = self.keys.read_key()
                    if answer and answer.upper() == 'Y':
                        error = delete(current)
                        if error:
                            bell()
                            message = 'Not deleted: ' + error
                        else:
                            rows.pop(current)
                            cells.pop(current)
                            current = max(0, min(current, len(cells) - 1))
                    continue
                if save and cells and (key in (ENTER, 'F2') or (len(key) == 1 and key.isprintable())):
                    ci = visible[cur_col]
                    if ci in locked:
                        bell()
                        message = f'{columns[ci]} is the key and cannot be changed.'
                        continue
                    result, end_key = edit_cell(r1 + 3 + current - top, cur_col, None if key in (ENTER, 'F2') else key)
                    if result is not None:
                        error = save(current, ci, result[1])
                        if error:
                            bell()
                            message = 'Not saved: ' + error
                        else:
                            rows[current][ci] = result[1]
                            cells[current][ci] = show(result[1])
                            widths[ci] = min(30, max(widths[ci], len(cells[current][ci])))
                            if end_key == TAB: key = 'RIGHT'
                            elif end_key in ('UP', 'DOWN'): key = end_key
                    if key in (ENTER, 'F2') or (len(key) == 1 and key not in (TAB,)):
                        continue
                elif key == ENTER and cells:
                    return current
                if key == 'DOWN': current = min(current + 1, len(cells) - 1)
                elif key == 'UP': current = max(current - 1, 0)
                elif key == 'PGDN': current = min(current + page, len(cells) - 1)
                elif key == 'PGUP': current = max(current - page, 0)
                elif key == 'HOME': current = 0
                elif key == 'END': current = len(cells) - 1
                elif save and key in ('RIGHT', TAB): cur_col = min(cur_col + 1, len(visible) - 1)
                elif save and key in ('LEFT', 'BTAB'): cur_col = max(cur_col - 1, 0)
                elif key == 'RIGHT': first_col = min(first_col + 1, len(visible) - 1)
                elif key == 'LEFT': first_col = max(first_col - 1, 0)
                current = max(current, 0)
                if current < top: top = current
                elif current >= top + page: top = current - page + 1
        finally:
            self.restore_saved(underneath)       # put back what the grid covered
            self._w('\x1b[?25h')

    # --- INKEY$ --------------------------------------------------------
    def inkey(self, wait=None):
        """INKEY$: no argument returns a waiting key or ''. INKEY$(0) waits for a key;
        INKEY$(n) waits up to n seconds."""
        if wait is None:
            timeout = 0
        elif wait <= 0:
            timeout = None
        else:
            timeout = wait
        key = self.keys.read_key(timeout)
        key = key or ''
        if key:
            self.last_key = key
        return key


# One screen per process, shared by RUN and CHAIN programs
SCREEN = Screen()
