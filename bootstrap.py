import os
import sys

here = os.path.abspath(os.path.dirname(__file__))
bundle_dir = os.path.join(here, 'bundle')
src_dir = os.path.join(here, 'src')


def fix_sys_path():
    if src_dir not in sys.path:
        sys.path.insert(0, src_dir)
    if bundle_dir not in sys.path:
        sys.path.insert(0, bundle_dir)

fix_sys_path()

from netprintbox import main
app = main.app
