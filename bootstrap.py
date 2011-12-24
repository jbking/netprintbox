import os
import sys

import webapp2 as w

here = os.path.dirname(__file__)
bundle_dir = os.path.join(here, 'bundle')
src_dir = os.path.join(here, 'src')
# Into debug mode when this is running under SDK.
debug = os.environ.get('SERVER_SOFTWARE', '').startswith('Dev')


def fix_sys_path():
    if src_dir not in sys.path:
        sys.path.insert(0, src_dir)
    if bundle_dir not in sys.path:
        sys.path.insert(0, bundle_dir)

fix_sys_path()


class CustomApplication(w.WSGIApplication):
    def __call__(self, environ, start_response):
        # execution in taskqueue needs this.
        fix_sys_path()

        import httplib2
        if debug:
            httplib2.debuglevel = 1

        return super(CustomApplication, self).\
                __call__(environ, start_response)

from netprintbox.main import routes
app = CustomApplication(routes, debug=debug)
