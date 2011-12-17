from unittest import TestCase
from StringIO import StringIO

from nose.plugins.attrib import attr
from minimock import mock, restore

from test_utils import create_user, create_file_info, create_netprint_item


class ServiceTestBase(TestCase):
    maxDiff = None

    def setUp(self):
        from google.appengine.ext.testbed import Testbed

        self.testbed = Testbed()
        self.testbed.activate()
        self.testbed.init_datastore_v3_stub()
        self.testbed.init_memcache_stub()

    def tearDown(self):
        self.testbed.deactivate()
        restore()


class NetprintboxServiceTest(ServiceTestBase):
    def _getOUT(self, user, request=None):
        from netprintbox.service import NetprintboxService
        return NetprintboxService(user, request=request)

    @attr('unit', 'light')
    def test_make_report(self):
        from google.appengine.api import memcache
        import settings
        from netprintbox.data import FileState
        from netprintbox.utils import normalize_name

        user = create_user()
        f1_path = '/need_netprint_id.data'
        f1 = create_file_info(user,
                              path=f1_path,
                              netprint_name=normalize_name(f1_path),
                              state=FileState.NEED_NETPRINT_ID)
        f2_path = '/lost_by_something.data'
        f2 = create_file_info(user,
                              path=f2_path,
                              netprint_name=normalize_name(f2_path),
                              state=FileState.LATEST)
        f3_path = '/latest.data'
        f3 = create_file_info(user,
                              path=f3_path,
                              netprint_id='latest',
                              netprint_name=normalize_name(f3_path),
                              state=FileState.LATEST)

        class netprint(object):
            @staticmethod
            def list():
                return [
                        create_netprint_item(
                            id='uncontrolled',
                            name='uncontrolled.jpg'),
                        create_netprint_item(
                            id='latest',
                            name=normalize_name('/latest.data')),
                       ]

        put_result = []

        class dropbox(object):
            @staticmethod
            def put(path, file_obj):
                put_result.append((path, file_obj))

        class request(object):
            host = 'localhost'

        service = self._getOUT(user, request=request)
        service.netprint = netprint
        service.dropbox = dropbox

        (need_report, result) = service._make_report()
        self.assertTrue(need_report)
        self.assertItemsEqual(
            [(item['id'], item['name'], item['controlled'],
              item['last_modified']) for item in result],
            [('FAKE:WAIT', f1.netprint_name, True,
              f1.last_modified.strftime(settings.DATETIME_FORMAT)),
             ('FAKE:ERROR', f2.netprint_name, True,
              f2.last_modified.strftime(settings.DATETIME_FORMAT)),
             ('uncontrolled', 'uncontrolled.jpg', False, None),
             ('latest', f3.netprint_name, True,
              f3.last_modified.strftime(settings.DATETIME_FORMAT)),
            ])

        # flush side-effect of above.
        memcache.flush_all()

        service.make_report()
        self.assertEqual(len(put_result), 1)
        self.assertEqual(put_result[0][0], settings.REPORT_PATH)
        report_data = put_result[0][1].read()
        if False:
            with open('report.html', 'wb') as f:
                f.write(report_data)
        self.assertRegexpMatches(report_data, 'latest')
        self.assertRegexpMatches(report_data, 'uncontrolled')

    @attr('unit', 'light')
    def test_do_not_make_report_if_no_change(self):
        import hashlib
        from google.appengine.api import memcache
        from netprintbox.data import FileState
        from netprintbox.utils import (
            normalize_name, get_namespace)

        NETPRINT_ID = 'latest'
        ORIGINAL_PATH = '/latest.data'
        NETPRINT_NAME = normalize_name(ORIGINAL_PATH)

        user = create_user()
        create_file_info(user,
                         path=ORIGINAL_PATH,
                         netprint_id=NETPRINT_ID,
                         netprint_name=NETPRINT_NAME,
                         state=FileState.LATEST)

        class netprint(object):
            @staticmethod
            def list():
                return [
                        create_netprint_item(
                            id=NETPRINT_ID,
                            name=NETPRINT_NAME)
                       ]

        md5 = hashlib.new('md5')
        md5.update(NETPRINT_ID)
        memcache.set(str(user.key()), md5.hexdigest(),
                     namespace=get_namespace())

        service = self._getOUT(user.key())
        service.netprint = netprint

        (need_report, _result) = service._make_report()
        self.assertFalse(need_report)

        # check no exception is occurred.
        service.make_report()

        from netprintbox.service import DropboxService

        class request(object):
            host = 'foobar'
        return DropboxService(user, request)


