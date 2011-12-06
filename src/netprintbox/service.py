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

import os
import logging
from StringIO import StringIO
from ConfigParser import ConfigParser

from google.appengine.ext import db
from httplib2 import Http
from dropbox.client import DropboxClient
from dropbox.session import DropboxSession

import settings

from netprint import Client as NetprintClient
from netprintbox.utils import load_template
from netprintbox.exceptions import OverLimit
from netprintbox.data import OAuthRequestToken, DropboxUser, FileState
from netprintbox.transaction import SyncTransaction
from dropbox_utils import traverse, ensure_binary_string
from settings import DROPBOX_APP_KEY, DROPBOX_APP_SECRET, DROPBOX_ACCESS_TYPE


class NetprintService(object):
    def __init__(self, username, password):
        self.username = username
        self.password = password

    @property
    def client(self):
        if getattr(self, '_client', None) is None:
            self._client = NetprintClient(Http(), settings.USER_AGENT)
            self._client.login(self.username, self.password)
        return self._client

    @client.setter
    def set_client(self, client):
        self._client = client

    def list(self):
        return self.client.list()

    def delete(self, id):
        logging.debug(u"Deleting file from Netprint: %s", id)
        return self.client.delete(id)

    def put(self, file_obj):
        logging.debug(u"Putting file to Netprint: %r", file_obj.name)
        return self.client.send(file_obj)


class NetprintboxService(object):
    def __init__(self, user):
        if isinstance(user, (basestring, db.Key)):
            user = DropboxUser.get(user)
        self.user = user

    @property
    def netprint(self):
        if getattr(self, '_netprint', None) is None:
            (username, password) = self.load_netprint_account_info()
            self._netprint = NetprintService(username, password)
        return self._netprint

    @netprint.setter
    def netprint(self, netprint):
        self._netprint = netprint

    @property
    def dropbox(self):
        if getattr(self, '_dropbox', None) is None:
            self._dropbox = DropboxService(self.user)
        return self._dropbox

    @dropbox.setter
    def dropbox(self, dropbox):
        self._dropbox = dropbox

    def load_netprint_account_info(self, path=settings.ACCOUNT_INFO_PATH):
        config = ConfigParser()
        config.readfp(self.dropbox.obtain(path))
        username = config.get('netprint', 'username')
        password = config.get('netprint', 'password')
        if username.strip() and password.strip():
            return (username, password)
        else:
            # XXX Use customized Exception.
            raise ValueError

    def sync(self):
        transaction = SyncTransaction(self)
        transaction.sync()

    def delete_from_netprint(self, netprint_id):
        self.netprint.delete(netprint_id)

    def delete_from_dropbox(self, path):
        self.dropbox.delete(path)

    def transfer_from_dropbox(self, path, limit=None):
        if os.path.splitext(path)[-1] in ('.jpg', '.jpeg'):
            file_limit = 4 * 1024 * 1024
        else:
            file_limit = 2 * 1024 * 1024
        if limit is None or limit > file_limit:
            limit = file_limit
        file_obj = self.dropbox.obtain(path, limit=limit)
        self.netprint.put(file_obj)

    def _make_report(self):
        own_files = list(self.user.own_files())
        controlled_map = dict((file_info.netprint_name, file_info)
                               for file_info in own_files)
        waiting_map = dict((file_info.netprint_name, file_info)
                           for file_info in own_files
                           if file_info.state == FileState.NEED_NETPRINT_ID)

        def txn():
            # XXX hook file deleted.
            need_report = False
            items = {}
            for item in self.netprint.list():
                item_dict = item._asdict()
                netprint_id = item_dict['id']
                netprint_name = item_dict['name']
                if netprint_name in controlled_map:
                    file_info = controlled_map[netprint_name]
                    if netprint_name in waiting_map:
                        # Set netprint_id by latest result.
                        file_info.netprint_id = netprint_id
                        file_info.state = FileState.LATEST
                        file_info.put()
                        need_report = True
                    item_dict['controlled'] = True
                    item_dict['last_modified'] = file_info.last_modified
                else:
                    need_report = True
                    item_dict['controlled'] = False
                items[netprint_name] = item_dict
            for file_info in own_files:
                netprint_name = file_info.netprint_name
                if netprint_name not in items:
                    items[netprint_name] = {
                            'name': netprint_name,
                            'id': "ERROR",
                            'controlled': True,
                            }
            return (need_report, items.values())
        return db.run_in_transaction(txn)

    def make_report(self):
        (need_report, item_list) = self._make_report()
        if need_report:
            template = load_template('report.html')
            self.dropbox.put(settings.REPORT_PATH,
                     StringIO(template.substitute(item_list=item_list)))


class DropboxService(object):
    def __init__(self, user):
        if isinstance(user, (basestring, db.Key)):
            user = DropboxUser.get(user)
        self.user = user

    @property
    def client(self):
        if getattr(self, '_client', None) is None:
            session = self.get_session()
            session.set_token(self.user.access_key, self.user.access_secret)
            self._client = DropboxClient(session)
        return self._client

    @client.setter
    def set_client(self, client):
        self._client = client

    def list(self, path, recursive=True):
        if recursive:
            result = self.list(path, recursive=False)
            if result['is_dir']:
                def _ls_rec(data):
                    if data['is_dir']:
                        data.update(self.list(data['path'], recursive=False))

                traverse(_ls_rec, result)
            return result
        else:
            path = ensure_binary_string(path)
            logging.debug(u"Listing metadata of: %r", path)
            return self.client.metadata(path)

    def obtain(self, path, limit=None):
        path = ensure_binary_string(path)
        logging.debug(u"Obtaining file: %r", path)
        metadata = self.list(path)
        if limit and metadata['bytes'] > limit:
            raise OverLimit("The response contains %d bytes data."\
                            % metadata['bytes'])
        res = self.client.get_file(path)
        file_obj = StringIO(res.read())
        file_obj.name = path
        return file_obj

    def put(self, path, file_obj, overwrite=True):
        path = ensure_binary_string(path)
        logging.debug(u"Putting file to Dropbox: %r", path)
        return self.client.put_file(path, file_obj, overwrite=overwrite)

    def delete(self, path):
        path = ensure_binary_string(path)
        logging.debug(u"Deleting file from Dropbox: %r", path)
        return self.client.file_delete(path)

    @classmethod
    def get_session(cls):
        return DropboxSession(DROPBOX_APP_KEY,
                              DROPBOX_APP_SECRET,
                              DROPBOX_ACCESS_TYPE)

    @classmethod
    def build_authorize_url(cls, callback_url):
        session = cls.get_session()
        request_token = session.obtain_request_token()
        token = OAuthRequestToken()
        token.key = request_token.key
        token.token = str(request_token)
        token.put()
        return session.build_authorize_url(request_token, callback_url)

    @classmethod
    def setup_user(cls, request_key):
        request_token = OAuthRequestToken.get(request_key)

        session = cls.get_session()
        session.obtain_access_token(request_token)
        client = DropboxClient(session)
        account_info = client.account_info()

        uid = str(account_info['uid'])
        q = DropboxUser.all().filter('uid = ', uid)
        if q.count() == 0:
            user = DropboxUser(uid=uid,
                               email=account_info['email'],
                               display_name=account_info['display_name'],
                               access_key=session.token.key,
                               access_secret=session.token.secret)
        else:
            user = q.get()
            user.email = account_info['email']
            user.display_name = account_info['display_name']
            user.access_key = session.token.key
            user.access_secret = session.token.secret
        user.put()

        OAuthRequestToken.delete(request_key)

        return user
