# DDGBasic for VS Code

Language support for [DDGBasic](https://github.com/ddgflorida/DDGBasic) programs (`.bas` files).

- **Syntax highlighting:** statements, built-in functions, strings (including `` `...${expr}...` `` templates), `REM`, `--` and `/* */` comments, labels, numbers, SQL words and `:name` bind variables. Words such as `NAME`, `ROW`, `KEY` and `TEXT` are colored as keywords only where they are keywords (`NAME a AS b`, `TRANSFORM ROW`, `USING KEY`, `LOAD TEXT`), not when they are variable or column names.
- **Hover help:** hover over a statement to see its `HELP` text, the syntax, a description and examples. Two-word topics such as `LOAD CSV`, `SET OUTPUT` and `ON ERROR` are found from either word. Hovering over a call to one of your own `FUNCTION`s shows its definition line.
- **Run:** F5, Ctrl+F5, the ▷ button in the editor title bar or **DDGBasic: Run DDGBasic Program** in the Command Palette saves the program and runs it in a terminal named DDGBasic, started in the program's folder so relative file names work. The terminal opens as an editor tab, which has room for full-screen programs (forms, `BROWSE`, `QR ... AT` need about 24 rows); the `ddgbasic.terminalLocation` setting can put it in the terminal panel instead. There is no debugger yet (no breakpoints or stepping), so F5 runs the program the same way as Ctrl+F5. A `launch.json` entry of type `ddgbasic` can run a fixed program: `"program": "${workspaceFolder}/nightly.bas"`.
- **Editing:** Toggle Line Comment uses `REM`, brackets and quotes close themselves, and lines after `IF ... THEN`, `FOR`, `WHILE`, `DO` and `FUNCTION` are indented.

## Requirements

DDGBasic itself: `pip install ddgbasic` puts the `ddgbasic` command on the PATH.

## Settings

| Setting | Default | Meaning |
|---|---|---|
| `ddgbasic.terminalLocation` | `editor` | Where the DDGBasic terminal opens: `editor` (an editor tab, full height) or `panel` (the terminal panel). |
| `ddgbasic.command` | `ddgbasic` | The command that runs a program; the file name is added after it. For example `ddgbasic.exe` or `python C:\DDGBasic\src\ddgbasic.py`. |

## .bas files and other BASIC extensions

The extension opens every `.bas` file as DDGBasic. If another BASIC extension is installed, choose the language for a file with **Change Language Mode** (click the language name in the status bar), or set it for all `.bas` files with this in `settings.json`:

```json
"files.associations": { "*.bas": "ddgbasic" }
```

## Building

The grammar and the hover help are generated from the interpreter, so they list exactly the statements and functions it knows:

```
python3 tools/gen_vscode.py           # from the repository folder
cd vscode
node --test test/help.test.js
npx @vscode/vsce package              # makes ddgbasic-<version>.vsix
code --install-extension ddgbasic-<version>.vsix
```
