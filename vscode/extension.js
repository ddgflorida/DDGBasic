'use strict';
const path = require('path');
const vscode = require('vscode');
const { findTopic, topicMarkdown, wordsOf } = require('./lib/help');
const topics = require('./help.json');

const TERMINAL_NAME = 'DDGBasic';

function quote(arg) {
  return '"' + arg + '"';
}

// The command line for the terminal's shell
function runCommandLine(command, fileName) {
  const shell = (vscode.env.shell || '').toLowerCase();
  const line = command + ' ' + quote(fileName);
  // PowerShell runs a quoted program name only after &
  if (/(powershell|pwsh)/.test(shell) && /^\s*"/.test(command)) return '& ' + line;
  return line;
}

// Runs the active program, or `program` (from a launch.json entry)
async function runProgram(program) {
  let fileName = program;
  if (!fileName) {
    const editor = vscode.window.activeTextEditor;
    if (!editor || editor.document.languageId !== 'ddgbasic') {
      vscode.window.showWarningMessage('Open a DDGBasic (.bas) program to run it.');
      return;
    }
    if (editor.document.isUntitled) {
      vscode.window.showWarningMessage('Save the program before running it.');
      return;
    }
    fileName = editor.document.fileName;
  }
  // Save the program first if it is open with changes
  const open = vscode.workspace.textDocuments.find(d => d.fileName === fileName);
  if (open && open.isDirty && !(await open.save())) return;

  const config = vscode.workspace.getConfiguration('ddgbasic');
  const command = config.get('command') || 'ddgbasic';
  // In an editor tab the terminal gets the editor's full height: screen programs (forms,
  // BROWSE, QR AT) need about 24 rows, more than the terminal panel usually has
  const location = config.get('terminalLocation') === 'panel'
    ? vscode.TerminalLocation.Panel
    : { viewColumn: vscode.ViewColumn.Active };
  // A new terminal in the program's folder, so relative file names in the program work
  for (const t of vscode.window.terminals) {
    if (t.name === TERMINAL_NAME) t.dispose();
  }
  const terminal = vscode.window.createTerminal({ name: TERMINAL_NAME, cwd: path.dirname(fileName), location });
  terminal.show();
  terminal.sendText(runCommandLine(command, path.basename(fileName)));
}

// F5 (Start Debugging) and Ctrl+F5 (Run Without Debugging) run the program in the terminal.
// There is no debugger yet, so no debug session starts: returning undefined ends the launch.
const debugProvider = {
  resolveDebugConfiguration(folder, config) {
    // No launch.json: run the file in the editor
    if (!config.type && !config.request && !config.name) {
      config = { type: 'ddgbasic', request: 'launch', name: 'Run DDGBasic program' };
    }
    if (!config.program) config.program = '${file}';
    return config;
  },
  resolveDebugConfigurationWithSubstitutedVariables(folder, config) {
    runProgram(config.program);
    return undefined;
  },
};

// A user FUNCTION's definition line, for hovering over a call
function userFunction(doc, name) {
  const pattern = new RegExp('^\\s*FUNCTION\\s+' + name.replace(/\$/g, '\\$') + '\\s*\\(', 'i');
  for (let i = 0; i < doc.lineCount; i++) {
    const text = doc.lineAt(i).text;
    if (pattern.test(text)) return { line: i, text: text.trim() };
  }
  return null;
}

const hoverProvider = {
  provideHover(doc, position) {
    const line = doc.lineAt(position.line).text;
    const hit = findTopic(topics, line, position.character);
    if (hit) return new vscode.Hover(new vscode.MarkdownString(topicMarkdown(hit.topic, hit.info)));

    const word = wordsOf(line).find(w => position.character >= w.start && position.character <= w.end);
    if (word && word.text !== 'FUNCTION') {
      const fn = userFunction(doc, word.text);
      if (fn && fn.line !== position.line) {
        const md = new vscode.MarkdownString();
        md.appendCodeblock(fn.text, 'ddgbasic');
        md.appendMarkdown('Defined on line ' + (fn.line + 1));
        return new vscode.Hover(md);
      }
    }
    return null;
  },
};

function activate(context) {
  context.subscriptions.push(
    vscode.commands.registerCommand('ddgbasic.run', runProgram),
    vscode.languages.registerHoverProvider('ddgbasic', hoverProvider),
    vscode.debug.registerDebugConfigurationProvider('ddgbasic', debugProvider),
  );
}

function deactivate() {}

module.exports = { activate, deactivate };
