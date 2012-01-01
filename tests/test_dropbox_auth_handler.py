from unittest import TestCase
from urlparse import urlparse

from pyramid import testing
from nose.plugins.attrib import attr
from minimock import mock, restore

from utils import create_user


class TestBase(TestCase):
    def setUp(self):
        from google.appengine.ext.testbed import Testbed

        self.testbed = Testbed()
        self.testbed.activate()
        self.testbed.init_datastore_v3_stub()

        import netprintbox
        self.config = testing.setUp()
        self.config.include('netprintbox')

    def tearDown(self):
        self.testbed.deactivate()
        restore()
        testing.tearDown()


class AuthorizeHandlerTest(TestBase):
    url = "http://fake.host/faked_url"

    def setUp(self):
        super(AuthorizeHandlerTest, self).setUp()
        # mockout
        import netprintbox.service
        mock('netprintbox.service.DropboxService.build_authorize_url',
             returns=self.url)

    @attr('integration', 'light')
    def test_it(self):
        from netprintbox.views import authorize

        request = testing.DummyRequest()
        response = authorize(request)
        self.assertEqual(response.status_int, 302)
        self.assertEqual(response.location, self.url)


class AuthorizeCallbackHandlerTest(TestBase):
    def setUp(self):
        super(AuthorizeCallbackHandlerTest, self).setUp()

        self.user = create_user()

        # mockout
        import netprintbox.service
        mock('netprintbox.service.DropboxService.setup_user',
             returns=self.user)

    @attr('integration', 'light')
    def test_it(self):
        from netprintbox.views import authorize_callback

        request = testing.DummyRequest({'oauth_token': 'token'})
        response = authorize_callback(request)
        self.assertEqual(response.status_int, 302)
        parsed = urlparse(response.location)
        actual_url = '%s?%s' % (parsed.path, parsed.query)

        expected_url = request.route_path('setup_guide',
                _query=(('key', self.user.access_key),))
        self.assertEqual(expected_url, actual_url)
