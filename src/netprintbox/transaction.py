from google.appengine.ext import db

from netprintbox.data import FileState, DropboxFileInfo

from utils import normalize_name, is_generated_file
from dropbox_utils import traverse
from netprintbox.exceptions import TransactionError, OverLimit


def _collect_entries(data):
    result = {}

    def __collect_entries(data):
        if not data['is_dir']:
            result[normalize_name(data['path'])] = data

    traverse(__collect_entries, data)
    return result


def _map_netprint_result(data):
    result = {}
    for item in data:
        dict_item = item._asdict()
        result[dict_item['name']] = dict_item
    return result


class SyncTransaction(object):

    ACCOUNT_CAPACITY = 10 * 1024 * 1024

    def __init__(self, context):
        self.context = context
        self.available_space = self.ACCOUNT_CAPACITY\
                - sum(file_info.size for file_info in context.user.own_files())

    def _capacity_check(self, size):
        if self.available_space - size < 0:
            raise OverLimit("Up to account capacity by %dbytes." % size)

    def _both(self, dropbox_item, netprint_item):
        def txn():
            path = dropbox_item['path']
            size = dropbox_item['bytes']
            rev = dropbox_item['rev']
            netprint_id = netprint_item['id']
            netprint_name = netprint_item['name']

            if is_generated_file(path):
                raise TransactionError(
                        "A generated file %s exists in netprint"\
                        % netprint_item['name'])

            query = self.context.user.own_files().filter('path = ', path)
            if query.count() == 0:
                # Files are found by same identifier.
                # In that case, assume dropbox's file is newer.
                self._capacity_check(size)
                self.available_space -= size
                file_info = DropboxFileInfo(parent=self.context.user,
                                            path=path,
                                            rev=rev,
                                            size=size,
                                            state=FileState.NEED_NETPRINT_ID,
                                            netprint_id=None,
                                            netprint_name=netprint_name)
                file_info.put()
            elif query.count() == 1:
                file_info = query.get()
                if file_info.rev != rev:
                    # Updated file.
                    self._capacity_check(size - file_info.size)
                    self.available_space -= size - file_info.size
                    file_info.rev = rev
                    file_info.size = size
                    file_info.state = FileState.NEED_NETPRINT_ID
                    # this will be re-assign after uploading.
                    file_info.netprint_id = None
                    file_info.put()
                else:
                    # Unmodified.
                    return
            else:
                raise TransactionError("Duplicated path? %s" % path)
            self.context.delete_from_netprint(netprint_id)
            self.context.transfer_from_dropbox(path,
                                               limit=self.available_space)
        db.run_in_transaction(txn)

    def _dropbox_only(self, dropbox_item):
        def txn():
            path = dropbox_item['path']
            size = dropbox_item['bytes']
            rev = dropbox_item['rev']

            # excludes system generating files at all.
            if is_generated_file(path):
                return

            query = self.context.user.own_files().filter('path = ', path)
            if query.count() == 0:
                # New file.
                netprint_name = normalize_name(path)
                self._capacity_check(size)
                self.available_space -= size
                file_info = DropboxFileInfo(parent=self.context.user,
                                            path=path,
                                            rev=rev,
                                            size=size,
                                            state=FileState.NEED_NETPRINT_ID,
                                            netprint_name=netprint_name)
                file_info.put()
            elif query.count() == 1:
                file_info = query.get()
                if file_info.rev != rev:
                    # Updated file.
                    self._capacity_check(size - file_info.size)
                    self.available_space -= size - file_info.size
                    file_info.rev = rev
                    file_info.size = size
                    file_info.state = FileState.NEED_NETPRINT_ID
                    file_info.put()
                elif file_info.netprint_id is None:
                    # Waiting for id assigning.
                    return
                else:
                    # The registered file is removed on netprint,
                    # so remove also it on datastore and dropbox.
                    file_info.delete()
                    self.context.delete_from_dropbox(path)
                    return
            else:
                raise TransactionError("Duplicated path? %s" % path)
            self.context.transfer_from_dropbox(path,
                                               limit=self.available_space)
        db.run_in_transaction(txn)

    def _netprint_only(self, netprint_item):
        def txn():
            netprint_id = netprint_item['id']
            query = self.context.user.own_files()\
                    .filter('netprint_id = ', netprint_id)

            if query.count() > 0:
                # The registered file is removed on dropbox,
                # so remove also it on datastore and netprint.
                for file_info in query:
                    file_info.delete()
                self.available_space += file_info.size
                self.context.netprint.delete(netprint_id)
            else:
                # An uncontrolled file is found.
                pass
        db.run_in_transaction(txn)

    def sync(self):
        item_in_dropbox = _collect_entries(self.context.dropbox.list('/'))
        item_in_netprint = _map_netprint_result(self.context.netprint.list())

        key_in_both = set(item_in_dropbox) & set(item_in_netprint)
        key_in_dropbox_only = set(item_in_dropbox) - set(item_in_netprint)
        key_in_netprint_only = set(item_in_netprint) - set(item_in_dropbox)

        for key in key_in_both:
            self._both(item_in_dropbox[key], item_in_netprint[key])

        for key in key_in_dropbox_only:
            self._dropbox_only(item_in_dropbox[key])

        for key in key_in_netprint_only:
            self._netprint_only(item_in_netprint[key])
