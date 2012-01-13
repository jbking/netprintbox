#!/usr/bin/env python
import os
import sys
import re

"""
Detect no copyright code.
"""


def main(*args):
    files = []
    for root in args:
        if os.path.isdir(root):
            for dirpath, _, filenames in os.walk(root):
                files.extend([
                    os.path.join(dirpath, name)
                    for name in filenames])
        else:
            files.append(root)
    pattern = re.compile('Netprintbox.*Copyright',
                         re.DOTALL)
    found = False
    for path in files:
        if os.path.splitext(path)[1] not in ('.coffee', '.py'):
            continue
        with open(path) as f:
            code = f.read()
            if pattern.search(code) is None:
                found = True
                head = '\n'.join(code.split('\n')[:5])
                print('-' * 20)
                print('path: %(path)s\n%(head)s' % locals())
    if found:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == '__main__':
    main(*sys.argv)
