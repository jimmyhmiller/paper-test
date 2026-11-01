#!/usr/bin/env python3
"""Copy the legacy curl bearer credential into a private token file, once."""
import argparse
import os
from pathlib import Path
import re
import shlex


def bearer_token(config):
    tokens = []
    for line in config.splitlines():
        words = shlex.split(line, comments=True)
        if not words:
            continue
        if words[0] not in ('header', '--header', '-H'):
            raise ValueError('Expected only an Authorization header in curl config')
        values = words[1:]
        if values and values[0] == '=':
            values = values[1:]
        if len(values) != 1:
            raise ValueError('Invalid curl header syntax')
        match = re.fullmatch(r'Authorization:\s*Bearer ([A-Za-z0-9._~+/-]+=*)', values[0], re.I)
        if not match:
            raise ValueError('Expected a Bearer Authorization header')
        tokens.append(match[1])
    if len(tokens) != 1:
        raise ValueError('Expected exactly one bearer credential')
    return tokens[0]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=Path.home() / '.jim/dataflow/analytics.curl')
    parser.add_argument('--destination', type=Path, default=Path.home() / '.jim/dataflow/analytics.token')
    args = parser.parse_args()
    token = bearer_token(args.source.read_text())
    # Exclusive creation preserves any existing credential and sets permissions
    # before the first credential byte is written.
    fd = os.open(args.destination, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'w') as stream:
        stream.write(token + '\n')
    print('Created private bearer-token file:', args.destination)


if __name__ == '__main__':
    main()
