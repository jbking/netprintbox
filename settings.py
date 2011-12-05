import os

DROPBOX_APP_KEY = 'YOUR_APP_KEY'
DROPBOX_APP_SECRET = 'YOUR_APP_SECRET'
DROPBOX_ACCESS_TYPE = 'app_folder'

ACCOUNT_INFO_PATH = '/account.ini'
REPORT_PATH = '/report.html'

USER_AGENT = ('Mozilla/5.0 (Macintosh; U; Intel Mac OS X 10_6_3; ja-jp) '
              'AppleWebKit/533.16 (KHTML, like Gecko) '
              'Version/5.0 Safari/533.16')

SLEEP_WAIT = 120

TEMPLATE_PATH = os.path.join(os.path.dirname(__file__), 'templates')

try:
    exec file(os.path.join(os.path.dirname(__file__),
                           'settings_local.py')).read()
except IOError:
    pass
