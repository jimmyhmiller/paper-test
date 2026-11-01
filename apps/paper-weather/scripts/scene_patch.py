#!/usr/bin/env python3
"""Apply small AI-authored edits, native-validate, then atomically publish JSON.

No model/API or image generator is involved. A supplying agent writes the patch.
The native player observes publication within 0.5s without rebuilding/restarting.
"""
from pathlib import Path
import argparse
import json
import fcntl
import os
import subprocess
import tempfile

APP = Path(__file__).resolve().parents[1]
VALIDATOR = APP.parents[1]/'build/paper-scene-validate'

def read(path):
    if path.stat().st_size > 1048576:
        raise ValueError('Document exceeds 1 MiB')
    def reject_constant(value):
        raise ValueError(f'Non-finite number: {value}')
    return json.loads(path.read_text(), parse_constant=reject_constant)

def locate(nodes, identity):
    for i, node in enumerate(nodes):
        if node['id'] == identity:
            return nodes, i
        result = locate(node.get('children', []), identity)
        if result is not None:
            return result
    return None

def apply(document, operations):
    if not isinstance(operations, list) or not 1 <= len(operations) <= 64:
        raise ValueError('Expected 1–64 patch operations')
    for op in operations:
        if not isinstance(op, dict):
            raise ValueError('Each patch operation must be an object')
        kind = op.get('op')
        if kind == 'conditions' and set(op) == {'op', 'values'}:
            document['conditions'].update(op['values'])
        elif kind == 'material' and set(op) == {'op', 'name', 'value'}:
            document['materials'][op['name']] = op['value']
        elif kind in ('set', 'remove'):
            expected = {'op', 'id', 'values'} if kind == 'set' else {'op', 'id'}
            if set(op) != expected:
                raise ValueError('Unexpected operation fields')
            found = locate(document['nodes'], op['id'])
            if found is None:
                raise ValueError(f'Unknown piece: {op["id"]}')
            siblings, index = found
            if kind == 'remove':
                del siblings[index]
            else:
                allowed = {'path', 'material', 'z', 'transform', 'motion', 'show', 'emitter'}
                if not isinstance(op['values'], dict) or not set(op['values']) <= allowed:
                    raise ValueError('set cannot change identity or replace child trees')
                siblings[index].update(op['values'])
        elif kind == 'append' and set(op) == {'op', 'parent', 'node'}:
            if op['parent'] is None:
                document['nodes'].append(op['node'])
            else:
                found = locate(document['nodes'], op['parent'])
                if found is None:
                    raise ValueError('Unknown parent')
                parent = found[0][found[1]]
                if 'children' not in parent:
                    raise ValueError('Can only append into a group')
                parent['children'].append(op['node'])
        else:
            raise ValueError('Unsupported operation or unexpected fields')
    return document

def _publish_locked(scene, patch, validator):
    original = scene.read_bytes()
    document = apply(read(scene), read(patch))
    encoded = json.dumps(document, indent=2, allow_nan=False).encode() + b'\n'
    if len(encoded) > 1048576:
        raise ValueError('Result exceeds 1 MiB')
    candidate = None
    try:
        with tempfile.NamedTemporaryFile(dir=scene.parent, prefix='.'+scene.name, suffix='.candidate', delete=False) as stream:
            candidate = Path(stream.name)
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())
        result = subprocess.run([str(validator), str(candidate)], capture_output=True, text=True)
        if result.returncode:
            raise ValueError('Native scene validation rejected patch; original file unchanged')
        if scene.read_bytes() != original:
            raise ValueError('Scene changed during validation; retry against current revision')
        os.chmod(candidate, scene.stat().st_mode & 0o777)
        os.replace(candidate, scene)
    finally:
        if candidate is not None:
            candidate.unlink(missing_ok=True)

def publish(scene, patch, validator=VALIDATOR):
    # The stable sidecar lock survives replacement of the scene's inode.
    # Other publishers using this API serialize; manual editor races are checked.
    with scene.with_name('.'+scene.name+'.lock').open('a') as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        return _publish_locked(scene, patch, validator)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('scene', type=Path)
    parser.add_argument('patch', type=Path)
    args = parser.parse_args()
    if not VALIDATOR.exists():
        parser.error('Build first: python3 apps/paper-weather/scripts/build_scene_proof.py')
    try:
        publish(args.scene.resolve(), args.patch.resolve())
    except (ValueError, KeyError, TypeError, OSError) as error:
        parser.exit(1, f'{error}\n')
    print('Published validated scene edit; a running player will reload it.')

if __name__ == '__main__':
    main()
