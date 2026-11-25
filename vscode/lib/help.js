'use strict';
// Finds the HELP topic for the word under the cursor. No VS Code API here, so
// test/help.test.js can run it with plain node.

const WORD = /[A-Za-z_][A-Za-z0-9_]*\$?|@/g;

// The words of a line, with their columns, leaving out strings and comments
function wordsOf(line) {
  const words = [];
  let i = 0;
  let codeStart = 0;
  const scan = (end) => {
    const part = line.slice(codeStart, end);
    WORD.lastIndex = 0;
    let m;
    while ((m = WORD.exec(part)) !== null) {
      words.push({ text: m[0].toUpperCase(), start: codeStart + m.index, end: codeStart + m.index + m[0].length });
    }
  };
  while (i < line.length) {
    const ch = line[i];
    if (ch === '"' || ch === '`' || ch === "'") {
      scan(i);
      let j = i + 1;
      while (j < line.length) {
        if (line[j] === ch) {
          if (ch === '"' && line[j + 1] === '"') { j += 2; continue; }
          break;
        }
        j++;
      }
      i = j + 1;
      codeStart = i;
      continue;
    }
    if (line.startsWith('--', i) || (/^REM(?![\w$])/i.test(line.slice(i)) && !/[\w$]/.test(line[i - 1] || ''))) {
      break;
    }
    i++;
  }
  scan(Math.min(i, line.length));
  return words;
}

// Returns { topic, info } or null
function findTopic(topics, line, column) {
  const words = wordsOf(line);
  const k = words.findIndex(w => column >= w.start && column <= w.end);
  if (k < 0) return null;
  const at = (n) => (words[n] ? words[n].text : null);
  const tryKey = (parts) => {
    if (parts.some(p => p === null)) return null;
    const key = parts.join(' ');
    return topics[key] ? { topic: key, info: topics[key] } : null;
  };
  // Longest topic first: SHOW CREATE TABLE, then LOAD CSV, then LOAD
  const candidates = [
    [k - 2, k - 1, k], [k - 1, k, k + 1], [k, k + 1, k + 2],
    [k - 1, k], [k, k + 1],
  ];
  for (const c of candidates) {
    if (c[0] < 0) continue;
    const hit = tryKey(c.map(at));
    if (hit) return hit;
  }
  const word = at(k);
  // FOR row IN (SELECT ...) and FOR line IN FILES ...
  if ((word === 'FOR' || word === 'IN') && words.some(w => w.text === 'FOR') && words.some(w => w.text === 'IN') && topics['FOR IN']) {
    return { topic: 'FOR IN', info: topics['FOR IN'] };
  }
  // END IF, END FUNCTION: not the END statement
  if (word === 'END' && at(k + 1) !== null) return null;
  return tryKey([word]);
}

// Markdown for a hover
function topicMarkdown(topic, info) {
  const fence = (code) => '```ddgbasic\n' + code + '\n```\n';
  let md = '**' + topic + '**\n\n';
  if (info.syntax) md += fence(info.syntax);
  if (info.desc) md += '\n' + info.desc + '\n';
  if (info.examples && info.examples.length) md += '\n' + fence(info.examples.join('\n'));
  return md;
}

module.exports = { wordsOf, findTopic, topicMarkdown };
