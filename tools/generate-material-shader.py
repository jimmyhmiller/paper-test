#!/usr/bin/env python3
"""Translate the pure scalar tex-* Coil kernels to Metal; reject unsupported syntax.

Coil is the source of truth. This deliberately small translator accepts only
numeric expressions, immutable lets and case returns, not general Coil code.
Run with --check in validation to detect stale generated shader code.
"""
import argparse
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCES = [ROOT / 'lib/paper/src/texture.coil', ROOT / 'lib/paper/src/finish_light.coil']
TARGET = ROOT / 'lib/paper/shaders/paper.metal'
BEGIN = '// BEGIN GENERATED MATERIAL KERNELS'
END = '// END GENERATED MATERIAL KERNELS'
TYPES = {'f64': 'float', 'i64': 'long', 'u32': 'uint'}


def parse(source):
    tokens = re.findall(r'"(?:\\.|[^"\\])*"|[^\s()\[\]]+|[()\[\]]', re.sub(r';[^\n]*', '', source))
    stack = [[]]
    for token in tokens:
        if token in ('(', '['):
            child = []
            stack[-1].append(child)
            stack.append(child)
        elif token in (')', ']'):
            if len(stack) == 1:
                raise ValueError('unbalanced source')
            stack.pop()
        else:
            stack[-1].append(token)
    if len(stack) != 1:
        raise ValueError('unbalanced source')
    return stack[0]


def name(value):
    return value.replace('-', '_')


def expr(value):
    if isinstance(value, str):
        if re.fullmatch(r'-?\d+\.\d+', value):
            return value + 'f'
        return name(value)
    op, *args = value
    if op == 'cast':
        return f'{TYPES[args[0]]}({expr(args[1])})'
    if op == 'if':
        return f'({expr(args[0])} ? {expr(args[1])} : {expr(args[2])})'
    if op in ('+', '-', '*', '/', '<', '>', '<=', '>=', '=', '^', '&', '>>'):
        return '(' + (' ' + ('==' if op == '=' else op) + ' ').join(expr(a) for a in args) + ')'
    if op in ('floor', 'sqrt', 'cos', 'sin', 'pow') or op.startswith(('tex-', 'fin-')):
        return name(op) + '(' + ', '.join(expr(a) for a in args) + ')'
    raise ValueError(f'unsupported expression: {value}')


def body(value, indent='    '):
    if isinstance(value, list) and value[0] == 'let':
        _, bindings, result = value
        lines = [f'{indent}const auto {name(bindings[i])} = {expr(bindings[i+1])};'
                 for i in range(0, len(bindings), 2)]
        return '\n'.join(lines) + '\n' + body(result, indent)
    if isinstance(value, list) and value[0] == 'case':
        _, selector, *cases = value
        lines = [f'{indent}switch ({expr(selector)}) {{']
        for i in range(0, len(cases)-1, 2):
            lines += [f'{indent}case {cases[i]}: {{', body(cases[i+1], indent+'    '), indent+'}']
        lines += [indent+'default: {', body(cases[-1], indent+'    '), indent+'}', indent+'}']
        return '\n'.join(lines)
    return indent + 'return ' + expr(value) + ';'


def generate():
    output = [BEGIN, '// Generated from texture.coil and finish_light.coil by tools/generate-material-shader.py.']
    for form in [form for source in SOURCES for form in parse(source.read_text())]:
        if form[0] != 'defn' or not form[1].startswith(('tex-', 'fin-')):
            continue
        _, symbol, params, result, code = form
        signature = ', '.join(TYPES[t[1]]+' '+name(t[0]) for t in params)
        output += [f'inline {TYPES[result[1]]} {name(symbol)}({signature}) {{', body(code), '}']
    return '\n'.join(output + [END])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    source = TARGET.read_text()
    generated = generate()
    if BEGIN in source:
        start, tail = source.split(BEGIN, 1)
        _, end = tail.split(END, 1)
        updated = start + generated + end
    else:
        marker = 'struct PaperParams'
        start, end = source.split(marker, 1)
        updated = start + generated + '\n\n' + marker + end
    if args.check:
        if updated != source:
            raise SystemExit('Material shader is stale; run tools/generate-material-shader.py')
    else:
        TARGET.write_text(updated)


if __name__ == '__main__':
    main()
