#!/usr/bin/env python
import os
import sys
from nose.core import run_exit


if __name__ == '__main__':
    sys.path.insert(0, '/usr/local/google_appengine')
    import dev_appserver
    dev_appserver.fix_sys_path()
    project_top = os.path.abspath(os.path.dirname(__file__))
    for dirname in ('bundle', 'src'):
        sys.path.insert(0, os.path.join(project_top, dirname))
    run_exit()
