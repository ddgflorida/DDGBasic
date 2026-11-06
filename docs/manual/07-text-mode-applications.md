# Chapter 7: Text-mode Applications

This chapter covers DbBasic's full-screen text interface: coloured screens, boxes, entry forms, menus, editable grids, a memo editor and a text viewer, in the style of 1990s BASIC and xBase programs. It starts with a tutorial, then describes each statement.

Example programs in `examples/`, each short enough to read in a minute:

| Example | Shows |
|---|---|
| `contact.bas` | The simplest useful form: a contact screen with `GET` into a hash, an `@R` phone, a `LIST`, a `CHECKBOX` and Save/Cancel buttons, saved with one `INSERT` |
| `make_form_demo.bas` | `MAKE FORM`: writes a complete data-entry program for a table |
| `form_demo.bas` | An order form: `GET` with `PICTURE`, a `LOOKUP` list, a date (`@D`), number masks, `@R` phone, `CHECKBOX`, a drop-down `LIST`, `VALID ... MESSAGE`, `WHEN`, Save/Cancel buttons, and F1 help with `ON KEY` |
| `menu_demo.bas` | `MENUBAR$` with pull-downs, a pop-up `MENU` that changes the colours, and `ALERT` |
| `grid_demo.bas` | `BROWSE` as a picker and as an editor (`EDIT`, Ins, Del) on 10,000 rows, with sorting, type-ahead, `FREEZE`, `FORMAT` and row colours (`COLOR`) |
| `invoice_demo.bas` | A traditional invoice screen on the Chinook database: the header as a form, the lines as a grid, PgUp/PgDn between invoices, F2 find, F4 edit the header, Ins add a track (`BROWSE ... EXIT ON`); only open invoices can be changed (`EDIT WHEN`) |
| `orders_demo.bas` | A master-detail screen: orders on top, their lines below (`BROWSE ... DETAIL`), editable only for open orders (`EDIT WHEN`), with totals that follow |
| `themes_demo.bas` | The same form in each `SET THEME` colour scheme |
| `progress_demo.bas` | A `PROGRESS` bar while a table loads, a `MENU` longer than the screen that scrolls, and drop shadows |
| `report_demo.bas` | `REPORT` with nested groups and totals, on the screen, in the viewer and in a paged file |
| `notes_demo.bas` | `EDIT TEXT` and `VIEW`, including `VIEW FILE` |
| `mouse_demo.bas` | A tiny paint program: `INKEY$` mouse keys with `MOUSEROW` and `MOUSECOL` |
| `retro_contacts.bas` | All of it together: the contact manager of 7.1 |

The test runner plays each of them with scripted keys, so they are also tests.

Related material in other chapters:

* `PRINT`, `INPUT` and the console: **Chapter 4** and **Chapter 6**.
* Queries, bind variables and `FOR row IN (SELECT ...)`: **Chapter 4**.
* `SET AUTOADVANCE` and the other `SET` options: **Chapter 4, 4.9**.

## Contents

