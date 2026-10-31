#!/usr/bin/env python3
"""Refresh bundled title metadata from a local checkout of the author's blog.

The app does not depend on this checkout at runtime. Unknown future posts use
their decoded slug until this optional catalog is updated.
"""
import argparse
import html
import json
import re
from pathlib import Path


def title_from(source):
    patterns = [
        r'<title>([^<]+)</title>',
        r'<Title\b[^>]*\btext="([^"]+)"',
        r'^# (.+)$',
        r'property="og:title" content="([^"]+)"',
        r'<Heading\b[^>]*\btext="([^"]+)"',
    ]
    for pattern in patterns:
        match = re.search(pattern, source, re.M)
        if match:
            return html.unescape(match.group(1)).replace('`', '').strip()
    return None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('checkout', type=Path)
    args = parser.parse_args()
    pages = args.checkout / 'pages'
    destination = Path(__file__).resolve().parents[1] / 'resources/titles.json'
    existing = json.loads(destination.read_text()) if destination.exists() else {}
    titles = {key: value for key, value in existing.items() if key.startswith('@short:')}
    for path in sorted(pages.rglob('*')):
        if path.suffix not in {'.js', '.jsx', '.mdx', '.md'}:
            continue
        relative = path.relative_to(pages).with_suffix('').as_posix()
        if relative.endswith('/index'):
            relative = relative[:-6]
        title = title_from(path.read_text())
        if title:
            titles['/api/' + relative.replace('/', '%2F')] = title
    destination.write_text(json.dumps(titles, ensure_ascii=False, indent=2) + '\n')
    print(f'Wrote {len(titles)} title and display-label entries to {destination}')


if __name__ == '__main__':
    main()
