"""
    Netprintbox
    Copyright (C) 2011  MURAOKA Yusuke <yusuke@jbking.org>

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU Affero General Public License as
    published by the Free Software Foundation, either version 3 of the
    License, or (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU Affero General Public License for more details.

    You should have received a copy of the GNU Affero General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""
import logging
import uuid

from dateutil.parser import parse as dt_parse

from google.appengine.ext import db

from netprintbox.data import FileState, DropboxFileInfo
from netprintbox.utils import normalize_name, is_generated_file
from netprintbox.dropbox_utils import traverse
from netprintbox.exceptions import TransactionError, OverLimit, UnsupportedFile


def _collect_entries(data):
    result = {}

    def __collect_entries(data):
        if not data['is_dir'] and not data.get('is_deleted', False):
            result[normalize_name(data['path'])] = data

    traverse(__collect_entries, data)
    return result


def _map_netprint_result(data):
    result = {}
    for item in data:
        dict_item = item._asdict()
        if item.error:
            result[dict_item['name'].split('.')[0]] = dict_item
        else:
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
            modified = dt_parse(dropbox_item['modified'])
            netprint_id = netprint_item['id']

            logging.debug(u"File exists on both: %s(%s)", path, rev)

            if is_generated_file(path):
                raise TransactionError(
                        u"A generated file %s exists in netprint"\
                        % netprint_item['name'])

            if netprint_id is None:
                raise TransactionError("netprint_id must not be None: %r",
                                       netprint_item)

            query = self.context.user.own_files().filter('path = ', path)
            if query.count() == 0:
                # Files are found on each side but gae by same identifier.
                # In that case, assume dropbox's file is newer.
                self._capacity_check(size)
                self.available_space -= size
                file_info = DropboxFileInfo(parent=self.context.user,
                                            path=path,
                                            rev=rev,
                                            size=size,
                                            state=FileState.NEED_NETPRINT_ID,
                                            last_modified=modified,
                                            netprint_id=None)
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
                    file_info.last_modified = modified
                    # this will be re-assign after uploading.
                    file_info.netprint_id = None
                    file_info.put()
                else:
                    # Unmodified.
                    return
            else:
                raise TransactionError("Duplicated path?: %r" % dropbox_item)

            self.context.delete_from_netprint(netprint_id)
            self.context.transfer_from_dropbox(path,
                                               limit=self.available_space)

        try:
            db.run_in_transaction(txn)
        except UnsupportedFile:
            logging.exception("Got an unsupported file: %r", dropbox_item)

    def _dropbox_only(self, dropbox_item):
        def txn():
            path = dropbox_item['path']
            size = dropbox_item['bytes']
            rev = dropbox_item['rev']
            modified = dt_parse(dropbox_item['modified'])

            logging.debug(u"File exists on dropbox: %s(%s)", path, rev)

            # excludes system generating files at all.
            if is_generated_file(path):
                return

            query = self.context.user.own_files().filter('path = ', path)
            if query.count() == 0:
                # New file.
                self._capacity_check(size)
                self.available_space -= size
                file_info = DropboxFileInfo(parent=self.context.user,
                                            path=path,
                                            rev=rev,
                                            size=size,
                                            state=FileState.NEED_NETPRINT_ID,
                                            last_modified=modified)
                file_info.put()
            elif query.count() == 1:
                file_info = query.get()
                if file_info.rev != rev or file_info.pin:
                    # Updated or pinned file.
                    self._capacity_check(size - file_info.size)
                    self.available_space -= size - file_info.size
                    file_info.rev = rev
                    file_info.size = size
                    file_info.state = FileState.NEED_NETPRINT_ID
                    file_info.last_modified = modified
                    file_info.put()
                elif file_info.state == FileState.NEED_NETPRINT_ID:
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

        try:
            db.run_in_transaction(txn)
        except UnsupportedFile:
            logging.exception("Got an unsupported file %r", dropbox_item)

    def _netprint_only(self, netprint_item):
        def txn():
            netprint_id = netprint_item['id']
            if netprint_id is None:
                raise TransactionError("netprint_id must not be None: %r",
                                       netprint_item)

            netprint_name = netprint_item['name']
            query = self.context.user.own_files()\
                    .filter('netprint_id = ', netprint_id)

            logging.debug(u"File exists on netprint: %s(%s)",
                          netprint_name, netprint_id)

            if query.count() > 0:
                # The registered file is removed on dropbox,
                # so remove also it on datastore and netprint.
                for file_info in query:
                    file_info.delete()
                self.available_space += file_info.size
                if netprint_id:
                    self.context.netprint.delete(netprint_id)
            else:
                # An uncontrolled file is found.
                pass
        db.run_in_transaction(txn)

    def _gae_only(self, file_info):
        logging.info(u"Remove an orphan data: netprint_id = %s\n"
                      "netprint_name = %s\n"
                      "dropbox rev = %s\n",
                      file_info.netprint_id,
                      file_info.as_netprint_name(),
                      file_info.rev)
        file_info.delete()

    def sync(self):
        item_in_dropbox = _collect_entries(self.context.dropbox.list('/'))
        item_in_netprint = _map_netprint_result(self.context.netprint.list())
        info_in_gae = dict((file_info.as_netprint_name(), file_info)
                           for file_info in self.context.user.own_files())

        key_in_dropbox = set(item_in_dropbox)
        key_in_netprint = set(item_in_netprint)
        key_in_both = key_in_dropbox & key_in_netprint
        key_in_dropbox_only = key_in_dropbox - key_in_netprint
        key_in_netprint_only = key_in_netprint - key_in_dropbox
        key_in_gae = set(info_in_gae)

        for key in key_in_both:
            self._both(item_in_dropbox[key], item_in_netprint[key])

        for key in key_in_dropbox_only:
            self._dropbox_only(item_in_dropbox[key])

        for key in key_in_netprint_only:
            self._netprint_only(item_in_netprint[key])

        for key in key_in_gae - (key_in_dropbox | key_in_netprint):
            self._gae_only(info_in_gae[key])


class TransactionBase(object):
    def __init__(self, context):
        self.context = context

    @property
    def uid(self):
        if getattr(self, '_uid_cache', None) is None:
            self._uid_cache = str(uuid.uuid4())
        return self._uid_cache

    @uid.setter
    def uid(self, value):
        self._uid_cache = value

    def run(self):
        raise NotImplementedError


class DropboxTransaction(TransactionBase):
    def __init__(self, context):
        super(DropboxTransaction, self).__init__(context)

    def run(self):
        entries_on_dropbox = self._collect_entries_on_dropbox()
        entries_on_site = self._collect_entries_on_site()

        keys_on_site = set(entries_on_site)
        keys_on_dropbox = set(entries_on_dropbox)
        only_exists_on_site = keys_on_site - keys_on_dropbox
        only_exists_on_dropbox = keys_on_dropbox - keys_on_site
        exists_on_both = keys_on_site & keys_on_dropbox

        for k in only_exists_on_site:
            self._run_for_item_only_on_site(entries_on_site[k])

        for k in exists_on_both:
            self._run_for_item_on_both(entries_on_site[k],
                                       entries_on_dropbox[k])

        for k in only_exists_on_dropbox:
            self._run_for_item_only_on_dropbox(entries_on_dropbox[k])

    def _run_for_item_only_on_site(self, item):
        """
        Recognize as gone file.
        """
        file_info = self.context.user.own_file(item['path'])
        file_info.delete()

    def _run_for_item_only_on_dropbox(self, item):
        """
        Recognize as new file.
        """
        file_info = DropboxFileInfo(parent=self.context.user,
                                    path=item['path'],
                                    rev=item['rev'],
                                    size=item['bytes'],
                                    state=FileState.NEED_NETPRINT_ID,
                                    last_modified=dt_parse(item['modified']))
        file_info.put()

    def _run_for_item_on_both(self, item_on_site, item_on_dropbox):
        rev = item_on_dropbox['rev']
        size = item_on_dropbox['bytes']
        file_info = self.context.user.own_file(item_on_site['path'])
        if file_info.rev != rev:
            # Updated file.
            file_info.rev = rev
            file_info.size = size
            file_info.state = FileState.NEED_NETPRINT_ID
            file_info.last_modified = dt_parse(item_on_dropbox['modified'])
            file_info.put()

    def _collect_entries_on_site(self):
        result = {}
        for file_info in self.context.user.own_files():
            result[file_info.path] = {
                    'path': file_info.path,
                    'rev': file_info.rev,
                    'bytes': file_info.size,
                }
        return result

    def _collect_entries_on_dropbox(self):
        data = self.context.dropbox.list('/')
        result = {}

        def __collect_entries(data):
            if not (data['is_dir']
                    or data.get('is_deleted', False)
                    or is_generated_file(data['path'])):
                result[data['path']] = data

        traverse(__collect_entries, data)
        return result
