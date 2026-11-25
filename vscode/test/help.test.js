'use strict';
// node --test test/help.test.js   (no VS Code needed)
const test = require('node:test');
const assert = require('node:assert');
const { findTopic, wordsOf } = require('../lib/help');
const topics = require('../help.json');

const topicAt = (line, word, nth = 0) => {
  let col = -1;
  for (let i = 0; i <= nth; i++) col = line.indexOf(word, col + 1);
  const hit = findTopic(topics, line, col + 1);
  return hit && hit.topic;
};

test('two-word topics win over one word', () => {
  const line = 'LOAD CSV "orders.csv" INTO TABLE orders REJECTS INTO bad';
  assert.strictEqual(topicAt(line, 'LOAD'), 'LOAD CSV');
  assert.strictEqual(topicAt(line, 'CSV'), 'LOAD CSV');
  assert.strictEqual(topicAt('LOAD XML "a.xml" CREATE TABLE x', 'LOAD'), 'LOAD');
  assert.strictEqual(topicAt('ON ERROR GOTO handler', 'ERROR'), 'ON ERROR');
  assert.strictEqual(topicAt('SET OUTPUT TO "a.csv"', 'SET'), 'SET OUTPUT');
  assert.strictEqual(topicAt('SHOW CREATE TABLE t', 'TABLE'), 'SHOW CREATE TABLE');
});

test('single words, case and $ names', () => {
  assert.strictEqual(topicAt('  print "hi"', 'print'), 'PRINT');
  assert.strictEqual(topicAt('k$ = INKEY$(0)', 'INKEY$'), 'INKEY$');
  assert.strictEqual(topicAt('FOR row IN (SELECT * FROM t)', 'IN'), 'FOR IN');
  assert.strictEqual(topicAt('FOR i = 1 TO 10', 'FOR'), 'FOR');
});

test('no help in strings, comments or END IF', () => {
  assert.strictEqual(topicAt('PRINT "LOAD the file"', 'LOAD'), null);
  assert.strictEqual(topicAt('x = 1 -- PRINT later', 'PRINT'), null);
  assert.strictEqual(topicAt('REM PRINT later', 'PRINT'), null);
  assert.strictEqual(topicAt('END IF', 'END'), null);
  assert.strictEqual(topicAt('END', 'END'), 'END');
  assert.strictEqual(topicAt('REMARK = 1 : PRINT REMARK', 'PRINT'), 'PRINT');
});

test('words skip "" inside strings', () => {
  assert.deepStrictEqual(wordsOf('PRINT "say ""hi"" now"; x').map(w => w.text), ['PRINT', 'X']);
});
