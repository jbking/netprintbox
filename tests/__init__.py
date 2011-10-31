import os
import sys


def setup():
    project_top = os.path.dirname(os.path.dirname(__file__))
    for dirname in ('bundle', 'src'):
        sys.path.insert(0, os.path.join(project_top, dirname))
