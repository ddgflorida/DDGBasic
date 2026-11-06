"""Checks of the IDE's editing logic (src/dbide.py) that need no terminal: loading and
saving, typing, Enter's indent, Backspace, Delete, Tab, line commands, undo, find,
syntax colouring, F1's choice of help topic and reading the line of an error.
run_tests.py runs it with the BASIC test scripts (from source only)."""
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'src'))
from dbbasic import HelpRegistry          # noqa: E402
from dbide import Editor, error_location  # noqa: E402

failures = []


def check(condition, what):
    if not condition:
        failures.append(what)


def editor(text=''):
    e = Editor(None, ['dbbasic'], HelpRegistry.list_topics(), HelpRegistry.get_help)
    e.lines = text.split('\n') if text else ['']
    return e


# Loading and saving: tabs become 4 spaces, the file's line endings are kept
folder = tempfile.mkdtemp()
path = os.path.join(folder, 'p.bas')
with open(path, 'w', newline='') as f:
    f.write('FOR i = 1 TO 2\r\n\tPRINT i\r\nNEXT\r\n')
e = Editor(path, ['dbbasic'], HelpRegistry.list_topics(), HelpRegistry.get_help)
check(e.lines == ['FOR i = 1 TO 2', '    PRINT i', 'NEXT'], f'load: {e.lines}')
check(e.newline == '\r\n', 'load: CRLF line endings')
e.row, e.col = 2, 4
e.type_char('!')
check(e.modified, 'typing marks the program changed')
e.save()
with open(path, 'rb') as f:
    check(f.read() == b'FOR i = 1 TO 2\r\n    PRINT i\r\nNEXT!\r\n', 'save keeps CRLF and adds the last newline')
check(not e.modified, 'save clears the changed mark')

# Typing, Enter keeps the indent, Backspace back to the indent stop, Delete joins lines
e = editor('IF x THEN\n    PRINT 1')
e.row, e.col = 1, 11
e.enter()
check(e.lines == ['IF x THEN', '    PRINT 1', '    '] and (e.row, e.col) == (2, 4), f'enter keeps the indent: {e.lines}')
e.backspace()
check(e.lines[2] == '' and e.col == 0, f'backspace in the indent goes back 4: {e.lines}')
e.backspace()
check(e.lines == ['IF x THEN', '    PRINT 1'] and (e.row, e.col) == (1, 11), 'backspace at the start joins lines')
e.row, e.col = 0, 9
e.delete()
check(e.lines == ['IF x THEN    PRINT 1'], f'delete at the end joins the next line: {e.lines}')

# Tab and Shift-Tab
e = editor('PRINT 1')
e.tab()
check(e.lines == ['    PRINT 1'] and e.col == 4, 'tab indents to the next stop')
e.tab(back=True)
check(e.lines == ['PRINT 1'] and e.col == 0, 'shift-tab unindents')

# Overwrite mode
e = editor('ABC')
e.insert = False
e.type_char('x')
check(e.lines == ['xBC'], 'overwrite replaces a character')

# Delete and duplicate a line, then undo each step
e = editor('a\nb\nc')
e.row = 1
e.delete_line()
check(e.lines == ['a', 'c'], 'Ctrl-Y deletes the line')
e.duplicate_line()
check(e.lines == ['a', 'c', 'c'], 'Ctrl-D duplicates the line')
e.do_undo()
check(e.lines == ['a', 'c'], 'undo the duplicate')
e.do_undo()
check(e.lines == ['a', 'b', 'c'], 'undo the delete')

# Typing on one line is one undo step
e = editor('')
for ch in 'PRINT':
    e.type_char(ch)
e.do_undo()
check(e.lines == [''], 'typing a word is one undo step')

# Find (again): case-insensitive, from after the cursor, wrapping round
e = editor('print a\nPRINT b\nx = 1')
e.find_text = 'print'
e.row, e.col = 0, 0
e.find(again=True)
check((e.row, e.col) == (1, 0), f'find the next match: {(e.row, e.col)}')
e.find(again=True)
check((e.row, e.col) == (0, 0), f'find wraps round: {(e.row, e.col)}')

# Syntax colouring
e = editor()
s = e.scheme
line = 'PRINT "hi" : x = 12 -- note'
c = e.colours_of(line)
check(c[0] == s['keyword'], 'PRINT is a keyword')
check(c[line.index('"hi"')] == s['string'], 'a string')
check(c[line.index('12')] == s['number'], 'a number')
check(c[line.index('-- note')] == s['comment'], 'a -- comment')
c = e.colours_of('REM all of this')
check(set(c) == {s['comment']}, 'a REM line is a comment')
c = e.colours_of('PRINT c.name')
check(c[line.index('PRINT')] == s['keyword'] and c[8] == s['text'], 'a field after a . is not a keyword')
c = e.colours_of('x$ = "say ""hi"""')
check(set(c[5:]) == {s['string']}, 'doubled quotes stay inside the string')

# F1: the help topic for the word under the cursor
def topic(text, col):
    e = editor(text)
    e.col = col
    return e.help_topic_at_cursor()

check(topic('PRINT x', 2) == 'PRINT', 'F1 on PRINT')
check(topic('@ 5, 10 SAY "x" GET a$', 18) == '@', 'F1 on GET shows the @ help')
check(topic('ON KEY "F1" CALL f', 4) == 'ON KEY', 'F1 on a two-word topic')
check(topic('SET THEME "green"', 1) == 'SET THEME', 'F1 on the first word of a two-word topic')
check(topic('NEXT i', 1) == 'FOR', 'F1 on NEXT shows FOR')
check(topic('x = 1', 0) is None, 'F1 on a variable has no topic')

# The line and column of an error, as programs print them
check(error_location('Hello\nRuntime Error: Unknown function: FOO at line 3, col 17.\n  Context: ...')
      == ('Unknown function: FOO', 3, 17), 'a runtime error')
check(error_location("Error: Unexpected character '{' at line 2, col 5\n")
      == ("Unexpected character '{'", 2, 5), 'a lexer error')
check(error_location('all fine\n') is None, 'no error')

# The Immediate window: its own session, ? for PRINT, variables kept, SQL, errors, CLS
from dbbasic import Interpreter, Lexer   # noqa: E402
e = Editor(None, ['dbbasic'], HelpRegistry.list_topics(), HelpRegistry.get_help,
           new_session=lambda: Interpreter(Lexer("\n"), cmd_args=[]))
check(e.execute_immediate('? 1 + 2') == [' 3'], 'the Immediate window: ? 1 + 2')
e.execute_immediate('x = 5')
check(e.execute_immediate('? x * 10') == [' 50'], 'the Immediate window keeps variables')
out = e.execute_immediate('SELECT 42 AS answer;')
check(any('42' in l for l in out) and any('answer' in l for l in out), f'the Immediate window runs SQL: {out}')
check(e.execute_immediate('PRINT FOO(1)') == ['Error: Unknown function: FOO'], 'an error shows only its message')
check(e.execute_immediate('INPUT a$')[0].startswith("INPUT can't be used here"), 'INPUT is refused')
check(e.imm_lines[0] == '> ? 1 + 2' and e.imm_history[-1] == 'INPUT a$', 'typed lines are kept and recalled')
e.execute_immediate('CLS')
check(e.imm_lines == [], 'CLS clears the Immediate window')

if failures:
    for f in failures:
        print('FAIL:', f)
    sys.exit(1)
print('ide_check: all checks passed')
