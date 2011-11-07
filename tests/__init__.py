import os
import sys


def setup():
    project_top = os.path.dirname(os.path.dirname(__file__))
    for dirname in ('bundle', 'src'):
        sys.path.insert(0, os.path.join(project_top, dirname))

    sys.path.insert(0, '/usr/local/google_appengine')
    import dev_appserver
    dev_appserver.fix_sys_path()
