import os
import sys

here = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(here, 'bundle'))
sys.path.insert(0, os.path.join(here, 'src'))

from netprintbox import main

app = main.app
