DROPBOX_APP_KEY = 'YOUR_APP_KEY'
DROPBOX_APP_SECRET = 'YOUR_APP_SECRET'
DROPBOX_ACCESS_TYPE = 'app_folder'

DEBUG = True
USER_AGENT = ('Mozilla/5.0 (Macintosh; U; Intel Mac OS X 10_6_3; ja-jp) '
              'AppleWebKit/533.16 (KHTML, like Gecko) '
              'Version/5.0 Safari/533.16')

import os
exec file(os.path.join(os.path.dirname(__file__), 'settings_local.py')).read()