1. [Tutorial: a contact manager](#71-tutorial-a-contact-manager)
2. [The screen](#72-the-screen)
   * [CLS, LOCATE, COLOR and BOX](#cls-locate-color-and-box) · [PROGRESS](#progress) · [SAVESCREEN and RESTSCREEN](#savescreen-and-restscreen)
3. [Entry fields](#73-entry-fields)
   * [@ ... SAY ... GET](#--say--get) · [READ](#read) · [Buttons](#buttons)
4. [Menus and message boxes](#74-menus-and-message-boxes)
   * [MENUBAR$()](#menubar) · [MENU()](#menu) · [ALERT()](#alert)
5. [Working with tables](#75-working-with-tables)
   * [BROWSE](#browse) · [EDIT RECORD](#edit-record) · [MAKE FORM](#make-form)
6. [Editing and viewing text](#76-editing-and-viewing-text)
   * [EDIT TEXT](#edit-text) · [VIEW](#view)
7. [The keyboard and mouse](#77-the-keyboard-and-mouse)
   * [INKEY$ and LASTKEY$](#inkey-and-lastkey) · [Hot keys: ON KEY](#hot-keys-on-key) · [The mouse](#the-mouse) · [Keyboard and terminal](#keyboard-and-terminal)
8. [Replacing the old FORM statements](#78-replacing-the-old-form-statements)
9. [Implementation notes](#79-implementation-notes)

---

## 7.1 Tutorial: a contact manager

`examples/retro_contacts.bas` is a complete application in about a hundred and fifty lines. This section builds it up piece by piece. Run it with `dbbasic examples/retro_contacts.bas` (or `python3 src/dbbasic.py examples/retro_contacts.bas`) in a terminal of at least 80 x 24.

**1. The data.** A text-mode application is an ordinary DbBasic program, so it starts with its tables:

```basic
DATABASE OPEN ":memory:"
CREATE TABLE states (code TEXT PRIMARY KEY, name TEXT);
INSERT INTO states VALUES ('CA', 'California'), ('FL', 'Florida'), ('NY', 'New York'), ('TX', 'Texas');
CREATE TABLE contacts (id INTEGER PRIMARY KEY, name TEXT NOT NULL, phone TEXT, email TEXT, state TEXT,
                       active TEXT DEFAULT 'Y', since TEXT, credit REAL CHECK (credit >= 0), notes TEXT);
```

**2. The desktop.** `COLOR` sets the colours (here bright white on blue, with black-on-cyan fields and menu bars), `CLS` clears the screen in them, and `BOX` draws the frame:

```basic
desktop:
    COLOR 15, 1, 0, 3
    CLS
    BOX 2, 1, 23, 80, "CONTACTS  " & DATE$ DOUBLE
    @ 24, 2 SAY "F1 help  Arrows move  Enter chooses  Esc goes back  Letters are hot keys"
    RETURN
```

F1 shows the keys from anywhere in the program: on the menu bar, in a form, in the grid or the editor. `ON KEY` binds the key to a function once, at the top, and every screen statement honours it, putting the screen back afterwards:

```basic
FUNCTION show_help()
    VIEW keys$ AT 5, 8, 17, 74 TITLE "Keys (Esc closes)"
END FUNCTION
ON KEY "F1" CALL show_help
```

**3. The menu bar.** `MENUBAR$` draws a bar with a pull-down under each title and returns the choice as `"Title.Item"`, so the main loop reads like a list of commands:

```basic
GOSUB desktop
DO
    GOSUB summary
    choice$ = MENUBAR$("File:Report|-|Quit", "Contacts:Browse|Add|Edit|Notes|Delete", "Help:Keys|About")
    IF choice$ = "File.Report" THEN GOSUB report
    IF choice$ = "Contacts.Browse" THEN GOSUB browse_contacts
    IF choice$ = "Contacts.Add" THEN GOSUB add_contact
    ...
LOOP UNTIL choice$ = "File.Quit" OR choice$ = ""
```

```
 File   Contacts   Help
╔════════───────┐════════════ CONTACTS  2026-11-05 ════════════════════════════╗
║      │ Browse │                                                              ║
║      │ Add    │                                                              ║
║      │ Edit   │                                                              ║
║      │ Notes  │                                                              ║
║      │ Delete │                                                              ║
║      └────────┘                                                              ║
```

`summary` fills the desktop with the contacts on file, so the opening screen isn't an empty frame, and it is drawn again on every pass of the loop, so the list stays current after each command:

```basic
summary:
    BOX 3, 3, 21, 78, "Contacts on file"
    @ 5, 6 SAY PADRIGHT$("Name", 20, " ") & " " & PADRIGHT$("Phone", 16, " ") & " " & PADRIGHT$("State", 5, " ") & "    Credit"
    @ 6, 6 SAY REPEAT$("-", 53)
    row = 7
    FOR s IN (SELECT name, phone, state, credit, active FROM contacts ORDER BY name LIMIT 12)
        IF s.active = "N" THEN COLOR 7
        @ row, 6 SAY PADRIGHT$(s.name, 20, " ") & " " & PADRIGHT$(s.phone, 16, " ") & " " & PADRIGHT$(s.state, 5, " ") & FORMAT$(s.credit, "###,##0.00")
        COLOR 15
        row = row + 1
    NEXT
    @ 20, 6 SAY LTRIM$(STR$((SELECT COUNT(*) FROM contacts))) & " contacts.  Press C for Contacts, F for File, H for Help."
    RETURN
```

```
 File   Contacts   Help
╔════════════════════════════ CONTACTS  2026-11-05 ════════════════════════════╗
║ ┌──────────────────────────── Contacts on file ────────────────────────────┐ ║
║ │                                                                          │ ║
║ │  Name                 Phone            State    Credit                   │ ║
║ │  -----------------------------------------------------                   │ ║
║ │  ACME CORP            (555) 123-4567   FL     1,000.00                   │ ║
║ │  GLOBEX               (555) 999-0000   NY       250.50                   │ ║
║ │  INITECH              (555) 444-1212   TX         0.00                   │ ║
```

**4. The list.** One `BROWSE ... EDIT` gives a scrolling grid in which Enter (or typing) edits a cell, Ins adds a row and Del deletes one. Every change goes straight to the table. A click on a heading (or F3) sorts by that column. `FREEZE 2` keeps the id and name in view while the other columns scroll, `FORMAT` shows the credit with commas, and `COLOR` takes each row's colour from a column of the query, here grey (7) for inactive contacts:

```basic
browse_contacts:
    BROWSE (SELECT id, name, phone, email, state, active, since, credit,
                   CASE WHEN active = 'N' THEN 7 END AS shade
              FROM contacts ORDER BY name) EDIT KEY "id" _
        AT 3, 3, 21, 78 TITLE "Contacts (Enter edits, Ins adds, Del deletes, F3 sorts)" _
        FREEZE 2 FORMAT credit "###,##0.00" COLOR "shade"
    RETURN
```

**5. An entry form.** For a form with its own layout, `@ ... SAY ... GET` places the fields and `READ` edits them. The fields here belong to a hash, `c`, so the `INSERT` can bind them directly. `PICTURE` shapes the input (`@D` is a date, `999,999.99` a number typed like a calculator), `VALID ... MESSAGE` explains a refusal, `LIST` makes the state a drop-down filled from a query, `CHECKBOX` gives a `[X]` box, and `HINT` puts a line of help on the bottom of the screen while the cursor is in that field. `BOX ... SHADOW` gives the form a drop shadow:

```basic
add_contact:
    c.name = "" : c.phone = "" : c.email = "" : c.state = "FL" : c.active = "Y" : c.since = DATE$ : c.credit = 0
    saved$ = SAVESCREEN()
    BOX 5, 12, 18, 68, "New contact" SHADOW
    @ 7, 15 SAY "Name   : " GET c.name PICTURE "@!S30" VALID LEN(TRIM$(c.name)) > 0 MESSAGE "A name is required" _
        HINT "The company or person's name (required)"
    @ 8, 15 SAY "Phone  : " GET c.phone PICTURE "(999) 999-9999" HINT "Ten digits: the brackets and dash are filled in"
    @ 9, 15 SAY "Email  : " GET c.email PICTURE "@S30" HINT "Optional"
    @ 10, 15 SAY "State  : " GET c.state LIST (SELECT code FROM states ORDER BY code) _
        HINT "Space or F2 opens the list; a letter jumps to a state"
    @ 11, 15 SAY "Active : " GET c.active CHECKBOX HINT "Space ticks or clears the box"
    @ 12, 15 SAY "Since  : " GET c.since PICTURE "@D" HINT "When they became a customer: YYYY-MM-DD"
    @ 13, 15 SAY "Credit : " GET c.credit PICTURE "999,999.99" VALID c.credit >= 0 AND c.credit <= 100000 _
        MESSAGE "Credit must be 0 to 100,000" HINT "Credit limit in dollars, 0 to 100,000"
    @ 16, 15 BUTTON "Save"
    @ 16, 25 BUTTON "Cancel" CANCEL
    READ
    RESTSCREEN saved$
    IF BUTTON$ <> "Save" THEN RETURN
    INSERT INTO contacts (name, phone, email, state, active, since, credit)
        VALUES (:c.name, :c.phone, :c.email, :c.state, :c.active, :c.since, :c.credit);
    x = ALERT("Saved " & c.name)
    RETURN
```

```
╔════════════════════════════ CONTACTS  2026-11-05 ════════════════════════════╗
║ ┌──────────────────────────── Contacts on file ────────────────────────────┐ ║
║ │                                                                          │ ║
║ │  Name  ┌───────────────────── New contact ─────────────────────┐         │ ║
║ │  ------│                                                       │         │ ║
║ │  ACME C│  Name   : HOOLI                                       │         │ ║
║ │  GLOBEX│  Phone  : (555) 222-3333                              │         │ ║
║ │  INITEC│  Email  :                                             │         │ ║
║ │        │  State  : FL ▼                                        │         │ ║
║ │        │  Active : [X]                                         │         │ ║
║ │        │  Since  : 2026-11-05                                  │         │ ║
║ │        │  Credit :       0.00                                  │         │ ║
║ │        │                                                       │         │ ║
║ │        │                                                       │         │ ║
║ │        │  [ Save ]  [ Cancel ]                                 │         │ ║
║ │        │                                                       │         │ ║
║ │        └───────────────────────────────────────────────────────┘         │ ║
...
 Space or F2 opens the list; a letter jumps to a state
```

The bottom line is the hint for the field with the cursor, State here; the program's own status line comes back when `READ` ends. `BUTTON` adds `[ Save ]` and `[ Cancel ]` after the fields: Enter on the last field moves onto them, and `BUTTON$` tells the program which was pressed (`CANCEL` makes a button put the old values back, like Esc). `SAVESCREEN` and `RESTSCREEN` put back what the form covered. `ALERT` shows a message box and waits for a key.

**6. A form in one line.** When the layout doesn't matter, `EDIT RECORD` lays out one labelled field per column and saves the changes with an `UPDATE`:

```basic
edit_contact:
    GOSUB pick_contact
    IF LASTKEY$ = CHR$(27) THEN RETURN
    EDIT RECORD (SELECT id, name, phone, state, credit FROM contacts WHERE id = :c.id) TITLE "Edit contact"
    RETURN

pick_contact:
    BROWSE (SELECT name, phone, state, id FROM contacts ORDER BY name) AT 3, 3, 21, 78 TITLE "Pick a contact (type a name)" INTO c
    RETURN
```

`BROWSE` without `EDIT` is a picker: Enter puts the chosen row into `c` as a hash. Typing jumps to the next row whose first column starts with what was typed, so the name comes first.

**7. Notes, confirmations and reports.** `EDIT TEXT` is a memo editor, `ALERT` with buttons asks a question, and `REPORT ... TO VIEW` lays out a report with a group per state and credit totals, and shows it in the scrolling viewer with search:

```basic
edit_notes:
    GOSUB pick_contact
    IF LASTKEY$ = CHR$(27) THEN RETURN
    FOR rec IN (SELECT id, name, notes FROM contacts WHERE id = :c.id)
        EDIT TEXT rec.notes AT 5, 10, 18, 70 TITLE "Notes: " & rec.name
        IF LASTKEY$ <> CHR$(27) THEN UPDATE contacts SET notes = :rec.notes WHERE id = :rec.id;
    NEXT
    RETURN

delete_contact:
    GOSUB pick_contact
    IF LASTKEY$ = CHR$(27) THEN RETURN
    IF ALERT("Delete " & c.name & "?", "No", "Yes") = 2 THEN DELETE FROM contacts WHERE id = :c.id;
    RETURN

report:
    REPORT (SELECT state, name, active, credit FROM contacts ORDER BY state, name) _
        TITLE "Contacts by state" GROUP BY state TOTAL credit FORMAT credit "###,##0.00" TO VIEW
    RETURN
```

```
║ ┌────────────────────── Contacts by state (q closes) ──────────────────────┐ ║
║ │┌───────┬──────────┬────────┐                                             │ ║
║ ││ state │ contacts │ credit │                                             │ ║
║ │├───────┼──────────┼────────┤                                             │ ║
║ ││ CA    │ 1        │ 750.0  │                                             │ ║
║ ││ FL    │ 1        │ 1000.0 │                                             │ ║
║ ││ TX    │ 1        │ 0.0    │                                             │ ║
║ │└───────┴──────────┴────────┘                                             │ ║
║ │(3 rows returned)                                                         │ ║
```

The pattern throughout is the same: every screen statement waits for the user, puts back what it covered, and leaves `LASTKEY$` set, so `IF LASTKEY$ = CHR$(27) THEN RETURN` is all it takes to honour Esc. The rest of this chapter is the reference for each statement.

The test runner plays the whole program with scripted keystrokes (`tests/run_tests.py`, `STDIN`), so it is also a regression test.

---

## 7.2 The screen

The screen is drawn with ANSI escape sequences, so `PRINT` keeps working between screen statements and no extra packages are needed. The code is in `src/dbscreen.py`. It has been tested in macOS terminals; Linux terminals work the same way. Windows 10 and later (Windows Terminal or the console) are supported by the code, but the Windows key handling has not been tested yet.

**Coordinates** are `row, col`, counted from 1 at the top left, as with `LOCATE`.

```basic
COLOR 15, 1                          REM bright white on blue
CLS
BOX 2, 5, 9, 60, "Customer" DOUBLE
name$ = "" : phone$ = "" : credit = 0
@ 4, 8 SAY "Name  : " GET name$  PICTURE "@!S20"
@ 5, 8 SAY "Phone : " GET phone$ PICTURE "(999) 999-9999"
@ 6, 8 SAY "Credit: " GET credit VALID credit >= 0
READ
IF LASTKEY$ = CHR$(27) THEN GOTO cancelled
```

```
    ╔══════════════════════ Customer ══════════════════════╗
    ║                                                      ║
    ║  Name  : ANN SMITH                                   ║
    ║  Phone : (555) 123-4567                              ║
    ║  Credit: 12                                          ║
    ║                                                      ║
    ║                                                      ║
    ╚══════════════════════════════════════════════════════╝
```

### CLS, LOCATE, COLOR and BOX

| Statement | Effect |
|---|---|
| `CLS` | Clears the screen in the current colours and moves the cursor to 1, 1. Pending `GET` fields are discarded. |
| `LOCATE row [, col]` | Moves the cursor. The next `PRINT` or `INPUT` starts there. `col` defaults to 1. |
| `COLOR [fg] [, bg] [, field_fg] [, field_bg]` | Sets the text colours. Any value can be left out (`COLOR , 4` changes only the background). `field_fg`/`field_bg` colour `GET` fields, the menu bar and the `BROWSE` bar; they start as black on white. |
| `BOX top, left, bottom, right [, title$] [DOUBLE] [SHADOW]` | Draws a single- or double-line box, clears its inside in the current colours, and centres the title in the top line. `SHADOW` adds a drop shadow (see below). |
| `SET THEME name$` | Sets all four colours of `COLOR` from a named theme (see below). `CLS` afterwards repaints the screen in it. |
| `SET SHADOW ON` / `OFF` | Whether pop-ups (`MENU`, `ALERT`, pull-downs, `LIST` and `LOOKUP` pickers, `EDIT RECORD` and `PROGRESS`) have a drop shadow. On by default. |

The colour numbers are those of QBasic:

| | | | | | | | |
|---|---|---|---|---|---|---|---|
| 0 black | 1 blue | 2 green | 3 cyan | 4 red | 5 magenta | 6 brown | 7 white |
| 8 grey | 9 light blue | 10 light green | 11 light cyan | 12 light red | 13 light magenta | 14 yellow | 15 bright white |

**Themes.** `SET THEME` picks a whole colour scheme in one line, so a program can change its look, or let the user choose, without a set of `COLOR` numbers:

| Theme | Text | Fields, menu bar, `BROWSE` bar | Looks like |
|---|---|---|---|
| `default` | white on black | black on white | the terminal; DbBasic's start-up colours |
| `classic` | bright white on blue | black on cyan | the blue screens of 1990s business software |
| `norton` | light cyan on blue | black on cyan | file managers of the same years |
| `green` | light green on black | black on light green | a green-screen terminal |
| `amber` | yellow on black | black on brown | an amber monitor |
| `paper` | black on white | bright white on blue | a printed form |
| `mono` | bright white on black | black on bright white | no colour at all |

```basic
SET THEME "classic"
CLS
```

The names can be in any case. An unknown name is an error that lists the themes. `MAKE FORM` programs start with `SET THEME "classic"`, so one word changes their look. `examples/themes_demo.bas` shows the same screen in each theme.

**Shadows.** A drop shadow darkens what is under the box: the two columns to its right and the row below it, offset as if the light came from the top left. The characters stay readable, drawn in grey on black. The pop-ups have one unless `SET SHADOW OFF`; a `BOX` has one when it says `SHADOW`. When a pop-up closes, the shadowed area is put back with the rest. A `BOX ... SHADOW` is part of the screen until something is drawn over it, so save the area with its shadow (two columns wider and one row taller) if you want to put it back.

```
xxxx┌──────── Shadow ────────┐xxxxx
xxxx│                        │▒▒xxx      ▒ = the characters under the shadow, in grey on black
xxxx│                        │▒▒xxx
xxxx└────────────────────────┘▒▒xxx
xxxxxx▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒xxx
```

### PROGRESS

```
PROGRESS done, total [TITLE title$]
PROGRESS OFF
```

`PROGRESS` shows a centred box with a bar and a percentage, for a long job. The first `PROGRESS` draws the box; later ones update the bar in place. Only a change in what is shown is drawn, so calling it on every pass of a tight loop costs little. `PROGRESS OFF` removes the box and puts back what it covered. The cursor is left where it was, so `PRINT` carries on as before.

```basic
FOR i = 1 TO n
    PROGRESS i, n TITLE "Copying"
    REM ... the work ...
NEXT i
PROGRESS OFF
```

```
┌──────────────────── Copying ─────────────────────┐
│                                                  │
│ ████████████████████░░░░░░░░░░░░░░░░░░░░░░░  46% │
│                                                  │
└──────────────────────────────────────────────────┘
```

### SAVESCREEN and RESTSCREEN

```
saved$ = SAVESCREEN()                          REM the whole screen
saved$ = SAVESCREEN(top, left, bottom, right)  REM an area
RESTSCREEN saved$
```

`SAVESCREEN` copies the screen, or an area of it, with its colours and the cursor position, into a string. `RESTSCREEN` puts that area back where it came from and returns the cursor. Use them around a pop-up window:

```basic
saved$ = SAVESCREEN(8, 20, 14, 60)
BOX 8, 20, 14, 60, "Warning" DOUBLE
@ 11, 24 SAY "Credit limit exceeded. Press a key."
k$ = INKEY$(0)
RESTSCREEN saved$
```

A terminal cannot report what it is showing, so DbBasic keeps its own copy of the screen. The copy includes everything drawn by `CLS`, `BOX`, `SAY`, `GET`, `MENU` and `BROWSE`, and the text of `PRINT`, `PRINT USING` and `INPUT` once a screen statement has been used. Output that bypasses it, such as query result tables, `SHELL` output or error messages, is not in the copy, and `RESTSCREEN` will draw over it with what the copy holds. `CLS` resets the copy to the terminal's current size.

Compare two saved strings to see whether the screen changed: `IF SAVESCREEN() <> saved$ THEN ...`.

---

## 7.3 Entry fields

### @ ... SAY ... GET

```
@ row, col [SAY expr [PICTURE mask$]] [GET target [PICTURE mask$] [VALID condition] [MESSAGE text$]
                                                  [HINT text$] [WHEN condition] [LOOKUP (SELECT ...)]
                                                  [CHECKBOX] [LIST items]]
```

The `GET` clauses can come in any order.

`SAY` writes the value of `expr` at the position. With `PICTURE`, the value is formatted as `FORMAT$(expr, mask$)` would format it: `@ 20, 1 SAY 1234.5 PICTURE "#,###.##"` shows `1,234.50`.

`GET` puts an entry field for a variable straight after the `SAY` text, or at `col` if there is no `SAY`. It shows the current value in the field colours. Nothing is edited until `READ`.

The target can be a variable (`name$`, `qty`), a hash field (`rec.name`, `rec.ship.city`, `h("key")`) or an array element (`a(2)`). A hash field is found the way `rec.name` reads it, ignoring case, so `GET rec.name` edits the `NAME` column of a row from `FOR rec IN (SELECT ...)` or `BROWSE ... INTO rec`. A field that does not exist yet is created when `READ` stores it. A target whose name ends in `$`, or that holds a string, gets a text field; one that holds a number gets a numeric field. A whole array or hash can't be edited.

Editing a record hash keeps a form short, because bind variables can name hash fields too:

```basic
FOR rec IN (SELECT * FROM contacts WHERE id = :id)
    @ 5, 13 SAY "Last  : " GET rec.last_name PICTURE "@!S20"
    @ 6, 13 SAY "Email : " GET rec.email     PICTURE "@S40"
    READ
    IF LASTKEY$ <> CHR$(27) THEN UPDATE contacts SET last_name = :rec.last_name, email = :rec.email WHERE id = :id;
NEXT
```

| `GET` picture | Meaning |
|---|---|
| (none) | Text: as wide as the current value, and at least 20. Numbers: 10 wide. |
| `@!` | Upper-case every letter typed. |
| `@Sn` | A field `n` characters wide, for example `@S30`. Combine with `!`: `@!S30`. |
| `@D` | A date, typed as `YYYY-MM-DD` (the `-` are fixed). Leaving the field with an impossible date, such as `2024-02-30`, shows `Not a valid date` and keeps the cursor there. An empty date is allowed. |
| `@Z` | Show nothing when a number is zero. |
| `@R` | Store only what was typed, not the template's fixed characters: `@R (999) 999-9999` stores `5551234567`. |
| `@K` | The first key typed clears the field, so a new value replaces the old one (numeric fields always do this). |
| template | One character per position. `9` digit, `A` letter, `N` letter or digit, `X` any character, `!` any character in upper case, `#` digit, space or sign. Any other character is fixed and is skipped by the cursor, as in `(999) 999-9999`. The stored value includes the fixed characters, or is `""` when nothing was typed. |

Functions and a template combine with a space between them: `@Z 9999`, `@R (999) 999-9999`.

**Numeric masks.** A numeric field whose template is made of `9`, `#`, `,` and `.` (such as `"99,999.99"`) is typed like a calculator: the cursor stays at the right, the first key replaces the old value, digits build the number, `.` starts the decimals, `-` changes the sign and Backspace removes the last character. Digits that would not fit the mask, or more decimals than it has, are refused with a beep. When the cursor leaves the field, the value is shown formatted with the mask (`1,234.50`). A numeric field without a template is typed as free text, and an entry that is not a number is refused with a beep.

**Check boxes.** `GET target CHECKBOX` shows `[X]` or `[ ]`. Space toggles it, as does a click; `Y`, `X`, `1` or `T` tick it and `N`, `0` or `F` clear it. A numeric target gets `-1` (ticked) or `0`; a string target (`active$`) gets `"Y"` or `"N"`.

**Lists.** `GET target LIST items` makes a drop-down: the field shows the value and `▼`, and only values from the list can be chosen. The items are a comma-separated string (`LIST "CA,FL,NY,TX"`), an array, or a query whose first column holds them (`LIST (SELECT code FROM states ORDER BY code)`; the query runs when the `@` statement runs). Space, F2 or a click opens the list under the field (a scrolling picker for more than 10 items); typing a letter jumps to the next item that starts with it.

```basic
@ 2, 5 SAY "Joined : " GET joined$ PICTURE "@D"
@ 3, 5 SAY "Amount : " GET amount PICTURE "99,999.99"
@ 4, 5 SAY "Phone  : " GET phone$ PICTURE "@R (999) 999-9999"
@ 5, 5 SAY "Active : " GET active CHECKBOX
@ 6, 5 SAY "State  : " GET state$ LIST "CA,FL,NY,TX"
```

```
    Joined :     -  -
    Amount :  1,234.50
    Phone  : (   )    -
    Active : [ ]
    State  : FL ▼
```

`VALID condition` is checked whenever the cursor leaves the field, after the variable has been given the typed value. If the condition is false, DbBasic beeps and the cursor stays in the field. With `MESSAGE text$`, the text is also shown on the bottom line of the screen until the next key, so the user knows why:

```basic
@ 5, 5 SAY "Credit: " GET credit VALID credit <= 5000 MESSAGE "Limit is 5,000"
```

`HINT text$` is a line of help for the field: while the cursor is in it, the text is shown on the bottom line of the screen. Moving to a field without a hint shows what was on that line before, and so does the end of `READ`, so a program's own status line comes back. A `MESSAGE` shows over the hint until the next key.

```basic
@ 6, 5 SAY "Phone : " GET phone$ PICTURE "@R (999) 999-9999" HINT "Ten digits; the brackets are filled in"
```

`WHEN condition` is checked when the cursor would move into the field. If it is false, the field is skipped, in whichever direction the cursor was moving. Use it for fields that only apply sometimes. A field skipped as the last one ends `READ`:

```basic
@ 3, 5 SAY "Type  : " GET type$ PICTURE "!" VALID type$ = "P" OR type$ = "B" MESSAGE "Type must be P or B"
@ 5, 5 SAY "Credit: " GET credit WHEN type$ = "B"
```

A condition ends at the end of the statement or at the next clause word (`MESSAGE`, `HINT`, `WHEN`, `LOOKUP`, `PICTURE`, `VALID`, `CHECKBOX`, `LIST`), so `VALID message$ <> ""` still works with a variable called `message$`.

**LOOKUP** gives a field a list of allowed values from a query. Its first column holds the values; any other columns are shown as a description:

```basic
@ 4, 5 SAY "State : " GET state$ PICTURE "!!" LOOKUP (SELECT code, name FROM states ORDER BY code)
```

- F2 opens the list under the field (above it if there is no room). Enter picks a row and puts its first column in the field; Esc closes the list.
- Leaving the field with a value that is not in the list (ignoring case and spaces) opens the list too, at the first row that starts with what was typed. Picking a row accepts it and moves on; Esc keeps the cursor in the field. An empty field is not checked; add `VALID state$ <> ""` to require a value.
- The query runs each time the list is needed, so bind variables (`:country$`) see the current values of other fields.

```
    State : ZZ
    Credit: ┌─────── Choose ───────┐
    Name  : │ code │ name          │
            │──────────────────────│
            │ CA   │ California    │
            │ FL   │ Florida       │
            │ NY   │ New York      │
            │ TX   │ Texas         │
            │ 1 of 4   Enter=select│
            └──────────────────────┘
```

### READ

`READ` edits the pending `GET` fields in the order they were defined, then clears the list.

| Key | Action |
|---|---|
| Enter, Tab, Down | Next field. On the last field, Enter, Tab or Down ends `READ`. |
| Shift-Tab, Up | Previous field. |
| PgDn, PgUp, Ctrl-W | End `READ`. |
| Esc | End `READ` and put back the values every field had when `READ` started. |
| Left, Right, Home, End | Move within the field. |
| Backspace, Del | Delete. |
| Ins | Switch between insert mode (the default) and overwrite mode. |
| Ctrl-Y | Clear the field. |
| F2 | Open the field's `LOOKUP` list. |

Each value is stored when you leave its field. The first key you type in a numeric field replaces the old number.

**Auto-advance.** `SET AUTOADVANCE ON` makes `READ` behave like Clipper with `SET CONFIRM OFF`: typing a character into a field's last position moves on as if Enter had been pressed. A field with a template such as `"99999"` or `"(999) 999-9999"` is then filled without pressing Tab, and filling the last field ends `READ` (`LASTKEY$` is `CHR$(13)`). `VALID` still applies: a refused value keeps the cursor in the field. `SET AUTOADVANCE OFF`, the default, keeps the cursor in a full field until Enter, Tab or an arrow key. Clipper's spelling also works, with the opposite sense: `SET CONFIRM OFF` is `SET AUTOADVANCE ON`, and `SET CONFIRM ON` is `SET AUTOADVANCE OFF`. The setting also applies to `EDIT RECORD`, but not to a cell being edited in `BROWSE`. Afterwards, `LASTKEY$` holds the key that ended `READ`, so `IF LASTKEY$ = CHR$(27)` tells you the user cancelled.

### Buttons

```
@ row, col BUTTON label$ [CANCEL]
```

A button is drawn as `[ label ]` and takes its place among the `GET` fields, in the order the statements run. `READ` moves onto it like a field: Enter on the last field before it, Tab, or the arrows.

| Key on a button | Action |
|---|---|
| Enter or Space | Press it. `READ` ends, `BUTTON$` returns the label and `LASTKEY$` is `CHR$(13)`. |
| Tab, Right, Down | The next field or button. After the last one, back to the first field. |
| Shift-Tab, Left, Up | The previous field or button. |
| Esc | Cancel, as in a field. |

A button marked `CANCEL` works like Esc: the fields get back the values they had when `READ` started. Its label is still returned by `BUTTON$`. Moving onto a button checks the field being left (its `VALID`), as moving to any field does. `BUTTON$` is `""` when `READ` ends without a button (Esc, PgDn, or Enter on a last field that has no button after it).

```basic
@ 3, 5 SAY "Name: " GET name$ PICTURE "@S20" VALID name$ <> "" MESSAGE "Name is required"
@ 4, 5 SAY "Qty : " GET qty
@ 6, 5 BUTTON "Save"
@ 6, 15 BUTTON "Cancel" CANCEL
READ
IF BUTTON$ = "Save" THEN INSERT INTO items VALUES (:name$, :qty);
```

```
    Name: new
    Qty : 5

    [ Save ]  [ Cancel ]
```

The button under the cursor is shown in the field colours.

---

## 7.4 Menus and message boxes

### MENUBAR$()

```
choice$ = MENUBAR$([row,] "Title:item|item|...", "Title:item|...", ...)
choice$ = MENUBAR$([row,] menus)                 REM an array of the same strings
```

`MENUBAR$` draws a menu bar across the screen, on row 1 unless `row` is given, with a pull-down menu under each title. Each argument is a title, a `:` and its items separated by `|`. An item `-` draws a separator line. A title with no items, such as `"Exit"`, is chosen directly.

```basic
DO
    choice$ = MENUBAR$("File:Open|Save|-|Quit", "Customers:Browse|Add|Report", "Help:About")
    IF choice$ = "Customers.Browse" THEN BROWSE "customers" EDIT
    IF choice$ = "Help.About" THEN x = ALERT("Contacts 1.0")
LOOP UNTIL choice$ = "File.Quit" OR choice$ = ""
```

```
 File   Customers   Help
       ┌────────┐
       │ Browse │
       │ Add    │
       │ Report │
       └────────┘
```

| Key | On the bar | In a pull-down |
|---|---|---|
| Left, Right | Move to the previous or next title. | Open the neighbouring menu. |
| Enter, Down | Open the menu (or choose a title with no items). | Enter chooses the item; Down moves down. |
| Up, Home, End | | Move; the separator is skipped. |
| A letter | Opens the title starting with it. | Chooses the item starting with it. |
| Esc | Return `""`. | Close the pull-down. |

It returns `"Title.Item"`, using the text as written, so the program reads naturally and does not depend on the order of the items. A title chosen directly gives `"Title"`. The bar stays on the screen as part of the program's display. The pull-downs are removed, and what they covered is put back, along with the cursor.

### MENU()

```
choice = MENU(row, col, item1$, item2$, ...)
choice = MENU(row, col, items)                 REM an array of items
```

`MENU` draws a box at `row, col` with one item per line and a highlighted bar. Up and Down move the bar, Enter chooses, and typing the first letter of an item chooses it at once. It returns the item number, counting from 1, or `0` for Esc. When it returns, the menu disappears and what it covered is put back.

A menu that would run off the bottom of the screen moves up. One with more items than the screen has rows scrolls: `▲` and `▼` on its border show there are more items above or below, and PgUp/PgDn move a page at a time. Pull-downs of `MENUBAR$` scroll the same way.

### ALERT()

```
choice = ALERT(message$ [, button1$, button2$, ...])
choice = ALERT(message$, buttons)               REM an array of labels
```

`ALERT` shows a centred, double-lined box with a message and a row of buttons, waits for a choice and puts the screen back. A `;` in the message starts a new line. Left/Right (or Tab) move between the buttons, Enter chooses, and the first letter of a button chooses it at once. It returns the button's number, counting from 1, or `0` for Esc. With no buttons there is a single `OK`.

```basic
IF ALERT("Save changes?;They can't be undone.", "Yes", "No", "Cancel") = 1 THEN GOSUB save
```

```
╔═════════════════════════╗
║      Save changes?      ║
║  They can't be undone.  ║
║                         ║
║   Yes    No    Cancel   ║
╚═════════════════════════╝
```

---

## 7.5 Working with tables

### BROWSE

```
BROWSE (SELECT ...) | BROWSE table$  [EDIT [KEY key$] [WHEN condition [MESSAGE text$]]]
        [AT top, left, bottom, right] [TITLE title$]
        [FREEZE n] [FORMAT column mask$, ...] [COLOR column$] [EXIT ON keys$] [INTO var]
        [DETAIL (SELECT ... WHERE column = :var.column) [EDIT [KEY key$] [WHEN condition [MESSAGE text$]]] [TITLE title$]
                [FREEZE n] [FORMAT column mask$, ...] [COLOR column$]]
```

`BROWSE` runs the query and shows the rows in a box: a header line, the rows, and a status line (`2 of 3   Enter=select  Esc=cancel`). Without `AT`, it fills the terminal. A string that does not start with `SELECT` or `WITH` is taken as a table name. Bind variables (`:id`) work as in any query.

Up/Down, PgUp/PgDn and Home/End move the bar, and Left/Right scroll the columns. Columns start as wide as their widest value in the first 200 rows, up to 30 characters, and widen when a wider value scrolls into view. Enter chooses the row. `INTO var` then receives it as a hash, keyed by upper-case column name and by column number, like the row of `FOR row IN (SELECT ...)`. Esc gives an empty hash. When `BROWSE` ends, what the grid covered is put back.

**Sorting.** A click on a column heading sorts the rows by that column, and the heading shows `▲`; another click reverses the order (`▼`). F3 does the same from the keyboard: for the current cell's column with `EDIT`, otherwise for the leftmost column scrolled into view (Left/Right choose it). Blanks come first, then numbers in order, or text ignoring case. A large grid is sorted by the database, by wrapping the query in `SELECT * FROM (...) ORDER BY ...`.

**Type-ahead.** Without `EDIT`, typing jumps to the next row whose sort column starts with what was typed (the first column before any sort), and the status line shows `Find: jo`. Letters typed within a second and a half add to the search; Backspace takes one back, and a key with no match beeps. On a grid sorted in ascending order, the search is a single count in the database, so it is quick even on a million rows; otherwise the rows are read in order from the current one.

**Frozen columns, formats and colours.**

- `FREEZE n` keeps the first `n` columns at the left (after a `║`) while Left/Right scroll the others, so a name stays in view next to wide data.
- `FORMAT column mask$, ...` shows columns with `FORMAT$` masks, right-aligned, as in `REPORT`. Only the display changes: `INTO` and editing see the stored values.
- `COLOR column$` names a column of the query that holds each row's text colour (0-15, as in `COLOR`). Pick strong colours, such as 10 (light green) or 12 (light red): in some colour schemes, such as Windows Terminal's default, 14 (yellow) is so pale and 7 (grey) so close to 15 (white) that a coloured row hardly stands out. The column is not shown. A row whose value is blank, or not a colour, uses the normal colour, and the current row keeps the highlight bar.

```basic
BROWSE (SELECT name, city, phone, email, balance,
               CASE WHEN balance < 0 THEN 12 END AS shade
          FROM people ORDER BY id) AT 2, 2, 12, 50 TITLE "People" FREEZE 1 FORMAT balance "#,##0.00" COLOR "shade"
```

```
┌─────────────────── People ────────────────────┐
│ name  ║ balance▲                              │
│───────────────────────────────────────────────│
│ Alice ║    -5.00                              │   (in bright red)
│ dave  ║     0.00                              │
│ bob   ║   200.00                              │
│ carol ║ 1,234.50                              │
```

This is after scrolling right past `city`, `phone` and `email` and clicking the `balance` heading.

**Business rules: EDIT WHEN.** `EDIT WHEN condition` lets the rows be changed only while the condition is true, the way `WHEN` switches a `GET` field on and off. It is checked each time the grid is shown, and for a `DETAIL` grid each time the master's bar moves, so it can look at the master row. When it is false, the rows can still be read, scrolled and sorted, but Enter, typing, Ins and Del beep and show the `MESSAGE` (or `These rows can't be changed.`), and the status line shows it in place of `Enter=edit  Ins=add  Del=delete`:

```basic
BROWSE (SELECT id, customer, status FROM orders ORDER BY id) INTO o _
    DETAIL (SELECT line_id, product, qty, price FROM order_lines WHERE order_id = :o.id) _
    EDIT KEY "line_id" WHEN o.status = "open" MESSAGE "Shipped and cancelled orders can't be changed"
```

The rule lives in the program, next to the screen it governs. A database can enforce the same rule as well (a `CHECK` constraint or, in SQLite, a trigger), as a second line of defence for changes made outside the program; `BROWSE` shows such a refusal as `Not saved: ...`.

**Keys for the program: EXIT ON.** `EXIT ON "PgUp,PgDn,F2"` makes those keys end `BROWSE`, wherever the bar is, and `LASTKEY$` says which one it was (`"PGUP"`, `"PGDN"`, `"F2"`), so the program can act on it and show the grid again. The key names are those of `ON KEY`. A listed key no longer does its own job in the grid: with `EXIT ON "Ins"`, Ins is the program's to handle (to add a row its own way, say), not the grid's.

```basic
DO
    BROWSE (SELECT ...) EDIT KEY "id" EXIT ON "PgUp,PgDn,F2"
    k$ = LASTKEY$
    IF k$ = "PGDN" THEN ...      REM the next invoice
LOOP UNTIL k$ = CHR$(27)
```

**Master and detail.** `DETAIL` adds a second grid under the first, for rows that belong to the row under the bar: the lines of an order, the payments of an invoice. While the bar moves, `INTO var` holds the master's current row, and the `DETAIL` query is run again with it, so it names the master's columns as bind variables (`:o.id`):

```basic
BROWSE (SELECT id, customer, placed FROM orders ORDER BY id) INTO o TITLE "Orders" _
    DETAIL (SELECT line_id, product, qty, price, qty * price AS total
              FROM order_lines WHERE order_id = :o.id ORDER BY line_id) _
    EDIT KEY "line_id" TITLE "Lines" FORMAT total "#,##0.00"
```

```
┌─────────────────────────────────── Orders ───────────────────────────────────┐
│ id │ customer  │ placed                                                      │
│──────────────────────────────────────────────────────────────────────────────│
│ 1  │ Acme Corp │ 2026-01-05                                                  │
│ 2  │ Globex    │ 2026-01-09                                                  │
│ 3  │ Initech   │ 2026-02-01                                                  │
│ 4  │ Hooli     │ 2026-02-11                                                  │
│                                                                              │
│ 3 of 4   Enter=lines  Esc=done  ←→=columns  F3=sort  Tab=switch              │
└──────────────────────────────────────────────────────────────────────────────┘
┌─────────────────────────────────── Lines ────────────────────────────────────┐
│ line_id │ product  │ qty │ price │ total                                     │
│──────────────────────────────────────────────────────────────────────────────│
│ 4       │ Widget   │ 100 │ 2.25  │ 225.00                                    │
│ 5       │ Sprocket │ 7   │ 4     │  28.00                                    │
│                                                                              │
...
```

- **Layout.** The `AT` area (the whole screen without it) is split: the master gets a little under half, the detail the rest. The area must be at least 12 rows high. `AT` and `INTO` belong to the master, before `DETAIL`; the other clauses can be given to each grid.
- **Status lines.** Only the grid with the keys shows key hints; the other shows just its position (`1 of 4`). The master keeps its bar on the row whose details are shown.
- **Keys.** The master has the keys first. Enter on it (or Tab) goes to the detail grid; in an `EDIT` grid, where Enter edits and Tab moves between cells, F6 does it. A click on the other grid switches too. In the detail grid, Esc, Tab/F6 or (without `EDIT`) Enter goes back to the master. Esc on the master ends the screen, and `INTO var` keeps the row its bar is on, so the program knows which one the user was looking at (`LASTKEY$` is Esc; a master with no rows gives an empty hash). Unlike a plain `BROWSE`, a master-detail screen is for working through rows, not for picking one.
- **Editing.** Either grid can have `EDIT`. A line added with Ins in the detail grid is linked to the master row: for each `column = :var.field` in the `DETAIL` query, the new row gets the master's value, and the form doesn't ask for it. When the keys come back from an `EDIT` detail grid, the master is fetched again, so a total it shows stays current.
- A column worked out by the query (`qty * price AS total`) is shown but can't be edited, in any `BROWSE ... EDIT`, and the Ins form leaves it out.

`examples/orders_demo.bas` is an orders screen built this way.

**A traditional invoice screen.** `DETAIL` puts a grid over a grid. The invoice screens of the 1990s put a form over a grid: the invoice's header (customer, date, billing address) at the top, its lines below, and PgUp/PgDn to step from one invoice to the next. That is a short program rather than one statement: draw the header with `@ ... SAY`, show the lines with `BROWSE ... EDIT ... EXIT ON "PgUp,PgDn,F2,F4,Ins"`, and act on `LASTKEY$` in a loop (move to another invoice, find one, edit the header with `@ ... GET` and `READ`, add a line from a pick list). `examples/invoice_demo.bas` does all of it on the Chinook sample database, in about 150 lines. It also has a business rule, only open invoices can be changed: the lines grid has `EDIT WHEN status$ = "open" MESSAGE rule$`, and the keys the program handles itself (F4, Ins) check `status$` before acting:

```
╔══════════════════════════════ Invoice 1 of 412 ══════════════════════════════╗
║ Invoice : 1           Date : 2009-01-01              Total :     1.98        ║
║ Customer: Leonie Köhler             Rep  : Steve Johnson                     ║
║ Company :                                                                    ║
║ Bill to : Theodor-Heuss-Straße 34, Stuttgart, Germany                        ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
┌─────────────────────────────────── Lines ────────────────────────────────────┐
│ track             │ album           │ Quantity │ UnitPrice │ amount │ Invoice│
│──────────────────────────────────────────────────────────────────────────────│
│ Balls to the Wall │ Balls to the Wa │ 1        │      0.99 │   0.99 │ 1      │
│ Restless and Wild │ Restless and Wi │ 1        │      0.99 │   0.99 │ 2      │
...
 PgUp/PgDn invoice  F2 find  F4 header  Ins add track  Del remove  Esc quit
```

**Large tables.** `BROWSE` does not read the whole result. It fetches 500 rows at a time as you scroll, by adding `LIMIT`/`OFFSET` to the query (so its `ORDER BY` is kept exactly), and counts the rows once with `COUNT(*)` for the status line. A million-row table opens as fast as a small one. A query that already ends in its own `LIMIT` (or `OFFSET`, `FETCH FIRST`) is read whole. After a row is added with Ins, the grid fetches again; finding the new row then reads through the result, which takes a moment on a very large table.

**Editing.** With `EDIT`, the grid is a spreadsheet-like editor for the table. Each change is saved at once: cell edits with an `UPDATE`, new rows with an `INSERT`, deleted rows with a `DELETE`:

| Key | Action |
|---|---|
| Left, Right, Tab, Shift-Tab | Move between cells. The current cell is shown in reverse. |
| Enter or F2 | Edit the current cell, starting from its value. |
| Any character | Edit the current cell, starting with that character (the old value is replaced). |
| Enter, Tab, Up, Down (while editing) | Save the cell. Tab, Up and Down also move. |
| Esc (while editing) | Cancel the edit. |
| Ins | Add a row. A blank form opens over the grid, the same form `EDIT RECORD` shows for a new row: one field per column, saved with an `INSERT` (see [EDIT RECORD](#edit-record) for how the key is filled in). The grid then reloads and moves to the new row. |
| Del | Delete the current row. The status line asks `Delete this row? (Y/N)`; only `Y` deletes it. |
| Esc | End `BROWSE`. `INTO` gets an empty hash. |

- `BROWSE "items" EDIT` edits a table by its `rowid`, which is fetched but not shown.
- A query needs the column that identifies a row: `BROWSE (SELECT id, name FROM items) EDIT KEY "id"`. The query must read `FROM` one table, and the edited columns must be plain column names of that table. The `KEY` column can't be edited.
- A cell that held a number is edited as a number. Emptying it stores `NULL`. An emptied text cell follows `SET NULL_HANDLING`: `NULL` by default.
- If the database refuses a change (a `CHECK` or `NOT NULL` constraint, a wrong type), DbBasic beeps, the status line shows `Not saved: ...` (or `Not deleted: ...`) with the database's message, and the cell keeps its old value. A refused new row keeps its form open, as in `EDIT RECORD`.

`examples/retro_contacts.bas` uses `BROWSE ... EDIT KEY "id"` for its contact list.

### EDIT RECORD

```
EDIT RECORD (SELECT ... FROM table WHERE ...) [KEY key$] [AT top, left] [TITLE title$] [INTO var]
```

`EDIT RECORD` is a whole entry form in one line, for when the layout doesn't matter. It runs the query and shows a box, centred unless `AT` is given, with one labelled field per column. The labels come from the column names (`last_name` becomes `Last Name`), and the title defaults to the table name.

```basic
EDIT RECORD (SELECT * FROM contacts WHERE id = :id) TITLE "Contact" INTO rec
```

```
┌──────────────── Contact ─────────────────┐
│                                          │
│        Id : 1                            │
│ Last Name : jones                        │
│     Email : a@x.com                      │
│    Credit : 50                           │
│                                          │
│ Enter=next  PgDn=save  Esc=cancel        │
└──────────────────────────────────────────┘
```

- **Keys:** the fields are edited as with `READ`. Enter on the last field, or PgDn, saves; Esc cancels and changes nothing.
- **Key column:** `KEY` names the column that identifies the row. It defaults to the table's primary key, and it is shown but can't be edited.
- **Saving an existing row:** an `UPDATE` of the columns that changed.
- **No matching row:** the form opens blank and saves with an `INSERT`. The key can be typed. Leave it at 0 to let SQLite number the row (`INTEGER PRIMARY KEY`). DuckDB has no automatic numbering unless the column has a `DEFAULT nextval(...)`, so type the key there.
- **Refused changes:** if the database refuses the change (a `CHECK` or `NOT NULL` constraint, a wrong type), DbBasic beeps and shows `Not saved: ...` under the box. After a key press, the form is shown again with what you typed, starting at the first field.
- **`INTO var`:** receives the saved record as a hash, keyed by upper-case column name, or an empty hash after Esc. After an `INSERT` on SQLite, it holds the new row's key.
- **Rules:** the query must read `FROM` one table and find at most one row, and its columns must be plain column names of that table. Numbers are edited as numbers, and an emptied text field follows `SET NULL_HANDLING`. What the form covered is put back when it closes.

Use `@ ... SAY ... GET` and `READ` when you want your own layout, pictures or `VALID` checks.

### MAKE FORM

```
MAKE FORM table$ TO file$ [KEY column$] [TITLE title$]
```

`MAKE FORM` writes a complete data-entry program for a table: point it at a table and get an application, then change the program as you like. It is ordinary DbBasic, about a hundred lines, built from the statements in this chapter:

- a menu bar with Browse, Add, Edit and Delete, and F1 help from anywhere (`ON KEY`);
- **Browse:** the table in an editable, sortable grid (`BROWSE ... EDIT`);
- **Add** and **Edit:** an entry form with a field for each column, with Save and Cancel buttons; **Edit** and **Delete** first show a pick list with type-ahead;
- a change the database refuses (a `CHECK`, `NOT NULL` or `UNIQUE` constraint) is shown in an `ALERT` and the form opens again with what was typed (the program uses `SET SQL_FATAL_ERRORS OFF` and checks `ERR`).

```basic
DATABASE OPEN "shop.db"
MAKE FORM "customers" TO "customers_form.bas"
```

```
Wrote customers_form.bas: a program for customers with 7 fields. Run it with: dbbasic customers_form.bas
```

Each field is chosen from its column:

| Column | Field |
|---|---|
| Text, `VARCHAR(n)` | A text field (`@S`), as wide as `n`, or as the longest value in the table (20 to 40) |
| An integer type | A number field, `PICTURE "9999999999"` |
| `REAL`, `DOUBLE`, `DECIMAL(p, s)` | A calculator-style number mask with commas and `s` decimals (2 by default), such as `"99,999,999.99"` |
| `DATE` | A date field, `@D` |
| `BOOLEAN` | A `CHECKBOX`, saved as true or false |
| `REFERENCES other(col)` | A drop-down `LIST` of the values in `other` |
| `NOT NULL` text, date or list | Required: `VALID ... MESSAGE "Name is required"` |
| SQLite's `INTEGER PRIMARY KEY` | Left out of the form, since SQLite numbers new rows |

Every field gets a `HINT` (`A date: YYYY-MM-DD`, `Text, up to 40 characters (required)`). Labels come from the column names (`joined_on` becomes `Joined On`). A form holds up to 26 fields, in two columns when there are more than 13.

```
┌─────────────────────────── New customer ───────────────────────────┐
│                                                                    │
│  Name   :                                                          │
│  Email  :                                                          │
│  State  :    ▼                                                     │
│  Joined :     -  -                                                 │
│  Credit :          0.00                                            │
│  Active : [ ]                                                      │
│  Visits :          0                                               │
│                                                                    │
│                                                                    │
│  [ Save ]  [ Cancel ]                                              │
│                                                                    │
└────────────────────────────────────────────────────────────────────┘
 Text, up to 20 characters (required)
```

- **The database.** The program opens the database that is open when `MAKE FORM` runs, with the same engine, so open a file first; an in-memory database is refused. The path is written as it was given to `DATABASE OPEN`, so run the program from the same folder, or edit the `DATABASE OPEN` line.
- **The key.** Edit and Delete find a row by the table's primary key. `KEY "column"` names another column. A SQLite table without one uses its `rowid`; on DuckDB, a table without a single-column primary key needs `KEY`.
- **The file** must not exist yet, so a program you have changed is never overwritten. `KILL` it first to make it again.
- `TITLE` names the program, the menu and the forms; it defaults to the table name (`customers` becomes `Customers`, and a form for one row is a `customer`).

`examples/make_form_demo.bas` makes a small shop database and a program for its customers.

---

## 7.6 Editing and viewing text

### EDIT TEXT

```
EDIT TEXT target [AT top, left, bottom, right] [TITLE title$]
```

`EDIT TEXT` is a memo editor: a box in which a multi-line string can be edited, like Clipper's MEMOEDIT. The target can be anything `GET` accepts: a variable (`notes$`), a hash field (`rec.notes`) or an array element. Lines are separated by `CHR$(10)`. Without `AT`, the box fills the screen with a small margin.

```basic
EDIT TEXT rec.notes AT 3, 5, 12, 50 TITLE "Notes"
IF LASTKEY$ <> CHR$(27) THEN UPDATE customers SET notes = :rec.notes WHERE id = :rec.id;
```

```
┌────────────────── Notes ───────────────────┐
│first line ok                               │
│third                                       │
│second line                                 │
│                                            │
└─ Ln 2, Col 6  Ctrl-W=save  Esc=cancel ─────┘
```

| Key | Action |
|---|---|
| Arrows, Home, End, PgUp, PgDn | Move. Left and Right wrap to the previous or next line. |
| Enter | Split the line at the cursor. |
| Backspace, Del | Delete a character; at the start or end of a line, join it to the line before or after. |
| Tab | Insert spaces up to the next multiple of 4. |
| Ctrl-Y | Delete the current line. |
| Ins | Switch between insert mode (the default) and overwrite mode. |
| Ctrl-W or F10 | Save: the target gets the text, and `LASTKEY$` is `CHR$(23)` or `F10`. |
| Esc | Cancel. If anything was changed, `ALERT` asks `Discard your changes?` first. The target keeps its old value, and `LASTKEY$` is `CHR$(27)`. |

Lines are not wrapped: a line longer than the box scrolls sideways while you edit it, so the saved text has exactly the lines you typed. The line and column are shown in the bottom border, and the screen under the box is put back afterwards.

### VIEW

```
VIEW FILE path$      [AT top, left, bottom, right] [TITLE title$]
VIEW (SELECT ...)    [AT ...] [TITLE title$]
VIEW text$           [AT ...] [TITLE title$]
```

`VIEW` shows text in a read-only, scrolling box: a file, the result of a query (laid out as the text table a `SELECT` prints, with box-drawing lines), or any string. Without `AT`, it fills the screen. A file's name is the default title; tabs are expanded to 8 columns.

```basic
VIEW FILE "report.txt" AT 2, 2, 12, 60
VIEW (SELECT region, SUM(amount) AS total FROM sales GROUP BY region) TITLE "Sales"
```

```
┌───────────────────────── report.txt ────────────────────┐
│Line 057 of the report  TOTAL                            │
│Line 058 of the report                                   │
│...                                                      │
└─ 57-65 of 100  /=find  n=next  Esc=close ───────────────┘
```

| Key | Action |
|---|---|
| Up, Down, Enter | Scroll a line. |
| PgUp, PgDn, Space | Scroll a page. |
| Home, End | Go to the start or the end. |
| Left, Right | Scroll sideways, 8 columns at a time. |
| `/` or Ctrl-F | Search: type the text on the status line and press Enter. The search ignores case and starts at the top line shown; the line found is highlighted. |
| `n` or F3 | Find the next match, wrapping round to the start. `Not found: ...` is shown when there is none. |
| Esc or `q` | Close the viewer. `LASTKEY$` holds the key. |

A missing file is an error with `ERR = 2`. What the box covered is put back when it closes. A variable called `file` can still be viewed: `VIEW file` and `VIEW file AT ...` show its value.

---

## 7.7 The keyboard and mouse

### INKEY$ and LASTKEY$

| Function | Returns |
|---|---|
| `INKEY$` | The key that has been pressed, or `""` if none is waiting. It does not wait. |
| `INKEY$(0)` | The next key, waiting as long as it takes. |
| `INKEY$(n)` | The next key, waiting at most `n` seconds; `""` if none arrives. |
| `LASTKEY$` | The key that ended the last `READ`, `MENU` or `BROWSE`, or the last key `INKEY$` returned. |

Ordinary keys come back as characters: Enter is `CHR$(13)`, Esc `CHR$(27)`, Tab `CHR$(9)` and Backspace `CHR$(8)`. Other keys come back as names: `UP`, `DOWN`, `LEFT`, `RIGHT`, `HOME`, `END`, `PGUP`, `PGDN`, `INS`, `DEL`, `BTAB` (Shift-Tab) and `F1` to `F12`.

```basic
PRINT "Press a key (Esc to stop)"
DO
    k$ = INKEY$(0)
    IF k$ = CHR$(27) THEN EXIT DO
    PRINT "You pressed "; k$
LOOP
```

### Hot keys: ON KEY

```
ON KEY key$ CALL function
ON KEY key$ OFF
```

`ON KEY` makes a key run a `FUNCTION` (with no arguments) whenever the program is waiting for a key: in `READ`, `BROWSE`, `MENU`, `MENUBAR$`, `ALERT`, `EDIT TEXT`, `VIEW` and `INKEY$`. When the function returns, the screen it may have drawn over is put back and the statement carries on as if the key had not been pressed. This is how an application gets F1 help or a save key that works everywhere:

```basic
FUNCTION show_help()
    BOX 8, 10, 14, 70, "Help" DOUBLE
    @ 10, 12 SAY "Tab moves between fields, F2 opens a list, Esc cancels."
    k$ = INKEY$(0)
END FUNCTION

ON KEY "F1" CALL show_help
```

`key$` is a key name: `F1` to `F12`, `CTRL-A` to `CTRL-Z`, `ALT-A` to `ALT-Z`, `UP`, `DOWN`, `LEFT`, `RIGHT`, `HOME`, `END`, `PGUP`, `PGDN`, `INS`, `DEL`, `ENTER`, `ESC`, `TAB`, `SPACE`, or a single character. The function must be defined in the program. While a hot-key function runs, other hot keys are switched off, so it can wait for keys of its own. A polling `INKEY$` (no argument) returns `""` for a hot key. `ON KEY key$ OFF` removes the binding, and the key then reaches the program normally.

Alt keys are recognised from the keyboard, where a terminal sends Alt-letter as Esc followed by the letter (on macOS Terminal, turn on *Use Option as Meta key*).

### The mouse

Every screen statement also takes mouse clicks, in terminals that report them (macOS Terminal, iTerm2, Linux terminals, Windows Terminal):

| Statement | Click | Wheel |
|---|---|---|
| `READ` | A field: move there (the field being left is checked first, as with Tab) or, inside the current field, move the cursor. A button: press it. | |
| `MENU()` | An item chooses it; a click outside the menu cancels it (returns 0). | Moves the bar. |
| `ALERT()` | A button chooses it. | |
| `MENUBAR$()` | A title opens its menu (or closes it), or chooses a title without items; an item chooses it; a click elsewhere closes an open menu. | Moves the bar in an open menu. |
| `BROWSE` | A row selects it (in `EDIT`, the cell); a click on the selected row (or cell) chooses it (or edits it), like Enter. | Scrolls 3 rows. |
| `EDIT TEXT` | Puts the cursor there. | Moves 3 lines. |
| `VIEW` | | Scrolls 3 lines. |

For your own screens, `INKEY$` returns `CLICK`, `RCLICK` (right button), `MCLICK` (middle button), `WHEELUP` or `WHEELDOWN`, and `MOUSEROW` and `MOUSECOL` give the position of the last click or wheel turn (row and column from 1, as with `LOCATE`):

```basic
DO
    k$ = INKEY$(0)
    IF k$ = "CLICK" THEN @ MOUSEROW, MOUSECOL SAY "*"
LOOP UNTIL k$ = CHR$(27)
```

`SET MOUSE OFF` turns the mouse off (and `SET MOUSE ON` back on). It is on by default on macOS and Linux. On Windows it is off by default, because the console then has to deliver all keys in its VT input mode: `SET MOUSE ON` switches it on there; this has not been tested on Windows yet. While the mouse is on, a plain drag no longer selects text in the terminal; most terminals select text when you hold Shift (or Option, depending on the terminal) while dragging. The terminal's normal behaviour comes back when the program ends or when `INPUT` reads a line.

### Keyboard and terminal

While a program reads keys, the terminal does not echo them and passes Ctrl-S, Ctrl-Q, Ctrl-Y, Ctrl-V and Ctrl-O to the program. Ctrl-C still stops the program. `INPUT` switches the terminal back to normal line editing. When the program ends, the colours, the cursor and the terminal mode are restored. The screen contents are left as they are, as they were in DOS.

On Windows, DbBasic turns on the console's ANSI support and `DISABLE_NEWLINE_AUTO_RETURN`, so that drawing the bottom-right character of the screen (a hint line, a full-screen box) doesn't scroll everything up a line, as it does in other terminals. A console too old for that setting gets everything but that one character.

DbBasic always writes its output as UTF-8. On Windows, output sent to a pipe or a file would otherwise use the ANSI code page (cp1252), which cannot encode the box-drawing characters and fails with `'charmap' codec can't encode ...`. The console itself shows them as long as its font has the characters (the default fonts of Windows Terminal and the Windows 10+ console do).

**Resizing.** When the terminal window changes size, DbBasic redraws the screen from its copy (see [SAVESCREEN and RESTSCREEN](#savescreen-and-restscreen)), so the window doesn't fill with wrapped or shuffled lines. What fits the new size is kept where it was. Nothing is laid out again: a full-screen `BROWSE` or a menu bar keeps the size it was drawn at until it is drawn again, and `CLS` starts over at the new size. The redraw happens while the program waits for a key; on Windows the size is checked four times a second during the wait.

When standard input is not a terminal, keys are read from it as a stream, with arrow keys written as their escape sequences (`\x1b[A` for Up). This is how `tests/screen.bas` and `examples/retro_contacts.bas` are run by the test runner.

---

## 7.8 Replacing the old FORM statements

The declarative forms (`FORM ... ENDFORM`, `OPENFORM`, `GRIDEDIT`), built on the Textual library in `src/tui_runner.py`, have been removed from `main`. The statements in this chapter replace them with less code:

| Old | New |
|---|---|
| `GRIDEDIT "orders"` | `BROWSE "orders" EDIT` (Enter edits a cell, Ins adds a row, Del deletes one) |
| A list `FORM` with `OPENFORM` and `FORM_SELECTED_ID` | `BROWSE (SELECT ...) INTO row` |
| An entry `FORM`, `FORM_RESULT$`, `FORM_DATA` and an `UPDATE` | `@ ... SAY ... GET`, `READ`, `LASTKEY$` and an `UPDATE` |
| `BUTTON` actions | `MENU(...)` |

`textual` is no longer a dependency. The last version with forms, including the form examples, is kept on the `archive/forms` branch.

---

## 7.9 Implementation notes

1. **Status.** The text-screen statements are new. Known limits:
    - `SAVESCREEN` and `RESTSCREEN` (added) work from DbBasic's own copy of the screen, which does not include query tables, `SHELL` output or error messages;
    - (added) `GET` edits hash fields and array elements as well as variables;
    - a numeric field's `PICTURE` sets only its width;
    - (changed) `BROWSE` fetches 500 rows at a time instead of the whole result;
    - the Windows key handling has not been tested;
    - (fixed) words such as `choice` and `title`, once reserved by the FORM statements, are ordinary variable names again.
2. **The old forms** (archived). `FORM`, `OPENFORM` and `GRIDEDIT` have been moved to the `archive/forms` branch (see 7.8). Their open issues there were: `PLACEHOLDER` not displayed, debug output on every button press, field `TYPE NUMBER` doing no conversion, `MATCHES` not working with a `CHOICE`, non-numeric primary keys failing in `FORM_SELECTED_ID`, unescaped `WHERE`/`ORDER BY` text and no delete confirmation in `GRIDEDIT`.
