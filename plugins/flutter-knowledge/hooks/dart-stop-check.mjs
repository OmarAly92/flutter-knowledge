#!/usr/bin/env node

import { spawnSync } from 'node:child_process';
import { existsSync, lstatSync, readFileSync } from 'node:fs';
import { dirname, join, relative, resolve, sep } from 'node:path';

const SOURCE_DIRS = ['lib', 'test', 'integration_test', 'test_driver'];
const GENERATED = ['.g.dart', '.freezed.dart', '.mocks.dart', '.gr.dart', '.gen.dart'];
const BLOCKING = new Set(['ERROR', 'WARNING']);
const MAX_ISSUES = 25;
const WINDOWS = process.platform === 'win32';

function readInput() {
  try {
    return JSON.parse(readFileSync(0, 'utf8') || '{}');
  } catch {
    return {};
  }
}

function findProjectRoot(startDir) {
  let dir = resolve(startDir);
  for (let i = 0; i < 25; i++) {
    if (existsSync(join(dir, 'pubspec.yaml'))) return dir;
    const parent = dirname(dir);
    if (parent === dir) return null;
    dir = parent;
  }
  return null;
}

function run(command, args, cwd, timeout) {
  return spawnSync(command, args, { cwd, encoding: 'utf8', timeout, shell: WINDOWS && command === 'dart' });
}

function gitLines(root, args) {
  const result = run('git', args, root, 20000);
  if (result.error || result.status !== 0) return null;
  return result.stdout.split('\0').filter(Boolean);
}

function changedDartFiles(root) {
  const unstaged = gitLines(root, ['ls-files', '-z', '--modified', '--others', '--exclude-standard']);
  const staged = gitLines(root, ['diff', '-z', '--name-only', '--cached', '--relative']);
  if (unstaged === null || staged === null) return [];
  const files = new Set();
  for (const file of [...unstaged, ...staged]) {
    const path = file.split('/').join(sep);
    if (!SOURCE_DIRS.some((folder) => path.startsWith(folder + sep))) continue;
    if (!path.endsWith('.dart') || GENERATED.some((suffix) => path.endsWith(suffix))) continue;
    const absolute = join(root, path);
    if (!existsSync(absolute) || lstatSync(absolute).isSymbolicLink()) continue;
    files.add(file);
  }
  return [...files].sort();
}

function blockingIssues(output, root) {
  const issues = [];
  for (const line of output.split('\n')) {
    const fields = line.split('|');
    if (fields.length < 8 || !BLOCKING.has(fields[0])) continue;
    const [severity, , , file, row, column] = fields;
    const message = fields.slice(7).join('|').trim();
    const path = relative(root, file).split(sep).join('/');
    issues.push(`${path}:${row}:${column} ${severity.toLowerCase()}: ${message}`);
  }
  return issues;
}

function main() {
  if (process.env.FLUTTER_KNOWLEDGE_STOP_HOOK === '0') return;
  const input = readInput();
  const root = findProjectRoot(input.cwd || process.cwd());
  if (!root) return;
  const files = changedDartFiles(root);
  if (files.length === 0) return;
  const format = run('dart', ['format', ...files], root, 30000);
  if (format.error) return;
  if (input.stop_hook_active === true) return;
  if (!existsSync(join(root, '.dart_tool', 'package_config.json'))) return;
  const analysis = run('dart', ['analyze', '--format=machine', ...files], root, 100000);
  if (analysis.error) return;
  const issues = blockingIssues(`${analysis.stdout}\n${analysis.stderr}`, root);
  if (issues.length === 0) return;
  const shown = issues.slice(0, MAX_ISSUES);
  const more = issues.length > shown.length ? `\n…and ${issues.length - shown.length} more.` : '';
  const reason =
    `Dart analysis found ${issues.length} error/warning issue(s) in the Dart files changed in this project. ` +
    'Fix the ones your change caused before finishing, following the flutter-knowledge conventions; ' +
    'report issues that predate the change instead of fixing them unasked.\n' +
    shown.map((issue) => `- ${issue}`).join('\n') +
    more;
  process.stdout.write(JSON.stringify({ decision: 'block', reason }));
}

try {
  main();
} catch {
  process.exitCode = 0;
}
