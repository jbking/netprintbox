# -*- encoding: utf-8 -*-
from utils import TestBase
from nose.plugins.attrib import attr

from utils import (create_user,
        create_file_info, create_dropbox_item, create_netprint_item)


class TransactionTestBase(TestBase):
    def setUp(self):
        super(TransactionTestBase, self).setUp()
        self.testbed.init_datastore_v3_stub()


class DropboxTestBase(TransactionTestBase):
    def _getOUT(self, context):
        from netprintbox.transaction import DropboxTransaction

        return DropboxTransaction(context)


class DropboxTest(DropboxTestBase):
    @attr('unit', 'light')
    def test_it(self):
        from netprintbox.data import FileState

        class context(object):
            user = create_user()
            dropbox = None

            @staticmethod
            def is_supporting_file_type(path):
                return path != '/'

            class dropbox(object):
                @staticmethod
                def list(path):
                    if path == '/':
                        return {
                            'path': '/',
                            'is_dir': True,
                            'contents': [
                                create_dropbox_item(path='/path1', rev='rev1'),
                                create_dropbox_item(path='/path2', rev='rev2'),
                                create_dropbox_item(path='/path3', rev='rev3-new'),
                            ]}
                    else:
                        raise AssertionError("Unexpected %s" % path)

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
        self.assertEqual(context.user.own_file('/path4').state,
                         FileState.DELETED, 'deleted file on dropbox')
        self.assertEqual(context.user.own_file('/path5').state,
                         FileState.DELETED, 'stay deleted file on site')


class IgnoreFilesTest(DropboxTestBase):
    @attr('unit', 'light')
    def test_it(self):
        from netprintbox.settings import ACCOUNT_INFO_PATH, REPORT_PATH

        class context(object):
            user = create_user()

            class dropbox(object):
                @staticmethod
                def list(path):
                    if path == '/':
                        return {
                            'path': '/',
                            'is_dir': True,
                            'contents': [
                                create_dropbox_item(path=ACCOUNT_INFO_PATH),
                                create_dropbox_item(path=REPORT_PATH),
                                create_dropbox_item(path='/unsupported.dat'),
                            ]}
                    else:
                        raise AssertionError("Unexpected %s" % path)

            @staticmethod
            def is_supporting_file_type(path):
                return path not in (ACCOUNT_INFO_PATH,
                                    REPORT_PATH,
                                    '/unsupported.dat',)

        transaction = self._getOUT(context)
        transaction.run()

        self.assertIsNone(context.user.own_file(ACCOUNT_INFO_PATH),
                          'generated file not be on')
        self.assertIsNone(context.user.own_file(REPORT_PATH),
                          'generated file not be on')
        self.assertIsNone(context.user.own_file('/unsupported.dat'),
                          'unsupported file not be on')


class NetprintTestBase(TransactionTestBase):
    def _getOUT(self, context):
        from netprintbox.transaction import NetprintTransaction

        return NetprintTransaction(context)


class NetprintTest(NetprintTestBase):
    @attr('unit', 'light')
    def test_it(self):
        from netprintbox.data import FileState

        class Context(object):
            user = None
            netprint = None

            def __init__(self):
                self.transferred = []

            def transfer_from_dropbox(self, path, limit=None):
                self.transferred.append(
                        {'path': path, 'limit': limit})

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
                         state=FileState.LATEST, size=3)
        create_file_info(context.user, path='/name4',
                         state=FileState.NEED_NETPRINT_ID, size=2)
        create_file_info(context.user, path='/name5',
                         state=FileState.LATEST, size=4)
        create_file_info(context.user, path='/name6',
                         state=FileState.LATEST, pin=True, size=7)

        transaction = self._getOUT(context)
        transaction.run()

        self.assertIsNone(context.user.own_file('/name1'),
                          'netprint only file')
        f2 = context.user.own_file('/name2')
        self.assertIsNotNone(f2, 'id assigned file')
        self.assertEqual(f2.state, FileState.LATEST)
        self.assertEqual(f2.netprint_id, 'id2')
        self.assertIsNotNone(context.user.own_file('/name3'),
                             'no change file')
        f4 = context.user.own_file('/name4')
        self.assertIsNotNone(f4, 'uploaded')
        self.assertEqual(f4.state, FileState.NEED_NETPRINT_ID)
        self.assertItemsEqual([item['path'] for item in context.transferred],
                              ['/name4', '/name6'])
        self.assertEqual(context.user.own_file('/name5').state,
                         FileState.DELETED, 'deleted')
        f6 = context.user.own_file('/name6')
        self.assertIsNotNone(f6, 'pinned for re-uploading')
        self.assertEqual(f6.state, FileState.NEED_NETPRINT_ID)


class ObtainingLimitTest(NetprintTestBase):
    @attr('unit', 'light')
    def test_it(self):
        from netprintbox.data import FileState
        from netprintbox.exceptions import OverLimit

        class context(object):
            user = create_user()

            class netprint(object):
                @staticmethod
                def list():
                    return [
                            create_netprint_item(name='path1'),
                            create_netprint_item(name='path2'),
                            create_netprint_item(name='path3'),
                            create_netprint_item(name='path4'),
                            create_netprint_item(name='path5'),
                            ]

        for i in range(5):
            create_file_info(context.user, path='/path%d' % (i + 1),
                             state=FileState.LATEST, size=(2 * 1024 * 1024))
        create_file_info(context.user, path='/path6',
                         state=FileState.NEED_NETPRINT_ID, size=1)

        transaction = self._getOUT(context)

        self.assertRaises(OverLimit, transaction.run)
