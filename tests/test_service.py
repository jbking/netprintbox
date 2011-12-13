from unittest import TestCase
from nose.plugins.attrib import attr

from test_utils import create_user, create_file_info, create_netprint_item


class ServiceTestBase(TestCase):
    def setUp(self):
        from google.appengine.ext.testbed import Testbed

        self.testbed = Testbed()
        self.testbed.activate()
        self.testbed.init_datastore_v3_stub()
        self.testbed.init_memcache_stub()

    def tearDown(self):
        self.testbed.deactivate()


class NetprintboxServiceTest(ServiceTestBase):
    def _getOUT(self, user):
        from netprintbox.service import NetprintboxService
        return NetprintboxService(user)

    @attr('unit', 'light')
    def test_construct_data_to_make_report(self):
        from netprintbox.data import FileState
        from netprintbox.utils import normalize_name as normalize

        user = create_user()
        create_file_info(user,
                         path='/need_netprint_id.data',
                         netprint_name=normalize('/need_netprint_id.data'),
                         state=FileState.NEED_NETPRINT_ID)
        create_file_info(user,
                         path='/latest.data',
                         netprint_id='latest',
                         netprint_name=normalize('/latest.data'),
                         state=FileState.LATEST)

        class netprint(object):
            @staticmethod
            def list():
                return [
                        create_netprint_item(
                            id='need_xxxx',
                            name=normalize('/need_netprint_id.data')),
                        create_netprint_item(
                            id='uncontrolled',
                            name='uncontrolled.jpg'),
                        create_netprint_item(
                            id='latest',
                            name=normalize('/latest.data')),
                       ]

        service = self._getOUT(user)
        service.netprint = netprint

        (need_report, result) = service._make_report()
        self.assertTrue(need_report)
        self.assertItemsEqual(
            [(item['id'], item['name'], item['controlled'])
             for item in result],
            [('need_xxxx', normalize('/need_netprint_id.data'), True),
             ('uncontrolled', 'uncontrolled.jpg', False),
             ('latest', normalize('/latest.data'), True),
            ])

    @attr('unit', 'light')
    def test_do_not_make_report_if_no_change(self):
        import hashlib
        from google.appengine.api import memcache
        from netprintbox.data import FileState
        from netprintbox.utils import normalize_name as normalize

        NETPRINT_ID = 'latest'
        ORIGINAL_PATH = '/latest.data'
        NETPRINT_NAME = normalize(ORIGINAL_PATH)

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
        memcache.set(str(user.key()), md5.hexdigest())

        service = self._getOUT(user.key())
        service.netprint = netprint

        (need_report, _result) = service._make_report()
        self.assertFalse(need_report)


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
