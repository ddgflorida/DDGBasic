"""
Text-mode screen support for DDGBasic, in the style of 1990s BASIC and xBase:
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
from datetime import datetime
import os
import re
import shutil
import signal
import sys
import time

# QBasic colour numbers 0-15 -> ANSI colour (0-7); 8-15 are the bright versions
_ANSI = [0, 4, 2, 6, 1, 5, 3, 7]

# SET STYLE: how screens look. MODERN, the default, draws the 16 colour numbers with softer
# tones from the terminal's 256-colour set (macOS Terminal, Windows 10/11 consoles and Linux
# terminals all have it): 1 (blue), the classic background, is a charcoal, 3 (cyan), the
# classic field colour, a light steel blue, and the bright colours are muted so text on them
# stays easy to read. Boxes have thin rounded corners, and buttons are flat blocks of colour.
# CLASSIC is the 1990s look: the terminal's own 16 colours, double-line boxes, [ buttons ].
STYLES = {
    #                     0    1    2    3    4    5    6    7    8   9    10   11   12   13   14   15
    'MODERN': {'palette': [234, 237, 71, 110, 167, 139, 179, 250, 243, 75, 114, 116, 210, 182, 222, 255],
               'rounded': True, 'flat_buttons': True},
    'CLASSIC': {'palette': None, 'rounded': False, 'flat_buttons': False},
}
_palette = STYLES['MODERN']['palette']

# Key names returned for keys that are not characters
_CSI_KEYS = {
    'A': 'UP', 'B': 'DOWN', 'C': 'RIGHT', 'D': 'LEFT', 'H': 'HOME', 'F': 'END', 'Z': 'BTAB',
    '1~': 'HOME', '7~': 'HOME', '4~': 'END', '8~': 'END', '2~': 'INS', '3~': 'DEL',
    '5~': 'PGUP', '6~': 'PGDN',
    '11~': 'F1', '12~': 'F2', '13~': 'F3', '14~': 'F4', '15~': 'F5', '17~': 'F6',
    '18~': 'F7', '19~': 'F8', '20~': 'F9', '21~': 'F10', '23~': 'F11', '24~': 'F12',
    '1;5H': 'CTRL-HOME', '1;5F': 'CTRL-END', '1;5C': 'CTRL-RIGHT', '1;5D': 'CTRL-LEFT', '1;2P': 'SHIFT-F1',
}
_SS3_KEYS = {'P': 'F1', 'Q': 'F2', 'R': 'F3', 'S': 'F4', 'A': 'UP', 'B': 'DOWN',
             'C': 'RIGHT', 'D': 'LEFT', 'H': 'HOME', 'F': 'END'}
_WIN_KEYS = {'H': 'UP', 'P': 'DOWN', 'K': 'LEFT', 'M': 'RIGHT', 'G': 'HOME', 'O': 'END',
             'R': 'INS', 'S': 'DEL', 'I': 'PGUP', 'Q': 'PGDN', '\x0f': 'BTAB',
             ';': 'F1', '<': 'F2', '=': 'F3', '>': 'F4', '?': 'F5', '@': 'F6',
             'A': 'F7', 'B': 'F8', 'C': 'F9', 'D': 'F10', '\x85': 'F11', '\x86': 'F12',
             'w': 'CTRL-HOME', 'u': 'CTRL-END', 't': 'CTRL-RIGHT', 's': 'CTRL-LEFT', 'T': 'SHIFT-F1'}

ENTER, ESC, TAB, BACKSPACE = '\r', '\x1b', '\t', '\x08'

SAVED_PREFIX = '\x00SCREEN:'   # marks a string made by SAVESCREEN

# SET THEME: (text fg, text bg, field fg, field bg), the four values of COLOR
THEMES = {
    'DEFAULT': (7, 0, 0, 7),       # the terminal's look: white on black, black-on-white fields
    'CLASSIC': (15, 1, 0, 3),      # the blue screen of 1990s business software
    'NORTON':  (11, 1, 0, 3),      # light cyan on blue, as in file managers of the time
    'GREEN':   (10, 0, 0, 10),     # a green-screen terminal
    'AMBER':   (14, 0, 0, 6),      # an amber monitor
    'PAPER':   (0, 7, 15, 1),      # black on white, white-on-blue fields
    'MONO':    (15, 0, 0, 15),     # bright white on black, no colour at all
}


class ScreenError(Exception):
    pass


_KEY_NAMES = {'ENTER': '\r', 'ESC': '\x1b', 'TAB': '\t', 'BACKSPACE': '\x08', 'SPACE': ' '}
_NAMED_KEYS = {'UP', 'DOWN', 'LEFT', 'RIGHT', 'HOME', 'END', 'PGUP', 'PGDN', 'INS', 'DEL', 'BTAB',
               'CLICK', 'RCLICK', 'MCLICK', 'WHEELUP', 'WHEELDOWN',
               'CTRL-HOME', 'CTRL-END', 'CTRL-LEFT', 'CTRL-RIGHT', 'SHIFT-F1'} | {f'F{n}' for n in range(1, 13)}


def key_from_name(name):
    """The key ON KEY means by a name: F1-F12, UP, DEL, ..., CTRL-A..CTRL-Z, ALT-A..ALT-Z,
    ENTER, ESC, TAB, SPACE, or a single character."""
    text = str(name)
    upper = text.upper().replace('+', '-')
    if upper in _NAMED_KEYS:
        return upper
    if upper in _KEY_NAMES:
        return _KEY_NAMES[upper]
    if upper.startswith('CTRL-') and len(upper) == 6 and 'A' <= upper[5] <= 'Z':
        return chr(ord(upper[5]) - 64)
    if upper.startswith('ALT-') and len(upper) == 5:
        return upper
    if len(text) == 1:
        return text
    raise ScreenError(f"Unknown key name '{text}'. Use F1-F12, CTRL-X, ALT-X, UP, DEL, ENTER, ESC or one character.")


class KeyReader:
    """Reads single keys. Characters come back as themselves (Enter is CHR$(13),
    Esc CHR$(27), Tab CHR$(9), Backspace CHR$(8)); other keys as names such as
    'UP', 'PGDN' or 'F1'."""

    def __init__(self):
        self.pending = []
        self.is_tty = sys.stdin.isatty()
        self.windows = os.name == 'nt'
        self._saved_mode = None
        # Mouse: on by default except on Windows, where it needs the console's VT input mode
        # (SET MOUSE ON switches it on there). Clicks arrive as keys named CLICK, RCLICK,
        # MCLICK, WHEELUP and WHEELDOWN, with the position in mouse_row/mouse_col.
        self.mouse_wanted = not self.windows
        self._mouse_on = False
        self._win_saved_mode = None
        self.mouse_row = self.mouse_col = 0
        # ON KEY: key name -> handler; on_hotkey(key) runs it (set by the Screen)
        self.hotkeys = {}
        self.on_hotkey = None
        self._in_hotkey = False
        # Terminal resize: on_resize() redraws; it runs while waiting for a key (SIGWINCH on
        # macOS/Linux, a size check while polling on Windows), never in the middle of output
        self.on_resize = None
        self.block_suspend = False   # True: Ctrl-Z reaches the program instead of suspending it
        self.waiting = False
        self.resized = False
        self._win_size = None

    # --- mouse -----------------------------------------------------------
    _MOUSE_ON, _MOUSE_OFF = '\x1b[?1000h\x1b[?1006h', '\x1b[?1000l\x1b[?1006l'

    def _mouse_reporting(self, on):
        if not self.is_tty or on == self._mouse_on:
            return
        if self.windows:
            try:
                import ctypes
                k32 = ctypes.windll.kernel32
                handle = k32.GetStdHandle(-10)                  # STD_INPUT_HANDLE
                if on:
                    mode = ctypes.c_uint32()
                    if not k32.GetConsoleMode(handle, ctypes.byref(mode)):
                        return
                    self._win_saved_mode = mode.value
                    # VT input (0x0200), mouse input (0x0010) and extended flags (0x0080), without
                    # quick-edit (0x0040), which would take clicks for selecting text
                    k32.SetConsoleMode(handle, (mode.value | 0x0200 | 0x0080 | 0x0010) & ~0x0040)
                elif self._win_saved_mode is not None:
                    k32.SetConsoleMode(handle, self._win_saved_mode)
                    self._win_saved_mode = None
            except Exception:
                return
        sys.stdout.write(self._MOUSE_ON if on else self._MOUSE_OFF)
        sys.stdout.flush()
        self._mouse_on = on

    def set_mouse(self, on):
        """SET MOUSE ON/OFF."""
        self.mouse_wanted = on
        if not on or self._saved_mode is not None or self.windows:
            self._mouse_reporting(on)

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
            names = ('VDSUSP', 'VLNEXT', 'VDISCARD') + (('VSUSP',) if self.block_suspend else ())
            slots = [getattr(termios, n) for n in names if hasattr(termios, n)]
            if sys.platform == 'darwin' and not hasattr(termios, 'VDSUSP'):
                slots.append(11)                            # VDSUSP in <sys/termios.h>
            for slot in slots:
                mode[6][slot] = bytes([disabled]) if isinstance(mode[6][slot], bytes) else disabled
            termios.tcsetattr(fd, termios.TCSANOW, mode)    # TCSAFLUSH would drop keys typed ahead
            if self.mouse_wanted:
                self._mouse_reporting(True)

    def raw_off(self):
        self._mouse_reporting(False)
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
            if self.mouse_wanted:
                self._mouse_reporting(True)
            deadline = None if timeout is None else time.time() + timeout
            checked = 0.0
            while not msvcrt.kbhit():
                if deadline is not None and time.time() >= deadline:
                    return None
                if self.on_resize and time.time() - checked > 0.25:   # no SIGWINCH on Windows
                    checked = time.time()
                    size = shutil.get_terminal_size((80, 24))
                    if self._win_size is not None and size != self._win_size:
                        self.on_resize()
                    self._win_size = size
                time.sleep(0.01)
            return msvcrt.getwch()
        import select
        self.raw_on()
        fd = sys.stdin.fileno()
        if self.resized and self.on_resize:
            self.resized = False
            self.on_resize()
        self.waiting = True
        try:
            ready, _, _ = select.select([fd], [], [], timeout)
        finally:
            self.waiting = False
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
        Returns '' if no key arrives in time, or None when input has ended.
        A key bound with ON KEY runs its handler instead of being returned."""
        sys.stdout.flush()                 # whatever was printed is on screen before the wait
        while True:
            key = self._read_key_once(timeout)
            if key and key in self.hotkeys and self.on_hotkey and not self._in_hotkey:
                self._in_hotkey = True
                try:
                    self.on_hotkey(key)
                finally:
                    self._in_hotkey = False
                if timeout is not None:
                    return ''              # a polling INKEY$ sees no key
                continue
            return key

    def _read_key_once(self, timeout=None):
        ch = self._read_char(timeout)
        if ch is None:
            return '' if (timeout is not None and self.is_tty) else None
        if self.windows and self.is_tty and ch in ('\x00', '\xe0'):
            # An arrow or function key: a prefix, then its code. The C runtime holds the code
            # back after handing over the prefix, where msvcrt.kbhit() can't see it, so it is
            # fetched with getwch() directly; waiting on kbhit() (as _read_char does) would
            # lose it and swallow the next key press.
            import msvcrt
            return _WIN_KEYS.get(msvcrt.getwch(), '')
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
                if seq.startswith('<') and seq[-1:] in ('M', 'm'):
                    return self._mouse_key(seq, timeout)
                return _CSI_KEYS.get(seq, '')
            if nxt == 'O':
                return _SS3_KEYS.get(self._read_char(0.05) or '', '')
            if nxt is not None and self.is_tty and len(nxt) == 1 and nxt.isprintable():
                return 'ALT-' + nxt.upper()        # a terminal sends Alt-letter as Esc + letter
            if nxt is not None:
                self.pending.insert(0, nxt)
            return ESC
        if ch in ('\n', '\r'):
            return ENTER
        if ch in ('\x7f', '\x08'):
            return BACKSPACE
        return ch

    def _mouse_key(self, seq, timeout):
        """Decodes an SGR mouse report, ESC [ < button ; col ; row M (press) or m (release).
        Presses and wheel turns become keys; releases and movement are skipped."""
        try:
            button, col, row = (int(n) for n in seq[1:-1].split(';'))
        except ValueError:
            return ''
        if seq[-1] == 'm' or button & 32:          # a release, or movement with a button held
            return self._read_key_once(timeout)
        self.mouse_row, self.mouse_col = row, col
        if button & 64:
            return 'WHEELDOWN' if button & 1 else 'WHEELUP'
        return {0: 'CLICK', 1: 'MCLICK', 2: 'RCLICK'}.get(button & 3, '')


