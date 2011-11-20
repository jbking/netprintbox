from StringIO import StringIO
from unittest2 import TestCase
from nose.plugins.attrib import attr


class SyncTransactionTest(TestCase):
    def setUp(self):
        from google.appengine.ext.testbed import Testbed

        self.testbed = Testbed()
        self.testbed.activate()
        self.testbed.init_datastore_v3_stub()

    def tearDown(self):
        self.testbed.deactivate()

    def _getOUT(self, dropbox_user):
        from handlers import SyncTransaction

        return SyncTransaction(dropbox_user)

    def create_user(self, **kwargs):
        import data

        default = {
                'uid': 'uid',
                'email': 'email',
                'display_name': 'display_name',
                'access_key': 'access_key',
                'access_secret': 'access_secret',
            }
        params = dict(default)
        params.update(kwargs)
        user = data.DropboxUser(**params)
        user.put()
        return user

    @attr(test_type='unit')
    def test_new_file(self):
        import data

        user = self.create_user()
        transaction = self._getOUT(user)

        class dropbox_client(object):
            @staticmethod
            def get_file(*args):
                return StringIO('test')

        put_commands = []

        class netprint_client(object):
            @staticmethod
            def send(file_obj):
                put_commands.append(file_obj)

        transaction.sync(dropbox_client, netprint_client,
                         dict(path='path', rev='rev'), None)

        q = data.DropboxFileInfo.all().ancestor(user)
        self.assertEqual(q.count(), 1)
        file_info = q.get()
        self.assertEqual(file_info.path, 'path')
        self.assertEqual(file_info.rev, 'rev')
        self.assertEqual(len(put_commands), 1)
        self.assertEqual(put_commands[0].read(), 'test')

    @attr(test_type='unit')
    def test_transaction_isolation(self):
        import data

        user1 = self.create_user()
        user2 = self.create_user()
        transaction1 = self._getOUT(user1)
        transaction2 = self._getOUT(user2)

        class dropbox_client(object):
            @staticmethod
            def get_file(*args):
                return StringIO('test')

        class netprint_client(object):
            @staticmethod
            def send(file_obj):
                pass

        transaction1.sync(dropbox_client, netprint_client,
                          dict(path='path', rev='rev'), None)
        self.assertEqual(data.DropboxFileInfo.all().ancestor(user1).count(), 1)
        self.assertEqual(data.DropboxFileInfo.all().ancestor(user2).count(), 0)

        transaction2.sync(dropbox_client, netprint_client,
                          dict(path='path', rev='rev'), None)
        self.assertEqual(data.DropboxFileInfo.all().ancestor(user1).count(), 1)
        self.assertEqual(data.DropboxFileInfo.all().ancestor(user2).count(), 1)

    @attr(test_type='unit')
    def test_modified_file(self):
        import data

        user = self.create_user()
        transaction = self._getOUT(user)

        class dropbox_client(object):
            @staticmethod
            def get_file(*args):
                return StringIO('test')

        put_commands = []

        class netprint_client(object):
            @staticmethod
            def send(file_obj):
                put_commands.append(file_obj)

        data.DropboxFileInfo(path='path', rev='prev').put()

        transaction.sync(dropbox_client, netprint_client,
                         dict(path='path', rev='rev'), None)

        q = data.DropboxFileInfo.all().ancestor(user)
        self.assertEqual(q.count(), 1)
        file_info = q.get()
        self.assertEqual(file_info.path, 'path')
        self.assertEqual(file_info.rev, 'rev')
        self.assertEqual(len(put_commands), 1)
        self.assertEqual(put_commands[0].read(), 'test')

    @attr(test_type='unit')
    def test_expired_file(self):
        import data

        user = self.create_user()
        transaction = self._getOUT(user)

        deleted = []
        class dropbox_client(object):
            @staticmethod
            def file_delete(path):
                deleted.append(path)

        class netprint_client(object):
            pass

        data.DropboxFileInfo(parent=user, path='path', rev='rev').put()

        transaction.sync(dropbox_client, netprint_client,
                         dict(path='path', rev='rev'), None)

        q = data.DropboxFileInfo.all().ancestor(user)
        self.assertEqual(q.count(), 0)
        self.assertListEqual(deleted, ['path'])

    @attr(test_type='unit')
    def test_ignore_generated(self):
        import data
        import settings

        user = self.create_user()
        transaction = self._getOUT(user)

        class dropbox_client(object):
            pass

        class netprint_client(object):
            pass

        for ignore_path in (settings.ACCOUNT_INFO_PATH, settings.REPORT_PATH):
            transaction.sync(dropbox_client, netprint_client,
                             dict(path=ignore_path, rev='rev'), None)
        q = data.DropboxFileInfo.all().ancestor(user)
        self.assertEqual(q.count(), 0)

    @attr(test_type='unit')
    def test_same_file(self):
        import data

        user = self.create_user()
        transaction = self._getOUT(user)

        class dropbox_client(object):
            pass

        class netprint_client(object):
            pass

        data.DropboxFileInfo(parent=user,
                             path='same_name',
                             rev='rev').put()

        transaction.sync(dropbox_client, netprint_client,
                         dict(path='same_name', rev='rev'),
                         dict(name='same_name'))

        q = data.DropboxFileInfo.all().ancestor(user)
        self.assertEqual(q.count(), 1)
        file_info = q.get()
        self.assertEqual(file_info.path, 'same_name')
        self.assertEqual(file_info.rev, 'rev')

    @attr(test_type='unit')
    def test_netprint_has_original_file(self):
        import data

        user = self.create_user()
        transaction = self._getOUT(user)

        class dropbox_client(object):
            pass

        class netprint_client(object):
            pass

        transaction.sync(dropbox_client, netprint_client,
                         None, dict(name='same_name'))

        q = data.DropboxFileInfo.all().ancestor(user)
        self.assertEqual(q.count(), 0)

    @attr(test_type='unit')
    def test_dropbox_cause_an_error(self):
        import data

        user = self.create_user()
        transaction = self._getOUT(user)

        class DropboxError(Exception):
            pass

        class dropbox_client(object):
            @staticmethod
            def get_file(path):
                raise DropboxError

        class netprint_client(object):
            pass

        self.assertRaises(DropboxError,
                          transaction.sync,
                          dropbox_client, netprint_client,
                          dict(path='path', rev='rev'), None)

        q = data.DropboxFileInfo.all().ancestor(user)
        self.assertEqual(q.count(), 0)

    @attr(test_type='unit')
    def test_netprint_cause_an_error(self):
        import data

        user = self.create_user()
        transaction = self._getOUT(user)

        class dropbox_client(object):
            @staticmethod
            def get_file(path):
                return StringIO('test')

        class NetprintError(Exception):
            pass

        class netprint_client(object):
            @staticmethod
            def send(file_obj):
                raise NetprintError

        self.assertRaises(NetprintError,
                          transaction.sync,
                          dropbox_client, netprint_client,
                          dict(path='path', rev='rev'), None)

        q = data.DropboxFileInfo.all().ancestor(user)
        self.assertEqual(q.count(), 0)
