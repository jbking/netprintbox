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

from google.appengine.ext import db
from google.appengine.api import memcache
from oauth.oauth import OAuthToken

from netprintbox.utils import get_namespace


class DropboxUser(db.Model):
    uid = db.StringProperty(required=True)
    email = db.StringProperty(required=True)
    display_name = db.StringProperty(indexed=False)
    access_key = db.StringProperty(required=True)
    access_secret = db.StringProperty(required=True, indexed=False)
    pending = db.BooleanProperty(default=False)

    def own_files(self):
        return DropboxFileInfo.all().ancestor(self)


class FileState(object):
    NEED_NETPRINT_ID, LATEST = range(2)


class DropboxFileInfo(db.Model):
    path = db.StringProperty()
    rev = db.StringProperty(indexed=False)
    size = db.IntegerProperty(indexed=False)
    state = db.IntegerProperty(required=True)
    netprint_id = db.StringProperty()
    netprint_name = db.StringProperty(required=True)
    last_modified = db.DateTimeProperty(auto_now=True)


class OAuthRequestToken(object):
    key = None
    token = None

    @staticmethod
    def get(key):
        logging.debug(u"Getting token by key: %s", key)
        return OAuthToken.from_string(
                memcache.get(key,
                             namespace=get_namespace()))

    def put(self):
        if self.key is None or self.token is None:
            raise ValueError
        logging.debug(u"Saving token: %s", self.token)
        memcache.set(self.key, str(self.token),
                     namespace=get_namespace())

    @staticmethod
    def delete(key):
        logging.debug(u"Deleting token by key: %s", key)
        memcache.delete(key,
                        namespace=get_namespace())
