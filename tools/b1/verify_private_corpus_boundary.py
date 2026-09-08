"""Bounded tracked/index path guard. Never reads document content or prints paths."""

import os
from pathlib import Path
import subprocess

RESERVED = {'.foundation-private', 'private-corpus', 'b1-private-corpus'}
ENV = 'FOUNDATION_B1_PRIVATE_CORPUS_DIR'


def violations(paths, root, configured=None):
    root = Path(root).resolve()
    private = Path(configured).resolve() if configured else None
    found = 0
    for value in paths:
        path = Path(value.replace('\\', '/'))
        resolved = (root / path).resolve()
        if (any(part.lower() in RESERVED for part in path.parts)
                or (private and private.is_relative_to(root) and resolved.is_relative_to(private))):
            found += 1
    return found


def verify(root, configured=None):
    result = subprocess.run(['git', '-C', str(root), 'ls-files', '-z', '--cached'],
                            capture_output=True, check=True)
    paths = result.stdout.decode('utf-8').split('\0')
    count = violations([p for p in paths if p], root, configured)
    if count:
        raise ValueError(f'PRIVATE_BOUNDARY_VIOLATION: {count} tracked/index entries; paths withheld')
    return True


if __name__ == '__main__':
    try:
        verify(Path(__file__).resolve().parents[2], os.environ.get(ENV))
    except Exception:
        print('PRIVATE_BOUNDARY_VIOLATION: inspect the Git index privately; no content published')
        raise SystemExit(1)
    print('Private corpus tracked/index boundary: PASS')