class Field:
    """One GET entry field."""

    def __init__(self, row, col, var_name, value, picture, valid, numeric):
        self.row, self.col = row, col
        self.var_name, self.valid = var_name, valid
        self.numeric = numeric
        self.upper = self.lower = self.blank_zero = self.raw = self.clear_first = self.is_date = False
        width = None
        template = picture or ''
        if template.startswith('@'):
            funcs, _, template = template[1:].partition(' ')
            funcs = funcs.upper()
            self.upper = '!' in funcs
            self.lower = 'L' in funcs           # @L: lower case, as @! is upper case
            self.blank_zero = 'Z' in funcs      # @Z: show nothing for zero
            self.raw = 'R' in funcs             # @R: the template's fixed characters are not stored
            self.clear_first = 'K' in funcs     # @K: the first key typed clears the field
            self.is_date = 'D' in funcs and not numeric
            m = re.search(r'S(\d+)', funcs)
            if m:
                width = int(m.group(1))
        if self.is_date:
            template = template or '9999-99-99'
        # A numeric field with a mask such as 99,999.99 is typed like a calculator
        self.calc = numeric and bool(re.fullmatch(r'[9#,.]+', template or ''))
        if self.calc:
            self.decimals = len(template.split('.', 1)[1]) if '.' in template else 0
            self.commas = ',' in template
            self.typed = None
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

    def _calc_text(self, number):
        """A calculator field's value, formatted with its mask and right-aligned."""
        if self.blank_zero and not number:
            return ' ' * self.width
        text = f"{number:,.{self.decimals}f}" if self.commas else f"{number:.{self.decimals}f}"
        return ('*' * self.width) if len(text) > self.width else text.rjust(self.width)

    def _initial_buffer(self, value):
        if self.calc:
            self.typed = None
            self.text_mode = False
            try:
                self.number = float(value) if value not in (None, '') else 0.0
            except (TypeError, ValueError):
                self.number = 0.0
            return list(self._calc_text(self.number))
        if self.numeric:
            if self.blank_zero and not value:
                return [' '] * self.width
            text = format_number(value)
            return list(text[:self.width].ljust(self.width))
        if self.is_date and hasattr(value, 'isoformat'):
            value = value.isoformat()
        text = str(value)
        if self.is_date:
            text = text[:10]
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
        if self.raw and self.template:
            return ''.join(raw[i] for i in range(self.width) if self._editable(i)).rstrip()
        return raw.rstrip()

    def clear(self):
        """Empties the field (Ctrl-Y, and the first key in a numeric or @K field)."""
        if self.calc:
            self.typed = ''
            self.text_mode = False
            self.buffer = [' '] * self.width
        else:
            self.buffer = [' ' if self._editable(i) else self.template[i] for i in range(self.width)]

    def value(self):
        """The typed value, converted for a numeric field. Raises ValueError."""
        if self.calc and self.text_mode:
            # Edited as text with the arrow keys: it must still be a number that fits the mask
            text = ''.join(self.buffer).replace(',', '').strip()
            number = float(text) if text not in ('', '-', '.', '-.') else 0.0
            if '.' in text and len(text.split('.', 1)[1]) > self.decimals:
                raise ValueError("more decimals than the mask has")
            if '*' in self._calc_text(abs(number)):
                raise ValueError("too large for the mask")
            return number
        if self.calc:
            if self.typed is None:
                return self.number
            typed = self.typed.strip()
            return float(typed) if typed not in ('', '-', '.', '-.') else 0.0
        text = self.text()
        if self.is_date:
            if text:
                datetime.strptime(text, '%Y-%m-%d')   # raises ValueError for an impossible date
            return text
        if not self.numeric:
            return text
        text = text.replace(',', '').strip()
        return float(text) if text else 0.0

    def incomplete(self):
        """True when a template field was started but not finished: something is typed,
        but a 9, A or N position is still blank. # and X positions may stay blank."""
        if not self.template or self.calc:
            return False
        if all(self.buffer[i] == ' ' for i in range(self.width) if self._editable(i)):
            return False                       # left empty: fine (REQUIRED decides if it may be)
        return any(self.buffer[i] == ' ' for i in range(self.width) if self.template[i] in '9AN')

    def first_pos(self):
        if self.calc and not self.text_mode:
            return self.width - 1               # the cursor sits at the right, as on a calculator
        return next((i for i in range(self.width) if self._editable(i)), 0)

    def _step(self, pos, direction):
        i = pos + direction
        while 0 <= i < self.width and not self._editable(i):
            i += direction
        return i if 0 <= i < self.width else pos

    def end_pos(self):
        """Just after the last character typed. In a free-text field that can be just past
        a full field, so Backspace removes its last character; a template field stops on
        its last position."""
        limit = self.width - 1 if self.template else self.width
        return min(len(''.join(self.buffer).rstrip()), limit)

    def last_pos(self):
        return next((i for i in range(self.width - 1, -1, -1) if self._editable(i)), self.width - 1)

    def _calc_key(self, key):
        """Calculator-style typing: digits build the number, '.' starts the decimals,
        '-' changes the sign, Backspace removes the last character."""
        typed = self.typed if self.typed is not None else ''
        if key == BACKSPACE and self.typed is None:
            typed = self._plain(self.number)       # Backspace first takes one digit off the value
        if key in ('\x19', 'DEL'):
            typed = ''
        elif key == BACKSPACE:
            typed = typed[:-1]
        elif len(key) == 1 and key.isdigit():
            candidate = typed + key
            if '.' in typed and len(typed.split('.', 1)[1]) >= self.decimals:
                bell()                              # no more decimals than the mask has
            elif '*' in self._calc_text(float(candidate.replace('-', '') or 0)):
                bell()                              # the number would no longer fit the mask
            else:
                typed = candidate
        elif key == '.' and self.decimals and '.' not in typed:
            typed += '.'
        elif key == '-':
            typed = typed[1:] if typed.startswith('-') else '-' + typed
        elif len(key) == 1 and key.isprintable():
            bell()
        self.typed = typed
        self.buffer = list(typed.rjust(self.width)[-self.width:])
        return self.width - 1

    def _plain(self, number):
        """A calculator field's number as typed digits: 1250 or 1250.50, without commas."""
        if self.blank_zero and not number:
            return ''
        return f"{number:.{self.decimals}f}"

    def edit_key(self, key, pos, insert):
        """Applies an editing key; returns the new cursor position. Sets self.filled when
        a character was typed into the field's last position (for SET AUTOADVANCE)."""
        self.filled = False
        if self.calc and not self.text_mode and key in ('LEFT', 'RIGHT', 'HOME', 'END'):
            # An arrow key first: edit the number as text, moving through its digits.
            # It is checked as a number, and shown with the mask again, on leaving the field
            text = ''.join(self.buffer).strip()
            self.buffer = list(text[:self.width].ljust(self.width))
            self.text_mode = True
            pos = self.end_pos()
        if self.calc and not self.text_mode:
            return self._calc_key(key)
        if key == 'LEFT':
            return self._step(pos, -1)
        if key == 'RIGHT':
            if not self.template:              # free text: no further than just after the text
                return min(pos + 1, self.end_pos())
            return self._step(pos, 1)
        if key == 'HOME':
            return self.first_pos()
        if key == 'END':
            return self.end_pos()
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
            if pos >= self.width:              # just past a full field: nothing under the cursor
                return pos
            if self.template:
                self.buffer[pos] = ' '
            else:
                del self.buffer[pos]
                self.buffer.append(' ')
            return pos
        if len(key) == 1 and key.isprintable():
            if pos >= self.width or not self._accepts(pos, key):
                bell()                         # the field is full, or the character isn't allowed
                return pos
            if self.upper or (self.template and self.template[pos] == '!'):
                key = key.upper()
            elif self.lower:
                key = key.lower()
            if insert and not self.template:
                if self.buffer[-1] != ' ':
                    bell()
                    return pos
                self.buffer.insert(pos, key)
                self.buffer.pop()
            else:
                self.buffer[pos] = key
            self.filled = pos == self.last_pos()
            if pos < self.width - 1:
                return self._step(pos, 1)
            # The last position: a free-text field puts the cursor just past it, after what was typed
            return pos if self.template else self.width
        return pos


