from unittest import TestCase
from urlparse import urlparse

from nose.plugins.attrib import attr
from minimock import mock, restore

from test_utils import create_user


class AuthorizeHandlerTest(TestCase):
    url = "http://fake.host/faked_url"

    def setUp(self):
        from google.appengine.ext.testbed import Testbed

        self.testbed = Testbed()
        self.testbed.activate()
        self.testbed.init_datastore_v3_stub()

        # mockout
        import netprintbox.service
        mock('netprintbox.service.DropboxService.build_authorize_url',
             returns=self.url)

    def tearDown(self):
        self.testbed.deactivate()
        restore()

    def _getAUT(self):
        from netprintbox.main import app
        return app

    @attr('functional', 'light')
    def test_it(self):
        app = self._getAUT()
        response = app.get_response('/dropbox/authorize')
        self.assertEqual(response.status_int, 302)
        self.assertEqual(response.location, self.url)


class AuthorizeCallbackHandlerTest(TestCase):
    oauth_token = 'fake_token'

    def setUp(self):
        from google.appengine.ext.testbed import Testbed

        self.testbed = Testbed()
        self.testbed.activate()
        self.testbed.init_datastore_v3_stub()

        self.user = create_user()

        # mockout
        import netprintbox.service
        mock('netprintbox.service.DropboxService.setup_user',
             returns=self.user)

    def tearDown(self):
        self.testbed.deactivate()
        restore()

    def _getAUT(self):
        from netprintbox.main import app
        return app

    @attr('functional', 'light')
    def test_it(self):
        app = self._getAUT()
        response = app.get_response('/dropbox/callback?oauth_token=hoge')
        self.assertEqual(response.status_int, 302)

        result = urlparse(response.location)
        self.assertEqual(result.path, '/guide/setup')
        self.assertEqual(result.query, 'key=%s' % self.user.access_key)
