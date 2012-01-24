# -*- encoding: utf-8 -*-
from utils import TestBase
from nose.plugins.attrib import attr

from utils import (create_user,
        create_file_info, create_dropbox_item, create_netprint_item)


class TransactionTestBase(TestBase):
    def setUp(self):
        super(TransactionTestBase, self).setUp()
        self.testbed.init_datastore_v3_stub()

    def _getOUT(self, context):
        from netprintbox.transaction import SyncTransaction

        return SyncTransaction(context)


class DropboxTest(TransactionTestBase):
    def _getOUT(self, context):
        from netprintbox.transaction import DropboxTransaction
        return DropboxTransaction(context)

    @attr('unit', 'light')
    def test_it(self):
        from netprintbox.data import FileState

        class Context(object):
            user = None
            dropbox = None

        class Dropbox(object):
            def __init__(self):
                self.deleted = []

            def list(self, path):
                if path == '/':
                    return {
                        'is_dir': True,
                        'contents': [
                            create_dropbox_item(path='/path1', rev='rev1'),
                            create_dropbox_item(path='/path2', rev='rev2'),
                            create_dropbox_item(path='/path3', rev='rev3-new'),
                        ]}
                else:
                    raise AssertionError("Unexpected %s" % path)

            def delete(self, path):
                self.deleted.append(path)

        context = Context()
        context.user = create_user()
        context.dropbox = Dropbox()

        create_file_info(context.user, path='/path2', rev='rev2')
        create_file_info(context.user, path='/path3', rev='rev3',
                         state=FileState.DELETED)
        create_file_info(context.user, path='/path4', rev='rev4')
        create_file_info(context.user, path='/path5', rev='rev5',
                         state=FileState.DELETED)

        transaction = self._getOUT(context)
        transaction.run()

        self.assertIsNotNone(context.user.own_file('/path1'), 'new file')
        self.assertIsNotNone(context.user.own_file('/path2'), 'no change file')
        f3 = context.user.own_file('/path3')
        self.assertEqual(f3.rev, 'rev3-new', 'updated file')
        self.assertEqual(f3.state, FileState.NEED_NETPRINT_ID)
        self.assertIsNone(context.user.own_file('/path4'),
                          'deleted file on dropbox')
        self.assertIsNone(context.user.own_file('/path5'),
                          'deleted file on site')
        self.assertItemsEqual(context.dropbox.deleted, ['/path5'],
                          'deleted file on site')


