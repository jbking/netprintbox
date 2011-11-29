from google.appengine.ext import db

import data
import settings
from netprint_utils import normalize_name
from dropbox_commands import delete_file as dropbox_delete_file
from netprintbox_commands import put_from_dropbox
from netprint_commands import delete_file as netprint_delete_file
from netprintbox.exceptions import TransactionError, OverLimit


class SyncTransaction(object):

    ACCOUNT_CAPACITY = 10 * 1024 * 1024

    def __init__(self, dropbox_user):
        self.dropbox_user = dropbox_user
        self.available_space = self.ACCOUNT_CAPACITY\
                - sum(file_info.size for file_info in dropbox_user.own_files())

    def _capacity_check(self, size):
        if self.available_space - size < 0:
            raise OverLimit("Up to account capacity by %dbytes." % size)

    def _sync_transaction_from_both(self, dropbox_client, netprint_client,
                                    dropbox_item, netprint_item):
        path = dropbox_item['path']
        size = dropbox_item['bytes']
        rev = dropbox_item['rev']
        netprint_id = netprint_item['id']
        netprint_name = netprint_item['name']

        # excludes system generating files at all.
        if path in (settings.ACCOUNT_INFO_PATH, settings.REPORT_PATH):
            raise TransactionError("There is generated file %s in netprint"\
                                   % netprint_item['name'])

        query = self.dropbox_user.own_files().filter('path = ', path)
        if query.count() == 0:
            self._capacity_check(size)
            self.available_space -= size
            file_info = data.DropboxFileInfo(parent=self.dropbox_user,
                                             path=path,
                                             size=size,
                                             rev=rev,
                                             netprint_id=netprint_id,
                                             netprint_name=netprint_name)
            file_info.put()
        elif query.count() == 1:
            file_info = query.get()
            if file_info.rev != rev:
                self._capacity_check(size - file_info.size)
                self.available_space -= size - file_info.size
                # upload new one if file is updated.
                file_info.size = size
                file_info.rev = rev
                # this will be re-assign after uploading.
                file_info.netprint_id = None
                file_info.put()
            else:
                return
        else:
            raise TransactionError("Duplicated path? %s" % path)
        put_from_dropbox(dropbox_client, netprint_client,
                         dropbox_item, None)

    def _sync_transaction_from_dropbox(self, dropbox_client, netprint_client,
                                       dropbox_item):
        path = dropbox_item['path']
        size = dropbox_item['bytes']
        rev = dropbox_item['rev']

        # excludes system generating files at all.
        if path in (settings.ACCOUNT_INFO_PATH, settings.REPORT_PATH):
            return

        query = self.dropbox_user.own_files().filter('path = ', path)
        if query.count() == 0:
            netprint_name = normalize_name(path)
            self._capacity_check(size)
            self.available_space -= size
            file_info = data.DropboxFileInfo(parent=self.dropbox_user,
                                             path=path,
                                             size=size,
                                             rev=rev,
                                             netprint_name=netprint_name)
            file_info.put()
        elif query.count() == 1:
            file_info = query.get()
            if file_info.rev != rev:
                self._capacity_check(size - file_info.size)
                self.available_space -= size - file_info.size
                # upload new one if file is updated.
                file_info.size = size
                file_info.rev = rev
                file_info.put()
            elif file_info.netprint_id is None:
                # waiting for id assigning.
                return
            else:
                # delete entry from datastore and dropbox otherwise.
                file_info.delete()
                dropbox_delete_file(dropbox_client, path)
                return
        else:
            raise TransactionError("Duplicated path? %s" % path)
        put_from_dropbox(dropbox_client, netprint_client,
                         dropbox_item, None)

    def _delete_transaction(self, netprint_client, netprint_item):
        """
        Delete file and info.
        """
        netprint_id = netprint_item['id']
        query = self.dropbox_user.own_files()\
                .filter('netprint_id = ', netprint_id)

        if query.count() > 0:
            for file_info in query:
                file_info.delete()
            self.available_space += file_info.size
            netprint_delete_file(netprint_client, netprint_id)
        else:
            # unmanaged file
            pass

    def sync(self, dropbox_client, netprint_client,
                   dropbox_item, netprint_item):
        # detect only situation a file in dropbox but not in netprint.
        if dropbox_item is not None and netprint_item is None:
            db.run_in_transaction(self._sync_transaction_from_dropbox,
                                  dropbox_client, netprint_client,
                                  dropbox_item)

        elif dropbox_item is None and netprint_item is not None:
            db.run_in_transaction(self._delete_transaction,
                                  netprint_client, netprint_item)

        elif dropbox_item is not None and netprint_item is not None:
            db.run_in_transaction(self._sync_transaction_from_both,
                                  dropbox_client, netprint_client,
                                  dropbox_item, netprint_item)
