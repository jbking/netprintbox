from unittest import TestCase
from datetime import datetime

from pyramid import testing

from netprint import Item, PaperSize
from netprintbox import data


class TestBase(TestCase):
    def setUp(self):
        from google.appengine.ext.testbed import Testbed

        self.testbed = Testbed()
        self.testbed.activate()
        # default setup with no param
        # you may re-setup in a test code by using this.
        self.setUpPyramid()

    def setUpPyramid(self, **kwargs):
        import netprintbox
        self.config = testing.setUp(**kwargs)
        self.config.include('netprintbox')

    def tearDown(self):
        self.testbed.deactivate()
        testing.tearDown()


def create_user(**kwargs):
    default = {
            'uid': 'uid',
            'email': 'email',
            'display_name': 'display_name',
            'access_key': 'access_key',
            'access_secret': 'access_secret',
            'country': 'JP',
            'report_token': '',
        }
    params = dict(default)
    params.update(kwargs)
    user = data.DropboxUser(**params)
    user.put()
    return user


def create_file_info(user, **kwargs):
    default = {
            'path': '/A4/path.doc',
            'rev': 'rev',
            'size': 1,
            'state': data.FileState.NEED_NETPRINT_ID,
            'last_modified': datetime.now(),
            'pin': False,
        }
    params = dict(default)
    params['parent'] = user
    params.update(kwargs)
    file_info = data.DropboxFileInfo(**params)
    file_info.put()
    return file_info


def create_netprint_item(**kwargs):
    default = {
            'id': 'id',
            'name': 'name',
            'file_size': '0MB',
            'paper_size': 'A4',
            'page_numbers': 1,
            'valid_date': '1900/01/01',
            'error': False,
        }
    params = dict(default)
    params.update(kwargs)
    return Item(**params)


def create_dropbox_item(**kwargs):
    default = {
            'is_dir': False,
            'path': 'path',
            'bytes': 0,
            'rev': 'rev',
            'modified': "Sat, 21 Aug 2010 22:31:20 +0000"}
    params = dict(default)
    params.update(kwargs)
    return params


def app_dir():
    return {
        'path': u'/',
        'is_dir': True,
        'contents': [
            {
                'path': u'/%s' % attr_name,
                'is_dir': True,
                 'contents': [],
             }
             for attr_name in dir(PaperSize)
             if not attr_name.startswith('_')
         ]}
