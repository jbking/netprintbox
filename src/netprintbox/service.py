# -*- encoding: utf-8 -*-
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
import uuid
import logging
import hashlib
from httplib import HTTPException
from StringIO import StringIO
from ConfigParser import ConfigParser

from google.appengine.ext import db
from google.appengine.api import memcache
from httplib2 import Http
from dropbox.rest import ErrorResponse

from netprint import (
        Client as NetprintClient,
        PaperSize, Color,
        get_sending_target, UnknownExtension, LoginFailure)
from netprintbox.utils import load_template, get_namespace, normalize_name
from netprintbox.exceptions import (
        OverLimit, PendingUser, InvalidNetprintAccountInfo,
        DropboxBadRequest, DropboxForbidden,
        DropboxNotFound, DropboxMethodNotAllowed,
        DropboxServiceUnavailable, DropboxInsufficientStorage,
        DropboxServerError,
        UnsupportedFile
)
from netprintbox.data import OAuthRequestToken, DropboxUser, FileState
from netprintbox.transaction import SyncTransaction
from dropbox_utils import traverse, ensure_binary_string
from settings import (
        DROPBOX_APP_KEY, DROPBOX_APP_SECRET, DROPBOX_ACCESS_TYPE,
        USER_AGENT, ACCOUNT_INFO_PATH, REPORT_PATH, DATETIME_FORMAT)
from netprintbox.template_utils import (
        get_namespace as get_template_namespace,
        )


