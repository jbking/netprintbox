from StringIO import StringIO
from unittest import TestCase
from nose.plugins.attrib import attr

from test_utils import create_user, create_file_info


class TransactionTestBase(TestCase):
    def setUp(self):
        from google.appengine.ext.testbed import Testbed

        self.testbed = Testbed()
        self.testbed.activate()
        self.testbed.init_datastore_v3_stub()

    def tearDown(self):
        self.testbed.deactivate()

    def _getOUT(self, dropbox_user):
        from netprintbox.transaction import SyncTransaction

        return SyncTransaction(dropbox_user)


class SyncFeatureTest(TransactionTestBase):
    @attr('unit', 'light')
    def test_new_file(self):
        user = create_user()
        transaction = self._getOUT(user)

        class dropbox_client(object):
            @staticmethod
            def get_file(*args):
                f = StringIO('test')
                f.length = len('test')
                return f

        put_commands = []

        class netprint_client(object):
            @staticmethod
            def send(file_obj):
                put_commands.append(file_obj)

        transaction.sync(dropbox_client, netprint_client,
                         dict(path='path', bytes=0, rev='rev'), None)

        q = user.own_files()
        self.assertEqual(q.count(), 1)
        file_info = q.get()
        self.assertEqual(file_info.path, 'path')
        self.assertEqual(file_info.rev, 'rev')
        self.assertEqual(len(put_commands), 1)
        self.assertEqual(put_commands[0].read(), 'test')

    @attr('unit', 'light')
    def test_transaction_isolation(self):
        user1 = create_user()
        user2 = create_user()
        transaction1 = self._getOUT(user1)
        transaction2 = self._getOUT(user2)

        class dropbox_client(object):
            @staticmethod
            def get_file(*args):
                f = StringIO('test')
                f.length = len('test')
                return f

        class netprint_client(object):
            @staticmethod
            def send(file_obj):
                pass

        transaction1.sync(dropbox_client, netprint_client,
                          dict(path='path', bytes=0, rev='rev'), None)
        self.assertEqual(user1.own_files().count(), 1)
        self.assertEqual(user2.own_files().count(), 0)

        transaction2.sync(dropbox_client, netprint_client,
                          dict(path='path', bytes=0, rev='rev'), None)
        self.assertEqual(user1.own_files().count(), 1)
        self.assertEqual(user2.own_files().count(), 1)

    @attr('unit', 'light')
    def test_modified_file_netprint_has_old_one(self):
        user = create_user()
        transaction = self._getOUT(user)

        class dropbox_client(object):
            @staticmethod
            def get_file(*args):
                f = StringIO('test')
                f.length = len('test')
                return f

        put_commands = []

        class netprint_client(object):
            @staticmethod
            def send(file_obj):
                put_commands.append(file_obj)

        file_info = create_file_info(user, rev='prev')

        transaction.sync(dropbox_client, netprint_client,
                         dict(path=file_info.path, bytes=4, rev='rev'),
                         dict(id=file_info.netprint_id,
                              name=file_info.netprint_name))

        q = user.own_files()
        self.assertEqual(q.count(), 1)
        latest_file_info = q.get()
        self.assertEqual(latest_file_info.path, file_info.path)
        self.assertEqual(latest_file_info.size, 4)
        self.assertEqual(latest_file_info.rev, 'rev')
        self.assertEqual(len(put_commands), 1)
        self.assertEqual(put_commands[0].read(), 'test')

    @attr('unit', 'light')
    def test_modified_file_netprint_has_not_old_one(self):
        user = create_user()
        transaction = self._getOUT(user)

        class dropbox_client(object):
            @staticmethod
            def get_file(*args):
                f = StringIO('test')
                f.length = len('test')
                return f

        put_commands = []

        class netprint_client(object):
            @staticmethod
            def send(file_obj):
                put_commands.append(file_obj)

        file_info = create_file_info(user, rev='prev')

        transaction.sync(dropbox_client, netprint_client,
                         dict(path=file_info.path, bytes=4, rev='rev'), None)

        q = user.own_files()
        self.assertEqual(q.count(), 1)
        latest_file_info = q.get()
        self.assertEqual(latest_file_info.path, file_info.path)
        self.assertEqual(latest_file_info.size, 4)
        self.assertEqual(latest_file_info.rev, 'rev')
        self.assertEqual(len(put_commands), 1)
        self.assertEqual(put_commands[0].read(), 'test')

    @attr('unit', 'light')
    def test_expired_file(self):
        user = create_user()
        transaction = self._getOUT(user)

        deleted = []

        class dropbox_client(object):
            @staticmethod
            def file_delete(path):
                deleted.append(path)

        class netprint_client(object):
            pass

        file_info = create_file_info(user, netprint_id='netprint_id')

        # when a file was removed on netprint,
        # remove data and the file on dropbox if exists.
        transaction.sync(dropbox_client, netprint_client,
                         dict(path=file_info.path, bytes=3, rev='rev'), None)

        q = user.own_files()
        self.assertEqual(q.count(), 0)
        self.assertListEqual(deleted, [file_info.path])

    @attr('unit', 'light')
    def test_do_not_sync_generated_file(self):
        import settings

        user = create_user()
        transaction = self._getOUT(user)

        class dropbox_client(object):
            pass

        class netprint_client(object):
            pass

        for ignore_path in (settings.ACCOUNT_INFO_PATH, settings.REPORT_PATH):
            transaction.sync(dropbox_client, netprint_client,
                             dict(path=ignore_path, bytes=0, rev='rev'), None)
        q = user.own_files()
        self.assertEqual(q.count(), 0)

    @attr('unit', 'light')
    def test_netprint_has_original_file(self):
        user = create_user()
        transaction = self._getOUT(user)

        class dropbox_client(object):
            pass

        class netprint_client(object):
            pass

        # don't affect anything when only netprint has a file.
        # its out of scope.
        transaction.sync(dropbox_client, netprint_client,
                         None, dict(id='original_id', name='same_name'))

        q = user.own_files()
        self.assertEqual(q.count(), 0)

    @attr('unit', 'light')
    def test_dropbox_cause_an_error(self):
        user = create_user()
        transaction = self._getOUT(user)

        class DropboxError(Exception):
            pass

        class dropbox_client(object):
            @staticmethod
            def get_file(path):
                raise DropboxError

        class netprint_client(object):
            pass

        # transaction check for dropbox reason.
        self.assertRaises(DropboxError,
                          transaction.sync,
                          dropbox_client, netprint_client,
                          dict(path='path', bytes=0, rev='rev'), None)

        q = user.own_files()
        self.assertEqual(q.count(), 0)

    @attr('unit', 'light')
    def test_netprint_cause_an_error(self):
        user = create_user()
        transaction = self._getOUT(user)

        class dropbox_client(object):
            @staticmethod
            def get_file(path):
                f = StringIO('test')
                f.length = len('test')
                return f

        class NetprintError(Exception):
            pass

        class netprint_client(object):
            @staticmethod
            def send(file_obj):
                raise NetprintError

        # transaction check for netprint reason.
        self.assertRaises(NetprintError,
                          transaction.sync,
                          dropbox_client, netprint_client,
                          dict(path='path', bytes=0, rev='rev'), None)

        q = user.own_files()
        self.assertEqual(q.count(), 0)


