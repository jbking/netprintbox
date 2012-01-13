import os
import sys
import logging

here = os.path.abspath(os.path.dirname(__file__))
bundle = os.path.join(here, 'bundle.zip')
src_dir = os.path.join(here, 'src')


def fix_sys_path():
    if src_dir not in sys.path:
        sys.path.insert(0, src_dir)
    if bundle not in sys.path:
        sys.path.insert(0, bundle)


def update_webob():
    import webob
    VERSION = '1.2b2'
    if webob.__version__ != VERSION:
        logging.debug('replacing webob from %s', webob.__version__)
        # flush existing appengine bundled ancestor webob.
        for module_name in sys.modules.keys():
            if module_name.startswith('webob.'):
                del sys.modules[module_name]
        if 'webob' in sys.modules:
            del sys.modules['webob']
        reload(webob)
        assert webob.__version__ == VERSION

fix_sys_path()
update_webob()


class EnvironmentRestore(object):
    def __init__(self, app):
        self.app = app

    def __call__(self, environ, start_response):
        fix_sys_path()
        update_webob()
        return self.app(environ, start_response)


def main():
    """ This function returns a Pyramid WSGI application.
    """
    from pyramid.config import Configurator

    settings = {}
    if os.environ.get('SERVER_SOFTWARE', '').startswith('Dev'):
        # Into debug mode when this is running under SDK.
        settings['debug'] = True
    else:
        settings['debug'] = False

    # session
    from netprintbox.settings import (
            SESSION_ENCRYPT_KEY, SESSION_VALIDATE_KEY)
    settings['beaker.session.type'] = 'cookie'
    settings['beaker.session.key'] = 'netprintbox.session'
    settings['beaker.session.encrypt_key'] = SESSION_ENCRYPT_KEY
    settings['beaker.session.validate_key'] = SESSION_VALIDATE_KEY

    config = Configurator(settings=settings)
    if settings['debug']:
        import httplib2
        httplib2.debuglevel = 1

    # include them
    config.include('netprintbox')
    config.include('pyramid_beaker')

    return EnvironmentRestore(config.make_wsgi_app())

app = main()