class NetprintService(object):
    def __init__(self, username, password):
        self.username = username
        self.password = password

    @property
    def client(self):
        if getattr(self, '_client', None) is None:
            self._client = NetprintClient(Http(), USER_AGENT)
            try:
                self._client.login(self.username, self.password)
            except LoginFailure:
                raise InvalidNetprintAccountInfo
        return self._client

    @client.setter
    def client(self, client):
        self._client = client

    @staticmethod
    def is_supporting_file_type(file_name):
        try:
            get_sending_target(file_name)
            return True
        except UnknownExtension:
            return False

    def list(self):
        return self.client.list()

    def delete(self, id):
        logging.debug(u"Deleting file from Netprint: %s", id)
        return self.client.delete(id)

    def put(self, file_obj, paper_size):
        file_name = normalize_name(file_obj.name, ext=True)
        logging.debug(u"Putting file to Netprint: %s as %s",
                      file_obj.name, file_name)
        if paper_size == PaperSize.L:
            color = Color.color
        else:
            color = Color.choice_at_printing
        return self.client.send(file_obj,
                                file_name=file_name,
                                color=color,
                                paper_size=paper_size)


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

    def load_netprint_account_info(self, path=ACCOUNT_INFO_PATH):
        config = ConfigParser()
        try:
            config.readfp(self.dropbox.obtain(path))
            username = config.get('netprint', 'username')
            password = config.get('netprint', 'password')
            if username.strip() and password.strip():
                return (username, password)
        except:
            pass
        raise InvalidNetprintAccountInfo

    def sync(self):
        self.ensure_paper_size_directories()
        transaction = SyncTransaction(self)
        transaction.sync()

    def ensure_paper_size_directories(self):
        root_dirs_path = [item['path']
                          for item in self.dropbox.list('/')['contents']
                          if item['is_dir']]
        for attr_name in dir(PaperSize):
            if (not attr_name.startswith('_')
                and '/' + attr_name not in root_dirs_path):
                self.dropbox.create_folder(attr_name)

    def delete_from_netprint(self, netprint_id):
        self.netprint.delete(netprint_id)

    def delete_from_dropbox(self, path):
        self.dropbox.delete(path)

    def transfer_from_dropbox(self, path, limit=None):
        try:
            paper_size_name = path[1:path.index('/', 1)]
            paper_size = getattr(PaperSize, paper_size_name)
        except (AttributeError, ValueError):
            logging.debug("Ignore a miss placed path silently: %s", path)
            return
        if os.path.splitext(path)[-1].lower() in ('.jpg', '.jpeg'):
            file_limit = 4 * 1024 * 1024
        else:
            file_limit = 2 * 1024 * 1024
        if limit is None or limit > file_limit:
            limit = file_limit
        if not self.netprint.is_supporting_file_type(path):
            raise UnsupportedFile(path)
        file_obj = self.dropbox.obtain(path, limit=limit)
        self.netprint.put(file_obj, paper_size)

    def _compare_by_hash(self, update_hash=False):
        md5 = hashlib.new('md5')
        key = str(self.user.key())
        for item in self.netprint.list():
            md5.update(item.id or '')
        namespace = get_namespace()
        digest = md5.hexdigest()
        previous_digest = memcache.get(key,
                          namespace=namespace)
        logging.debug('Generated digest is %s, and cached is %s',
                      digest,
                      previous_digest)
        changed = digest != previous_digest
        if update_hash and changed:
            memcache.set(key, digest, namespace=namespace)
        return changed

    def _make_report(self):
        own_files = list(self.user.own_files())
        controlled_map = dict((file_info.as_netprint_name(), file_info)
                               for file_info in own_files)
        possible_error_map = dict((file_info.as_netprint_name(True), file_info)
                                  for file_info in own_files)

        def txn():
            items = {}
            need_report = False
            for item in self.netprint.list():
                item_dict = item._asdict()
                netprint_id = item_dict['id']
                netprint_name = item_dict['name']
                netprint_error = item_dict['error']

                items[netprint_name] = item_dict
                if netprint_name in controlled_map:
                    file_info = controlled_map[netprint_name]
                    item_dict['file-key'] = str(file_info.key())
                    item_dict['pin-state'] = "on" if file_info.pin else "off"
                    item_dict['make-link'] = True
                elif netprint_error and netprint_name in possible_error_map:
                    file_info = possible_error_map[netprint_name]
                else:
                    item_dict['last_modified'] = None
                    continue
                item_dict['controlled'] = True
                item_dict['last_modified'] = file_info.local_last_modified\
                        .strftime(DATETIME_FORMAT)
                if file_info.state == FileState.NEED_NETPRINT_ID:
                    # Set netprint_id by latest result.
                    file_info.netprint_id = netprint_id
                    file_info.state = FileState.LATEST
                    file_info.put()
            for file_info in own_files:
                netprint_name = file_info.as_netprint_name()
                netprint_name_error = file_info.as_netprint_name(True)
                if not (netprint_name in items
                        or netprint_name_error in items):
                    if file_info.state == FileState.LATEST:
                        fake_id = "FAKE:ERROR"
                    else:
                        fake_id = "FAKE:WAIT"
                    items[netprint_name] = {
                            'name': netprint_name,
                            'id': fake_id,
                            'controlled': True,
                            'valid_date': None,
                            'page_numbers': 0,
                            'paper_size': '',
                            'last_modified': file_info.local_last_modified\
                                    .strftime(DATETIME_FORMAT),
                            }

            if not need_report:
                need_report = self._compare_by_hash(update_hash=True)
            return (need_report, items.values())
        return db.run_in_transaction(txn)

    def make_report(self):
        (need_report, item_list) = self._make_report()
        if need_report:
            report_token = str(uuid.uuid4())
            self.user.report_token = report_token
            self.user.put()
            logging.debug('Making a report for %s(%s)',
                          self.user.email,
                          self.user.uid)
            template = load_template('report.html',
                    namespace=get_template_namespace())
            rendered_data = template.substitute(
                    report_token=report_token,
                    item_list=item_list)
            self.dropbox.put(REPORT_PATH, StringIO(rendered_data))
        else:
            logging.debug('No need to make a report for %s(%s)',
                          self.user.email,
                          self.user.uid)

    def is_supporting_file_type(self, file_name):
        # do as interface.
        return self.netprint.is_supporting_file_type(file_name)


def handle_error_response(func):
    def _func(self, *args, **kwargs):
        try:
            return func(self, *args, **kwargs)
        except ErrorResponse as e:
            exc_type = None
            status = int(e.status)
            if status == 400:
                exc_type = DropboxBadRequest
            elif status == 401:
                self.user.put_pending()
            elif status == 403:
                exc_type = DropboxForbidden
            elif status == 404:
                exc_type = DropboxNotFound
            elif status == 405:
                exc_type = DropboxMethodNotAllowed
            elif status == 503:
                exc_type = DropboxServiceUnavailable
            elif status == 507:
                exc_type = DropboxInsufficientStorage
            raise exc_type(e.message)
        except HTTPException as e:
            raise DropboxServerError(e.message)
    _func.func_name = func.func_name
    _func.func_doc = func.func_doc
    return _func