class DropboxServiceObtainTest(ServiceTestBase):
    def _getOUT(self, user):
        from netprintbox.service import DropboxService
        return DropboxService(user)

    @attr('unit', 'light')
    def test_it(self):
        class client(object):
            @staticmethod
            def metadata(path):
                return {'is_dir': False, 'bytes': 3}

            @staticmethod
            def get_file(path):
                return StringIO('foo')

        user = create_user()
        service = self._getOUT(user)
        service.client = client
        file_obj = service.obtain('fake_path')
        self.assertEqual(file_obj.name, 'fake_path')
        self.assertEqual(file_obj.read(), 'foo')


class DropboxServiceObtainLimitTest(ServiceTestBase):
    def _getOUT(self, user):
        from netprintbox.service import DropboxService
        return DropboxService(user)

    @attr('unit', 'light')
    def test_it(self):
        from netprintbox.exceptions import OverLimit

        class client(object):
            @staticmethod
            def metadata(path):
                return {'is_dir': False, 'bytes': 3}

            @staticmethod
            def get_file(path):
                return StringIO('foo')

        user = create_user()
        service = self._getOUT(user)
        service.client = client
        with self.assertRaises(OverLimit):
            service.obtain('fake_path', limit=2)


class DropboxServiceBuildURLTest(ServiceTestBase):
    url = 'fake_url'

    def setUp(self):
        super(DropboxServiceBuildURLTest, self).setUp()

        class request_token(object):
            key = 'key'

            def __str__(self):
                return 'token'

        class session(object):
            @staticmethod
            def obtain_request_token():
                return request_token()

            @staticmethod
            def build_authorize_url(request_token, url):
                return self.url

        import dropbox.session
        mock('dropbox.session.DropboxSession', returns=session)

    def _getOUT(self):
        from netprintbox.service import DropboxService
        return DropboxService

    @attr('unit', 'light')
    def test_it(self):
        service = self._getOUT()
        url = service.build_authorize_url('callback_url')
        self.assertEqual(url, self.url)


class DropboxServiceSetupTest(ServiceTestBase):
    uid = 'uid'
    key = 'key'

    def setUp(self):
        from netprintbox.data import OAuthRequestToken

        super(DropboxServiceSetupTest, self).setUp()

        token = 'oauth_token=token&oauth_token_secret=secret'
        token = OAuthRequestToken(key=self.key, token=token)
        token.put()

        class client(object):
            @staticmethod
            def account_info():
                return {'uid': self.uid,
                        'email': 'email',
                        'display_name': 'display_name',
                        }

        class session(object):
            @staticmethod
            def obtain_access_token(request_token):
                pass

            class token(object):
                key = 'access_key'
                secret = 'access_secret'

        import dropbox.client
        import dropbox.session
        mock('dropbox.client.DropboxClient', returns=client)
        mock('dropbox.session.DropboxSession', returns=session)

    def _getOUT(self):
        from netprintbox.service import DropboxService
        return DropboxService

    @attr('unit', 'light')
    def test_new_user(self):
        from netprintbox.data import DropboxUser

        service = self._getOUT()
        service.setup_user(self.key)

        q = DropboxUser.all()
        self.assertEqual(q.count(), 1)
        user = q.get()
        self.assertEqual(user.uid, self.uid)
        self.assertEqual(user.access_key, 'access_key')
        self.assertEqual(user.access_secret, 'access_secret')

    @attr('unit', 'light')
    def test_existing_user(self):
        from netprintbox.data import DropboxUser

        user = create_user()
        user.pending = True
        user.put()

        service = self._getOUT()
        service.setup_user(self.key)

        q = DropboxUser.all()
        self.assertEqual(q.count(), 1)
        queried_user = q.get()
        self.assertEqual(user.uid, queried_user.uid)
        self.assertFalse(queried_user.pending)


