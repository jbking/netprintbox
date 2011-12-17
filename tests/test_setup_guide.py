import re
from unittest import TestCase
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

        import dropbox.rest
        # mockout
        import netprintbox.service
        import google.appengine.api.taskqueue

        res = StringIO('body')
        res.status = '400'
        res.reason = 'reason'

        class m1(object):
            def __init__(self):
                self.state = 0

            def __call__(self, path):
                if self.state == 0:
                    self.state += 1
                    raise dropbox.rest.ErrorResponse(res)
                else:
                    return {}

        class m2(object):
            def __init__(self):
                self.state = 0

            def __call__(self):
                if self.state == 0:
                    self.state += 1
                    raise dropbox.rest.ErrorResponse(res)

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
                    raise dropbox.rest.ErrorResponse(res)
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
                    raise dropbox.rest.ErrorResponse(res)

        mock('netprintbox.service.NetprintboxService',
             returns=service())
        mock('google.appengine.api.taskqueue.add')

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
        self.assertEqual(response.status_int, 401,
                         "Unknown user can't into setup.")

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
