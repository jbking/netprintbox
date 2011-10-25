# On running tests, this file will be run in the tests directory.
# So the path of top of this project is needed.
import os, sys
sys.path.insert(0, os.path.join(*os.path.split(os.path.abspath(os.path.dirname(__file__)))[:-1]))

import kay
kay.setup_env(manage_py_env=True)
from kay.management.test import setup_env, setup_stub

setup_env()
setup_stub()

from netprint import Client
from mechanize import Browser
from mocker import Mocker

def pytest_addoption(parser):
    parser.addoption("--username", default=None,
                     help="The username for Net print")
    parser.addoption("--password", default=None,
                     help="The password for Net print")

def pytest_funcarg__context(request):
    return Context(request)

class Context(object):
    def __init__(self, request):
        self.config = request.config

    def need_connect(self):
        return (self.config.option.username is not None and
                self.config.option.password is not None)

    def mocker(self):
        return Mocker()

    def get_netprint_client(self, browser=None):
        if browser is None:
            browser = Browser()
        client = Client(browser)
        if self.config.option.verbose:
            client.set_debug()
        return client
