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

    def _getOUT(self, context):
        from netprintbox.transaction import SyncTransaction

        return SyncTransaction(context)


class SyncFeatureTest(TransactionTestBase):
    @attr('unit', 'light')
    def test_new_file(self):
        from netprintbox.data import FileState

        commands = []

        class context(object):
            user = create_user()

            @staticmethod
            def transfer_from_dropbox(path, limit=None):
                commands.append((path, limit))

        transaction = self._getOUT(context)
        transaction._dropbox_only(dict(path='path', bytes=0, rev='rev'))

        q = context.user.own_files()
        self.assertEqual(q.count(), 1)
        file_info = q.get()
        self.assertEqual(file_info.path, 'path')
        self.assertEqual(file_info.rev, 'rev')
        self.assertIsNone(file_info.netprint_id)
        self.assertEqual(file_info.state,
                         FileState.NEED_NETPRINT_ID)
        self.assertEqual(len(commands), 1)
        self.assertEqual(commands[0][0], 'path')

    @attr('unit', 'light')
    def test_transaction_isolation(self):
        class context1(object):
            user = create_user()

            @staticmethod
            def transfer_from_dropbox(path, limit=None):
                pass

        class context2(object):
            user = create_user()

            @staticmethod
            def transfer_from_dropbox(path, limit=None):
                pass

        transaction1 = self._getOUT(context1)
        transaction2 = self._getOUT(context2)

        transaction1._dropbox_only(dict(path='path', bytes=0, rev='rev'))
        self.assertEqual(context1.user.own_files().count(), 1)
        self.assertEqual(context2.user.own_files().count(), 0)

        transaction2._dropbox_only(dict(path='path', bytes=0, rev='rev'))
        self.assertEqual(context1.user.own_files().count(), 1)
        self.assertEqual(context2.user.own_files().count(), 1)

    @attr('unit', 'light')
    def test_modified_file_netprint_has_old_one(self):
        from netprintbox.data import FileState

        commands = []

        class context(object):
            user = create_user()

            @staticmethod
            def delete_from_netprint(netprint_id):
                commands.append((netprint_id,))

            @staticmethod
            def transfer_from_dropbox(path, limit=None):
                commands.append((path, limit))

        transaction = self._getOUT(context)

        file_info = create_file_info(context.user, rev='prev')

        transaction._both(dict(path=file_info.path, bytes=4, rev='rev'),
                          dict(id=file_info.netprint_id,
                               name=file_info.netprint_name))

        q = context.user.own_files()
        self.assertEqual(q.count(), 1)
        latest_file_info = q.get()
        self.assertEqual(latest_file_info.path, file_info.path)
        self.assertEqual(latest_file_info.size, 4)
        self.assertEqual(latest_file_info.rev, 'rev')
        self.assertIsNone(latest_file_info.netprint_id)
        self.assertEqual(latest_file_info.state,
                         FileState.NEED_NETPRINT_ID)
        self.assertEqual(len(commands), 2)
        self.assertEqual(commands[0][0], file_info.netprint_id)
        self.assertEqual(commands[1][0], file_info.path)

    @attr('unit', 'light')
    def test_modified_file_netprint_has_no_file(self):
        from netprintbox.data import FileState

        commands = []

        class context(object):
            user = create_user()

            @staticmethod
            def transfer_from_dropbox(path, limit=None):
                commands.append((path, limit))

        transaction = self._getOUT(context)
        file_info = create_file_info(context.user, rev='prev')

        transaction._dropbox_only(dict(path=file_info.path,
                                       bytes=4, rev='rev'))

        q = context.user.own_files()
        self.assertEqual(q.count(), 1)
        latest_file_info = q.get()
        self.assertEqual(latest_file_info.path, file_info.path)
        self.assertEqual(latest_file_info.size, 4)
        self.assertEqual(latest_file_info.rev, 'rev')
        self.assertIsNone(latest_file_info.netprint_id)
        self.assertEqual(latest_file_info.state,
                         FileState.NEED_NETPRINT_ID)
        self.assertEqual(len(commands), 1)
        self.assertEqual(commands[0][0], file_info.path)

    @attr('unit', 'light')
    def test_expired_file(self):
        deleted = []

        class context(object):
            user = create_user()

            @staticmethod
            def delete_from_dropbox(path):
                deleted.append(path)

        transaction = self._getOUT(context)

        file_info = create_file_info(context.user, netprint_id='netprint_id')

        # when a file was removed on netprint,
        # remove data and the file on dropbox if exists.
        transaction._dropbox_only(dict(path=file_info.path,
                                       bytes=3, rev='rev'))

        q = context.user.own_files()
        self.assertEqual(q.count(), 0)
        self.assertListEqual(deleted, [file_info.path])

    @attr('unit', 'light')
    def test_do_not_sync_generated_file(self):
        import settings

        class context(object):
            user = create_user()

        transaction = self._getOUT(context)

        for ignore_path in (settings.ACCOUNT_INFO_PATH,
                            settings.REPORT_PATH):
            transaction._dropbox_only(dict(path=ignore_path,
                                           bytes=0, rev='rev'))
        q = context.user.own_files()
        self.assertEqual(q.count(), 0)

    @attr('unit', 'light')
    def test_netprint_has_original_file(self):
        class context(object):
            user = create_user()

        transaction = self._getOUT(context)

        # don't affect anything when only netprint has a file.
        # its out of scope.
        transaction._netprint_only(dict(id='original_id',
                                        name='original_name'))

        q = context.user.own_files()
        self.assertEqual(q.count(), 0)

    @attr('unit', 'light')
    def test_causing_an_error(self):
        class TransferError(Exception):
            pass

        class context(object):
            user = create_user()

            @staticmethod
            def transfer_from_dropbox(path, limit=None):
                raise TransferError

        transaction = self._getOUT(context)

        # transaction check for netprint reason.
        self.assertRaises(TransferError,
                          transaction._dropbox_only,
                          dict(path='path', bytes=0, rev='rev'))

        q = context.user.own_files()
        self.assertEqual(q.count(), 0)

    @attr('unit', 'light')
    def test_file_data_only_neither_netprint_or_dropbox(self):
        class context(object):
            user = create_user()

            class dropbox(object):
                @staticmethod
                def list(path):
                    return {'is_dir': True,
                            'contents': []}

            class netprint(object):
                @staticmethod
                def list():
                    return {}

        create_file_info(context.user)

        transaction = self._getOUT(context)
        transaction.sync()

        self.assertEqual(list(context.user.own_files()), [])

class ObtainingLimitTest(TransactionTestBase):
    @attr('unit', 'light')
    def test_over_limit_for_account(self):
        from netprintbox.exceptions import OverLimit

        class context(object):
            user = create_user()

        for _ in range(5):
            create_file_info(context.user, size=(2 * 1024 * 1024))
        transaction = self._getOUT(context)

        self.assertRaises(OverLimit, transaction._dropbox_only,
                          dict(path='/over_limit.dat',
                               bytes=1, rev='rev'))
