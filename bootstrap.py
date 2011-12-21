import logging
import os
import sys

here = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(here, 'bundle'))
sys.path.insert(0, os.path.join(here, 'src'))

import httplib2

if logging.getLogger().level <= logging.DEBUG:
    httplib2.debuglevel = 1

from netprintbox import main

app = main.app
