import os
import sys


def setup():
    sys.path.insert(0, os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        'bundle'))
