from google.appengine.ext import db

import data
import settings
from netprint_utils import normalize_name
from commands.dropbox import delete_file as dropbox_delete_file
from commands.netprintbox import put_from_dropbox
from commands.netprint import delete_file as netprint_delete_file


class SyncTransaction(object):
    def __init__(self, dropbox_user):
        self.dropbox_user = dropbox_user

    def _sync_transaction(self, dropbox_client, netprint_client,
                                dropbox_item):
        path = dropbox_item['path']
        rev = dropbox_item['rev']

        # excludes system generating files at all.
        if path in (settings.ACCOUNT_INFO_PATH, settings.REPORT_PATH):
            return

        query = data.DropboxFileInfo.all()\
                    .ancestor(self.dropbox_user)\
                    .filter('path = ', path)
        if query.count() == 0:
            netprint_name = normalize_name(path)
            file_info = data.DropboxFileInfo(parent=self.dropbox_user,
                                             path=path,
                                             rev=rev,
                                             netprint_name=netprint_name)
            file_info.put()
        elif query.count() == 1:
            file_info = query.get()
            if file_info.rev != rev:
                # upload new one if file is updated.
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
            raise ValueError("Duplicated path? %s" % path)
        put_from_dropbox(dropbox_client, netprint_client,
                         dropbox_item, None)

    def _delete_transaction(self, netprint_client, netprint_item):
        """
        Delete file and info.
        """
        netprint_id = netprint_item['id']
        query = data.DropboxFileInfo.all()\
                    .ancestor(self.dropbox_user)\
                    .filter('netprint_id = ', netprint_id)

        if query.count() > 0:
            for file_info in query:
                file_info.delete()
            netprint_delete_file(netprint_client, netprint_id)
        else:
            # unmanaged file
            pass

    def sync(self, dropbox_client, netprint_client,
                   dropbox_item, netprint_item):
        # detect only situation a file in dropbox but not in netprint.
        if dropbox_item is not None and netprint_item is None:
            db.run_in_transaction(self._sync_transaction,
                                  dropbox_client, netprint_client,
                                  dropbox_item)

        if dropbox_item is None and netprint_item is not None:
            db.run_in_transaction(self._delete_transaction,
                                  netprint_client, netprint_item)

        # XXX How about a file exists on netprint,
        #     but new one is uploaded on dropbox?
