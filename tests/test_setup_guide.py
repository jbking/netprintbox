import re
from unittest2 import TestCase
from StringIO import StringIO
from nose.plugins.attrib import attr
from minimock import mock, Mock, restore

from test_utils import create_user


class SetupGuideTest(TestCase):
    def setUp(self):
        from google.appengine.ext.testbed import Testbed

        self.testbed = Testbed()
        self.testbed.activate()
        self.testbed.init_datastore_v3_stub()

        # mockout
        import dropbox.session
        import dropbox.client
        import commands.dropbox
        import commands.netprintbox
        mock('dropbox.session.DropboxSession')
        mock('dropbox.client.DropboxClient')
        mock('commands.dropbox.ls')
        mock('commands.dropbox.load_netprint_account_info')
        dropbox.session.DropboxSession.mock_returns = Mock('DropboxSession')
        dropbox.client.DropboxClient.mock_returns = Mock('DropboxClient')

        res = StringIO('body')
        res.status = '400'
        res.reason = 'reason'

        class m1(object):
            def __init__(self):
                self.state = 0

            def __call__(self, client, path):
                if self.state == 0:
                    self.state += 1
                    raise dropbox.rest.ErrorResponse(res)

        class m2(object):
            def __init__(self):
                self.state = 0

            def __call__(self, client):
                if self.state == 0:
                    self.state += 1
                    raise dropbox.rest.ErrorResponse(res)

        commands.dropbox.ls.mock_returns_func = m1()
        commands.dropbox.load_netprint_account_info = m2()

    def tearDown(self):
        self.testbed.deactivate()
        restore()

    def _getAUT(self):
        from main import app
        return app

    @attr('functional', 'light')
    def test_guide(self):
        app = self._getAUT()

        response = app.get_response('/guide/setup?key=key')
        self.assertEqual(response.status_int, 400)

        user = create_user()
        response = app.get_response('/guide/setup?key=%s' % user.access_key)
        self.assertEqual(response.status_int, 200)
        self.assertRegexpMatches(response.body, re.compile('step1'))

        # fall back to step1 if login failed.
        response = app.get_response('/guide/setup?key=%s' % user.access_key)
        self.assertEqual(response.status_int, 200)
        self.assertRegexpMatches(response.body, re.compile('step1'))

        # login succeed.
        response = app.get_response('/guide/setup?key=%s' % user.access_key)
        self.assertEqual(response.status_int, 200)
        self.assertRegexpMatches(response.body, re.compile('step2'))