class DropboxService(object):
    def __init__(self, user):
        if isinstance(user, (basestring, db.Key)):
            user = DropboxUser.get(user)
        self.user = user

    @property
    def client(self):
        from dropbox.client import DropboxClient

        if getattr(self, '_client', None) is None:
            if self.user.is_pending:
                raise PendingUser(self.user)
            session = self.get_session()
            session.set_token(self.user.access_key, self.user.access_secret)
            self._client = DropboxClient(session)
        return self._client

    @client.setter
    def client(self, client):
        self._client = client

    @property
    def cached_list(self):
        try:
            return getattr(self, '_cached_list')
        except AttributeError:
            self._cached_list = {}
            return self._cached_list

    @handle_error_response
    def list(self, path, recursive=True):
        if path in self.cached_list:
            return self.cached_list[path]
        if recursive:
            result = self.list(path, recursive=False)
            if result['is_dir']:
                def _ls_rec(data):
                    if data['is_dir']:
                        data.update(self.list(data['path'], recursive=False))

                traverse(_ls_rec, result)
            return result
        else:
            path_for_dropbox = ensure_binary_string(path)
            logging.debug(u"Listing metadata of: %s", path)
            result = self.client.metadata(path_for_dropbox)
            self.cached_list[path] = result
            return result

    @handle_error_response
    def obtain(self, path, limit=None):
        path_for_dropbox = ensure_binary_string(path)
        logging.debug(u"Obtaining file: %s", path)
        metadata = self.list(path)
        if limit and metadata['bytes'] > limit:
            raise OverLimit("The response contains %d bytes data."\
                            % metadata['bytes'])
        res = self.client.get_file(path_for_dropbox)
        file_obj = StringIO(res.read())
        file_obj.name = path
        return file_obj

    @handle_error_response
    def put(self, path, file_obj, overwrite=True):
        path_for_dropbox = ensure_binary_string(path)
        logging.debug(u"Putting file to Dropbox: %s", path)
        return self.client.put_file(path_for_dropbox,
                                    file_obj, overwrite=overwrite)

    @handle_error_response
    def delete(self, path):
        path_for_dropbox = ensure_binary_string(path)
        logging.debug(u"Deleting file from Dropbox: %s", path)
        return self.client.file_delete(path_for_dropbox)

    @handle_error_response
    def create_folder(self, path):
        path_for_dropbox = ensure_binary_string(path)
        logging.debug(u"Creating a directory: %s", path)
        return self.client.file_create_folder(path_for_dropbox)

    @handle_error_response
    def move(self, from_path, to_path):
        from_path_for_dropbox = ensure_binary_string(from_path)
        to_path_for_dropbox = ensure_binary_string(to_path)
        logging.debug(u"Moving into: %s %s", from_path, to_path)
        return self.client.file_move(from_path_for_dropbox,
                                     to_path_for_dropbox)

    @classmethod
    def get_session(cls):
        from dropbox.session import DropboxSession

        return DropboxSession(DROPBOX_APP_KEY,
                              DROPBOX_APP_SECRET,
                              DROPBOX_ACCESS_TYPE)

    @classmethod
    def build_authorize_url(cls, callback_url):
        session = cls.get_session()
        request_token = session.obtain_request_token()
        token = OAuthRequestToken(key=request_token.key,
                                  token=str(request_token))
        token.put()
        return session.build_authorize_url(request_token, callback_url)

    @classmethod
    def setup_user(cls, request_key):
        from dropbox.client import DropboxClient

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
                               access_secret=session.token.secret,
                               country=account_info['country'])
        else:
            user = q.get()
            user.email = account_info['email']
            user.display_name = account_info['display_name']
            user.access_key = session.token.key
            user.access_secret = session.token.secret
            user.put_pending_away(_save=False)
            user.country = account_info['country']
        user.put()

        OAuthRequestToken.delete(request_key)

        return user
