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
import uuid

from dateutil.parser import parse as dt_parse
from dropbox.rest import ErrorResponse

from netprintbox.data import FileState, DropboxFileInfo
from netprintbox.utils import is_generated_file
from netprintbox.dropbox_utils import traverse
from netprintbox.exceptions import OverLimit


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


class DeleteTransaction(TransactionBase):
    """ Keep in mind. This transaction does delete on external system.
        Pay attention for race condition. """
    def run(self):
        deleted_list = [file_info
                        for file_info in self.context.user.own_files()
                        if file_info.state == FileState.DELETED]
        for deleted in deleted_list:
            try:
                self.context.delete_from_dropbox(deleted.path)
            except ErrorResponse:
                pass

            try:
                # XXX temporary implementation.
                self.context.delete_from_netprint(deleted.netprint_id)
            except:
                pass

            deleted.delete()


class DropboxTransaction(TransactionBase):
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
        file_info = self.context.user.own_file(item['uid'])
        if file_info.state != FileState.DELETED:
            file_info.state = FileState.DELETED
            file_info.put()

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
        file_info = self.context.user.own_file(item_on_site['uid'])
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
                    'uid': file_info.uid,
                    'path': file_info.path,
                    'rev': file_info.rev,
                    'bytes': file_info.size,
                }
        return result

    def _collect_entries_on_dropbox(self):
        data = self.context.dropbox.list('/')
        result = {}

        def __collect_entries(data):
            path = data['path']
            if not data['is_dir']:
                # file only
                if not (data.get('is_deleted', False) or
                        is_generated_file(path) or
                        not self.context.is_supporting_file_type(path)):
                    result[path] = data

        traverse(__collect_entries, data)
        return result


class NetprintTransaction(TransactionBase):

    ACCOUNT_CAPACITY = 10 * 1024 * 1024

    def __init__(self, context):
        super(NetprintTransaction, self).__init__(context)
        using_space = sum(file_info.size
                for file_info in context.user.own_files()
                if file_info.state == FileState.LATEST)
        self.available_space = self.ACCOUNT_CAPACITY - using_space

    def _decr_capacity(self, size):
        if self.available_space - size < 0:
            raise OverLimit("Up to account capacity by %dbytes." % size)
        self.available_space -= size

    def _incr_capacity(self, size):
        self.available_space += size

    def run(self):
        entries_on_netprint = self._collect_entries_on_netprint()
        entries_on_site = self._collect_entries_on_site()

        keys_on_site = set(entries_on_site)
        keys_on_netprint = set(entries_on_netprint)
        only_exists_on_site = keys_on_site - keys_on_netprint
        only_exists_on_netprint = keys_on_netprint - keys_on_site
        exists_on_both = keys_on_site & keys_on_netprint

        for k in only_exists_on_site:
            self._run_for_item_only_on_site(entries_on_site[k])

        for k in exists_on_both:
            self._run_for_item_on_both(entries_on_site[k],
                                       entries_on_netprint[k])

        for k in only_exists_on_netprint:
            self._run_for_item_only_on_netprint(entries_on_netprint[k])

    def _run_for_item_only_on_site(self, item):
        file_info = self.context.user.own_file(item['uid'])
        if file_info.state == FileState.NEED_NETPRINT_ID:
            size = item['size']
            self._decr_capacity(size)
            self.context.transfer_from_dropbox(
                    item['path'], limit=self.available_space + size)
        elif file_info.pin:
            self.context.transfer_from_dropbox(
                    item['path'], limit=self.available_space)
            file_info.state = FileState.NEED_NETPRINT_ID
            file_info.put()
        else:
            file_info.state = FileState.DELETED
            file_info.put()
            self._incr_capacity(item['size'])

    def _run_for_item_only_on_netprint(self, item):
        pass

    def _run_for_item_on_both(self, item_on_site, item_on_netprint):
        file_info = self.context.user.own_file(item_on_site['uid'])
        if file_info.state == FileState.NEED_NETPRINT_ID:
            file_info.netprint_id = item_on_netprint['id']
            file_info.state = FileState.LATEST
            file_info.put()

    def _collect_entries_on_site(self):
        result = {}
        for file_info in self.context.user.own_files():
            netprint_name = file_info.as_netprint_name()
            result[netprint_name] = {
                    'uid': file_info.uid,
                    'path': file_info.path,
                    'size': file_info.size,
                }
        return result

    def _collect_entries_on_netprint(self):
        result = {}
        for item in self.context.netprint.list():
            dict_item = item._asdict()
            if item.error:
                result[dict_item['name'].split('.')[0]] = dict_item
            else:
                result[dict_item['name']] = dict_item
        return result
