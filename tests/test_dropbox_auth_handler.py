from urlparse import urlparse

from pyramid import testing
from nose.plugins.attrib import attr
from minimock import mock, restore

from utils import create_user, TestBase


class ATestBase(TestBase):
    def setUp(self):
        super(ATestBase, self).setUp()
        self.testbed.init_datastore_v3_stub()

    def tearDown(self):
        super(TestBase, self).tearDown()
        restore()


class AuthorizeHandlerTest(ATestBase):
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


class AuthorizeCallbackHandlerTest(ATestBase):
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
        from netprintbox.data import DropboxUser

        request = testing.DummyRequest({'oauth_token': 'token'})
        response = authorize_callback(request)
        self.assertEqual(response.status_int, 302)
        actual_url = response.location
        expected_url = request.route_path('setup_guide')
        self.assertEqual(expected_url, actual_url)
        key = request.session['netprintbox.dropbox_user.key']
        self.assertIsNotNone(DropboxUser.get(key))