class NetprintTest(TransactionTestBase):
    def _getOUT(self, context):
        from netprintbox.transaction import NetprintTransaction
        return NetprintTransaction(context)

    @attr('unit', 'light')
    def test_it(self):
        from netprintbox.data import FileState

        class Context(object):
            user = None
            netprint = None

        class netprint(object):
            @staticmethod
            def list():
                return [
                        create_netprint_item(id='id1', name='name1'),
                        create_netprint_item(id='id2', name='name2'),
                        create_netprint_item(id='id3', name='name3'),
                    ]

        context = Context()
        context.user = create_user()
        context.netprint = netprint

        create_file_info(context.user, path='/name2',
                         state=FileState.NEED_NETPRINT_ID)
        create_file_info(context.user, netprint_id='id3', path='/name3',
                         state=FileState.LATEST)
        create_file_info(context.user, path='/name4',
                         state=FileState.NEED_NETPRINT_ID)
        create_file_info(context.user, path='/name5',
                         state=FileState.LATEST)

        transaction = self._getOUT(context)
        transaction.run()

        self.assertIsNone(context.user.own_file('/name1'),
                          'netprint only file')
        f2 = context.user.own_file('/name2')
        self.assertIsNotNone(f2, 'id assigned file')
        self.assertEqual(f2.state, FileState.LATEST)
        self.assertEqual(f2.netprint_id, 'id2')
        f3 = context.user.own_file('/name3')
        self.assertIsNotNone(f3, 'no changed')
        self.assertEqual(f3.state, FileState.LATEST)
        self.assertEqual(f3.netprint_id, 'id3')
        f4 = context.user.own_file('/name4')
        self.assertIsNotNone(f4, 'updated')
        self.assertEqual(f4.state, FileState.LATEST)
        self.assertEqual(f4.netprint_id, 'id4')
        self.assertIsNone(context.user.own_file('/name5'), 'deleted file')


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
        transaction._dropbox_only(create_dropbox_item(path='path',
                                                      bytes=3, rev='rev'))

        q = context.user.own_files()
        self.assertEqual(q.count(), 1)
        file_info = q.get()
        self.assertEqual(file_info.path, 'path')
        self.assertEqual(file_info.size, 3)
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

        transaction1._dropbox_only(create_dropbox_item())
        self.assertEqual(context1.user.own_files().count(), 1)
        self.assertEqual(context2.user.own_files().count(), 0)

        transaction2._dropbox_only(create_dropbox_item())
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

        file_info = create_file_info(context.user, rev='prev',
                                     netprint_id='aaa')

        transaction._both(create_dropbox_item(path=file_info.path,
                                              bytes=4, rev='rev'),
                          dict(id=file_info.netprint_id,
                               name=file_info.as_netprint_name()))

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

        transaction._dropbox_only(create_dropbox_item(path=file_info.path,
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
    def test_pinned_file(self):
        from netprintbox.data import FileState

        commands = []

        class context(object):
            user = create_user()

            @staticmethod
            def transfer_from_dropbox(path, limit=None):
                commands.append((path, limit))

        transaction = self._getOUT(context)
        file_info = create_file_info(context.user, pin=True)

        transaction._dropbox_only(create_dropbox_item(path=file_info.path,
                                                      rev=file_info.rev))

        q = context.user.own_files()
        self.assertEqual(q.count(), 1)
        latest_file_info = q.get()
        self.assertEqual(latest_file_info.path, file_info.path)
        self.assertEqual(latest_file_info.rev, file_info.rev)
        self.assertIsNone(latest_file_info.netprint_id)
        self.assertEqual(latest_file_info.state,
                         FileState.NEED_NETPRINT_ID)
        self.assertEqual(len(commands), 1)
        self.assertEqual(commands[0][0], file_info.path)

    @attr('unit', 'light')
    def test_expired_file(self):
        from netprintbox.data import FileState

        deleted = []

        class context(object):
            user = create_user()

            @staticmethod
            def delete_from_dropbox(path):
                deleted.append(path)

        transaction = self._getOUT(context)

        file_info = create_file_info(context.user,
                                     state=FileState.LATEST,
                                     netprint_id='netprint_id')

        # when a file was removed on netprint,
        # remove data and the file on dropbox if exists.
        transaction._dropbox_only(create_dropbox_item(path=file_info.path))

        q = context.user.own_files()
        self.assertEqual(q.count(), 0)
        self.assertListEqual(deleted, [file_info.path])

    @attr('unit', 'light')
    def test_deleted_file(self):
        item_list = []

        class context(object):
            user = create_user()

            class netprint(object):
                @staticmethod
                def list():
                    return []

            class dropbox(object):
                @staticmethod
                def list(path):
                    return {'is_dir': True,
                            'path': '/',
                            'contents': [
                                {'is_dir': True,
                                 'path': '/A4',
                                 'contents': item_list,
                                 },
                                ]}

        transaction = self._getOUT(context)

        file_info = create_file_info(context.user,
                                     path='/A4/foo.doc',
                                     netprint_id='netprint_id')
        item_list.append(create_dropbox_item(path=file_info.path,
                                             is_deleted=True))

        transaction.sync()

        q = context.user.own_files()
        self.assertEqual(q.count(), 0)

    @attr('unit', 'light')
    def test_do_not_sync_generated_file(self):
        from netprintbox.settings import ACCOUNT_INFO_PATH, REPORT_PATH

        class context(object):
            user = create_user()

        transaction = self._getOUT(context)

        for ignore_path in (ACCOUNT_INFO_PATH, REPORT_PATH):
            transaction._dropbox_only(create_dropbox_item(path=ignore_path))
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
                                        name=u'オリジナル名'))

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
                          create_dropbox_item())

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

    @attr('unit', 'light')
    def test_handle_unsupport_exception_on_each_item(self):
        """
        An unsupported file is put on netprintbox directory,
        it appears on dropbox's metadata.
        On such situation, the file is never transferred from dropbox.
        And the transaction is never failed by that.
        """
        from netprintbox.exceptions import UnsupportedFile

        result = []

        class context(object):
            user = create_user()

            @staticmethod
            def transfer_from_dropbox(path, limit=None):
                result.append(path)
                raise UnsupportedFile(path)

        transaction = self._getOUT(context)
        transaction._dropbox_only(create_dropbox_item(path='path'))

        self.assertEqual(result, ['path'])
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
                          create_dropbox_item(bytes=1))