class ObtainingLimitTest(TransactionTestBase):
    @attr('unit', 'light')
    def test_under_limit(self):
        DATA = 'a' * (2 * 1024 * 1024)

        user = create_user()
        transaction = self._getOUT(user)

        class dropbox_client(object):
            @staticmethod
            def get_file(path):
                f = StringIO(DATA)
                f.length = len(DATA)
                return f

        sent = []

        class netprintbox_client(object):
            @staticmethod
            def send(file_obj):
                sent.append(file_obj)

        transaction.sync(dropbox_client, netprintbox_client,
                         dict(path='/under_limit.dat', bytes=len(DATA),
                              rev='rev'),
                         None)

        self.assertEqual(len(sent), 1)
        f = sent[0]
        f.seek(0)
        self.assertEqual(f.read(), DATA)

    @attr('unit', 'light')
    def test_under_limit_for_jpeg(self):
        DATA = 'b' * (4 * 1024 * 1024)

        user = create_user()
        transaction = self._getOUT(user)

        class dropbox_client(object):
            @staticmethod
            def get_file(path):
                f = StringIO(DATA)
                f.length = len(DATA)
                return f

        sent = []

        class netprintbox_client(object):
            @staticmethod
            def send(file_obj):
                sent.append(file_obj)

        transaction.sync(dropbox_client, netprintbox_client,
                         dict(path='/under_limit.jpg', bytes=len(DATA),
                              rev='rev'),
                         None)

        self.assertEqual(len(sent), 1)
        f = sent[0]
        f.seek(0)
        self.assertEqual(f.read(), DATA)

    @attr('unit', 'light')
    def test_over_limit(self):
        from netprintbox.exceptions import OverLimit

        DATA = 'a' * (2 * 1024 * 1024 + 1)

        user = create_user()
        transaction = self._getOUT(user)

        class dropbox_client(object):
            @staticmethod
            def get_file(path):
                f = StringIO(DATA)
                f.length = len(DATA)
                return f

        sent = []

        class netprintbox_client(object):
            @staticmethod
            def send(file_obj):
                sent.append(file_obj)

        self.assertRaises(OverLimit, transaction.sync,
                          dropbox_client, netprintbox_client,
                          dict(path='/over_limit.dat', bytes=len(DATA),
                               rev='rev'),
                          None)
        self.assertEqual(len(sent), 0)
