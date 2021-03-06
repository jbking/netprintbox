#!/usr/bin/env python
import os
import sys
from nose.core import run_exit


if __name__ == '__main__':
    os.environ['HTTP_HOST'] = 'testhost.testdomain'
    sys.path.insert(0, '/usr/local/google_appengine')
    import dev_appserver
    dev_appserver.fix_sys_path()
    project_top = os.path.abspath(os.path.dirname(__file__))
    sys.path.insert(0, os.path.join(project_top, 'bundle.zip'))
    sys.path.insert(0, os.path.join(project_top, 'src'))
    run_exit()
