import os
import logging

SYSADMIN_ADDRESS = 'YOUR_ADMIN_ADDRESS'
DROPBOX_APP_KEY = 'YOUR_APP_KEY'
DROPBOX_APP_SECRET = 'YOUR_APP_SECRET'
DROPBOX_ACCESS_TYPE = 'app_folder'

ACCOUNT_INFO_PATH = '/account.ini'
REPORT_PATH = '/report.html'

USER_AGENT = ('Mozilla/5.0 (Macintosh; U; Intel Mac OS X 10_6_3; ja-jp) '
              'AppleWebKit/533.16 (KHTML, like Gecko) '
              'Version/5.0 Safari/533.16')

DATETIME_FORMAT = "%Y/%m/%d %H:%M:%S"

SLEEP_WAIT = 120

PACKAGE_DIR = os.path.dirname(__file__)
ROOT_DIR = os.path.dirname(os.path.dirname(PACKAGE_DIR))
TEMPLATE_PATH = os.path.join(ROOT_DIR, 'templates')

SESSION_ENCRYPT_KEY = 'encrypt_key'
SESSION_VALIDATE_KEY = 'validate_key'

try:
    exec file(os.path.join(PACKAGE_DIR, 'settings_local.py')).read()
    logging.info("settings_local.py loaded")
except IOError:
    logging.info("no settings_local.py")