class CheckBox(Field):
    """GET ... CHECKBOX: [X] or [ ]. Space (or a click) toggles it; Y/N/X/1/0 set it."""
    is_check = True

    def __init__(self, row, col, var_name, value, valid, as_text):
        self.row, self.col, self.var_name, self.valid = row, col, var_name, valid
        self.numeric = self.calc = self.is_date = self.clear_first = self.raw = False
        self.upper = self.blank_zero = False
        self.template, self.width, self.as_text = '[X]', 3, as_text
        self.buffer = self._initial_buffer(value)

    def _editable(self, i):
        return i == 1

    def incomplete(self):
        return False

    def _initial_buffer(self, value):
        if isinstance(value, str):
            on = value.strip().upper() in ('Y', 'YES', 'T', 'TRUE', 'X', '1', '-1')
        else:
            on = bool(value)
        return list('[X]' if on else '[ ]')

    def text(self):
        return 'Y' if self.buffer[1] == 'X' else 'N'

    def value(self):
        on = self.buffer[1] == 'X'
        return ('Y' if on else 'N') if self.as_text else (-1.0 if on else 0.0)

    def edit_key(self, key, pos, insert):
        self.filled = False
        if key == ' ':
            self.buffer[1] = ' ' if self.buffer[1] == 'X' else 'X'
        elif len(key) == 1 and key.upper() in ('Y', 'X', '1', 'T'):
            self.buffer[1] = 'X'
        elif len(key) == 1 and key.upper() in ('N', '0', 'F'):
            self.buffer[1] = ' '
        elif len(key) == 1 and key.isprintable():
            bell()
        return 1


class ListField(Field):
    """GET ... LIST: a drop-down. Space, F2 or a click opens the list; a letter jumps to the
    next item that starts with it."""
    is_list = True

    def __init__(self, row, col, var_name, value, valid, items):
        self.row, self.col, self.var_name, self.valid = row, col, var_name, valid
        self.numeric = self.calc = self.is_date = self.clear_first = self.raw = False
        self.upper = self.blank_zero = False
        self.items = [str(i) for i in items]
        if not self.items:
            raise ScreenError("GET ... LIST needs at least one item.")
        self.inner = max([len(i) for i in self.items] + [len(str(value))])
        self.template, self.width = '', self.inner + 2
        self.buffer = self._initial_buffer(value)

    def _editable(self, i):
        return i == 0

    def incomplete(self):
        return False

    def _initial_buffer(self, value):
        self.current = '' if value is None else str(value)
        return list(self.current.ljust(self.inner) + ' ▼')

    def set(self, value):
        self.buffer = self._initial_buffer(value)

    def text(self):
        return self.current

    def value(self):
        return self.current

    def edit_key(self, key, pos, insert):
        self.filled = False
        if len(key) == 1 and key.isprintable() and key != ' ':
            start = self.items.index(self.current) + 1 if self.current in self.items else 0
            for k in range(len(self.items)):
                item = self.items[(start + k) % len(self.items)]
                if item[:1].upper() == key.upper():
                    self.set(item)
                    return 0
            bell()
        elif key in ('\x19', 'DEL'):
            self.set('')
        return 0


