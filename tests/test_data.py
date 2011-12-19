from unittest import TestCase

from nose.plugins.attrib import attr

from webapp2 import uri_for
from test_utils import (
        create_user, create_file_info,
        get_blank_request, set_request_local)


class DropboxUserTest(TestCase):
    def setUp(self):
        from google.appengine.ext.testbed import Testbed, MAIL_SERVICE_NAME

        self.testbed = Testbed()
        self.testbed.activate()
        self.testbed.init_datastore_v3_stub()
        self.testbed.init_mail_stub()
        self.mail_stub = self.testbed.get_stub(MAIL_SERVICE_NAME)

    def tearDown(self):
        self.testbed.deactivate()

    def _getOUT(self):
        return create_user()

    @attr('unit', 'light')
    def test_own_files(self):
        user = self._getOUT()
        create_file_info(user)
        create_file_info(user)
        create_file_info(user)
        self.assertEqual(user.own_files().count(), 3)

    @attr('unit', 'light')
    def test_put_pending(self):
        from netprintbox.exceptions import BecomePendingUser

        user = self._getOUT()
        with self.assertRaises(BecomePendingUser):
            set_request_local()
            user.put_pending()
            self.assertTrue(user.is_pending)
        sent_messages = self.mail_stub.get_sent_messages(to=user.email)
        self.assertEqual(len(sent_messages), 1)
        message = sent_messages[0]

        request = get_blank_request()
        self.assertIn(uri_for('authorize', _request=request, _full=True),
                      str(message.body))

    @attr('unit', 'light')
    def test_put_pending_without_notification(self):
        from netprintbox.exceptions import BecomePendingUser

        user = self._getOUT()
        with self.assertRaises(BecomePendingUser):
            user.put_pending(notify=False)
            self.assertTrue(user.is_pending)
        sent_messages = self.mail_stub.get_sent_messages(to=user.email)
        self.assertEqual(len(sent_messages), 0)

    @attr('unit', 'light')
    def test_put_pending_away(self):
        from netprintbox.exceptions import BecomePendingUser

        user = self._getOUT()
        with self.assertRaises(BecomePendingUser):
            user.put_pending(notify=False)
            self.assertTrue(user.is_pending)

        user.put_pending_away()
        self.assertFalse(user.is_pending)
