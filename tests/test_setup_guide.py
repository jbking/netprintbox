import re
from StringIO import StringIO

from pyramid import testing
from nose.plugins.attrib import attr
from minimock import mock, restore
from webob import exc

from utils import create_user, TestBase


class SetupGuideTestBase(TestBase):
    def setUp(self):
        super(SetupGuideTestBase, self).setUp()
        self.testbed.init_datastore_v3_stub()

    def tearDown(self):
        super(SetupGuideTestBase, self).tearDown()
        restore()


class SetupGuideTest(SetupGuideTestBase):
    def setUp(self):
        super(SetupGuideTest, self).setUp()

        from netprintbox.exceptions import DropboxNotFound
        # mockout
        import netprintbox.service
        import google.appengine.api.taskqueue

        res = StringIO('')
        res.status = 404
        res.reason = 'reason'

        class service(object):
            def __init__(self):
                self.state = 0
                self.dropbox = type('fake_dropbox', (), {})
                self.dropbox.list = self._list
                self.dropbox.put = self._put

            def _list(self, path):
                assert self.state in (0, 2, 4), \
                       "Invalid state %r" % self.state
                if self.state == 0:
                    self.state += 1
                    raise DropboxNotFound
                else:
                    self.state += 1
                    return {}

            def _put(self, path, file_obj):
                assert self.state in (1,), \
                       "Invalid state %r" % self.state
                self.state += 1

            def load_netprint_account_info(self):
                assert self.state in (3, 5), \
                       "Invalid state %r" % self.state
                if self.state == 3:
                    self.state += 1
                    raise DropboxNotFound
                else:
                    return ('username', 'password')

        class netprint_service(object):
            client = object()

        mock('netprintbox.service.NetprintboxService',
             returns=service())
        mock('netprintbox.service.NetprintService',
             returns=netprint_service)
        mock('google.appengine.api.taskqueue.add')

    @attr('integration', 'light')
    def test_it(self):
        from netprintbox.views import setup_guide

        request1 = testing.DummyRequest(params={'key': 'key'})
        with self.assertRaises(exc.HTTPUnauthorized):
            setup_guide(request1)

        user = create_user()
        request2 = testing.DummyRequest(params={'key': user.access_key})
        response2 = setup_guide(request2)
        self.assertEqual(response2.status_int, 200)
        self.assertRegexpMatches(response2.body, re.compile('Step1'))

        # fall back to step1 if login failed.
        request3 = testing.DummyRequest(params={'key': user.access_key})
        response3 = setup_guide(request3)
        self.assertEqual(response3.status_int, 200)
        self.assertRegexpMatches(response3.body, re.compile('Step1'))

        # login succeed.
        request4 = testing.DummyRequest(params={'key': user.access_key})
        response4 = setup_guide(request4)
        self.assertEqual(response4.status_int, 200)
        self.assertRegexpMatches(response4.body, re.compile('Step2'))


class SetupGuidePendingTest(SetupGuideTestBase):
    @attr('integration', 'light')
    def test_it(self):
        from netprintbox.views import setup_guide
        from netprintbox.exceptions import BecomePendingUser

        user = create_user()
        with self.assertRaises(BecomePendingUser):
            user.put_pending(notify=False)
        request = testing.DummyRequest(params={'key': user.access_key})
        try:
            setup_guide(request)
            self.fail("No redirect response found")
        except exc.HTTPFound as response:
            self.assertEqual(response.status_int, 302)
            self.assertEqual(response.location,
                             request.route_path('authorize'))