class Button:
    """A [ label ] button among the GET fields. READ ends when it is pressed."""
    is_button = True

    def __init__(self, row, col, label, cancel=False):
        self.row, self.col, self.label, self.cancel = row, col, str(label), cancel
        self.when = None
        self.width = len(self.label) + 4

    def first_pos(self):
        return 0


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
        self.last_button = ''       # BUTTON$: the label of the button that ended the last READ
        self.hotkey_call = None     # set by the interpreter: runs the function bound to a key
        self.keys.on_hotkey = self._run_hotkey
        self.shadows = True         # SET SHADOW OFF: pop-ups without a drop shadow
        self.style = STYLES['MODERN']   # SET STYLE
        # Whether writing the bottom-right cell leaves the cursor there (as xterm, macOS and
        # Linux terminals do) rather than scrolling the screen up a line. The Windows console
        # does it only with DISABLE_NEWLINE_AUTO_RETURN, which _activate turns on.
        self.deferred_wrap = os.name != 'nt'
        self.progress_box = None    # PROGRESS: (area, what it covered, last drawn bar)
        self.keys.on_resize = self._resized
        if hasattr(signal, 'SIGWINCH') and self.keys.is_tty:
            try:
                signal.signal(signal.SIGWINCH, self._on_sigwinch)
            except ValueError:      # not the main thread
                pass
        # A copy of what is on the screen, one (char, fg, bg) cell per position, so that
        # SAVESCREEN, MENU and BROWSE can put back what they cover (ANSI can't read it back)
        self.rows, self.cols = self.size()
        self.cells = self._blank(self.rows, self.cols, 7, 0)
        self.cur_row, self.cur_col = 1, 1

    def _on_sigwinch(self, signum, frame):
        if self.keys.waiting:       # blocked reading a key: safe to redraw now
            self._resized()
        else:
            self.keys.resized = True

    def _resized(self):
        """The terminal changed size: keep the screen copy that still fits, and redraw it all,
        since terminals shuffle or wrap what was there."""
        rows, cols = self.size()
        if not self.used or (rows, cols) == (self.rows, self.cols):
            self.rows, self.cols = rows, cols
            return
        cells = self._blank(rows, cols, self.fg, self.bg)
        for r in range(min(rows, self.rows)):
            cells[r][:min(cols, self.cols)] = self.cells[r][:min(cols, self.cols)]
        self.rows, self.cols = rows, cols
        self.cells = [[(' ', self.fg, self.bg)] * cols for _ in range(rows)]
        row, col = min(self.cur_row, rows), min(self.cur_col, cols)
        self._w('\x1b[0m\x1b[2J' + self._draw_cells(1, 1, cells) + self._normal() + f'\x1b[{row};{col}H')

    def _run_hotkey(self, key):
        """Runs an ON KEY handler, then puts back the screen it may have drawn over."""
        if not self.hotkey_call:
            return
        under = self.save() if self.used else None
        try:
            self.hotkey_call(self.keys.hotkeys[key])
        finally:
            if under:
                self.restore_saved(under)

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
                    # 0x0004: interpret ANSI sequences. 0x0008 (DISABLE_NEWLINE_AUTO_RETURN):
                    # writing the last column doesn't move the cursor on, so drawing the
                    # bottom-right cell (a hint line, a full-screen box) doesn't scroll the
                    # screen up. Older consoles refuse 0x0008; _put then skips that cell.
                    if k32.SetConsoleMode(handle, mode.value | 0x0004 | 0x0008):
                        self.deferred_wrap = True
                    else:
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
        if _palette:
            return f'\x1b[0;38;5;{_palette[fg % 16]};48;5;{_palette[bg % 16]}m'
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
        if not self.deferred_wrap and row == self.rows and col - 1 + len(text) >= self.cols:
            # The bottom-right cell would scroll the screen, so it isn't drawn. The screen
            # copy above still has it, so SAVESCREEN and RESTSCREEN see the same contents
            text = text[:max(0, self.cols - col)]
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
            row = r1 + n - 1
            if 0 <= row < self.rows:
                for i, cell in enumerate(line):
                    if 0 <= c1 - 1 + i < self.cols:
                        self.cells[row][c1 - 1 + i] = cell
            if not self.deferred_wrap and r1 + n == self.rows and c1 - 1 + len(line) >= self.cols:
                line = line[:max(0, self.cols - c1)]    # as in _put: not the bottom-right cell
            out.append(f'\x1b[{r1 + n};{c1}H')
            colour = None
            for ch, fg, bg in line:
                if (fg, bg) != colour:
                    out.append(self._sgr(fg, bg))
                    colour = (fg, bg)
                out.append(ch)
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

    def set_style(self, name):
        """SET STYLE: MODERN (the default) or CLASSIC (the 1990s look); see STYLES."""
        global _palette
        key = str(name).strip().upper()
        if key not in STYLES:
            raise ScreenError(f"There is no style called {name}. The styles are: " +
                              ', '.join(s.lower() for s in STYLES) + '.')
        self.style = STYLES[key]
        _palette = self.style['palette']

    def frame_chars(self, double=False):
        """The corners and lines of a box: (top-left, top-right, bottom-left, bottom-right,
        horizontal, vertical). The modern style draws every box thin with rounded corners."""
        if self.style['rounded']:
            return '╭', '╮', '╰', '╯', '─', '│'
        return ('╔', '╗', '╚', '╝', '═', '║') if double else ('┌', '┐', '└', '┘', '─', '│')

    def theme(self, name):
        """SET THEME: sets the four colours of COLOR from a named theme."""
        colours = THEMES.get(str(name).strip().upper())
        if colours is None:
            raise ScreenError(f"There is no theme called {name}. The themes are: " +
                              ', '.join(t.lower() for t in THEMES) + '.')
        self.color(*colours)

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
        tl, tr, bl, br, h, v = self.frame_chars(double)
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

    def shadow(self, r1, c1, r2, c2):
        """Darkens what is under the box's drop shadow: two columns to its right and the row
        below it, offset by one row and two columns, as a light falls from the top left."""
        out = []
        for r in range(r1 + 1, r2 + 2):
            first = c2 + 1 if r <= r2 else c1 + 2
            for c in range(first, c2 + 3):
                if 1 <= r <= self.rows and 1 <= c <= self.cols:
                    ch = self.cells[r - 1][c - 1][0]
                    out.append(self._put(r, c, ch, 8, 0))
        self._w(''.join(out) + self._normal())

    def popup(self, r1, c1, r2, c2, title='', double=False, shadow=None):
        """Draws a pop-up box, with a shadow unless SET SHADOW OFF, and returns what it
        covered (shadow included) for restore_saved."""
        shadow = self.shadows if shadow is None else shadow
        under = self.save(r1, c1, min(r2 + (1 if shadow else 0), self.rows), min(c2 + (2 if shadow else 0), self.cols))
        self.box(r1, c1, r2, c2, title, double)
        if shadow:
            self.shadow(r1, c1, r2, c2)
        return under

    # --- PROGRESS ------------------------------------------------------
    def progress(self, done, total, title=''):
        """PROGRESS: a centred box with a bar and a percentage, drawn when first used and
        updated in place (only when what it shows changes, so a tight loop stays fast)."""
        fraction = 0.0 if not total else max(0.0, min(1.0, done / total))
        cursor = (self.cur_row, self.cur_col)     # PRINT carries on where it was
        if self.progress_box is None:
            inner = max(20, min(50, self.cols - 6))
            top = max(1, (self.rows - 5) // 2 + 1)
            left = max(1, (self.cols - inner - 2) // 2 + 1)
            area = (top, left, top + 4, left + inner + 1)
            self.progress_box = [area, self.popup(*area, title=title), None]
        area, under, last = self.progress_box
        top, left, bottom, right = area
        width = right - left - 8                  # room for ' 100% '
        filled = int(fraction * width + 1e-9)
        shown = (filled, int(fraction * 100 + 1e-9), title)
        if shown != last:
            self.progress_box[2] = shown
            if last and last[2] != title:
                self.box(top, left, bottom, right, title)
            bar = ' ' + '█' * filled + '░' * (width - filled) + f'{shown[1]:4d}%'
            self._w(self._put(top + 2, left + 1, bar.ljust(right - left - 1), self.fg, self.bg) + self._normal())
        self.cur_row, self.cur_col = cursor
        self._w(f'\x1b[{cursor[0]};{cursor[1]}H')

    def progress_off(self):
        """PROGRESS OFF: removes the box and puts back what it covered."""
        if self.progress_box:
            row, col = self.cur_row, self.cur_col
            self.restore_saved(self.progress_box[1])
            self.progress_box = None
            self.cur_row, self.cur_col = row, col
            self._w(f'\x1b[{row};{col}H')

    # --- GET / READ ----------------------------------------------------
    def add_get(self, row, col, var_name, value, picture, valid, numeric, target=None,
                message=None, when=None, lookup=None, kind=None, items=None, hint=None, required=False):
        if kind == 'check':
            field = CheckBox(row, col, var_name, value, valid, isinstance(value, str) or var_name.endswith('$'))
        elif kind == 'list':
            field = ListField(row, col, var_name, value, valid, items or [])
        else:
            field = Field(row, col, var_name, value, picture, valid, numeric)
        field.target = target       # where READ stores the value (the interpreter's description)
        field.message, field.when, field.lookup = message, when, lookup
        field.hint, field.required = hint, required
        self.gets.append(field)
        self._draw_field(field)
        if required:
            # A * just after a required field, if nothing else is written there
            r, c = field.row, field.col + field.width
            if 1 <= r <= self.rows and 1 <= c <= self.cols and self.cells[r - 1][c - 1][0] == ' ':
                self._w(self._put(r, c, '*', self.fg, self.bg) + self._normal())
        return field

    def add_button(self, row, col, label, cancel=False):
        button = Button(row, col, label, cancel)
        self.gets.append(button)
        self._draw_button(button, False)
        return button

    def _draw_button(self, button, focused):
        if self.style['flat_buttons']:
            # A flat block of colour, as wide as [ label ]: the field colours when it has the
            # focus, light text on grey otherwise
            fg, bg = (self.field_fg, self.field_bg) if focused else (15, 8)
            text = f'  {button.label}  '
        else:
            fg, bg = (self.field_fg, self.field_bg) if focused else (self.fg, self.bg)
            text = f'[ {button.label} ]'
        self._w(self._put(button.row, button.col, text, fg, bg) + self._normal())

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
        self.last_button = ''
        if not fields:
            return ''
        data_fields = [f for f in fields if not getattr(f, 'is_button', False)]
        saved = current_values(data_fields)

        def put_back():
            """Esc or a CANCEL button: every field gets the value it had when READ started."""
            for f, value in zip(data_fields, saved):
                assign(f, value)
                f.buffer = f._initial_buffer(value)
                self._draw_field(f)

        def allowed(i):
            f = fields[i]
            return getattr(f, 'when', None) is None or check_when is None or check_when(f)

        def problem(f, required=True):
            """What is wrong with a field's value, or None: REQUIRED and empty, or VALID false.
            required=False checks VALID only (leaving a field: an empty field isn't finished
            yet, but it isn't wrong; REQUIRED waits for the form to be saved)."""
            if required and getattr(f, 'required', False):
                try:
                    value = f.value()
                except ValueError:
                    value = ''
                if (value == 0 or value == 'N') if (f.numeric or getattr(f, 'is_check', False)) \
                        else not str(value).strip():
                    return getattr(f, 'message', None) or 'This field is required'
            if f.incomplete():
                return getattr(f, 'message', None) or 'Fill in the whole field, or leave it empty'
            if f.valid is not None and not check_valid(f):
                return getattr(f, 'message', None) or ''
            return None

        def first_problem():
            """On saving: the first field (that WHEN allows) whose rule fails, visited or not."""
            for i, f in enumerate(fields):
                if not getattr(f, 'is_button', False) and allowed(i):
                    found = problem(f)
                    if found is not None:
                        return i, found
            return None

        def finish():
            """Saving the form: True if every field's rules hold; otherwise the cursor goes
            to the first field that fails, with its message."""
            nonlocal index, pos, fresh, pending_message
            stop = first_problem()
            if not stop:
                return True
            index, pos, fresh = stop[0], fields[stop[0]].first_pos(), True
            bell()
            pending_message = stop[1]      # shown once that field's hint is on the bottom line
            return False

        def step(i, direction):
            """The next field in a direction whose WHEN allows it, or None."""
            i += direction
            while 0 <= i < len(fields):
                if allowed(i):
                    return i
                i += direction
            return None

        def hit():
            """The field or button under the mouse, or None."""
            r, c = self.keys.mouse_row, self.keys.mouse_col
            for j, f in enumerate(fields):
                if f.row == r and f.col <= c < f.col + f.width and allowed(j):
                    return j
            return None

        def click_pos(f):
            """The cursor position for a click inside a field (an editable position)."""
            if getattr(f, 'is_button', False):
                return 0
            p = max(0, min(self.keys.mouse_col - f.col, f.width - 1))
            while p < f.width and not f._editable(p):
                p += 1
            return p if p < f.width else f.first_pos()

        index = step(-1, 1)
        if index is None:                      # every field is switched off by WHEN
            self.last_key = ENTER
            return ENTER
        insert = True
        pos = fields[index].first_pos()
        fresh = True        # the first key typed into a numeric field replaces its value
        message_under = None
        # HINT: the current field's hint is shown on the bottom line; what was there comes back
        # for a field without one, and when READ ends
        hint_under = self.save(self.rows, 1, self.rows, self.cols) \
            if any(getattr(f, 'hint', None) for f in fields) else None
        hint_shown = None
        pending_message = None
        self._w('\x1b[?25h')
        try:
            while True:
                field = fields[index]
                if hint_under and getattr(field, 'hint', None) != hint_shown:
                    hint_shown = getattr(field, 'hint', None)
                    if hint_shown:
                        self._w(self._put(self.rows, 1, (' ' + hint_shown)[:self.cols].ljust(self.cols),
                                          self.fg, self.bg) + self._normal())
                    else:
                        self.restore_saved(hint_under)
                if pending_message:
                    message_under = self._show_message(pending_message)
                    pending_message = None
                if getattr(field, 'is_button', False):
                    # A button: Enter or Space presses it; Tab, arrows and Shift-Tab move on
                    self._w('\x1b[?25l')
                    self._draw_button(field, True)
                    key = self.keys.read_key()
                    if key is None:
                        key = ESC
                    if message_under:
                        self.restore_saved(message_under)
                        message_under = None
                    self.last_key = key
                    self._draw_button(field, False)
                    self._w('\x1b[?25h')
                    if key == 'CLICK':
                        j = hit()
                        if j is None:
                            continue
                        if j != index:             # another field or button: go there (and press a button)
                            index, pos, fresh = j, click_pos(fields[j]), True
                            if getattr(fields[j], 'is_button', False):
                                self.keys.pending.insert(0, '\r')
                            elif getattr(fields[j], 'is_check', False) or getattr(fields[j], 'is_list', False):
                                self.keys.pending.insert(0, ' ')   # toggle the box / open the list
                            continue
                        key = ENTER                # a click on this button presses it
                    if key == ESC or (key in (ENTER, ' ') and field.cancel):
                        put_back()
                        if key != ESC:
                            self.last_button, self.last_key = field.label, ENTER
                        return self.last_key
                    if key in (ENTER, ' '):
                        if not finish():
                            continue
                        self.last_button, self.last_key = field.label, ENTER
                        return ENTER
                    if key in (TAB, 'DOWN', 'RIGHT'):
                        nxt = step(index, 1)
                        index = nxt if nxt is not None else step(-1, 1)   # wrap round to the first field
                    elif key in ('BTAB', 'UP', 'LEFT'):
                        nxt = step(index, -1)
                        if nxt is None and key == 'BTAB':
                            nxt = step(len(fields), -1)       # Shift-Tab wraps round to the last
                        index = nxt if nxt is not None else index
                    elif len(key) == 1 and key.isprintable():
                        bell()
                    pos = fields[index].first_pos()
                    fresh = True
                    continue
                self._draw_field(field, pos)
                key = self.keys.read_key()
                if key is None:            # input ended: give up as if Esc was pressed
                    key = ESC
                if message_under:          # a VALID message stays up until the next key
                    self.restore_saved(message_under)
                    message_under = None
                self.last_key = key
                if key == ESC:
                    put_back()
                    return key
                click_target = None
                if key == 'CLICK':
                    j = hit()
                    if j is None:
                        continue
                    if j == index:                 # inside this field: move the cursor
                        if getattr(field, 'is_check', False) or getattr(field, 'is_list', False):
                            key = ' '              # a click toggles a check box or opens a list
                        else:
                            pos = click_pos(field)
                            continue
                    else:
                        click_target, key = j, TAB     # leave this field with the usual checks first
                if getattr(field, 'is_list', False) and key in (' ', 'F2'):
                    self._choose_from_list(field)
                    continue
                if key == 'F2' and getattr(field, 'lookup', None) is not None and lookup:
                    if self._pick(field, lookup) is not None:
                        pos = field.first_pos()
                    continue
                if key in (ENTER, TAB, 'DOWN', 'UP', 'BTAB', 'PGDN', 'PGUP', '\x17'):
                    try:
                        value = field.value()
                    except ValueError:
                        bell()
                        if getattr(field, 'is_date', False):
                            message_under = self._show_message("Not a valid date: type it as YYYY-MM-DD")
                        continue
                    if getattr(field, 'lookup', None) is not None and lookup and str(value).strip() \
                            and not self._in_lookup(field, value, lookup):
                        # Not an allowed value: offer the list, starting at the closest match
                        if self._pick(field, lookup, value) is None:
                            bell()
                            continue
                        value = field.value()
                    assign(field, value)
                    if getattr(field, 'calc', False):
                        field.buffer = field._initial_buffer(value)   # show it formatted with the mask
                    # Typed values are checked going forward; going back is never blocked
                    backwards = key in ('UP', 'BTAB') or (click_target is not None and click_target < index)
                    found = None if backwards else problem(field, required=False)
                    if found is not None:
                        bell()
                        if found:
                            message_under = self._show_message(found)
                        continue
                    self._draw_field(field)
                    if key in ('PGDN', 'PGUP', '\x17'):
                        if finish():
                            return key
                        continue
                    if click_target is not None:
                        index, pos, fresh = click_target, click_pos(fields[click_target]), True
                        if getattr(fields[index], 'is_button', False):
                            self.keys.pending.insert(0, '\r')   # a click on a button presses it
                        elif getattr(fields[index], 'is_check', False) or getattr(fields[index], 'is_list', False):
                            self.keys.pending.insert(0, ' ')    # toggle the box / open the list
                        continue
                    nxt = step(index, -1 if key in ('UP', 'BTAB') else 1)
                    if nxt is None:
                        if key in (ENTER, TAB, 'DOWN'):
                            if finish():
                                return key     # past the last field
                            continue
                        # At the first field: Shift-Tab wraps round to the last field or button
                        nxt = step(len(fields), -1) if key == 'BTAB' else index
                    index = nxt
                    pos = fields[index].first_pos()
                    fresh = True
                    continue
                if key == 'INS':
                    insert = not insert
                    continue
                if fresh and (field.numeric or field.clear_first) and len(key) == 1 and key.isprintable():
                    field.clear()                  # the first key typed replaces the old value
                    pos = field.first_pos()
                fresh = False
                pos = field.edit_key(key, pos, insert)
                if self.auto_advance and getattr(field, 'filled', False):
                    # The field is full: go on as if Enter had been pressed
                    self.keys.pending.insert(0, ENTER)
        finally:
            if message_under:
                self.restore_saved(message_under)
            if hint_under and hint_shown:
                self.restore_saved(hint_under)
            self._w(self._normal())

    def _choose_from_list(self, field):
        """Opens a LIST field's drop-down under it; the chosen item becomes the value."""
        items = field.items
        if len(items) <= 10 and field.row + len(items) + 2 <= self.rows:
            n = self.menu(field.row + 1, field.col, items)
            if n:
                field.set(items[n - 1])
        else:
            self._pick(field, lambda f: (['Choose'], [[i] for i in f.items]), field.current)
        self._draw_field(field)

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
                             'Choose', start=start, shadow=True)
        if chosen < 0:
            return None
        value = rows[chosen][0]
        if isinstance(value, float) and value == int(value):
            value = int(value)
        field.buffer = field._initial_buffer('' if value is None else value)
        self._draw_field(field)
        return value

    # --- EDIT TEXT (memo editor) ----------------------------------------
    def edit_text(self, text, area=None, title=''):
        """A boxed multi-line editor. Returns the edited text (lines joined with CHR$(10)),
        or None when the user cancels. Ctrl-W or F10 saves; Esc cancels, asking first if
        anything was changed. Long lines scroll sideways."""
        r1, c1, r2, c2 = area or (3, 5, max(8, self.rows - 2), max(30, self.cols - 4))
        if r2 - r1 < 3 or c2 - c1 < 12:
            raise ScreenError("EDIT TEXT area is too small.")
        lines = str(text).replace('\r\n', '\n').replace('\r', '\n').split('\n')
        original = list(lines)
        height, width = r2 - r1 - 1, c2 - c1 - 1
        row = col = top = left = 0
        insert = True
        underneath = self.save(r1, c1, r2, c2)
        self.box(r1, c1, r2, c2, title)
        self._w('\x1b[?25h')

        def draw():
            out = []
            for n in range(height):
                i = top + n
                piece = lines[i][left:left + width] if i < len(lines) else ''
                out.append(self._put(r1 + 1 + n, c1 + 1, piece.ljust(width), self.fg, self.bg))
            status = f' Ln {row + 1}, Col {col + 1}  Ctrl-W=save  Esc=cancel '
            border = '─' * (c2 - c1 - 1)
            if len(status) <= len(border) - 2:
                border = border[:1] + status + border[1 + len(status):]
            out.append(self._put(r2, c1 + 1, border, self.fg, self.bg))
            out.append(self._normal() + f'\x1b[{r1 + 1 + row - top};{c1 + 1 + col - left}H')
            self._w(''.join(out))

        try:
            while True:
                # keep the cursor in view
                top = min(max(top, row - height + 1), row)
                left = min(max(left, col - width + 1), col)
                draw()
                key = self.keys.read_key()
                if key is None:
                    key = ESC
                self.last_key = key
                if key == 'CLICK':                              # put the cursor where the click was
                    r, c = self.keys.mouse_row, self.keys.mouse_col
                    if r1 < r < r2 and c1 < c < c2:
                        row = min(top + r - r1 - 1, len(lines) - 1)
                        col = min(left + c - c1 - 1, len(lines[row]))
                    continue
                if key in ('WHEELDOWN', 'WHEELUP'):
                    row = max(0, min(len(lines) - 1, row + (3 if key == 'WHEELDOWN' else -3)))
                    col = min(col, len(lines[row]))
                    continue
                line = lines[row]
                if key in ('\x17', 'F10'):                     # Ctrl-W / F10: save
                    return '\n'.join(lines)
                if key == ESC:
                    if lines == original or self.alert("Discard your changes?", ["No", "Yes"]) == 2:
                        self.last_key = ESC
                        return None
                    self._w('\x1b[?25h')
                    continue
                if key == ENTER:
                    lines[row:row + 1] = [line[:col], line[col:]]
                    row, col = row + 1, 0
                elif key == BACKSPACE:
                    if col > 0:
                        lines[row] = line[:col - 1] + line[col:]
                        col -= 1
                    elif row > 0:
                        col = len(lines[row - 1])
                        lines[row - 1:row + 1] = [lines[row - 1] + line]
                        row -= 1
                elif key == 'DEL':
                    if col < len(line):
                        lines[row] = line[:col] + line[col + 1:]
                    elif row < len(lines) - 1:
                        lines[row:row + 2] = [line + lines[row + 1]]
                elif key == '\x19':                            # Ctrl-Y: delete the line
                    if len(lines) > 1:
                        del lines[row]
                        row = min(row, len(lines) - 1)
                    else:
                        lines[0] = ''
                    col = min(col, len(lines[row]))
                elif key == TAB:
                    spaces = 4 - col % 4
                    lines[row] = line[:col] + ' ' * spaces + line[col:]
                    col += spaces
                elif key == 'INS':
                    insert = not insert
                elif key == 'LEFT':
                    if col > 0:
                        col -= 1
                    elif row > 0:
                        row -= 1
                        col = len(lines[row])
                elif key == 'RIGHT':
                    if col < len(line):
                        col += 1
                    elif row < len(lines) - 1:
                        row, col = row + 1, 0
                elif key in ('UP', 'DOWN', 'PGUP', 'PGDN'):
                    step = {'UP': -1, 'DOWN': 1, 'PGUP': -height, 'PGDN': height}[key]
                    row = max(0, min(len(lines) - 1, row + step))
                    col = min(col, len(lines[row]))
                elif key == 'HOME':
                    col = 0
                elif key == 'END':
                    col = len(line)
                elif len(key) == 1 and key.isprintable():
                    if insert or col >= len(line):
                        lines[row] = line[:col] + key + line[col:]
                    else:
                        lines[row] = line[:col] + key + line[col + 1:]
                    col += 1
        finally:
            self.restore_saved(underneath)
            self._w('\x1b[?25h')

    # --- VIEW (text viewer) --------------------------------------------
    def view(self, text, area=None, title=''):
        """A read-only, scrolling box for text. Arrows, PgUp/PgDn and Home/End move; '/' or
        Ctrl-F searches (ignoring case) and 'n' or F3 finds the next match; Esc or 'q' closes."""
        r1, c1, r2, c2 = area or (1, 1, self.rows, self.cols)
        if r2 - r1 < 3 or c2 - c1 < 12:
            raise ScreenError("VIEW area is too small.")
        lines = str(text).replace('\r\n', '\n').replace('\r', '\n').split('\n')
        if len(lines) > 1 and lines[-1] == '':
            lines.pop()                       # a final newline doesn't make an extra line
        lines = [line.expandtabs(8) for line in lines]
        height, width = r2 - r1 - 1, c2 - c1 - 1
        widest = max((len(line) for line in lines), default=0)
        top = left = 0
        found, search = None, ''
        message = ''
        underneath = self.save(r1, c1, r2, c2)
        self.box(r1, c1, r2, c2, title)
        self._w('\x1b[?25l')

        def find(start):
            needle = search.lower()
            for k in range(len(lines)):
                i = (start + k) % len(lines)
                if needle in lines[i].lower():
                    return i
            return None

        def prompt(label):
            """Reads a line of text on the status line; returns it, or None for Esc."""
            typed = ''
            while True:
                status = f' {label}{typed}_'
                self._w(self._put(r2, c1 + 1, status[:width].ljust(width, '─'), self.field_fg, self.field_bg) + self._normal())
                key = self.keys.read_key()
                if key is None or key == ESC:
                    return None
                if key == ENTER:
                    return typed
                if key == BACKSPACE:
                    typed = typed[:-1]
                elif len(key) == 1 and key.isprintable():
                    typed += key

        try:
            while True:
                top = max(0, min(top, len(lines) - height))
                left = max(0, min(left, max(0, widest - width)))
                out = []
                for n in range(height):
                    i = top + n
                    piece = lines[i][left:left + width] if i < len(lines) else ''
                    fg, bg = (self.field_fg, self.field_bg) if i == found else (self.fg, self.bg)
                    out.append(self._put(r1 + 1 + n, c1 + 1, piece.ljust(width), fg, bg))
                last = min(len(lines), top + height)
                status = message or f' {top + 1}-{last} of {len(lines)}  /=find  n=next  Esc=close '
                message = ''
                border = '─' * width
                status = status[:width - 2]
                border = border[:1] + status + border[1 + len(status):]
                out.append(self._put(r2, c1 + 1, border, self.fg, self.bg))
                self._w(''.join(out) + self._normal())
                key = self.keys.read_key()
                if key is None:
                    key = ESC
                self.last_key = key
                if key in (ESC, 'q', 'Q'):
                    return
                if key in ('WHEELDOWN', 'WHEELUP'):
                    top += 3 if key == 'WHEELDOWN' else -3
                    continue
                if key in ('DOWN', ENTER): top += 1
                elif key == 'UP': top -= 1
                elif key in ('PGDN', ' '): top += height
                elif key == 'PGUP': top -= height
                elif key == 'HOME': top, left = 0, 0
                elif key == 'END': top = len(lines)
                elif key == 'RIGHT': left += 8
                elif key == 'LEFT': left -= 8
                elif key in ('/', '\x06'):            # '/' or Ctrl-F: search
                    typed = prompt('Find: ')
                    if typed:
                        search = typed
                        found = find(top)
                        if found is None:
                            bell()
                            message = f' Not found: {search} '
                        else:
                            top = found if not (top <= found < top + height) else top
                elif key in ('n', 'N', 'F3') and search:
                    nxt = find((found if found is not None else top) + 1)
                    if nxt is None:
                        bell()
                        message = f' Not found: {search} '
                    else:
                        found = nxt
                        if not (top <= found < top + height):
                            top = found
        finally:
            self.restore_saved(underneath)
            self._w('\x1b[?25h')

    # --- MENUBAR -------------------------------------------------------
    def menubar(self, menus, row=1, leave_easily=False):
        """A menu bar across the screen with pull-down menus. menus is a list of
        (title, [items]); an item '-' is a separator. Returns "Title.Item", "Title" for
        a title with no items, or "" for Esc. The bar stays drawn; the pull-downs don't."""
        if not menus:
            raise ScreenError("MENUBAR needs at least one menu.")
        positions, x = [], 2
        for title, _ in menus:
            positions.append(x)
            x += len(title) + 3
        current, opened, item, first = 0, False, 0, 0   # first: the top item of a scrolled pull-down
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
            height = max(1, min(len(items), self.rows - row - 2 - (1 if self.shadows else 0)))
            return row + 1, left, row + 2 + height, left + width + 1

        def draw_dropdown():
            nonlocal first
            items = menus[current][1]
            top, left, bottom, right = dropdown_area(current)
            height = bottom - top - 1
            first = min(max(first, item - height + 1), item)
            self.box(top, left, bottom, right)
            if self.shadows:
                self.shadow(top, left, bottom, right)
            width = right - left - 1
            out = []
            for n in range(first, first + height):
                text = items[n]
                if not selectable(items, n):
                    out.append(self._put(top + 1 + n - first, left, '├' + '─' * width + '┤', self.fg, self.bg))
                    continue
                fg, bg = (self.field_fg, self.field_bg) if n == item else (self.fg, self.bg)
                out.append(self._put(top + 1 + n - first, left + 1, (' ' + text).ljust(width), fg, bg))
            if height < len(items):                    # arrows on the border show there is more
                out.append(self._put(top, right - 1, '▲' if first > 0 else '─', self.fg, self.bg))
                out.append(self._put(bottom, right - 1, '▼' if first + height < len(items) else '─', self.fg, self.bg))
            self._w(''.join(out) + self._normal())

        def open_menu():
            nonlocal opened, item, underneath, first
            close_menu()
            if menus[current][1]:
                top, left, bottom, right = dropdown_area(current)
                shade = 1 if self.shadows else 0
                underneath = self.save(top, left, min(bottom + shade, self.rows), min(right + 2 * shade, self.cols))
                opened, item, first = True, first_item(menus[current][1]), 0
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
                if key == 'CLICK':
                    r, c = self.keys.mouse_row, self.keys.mouse_col
                    if r == row:                       # on the bar: open (or close) that menu
                        for n, (title_n, items_n) in enumerate(menus):
                            if positions[n] - 1 <= c < positions[n] + len(title_n) + 1:
                                if not items_n:
                                    return title_n
                                if opened and n == current:
                                    close_menu()
                                else:
                                    current = n
                                    open_menu()
                                break
                        continue
                    if opened:
                        top, left, bottom, right = dropdown_area(current)
                        if top < r < bottom and left < c < right:
                            k = r - top - 1 + first
                            if selectable(menus[current][1], k):
                                return f'{menus[current][0]}.{menus[current][1][k].strip()}'
                            continue
                        close_menu()                   # a click elsewhere closes the pull-down
                    if leave_easily:
                        return ''                      # (the IDE: and gives the keys back)
                    continue
                if key in ('WHEELDOWN', 'WHEELUP'):
                    if not opened:
                        continue
                    key = 'DOWN' if key == 'WHEELDOWN' else 'UP'
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
                    if leave_easily:
                        return ''                      # the IDE: Esc goes straight back to the editor
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
        underneath = self.popup(top, left, bottom, right, double=True)
        for n, line in enumerate(lines):
            self._w(self._put(top + 1 + n, left + 1, line.strip()[:inner].center(inner), self.fg, self.bg))
        choice = 0
        self._w('\x1b[?25l')
        try:
            while True:
                col = left + 1 + (inner - len(bar)) // 2
                out, spans = [], []
                for n, label in enumerate(labels):
                    fg, bg = (self.field_fg, self.field_bg) if n == choice else (self.fg, self.bg)
                    out.append(self._put(bottom - 1, col, label, fg, bg))
                    spans.append((col, col + len(label)))
                    col += len(label) + 2
                self._w(''.join(out) + self._normal())
                key = self.keys.read_key()
                if key is None:
                    key = ESC
                self.last_key = key
                if key == 'CLICK':
                    if self.keys.mouse_row == bottom - 1:
                        for n, (start, end) in enumerate(spans):
                            if start <= self.keys.mouse_col < end:
                                return n + 1           # the button clicked
                    continue
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
        # A menu taller than the room below it moves up; one taller than the screen scrolls
        below = 1 if self.shadows else 0
        if row + len(items) + 1 + below > self.rows:
            row = max(1, self.rows - len(items) - 1 - below)
        height = max(1, min(len(items), self.rows - row - 1 - below))
        underneath = self.popup(row, col, row + height + 1, col + width + 1)
        choice, first = 0, 0
        self._w('\x1b[?25l')
        try:
            while True:
                first = min(max(first, choice - height + 1), choice)
                for n in range(height):
                    i = first + n
                    fg, bg = (self.field_fg, self.field_bg) if i == choice else (self.fg, self.bg)
                    self._w(self._put(row + 1 + n, col + 1, ' ' + items[i].ljust(width - 1), fg, bg) + self._normal())
                if height < len(items):                # arrows on the border show there is more
                    self._w(self._put(row, col + width, '▲' if first > 0 else '─', self.fg, self.bg) +
                            self._put(row + height + 1, col + width, '▼' if first + height < len(items) else '─',
                                      self.fg, self.bg) + self._normal())
                key = self.keys.read_key()
                if key is None:
                    key = ESC
                self.last_key = key
                if key == 'CLICK':
                    r, c = self.keys.mouse_row, self.keys.mouse_col
                    if row < r <= row + height and col < c <= col + width:
                        return first + r - row         # the item clicked
                    if not (row <= r <= row + height + 1 and col <= c <= col + width + 1):
                        return 0                       # a click outside the menu cancels it
                    continue
                if key == 'WHEELDOWN':
                    key = 'DOWN'
                elif key == 'WHEELUP':
                    key = 'UP'
                if key == ESC:
                    return 0
                if key == ENTER:
                    return choice + 1
                if key in ('DOWN', 'RIGHT', TAB):
                    choice = (choice + 1) % len(items)
                elif key in ('UP', 'LEFT', 'BTAB'):
                    choice = (choice - 1) % len(items)
                elif key == 'HOME':
                    choice = 0
                elif key == 'END':
                    choice = len(items) - 1
                elif key == 'PGUP':
                    choice = max(0, choice - height) if height < len(items) else 0
                elif key == 'PGDN':
                    choice = min(len(items) - 1, choice + height) if height < len(items) else len(items) - 1
                elif len(key) == 1:
                    hits = [n for n, item in enumerate(items) if item.strip()[:1].upper() == key.upper()]
                    if hits:
                        return hits[0] + 1
        finally:
            self.restore_saved(underneath)       # put back what the menu covered
            self._w('\x1b[?25h')

    # --- BROWSE --------------------------------------------------------
    def browse(self, columns, rows, area=None, title='', save=None, hidden=(), locked=(), add=None, delete=None,
               start=0, frozen=0, formats=None, color_col=None, shadow=False,
               on_move=None, switch=False, keep=False, draw_only=False, bar=True, state=None, keys_hint=None,
               exit_keys=(), can_edit=None):
        """A scrolling grid. Returns the index of the chosen row, or -1 for Esc.

        With save, the grid is editable: Left/Right move between cells, Enter (or typing)
        edits the current cell, and save(row_index, col_index, value) stores the new value,
        returning an error message or None. Columns in hidden are not shown; columns in
        locked can't be edited. rows is updated in place with the saved values.

        With add, Ins calls add(), which inserts a row, reloads rows in place and returns the
        index of the new row (or None if it isn't known), or False when cancelled. With delete,
        Del asks for confirmation and calls delete(row_index), which returns an error or None.

        A click on a heading (or F3) sorts by that column; again reverses it. rows is sorted in
        place, or, if it has sort_by(col_index, descending, numeric), asked to sort itself.
        Without save, typing jumps to the next row whose sort column (or first column) starts
        with what was typed. frozen columns stay at the left when the others scroll. formats
        maps a column index to a function giving its text (shown right-aligned). color_col is
        the index of a column holding each row's text colour (0-15).

        For a master-detail screen (two grids taking turns): on_move(index) is called when the
        current row changes; with switch, F6 (and Tab when not editing) or a click outside the
        grid ends it with last_key set to that key; keep leaves the grid drawn instead of
        putting back what it covered; draw_only draws it and returns; bar=False draws no bar;
        state, a dict, keeps the position and sort between turns. keys_hint replaces
        "Enter=select  Esc=cancel" on the status line; 'back' marks a detail grid, whose Esc
        goes back to the master. A key in exit_keys (EXIT ON) ends the grid, returning the
        current row, with last_key set to it, so the program can act on it. can_edit()
        (EDIT WHEN), asked once as the grid is shown, returns None or why the rows can't be
        changed now: editing, Ins and Del are then refused with that message."""
        screen_rows, screen_cols = self.size()
        r1, c1, r2, c2 = area or (1, 1, screen_rows, screen_cols)
        if r2 - r1 < 4 or c2 - c1 < 10:
            raise ScreenError("BROWSE area is too small.")
        visible = [i for i in range(len(columns)) if i not in hidden]
        if not visible:
            raise ScreenError("BROWSE has no columns to show.")
        formats = formats or {}
        frozen = max(0, min(frozen, len(visible) - 1))

        def show(v, ci):
            if v is None:
                return ''
            if ci in formats:
                return formats[ci](v)
            return format_number(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else str(v)

        # Rows are formatted only when they are shown, so rows can be a lazy, paged list
        # (the interpreter passes one for large queries). Column widths start from the
        # first rows and grow when a wider value scrolls into view.
        class Cells:
            def __init__(self):
                self.cache = {}

            def __len__(self):
                return len(rows)

            def __bool__(self):
                return len(rows) > 0

            def __getitem__(self, i):
                if i not in self.cache:
                    self.cache[i] = [show(v, k) for k, v in enumerate(rows[i])]
                return self.cache[i]

            def pop(self, i):
                self.cache.clear()

        def widen(i):
            for k, text in enumerate(cells[i][:len(widths)]):
                widths[k] = min(30, max(widths[k], len(text)))

        def layout():
            cells = Cells()
            widths = [min(30, len(str(c))) for c in columns]
            for i in range(min(len(rows), 200)):
                for k, text in enumerate(cells[i][:len(widths)]):
                    widths[k] = min(30, max(widths[k], len(text)))
            if sort_col is not None:           # room for the heading's sort arrow
                widths[sort_col] = max(widths[sort_col], min(30, len(str(columns[sort_col])) + 1))
            return cells, widths

        sort_col, sort_desc = None, False      # column index of the sort, if any
        state = {} if state is None else state
        if state:
            sort_col, sort_desc = state.get('sort_col'), state.get('sort_desc', False)
        cells, widths = layout()
        page = r2 - r1 - 4                     # rows between the header line and the status line
        inner = c2 - c1 - 1
        top, current, cur_col = 0, 0, 0        # cur_col indexes visible[]
        first_col = frozen                     # the first scrolling column (index into visible[])
        typed, typed_at = '', 0.0              # type-ahead
        if 0 < start < len(rows):
            current = start
            top = max(0, start - (page - 1))
        if state:
            top, current = state.get('top', 0), state.get('current', 0)
            cur_col, first_col = state.get('cur_col', 0), state.get('first_col', frozen)
            current = max(0, min(current, len(rows) - 1))
        notified = None                        # the row on_move last heard about
        refusal = can_edit() if (save and can_edit) else None   # EDIT WHEN: why the rows are read-only
        message = ''
        if keep or draw_only:
            underneath = None
            self.box(r1, c1, r2, c2, title)
        else:
            underneath = self.popup(r1, c1, r2, c2, title, shadow=shadow and self.shadows)
        self._w('\x1b[?25l')

        def shown():
            """Indexes into visible[] of the columns drawn, left to right."""
            return list(range(frozen)) + list(range(first_col, len(visible)))

        def line(values, heading=False):
            parts = []
            for n in shown():
                i = visible[n]
                text = str(values[i])[:widths[i]]
                if heading and i == sort_col:
                    text = (text[:widths[i] - 1] + ('▼' if sort_desc else '▲'))
                parts.append(text.rjust(widths[i]) if i in formats and not heading else text.ljust(widths[i]))
                if frozen and n == frozen - 1:
                    parts[-1] += ' ║'
                elif n != len(visible) - 1:
                    parts[-1] += ' │'
            return (' ' + ' '.join(parts))[:inner].ljust(inner)

        def cell_offset(n):
            """Column within the grid where visible column n starts."""
            offset = 1
            for k in shown():
                if k == n:
                    return offset
                offset += widths[visible[k]] + 3
            return offset

        def column_at(c):
            """Index into visible[] of the column under screen column c, or None."""
            x = c - (c1 + 1)
            columns_shown = shown()
            for k in columns_shown:
                if x < cell_offset(k) + widths[visible[k]] + 2:
                    return k
            return columns_shown[-1]          # the last column runs to the edge of the box

        def numeric_column(ci):
            return any(isinstance(rows[i][ci], (int, float)) and not isinstance(rows[i][ci], bool)
                       for i in range(min(len(rows), 200)))

        def sort_key(v, numeric):
            """The order the grid sorts in: blanks first, then numbers or text (ignoring case)."""
            if v is None:
                return (0, 0)
            if numeric:
                if isinstance(v, (int, float)) and not isinstance(v, bool):
                    return (1, float(v))
                return (2, str(v).lower())
            return (1, str(v).lower())

        def sort_by(ci):
            nonlocal sort_col, sort_desc, cells, widths, current, top, message
            desc = (not sort_desc) if ci == sort_col else False
            numeric = numeric_column(ci)
            if hasattr(rows, 'sort_by'):
                error = rows.sort_by(ci, desc, numeric)
                if error:
                    bell()
                    message = 'Cannot sort: ' + error
                    return
            else:
                rows.sort(key=lambda r: sort_key(r[ci], numeric), reverse=desc)
            sort_col, sort_desc = ci, desc
            cells, widths = layout()
            current, top = 0, 0

        def find(text):
            """The row type-ahead jumps to: the next row whose search column starts with text."""
            ci = sort_col if sort_col is not None else visible[0]
            if not cells:
                return None
            if sort_col is not None and not sort_desc:
                # sorted ascending: a binary search, so even a paged million-row grid answers at once
                numeric = numeric_column(ci)
                if numeric:
                    try:
                        want = (1, float(text))
                    except ValueError:
                        return None
                else:
                    want = (1, text.lower())
                lo, hi = 0, len(rows)
                if hasattr(rows, 'position'):  # a paged grid counts in the database instead
                    lo = hi = rows.position(want[1])
                while lo < hi:
                    mid = (lo + hi) // 2
                    if sort_key(rows[mid][ci], numeric) < want:
                        lo = mid + 1
                    else:
                        hi = mid
                if lo >= len(rows):
                    return None
                return lo if numeric or str(rows[lo][ci]).lower().startswith(text.lower()) else None
            first = current if len(text) > 1 else current + 1
            for k in range(len(rows)):
                i = (first + k) % len(rows)
                if cells[i][ci].lower().startswith(text.lower()):
                    return i
            return None

        def edit_cell(screen_row, n, first_key):
            ci = visible[n]
            raw = rows[current][ci]
            numeric = isinstance(raw, (int, float)) and not isinstance(raw, bool)
            offset = cell_offset(n)
            # Room for at least 10 characters. A wider box covers whole cells to its right,
            # so no piece of the next column shows beside the value being typed
            needed = max(widths[ci], len(show(raw, None)), 10)
            span, order = widths[ci], shown()
            for k in order[order.index(n) + 1:] if n in order else []:
                if span >= needed:
                    break
                span += 3 + widths[visible[k]]
            width = max(1, min(max(span, needed), inner - offset))
            field = Field(screen_row, c1 + 1 + offset, '', '' if raw is None else raw, f'@S{width}', None, numeric)
            # Enter edits the value with the cursor after it, as in a spreadsheet
            pos, insert = field.end_pos(), True
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

        def row_colour(i):
            if color_col is None or i >= len(rows):
                return self.fg
            try:
                colour = int(rows[i][color_col])
            except (TypeError, ValueError):
                return self.fg
            return colour if 0 <= colour <= 15 else self.fg

        try:
            while True:
                # keep the current cell in view
                if save and cur_col >= frozen:
                    first_col = min(first_col, cur_col)
                    while first_col < cur_col and cell_offset(cur_col) + widths[visible[cur_col]] > inner:
                        first_col += 1
                out = [self._put(r1 + 1, c1 + 1, line(columns, heading=True), self.fg, self.bg),
                       self._put(r1 + 2, c1 + 1, '─' * inner, self.fg, self.bg)]
                for n in range(page):
                    if top + n < len(cells):
                        widen(top + n)
                for n in range(page):
                    i = top + n
                    fg, bg = (self.field_fg, self.field_bg) if i == current and bar else (row_colour(i), self.bg)
                    text = line(cells[i]) if i < len(cells) else ' ' * inner
                    out.append(self._put(r1 + 3 + n, c1 + 1, text, fg, bg))
                    if save and bar and i == current:   # the current cell in reverse
                        off = cell_offset(cur_col)
                        ci = visible[cur_col]
                        cell_text = text[off:off + widths[ci]]
                        out.append(self._put(r1 + 3 + n, c1 + 1 + off, cell_text, self.field_bg, self.field_fg))
                if message:
                    status = ' ' + message
                elif typed:
                    status = f' {current + 1 if cells else 0} of {len(cells)}   Find: {typed}'
                elif save and refusal:
                    status = f' {current + 1 if cells else 0} of {len(cells)}   {refusal}  F3=sort  Esc=done'
                elif save:
                    extra = ('  Ins=add' if add else '') + ('  Del=delete' if delete else '')
                    status = f' {current + 1 if cells else 0} of {len(cells)}   Enter=edit{extra}  F3=sort  Esc=done'
                else:
                    hint = 'Enter=back  Esc=back' if keys_hint == 'back' else keys_hint or 'Enter=select  Esc=cancel'
                    status = f' {current + 1 if cells else 0} of {len(cells)}   {hint}  ←→=columns  F3=sort'
                if switch and not message and not typed:
                    status = status.replace('  F3=sort', '  F3=sort  ' + ('F6' if save else 'Tab') + '=switch')
                    if keys_hint == 'back':        # a detail grid: Esc (and Enter) go back to the master
                        status = status.replace('Esc=done', 'Esc=back')
                if draw_only:                      # the grid without the keys shows no key hints
                    status = f' {current + 1 if cells else 0} of {len(cells)}'
                message = ''
                out.append(self._put(r2 - 1, c1 + 1, status[:inner].ljust(inner), self.fg, self.bg))
                self._w(''.join(out) + self._normal())
                state.update(top=top, current=current, cur_col=cur_col, first_col=first_col,
                             sort_col=sort_col, sort_desc=sort_desc)
                if on_move and current != notified and not draw_only:
                    notified = current
                    on_move(current if cells else -1)
                if draw_only:
                    return current
                key = self.keys.read_key()
                if key is None:
                    key = ESC
                self.last_key = key
                if key in exit_keys:
                    return current             # EXIT ON: the program handles this key
                if switch and (key == 'F6' or (key == TAB and not save) or
                               (key == 'CLICK' and not (r1 <= self.keys.mouse_row <= r2 and
                                                        c1 <= self.keys.mouse_col <= c2))):
                    return current             # the other grid's turn

                # type-ahead (when not editing): printable keys search, Backspace takes one back
                if not save and ((len(key) == 1 and key.isprintable()) or (key == BACKSPACE and typed)):
                    now = time.monotonic()
                    if now - typed_at > 1.5:
                        typed = ''
                    typed_at = now
                    wanted = typed[:-1] if key == BACKSPACE else typed + key
                    found = find(wanted) if wanted else current
                    if found is None:
                        bell()
                    else:
                        typed, current = wanted, found
                    if current < top or current >= top + page:
                        top = max(0, current - page // 2)
                    continue
                typed = ''

                if key == 'CLICK':
                    r, c = self.keys.mouse_row, self.keys.mouse_col
                    if r == r1 + 1 and c1 < c < c2:    # a heading: sort by it
                        n = column_at(c)
                        if n is not None:
                            sort_by(visible[n])
                        continue
                    n, i = r - (r1 + 3), top + r - (r1 + 3)
                    if not (0 <= n < page and i < len(cells) and c1 < c < c2):
                        continue                       # not on a row
                    new_col = cur_col
                    if save:                           # which cell: column offsets as drawn
                        k = column_at(c)
                        new_col = cur_col if k is None else k
                    if i == current and new_col == cur_col:
                        key = ENTER                    # a click on the selected row (or cell) chooses (edits) it
                    else:
                        current, cur_col, key = i, new_col, ''
                elif key in ('WHEELDOWN', 'WHEELUP'):
                    current += 3 if key == 'WHEELDOWN' else -3
                    current = min(max(current, 0), max(len(cells) - 1, 0))
                    key = ''
                if key == ESC:
                    return -1
                if key == 'F3':
                    sort_by(visible[cur_col] if save else visible[first_col if first_col < len(visible) else 0])
                    continue
                if refusal and (key in ('INS', 'DEL', ENTER, 'F2') or (len(key) == 1 and key.isprintable())):
                    bell()                     # EDIT WHEN: these rows can't be changed now
                    message = refusal
                    continue
                if save and add and key == 'INS':
                    new_index = add()
                    if new_index is not False:
                        new_row = rows[new_index] if new_index is not None else None
                        if sort_col is not None and not hasattr(rows, 'sort_by'):
                            numeric = numeric_column(sort_col)
                            rows.sort(key=lambda r: sort_key(r[sort_col], numeric), reverse=sort_desc)
                            new_index = next((k for k, r in enumerate(rows) if r is new_row), None)
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
                        message = locked[ci] if isinstance(locked, dict) else \
                            f'{columns[ci]} is the key and cannot be changed.'
                        continue
                    result, end_key = edit_cell(r1 + 3 + current - top, cur_col, None if key in (ENTER, 'F2') else key)
                    if result is not None:
                        error = save(current, ci, result[1])
                        if error:
                            bell()
                            message = 'Not saved: ' + error
                        else:
                            rows[current][ci] = result[1]
                            cells[current][ci] = show(result[1], ci)
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
                elif key == 'LEFT': first_col = max(first_col - 1, frozen)
                current = max(current, 0)
                if current < top: top = current
                elif current >= top + page: top = current - page + 1
        finally:
            if underneath:
                self.restore_saved(underneath)   # put back what the grid covered
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