class DropboxServicePendingNotificationTest(ServiceTestBase):
    def setUp(self):
        from google.appengine.ext import testbed

        super(DropboxServicePendingNotificationTest, self).setUp()
        self.testbed.init_mail_stub()
        self.mail_stub = self.testbed.get_stub(testbed.MAIL_SERVICE_NAME)

    def _getOUT(self, user):
        from netprintbox.service import DropboxService

        class request(object):
            host = 'foobar'
        return DropboxService(user, request)

    def _test_session_error(self, method_name, *args):
        from dropbox.rest import ErrorResponse
        from netprintbox.exceptions import BecomePendingUser
        import settings

        class FakeClient(object):
            def __getattr__(self, name):
                class http_resp(object):
                    status = 401
                    reason = 'Unauthorized'

                    @staticmethod
                    def read():
                        return ''
                raise ErrorResponse(http_resp)

        user = create_user()
        service = self._getOUT(user)
        service.client = FakeClient()
        try:
            self.assertFalse(user.pending)
            getattr(service, method_name)(*args)
            self.fail("Don't become pending")
        except BecomePendingUser:
            self.assertTrue(user.pending)
            sent_messages = self.mail_stub.get_sent_messages(to=user.email)
            self.assertEqual(len(sent_messages), 1)
            message = sent_messages[0]
            message_body = str(message.body)
            self.assertIn('http://foobar/dropbox/authorize', message_body)
            self.assertIn(settings.SYSADMIN_ADDRESS, message.sender)

    @attr('unit', 'light')
    def test_list(self):
        self._test_session_error('list', '/')

    @attr('unit', 'light')
    def test_obtain(self):
        self._test_session_error('obtain', '/')

    @attr('unit', 'light')
    def test_put(self):
        self._test_session_error('put', '/', None)

    @attr('unit', 'light')
    def test_delete(self):
        self._test_session_error('delete', '/')


class DropboxServiceRecognizeErrorResponse(ServiceTestBase):
    def setUp(self):
        from google.appengine.ext import testbed

        super(DropboxServiceRecognizeErrorResponse, self).setUp()
        self.testbed.init_mail_stub()
        self.mail_stub = self.testbed.get_stub(testbed.MAIL_SERVICE_NAME)

    def _getOUT(self, user):
        from netprintbox.service import DropboxService

        class request(object):
            host = 'foobar'
        return DropboxService(user, request)

    def _test_metadata(self, expected_exception, status, reason,
                       how_many_messages=0):
        from dropbox.rest import ErrorResponse

        class client(object):

            def __init__(self, status, reason):
                self.status = status
                self.reason = reason

            def metadata(self, path):
                class http_resp(object):
                    status = self.status
                    reason = self.reason

                    @staticmethod
                    def read():
                        return ''
                raise ErrorResponse(http_resp)

        user = create_user()
        service = self._getOUT(user)
        service.client = client(status, reason)
        with self.assertRaises(expected_exception):
            service.list('/')
        sent_messages = self.mail_stub.get_sent_messages(to=user.email)
        self.assertEqual(len(sent_messages), how_many_messages)

    @attr('unit', 'light')
    def test_bad_request(self):
        from netprintbox.exceptions import DropboxBadRequest
        self._test_metadata(DropboxBadRequest, 400, 'Bad request')

    @attr('unit', 'light')
    def test_unauthorized(self):
        from netprintbox.exceptions import BecomePendingUser
        self._test_metadata(BecomePendingUser, 401, 'Unauthorized',
                            how_many_messages=1)

    @attr('unit', 'light')
    def test_forbidden(self):
        from netprintbox.exceptions import DropboxForbidden
        self._test_metadata(DropboxForbidden, 403, 'Forbidden')

    @attr('unit', 'light')
    def test_not_found(self):
        from netprintbox.exceptions import DropboxNotFound
        self._test_metadata(DropboxNotFound, 404, 'Not found')

    @attr('unit', 'light')
    def test_method_not_allowed(self):
        from netprintbox.exceptions import DropboxMethodNotAllowed
        self._test_metadata(DropboxMethodNotAllowed, 405,
                            'Method not allowed')

    @attr('unit', 'light')
    def test_service_unavailable(self):
        from netprintbox.exceptions import DropboxServiceUnavailable
        self._test_metadata(DropboxServiceUnavailable, 503,
                            'Service unavailable')

    @attr('unit', 'light')
    def test_insufficient_storage(self):
        from netprintbox.exceptions import DropboxInsufficientStorage
        self._test_metadata(DropboxInsufficientStorage, 507,
                            'Insufficient storage')
