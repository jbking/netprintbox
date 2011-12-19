from unittest import TestCase
from urlparse import urlparse

from webapp2 import uri_for
from nose.plugins.attrib import attr
from minimock import mock, restore

from test_utils import (create_user, get_blank_request)


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
        request = get_blank_request()
        response = app.get_response(uri_for('authorize', _request=request))
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

        request = get_blank_request()
        response = app.get_response(uri_for('authorize_callback',
                                            _request=request,
                                            oauth_token='hoge'))
        self.assertEqual(response.status_int, 302)
        parsed = urlparse(response.location)
        actual_url = '%s?%s' % (parsed.path, parsed.query)

        request = get_blank_request()
        expected_url = uri_for('setup_guide', _request=request,
                      key=self.user.access_key)
        self.assertEqual(expected_url, actual_url)
