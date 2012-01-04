import os
import sys

here = os.path.abspath(os.path.dirname(__file__))
bundle = os.path.join(here, 'bundle.zip')
src_dir = os.path.join(here, 'src')


def fix_sys_path():
    if src_dir not in sys.path:
        sys.path.insert(0, src_dir)
    if bundle not in sys.path:
        sys.path.insert(0, bundle)

fix_sys_path()

# flush existing appengine bundled ancestor webob.
for module_name in sys.modules.keys():
    if module_name.startswith('webob.'):
        del sys.modules[module_name]
if 'webob' in sys.modules:
    del sys.modules['webob']


def main():
    """ This function returns a Pyramid WSGI application.
    """
    from pyramid.config import Configurator

    settings = {}
    if os.environ.get('SERVER_SOFTWARE', '').startswith('Dev'):
        # Into debug mode when this is running under SDK.
        settings['debug'] = True

    config = Configurator(settings=settings)
    if settings['debug']:
        import httplib2
        httplib2.debuglevel = 1
    config.include('netprintbox')
    return config.make_wsgi_app()

app = main()
