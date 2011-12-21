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
import logging

from google.appengine.ext import db
from google.appengine.api import memcache, mail
from oauth.oauth import OAuthToken
from dateutil import tz

import settings
from netprintbox.utils import get_namespace, load_template, normalize_name
from netprintbox.exceptions import BecomePendingUser
from netprintbox.template_utils import (
        get_namespace as get_template_namespace,)


TZ_MAP = {
    'JP': 'Asia/Tokyo',
}


class DropboxUser(db.Model):
    uid = db.StringProperty(required=True)
    email = db.StringProperty(required=True)
    display_name = db.StringProperty(indexed=False)
    access_key = db.StringProperty(required=True)
    access_secret = db.StringProperty(required=True, indexed=False)
    pending = db.BooleanProperty(default=False)
    country = db.StringProperty(default='JP')

    def own_files(self):
        return DropboxFileInfo.all().ancestor(self)

    @property
    def is_pending(self):
        return self.pending

    def put_pending_away(self, _save=True):
        self.pending = False
        self.put()

    def put_pending(self, notify=True):
        self.pending = True
        self.put()
        logging.exception("User becomes pending: %s", self.key())
        if notify:
            template = load_template('pending_notification.txt',
                                     namespace=get_template_namespace())
            mail.send_mail(to=self.email,
                    subject=u'Dropbox連携の一時停止',
                    sender=settings.SYSADMIN_ADDRESS,
                    body=template.substitute(user_name=self.display_name))
        raise BecomePendingUser


class FileState(object):
    NEED_NETPRINT_ID, LATEST = range(2)


class DropboxFileInfo(db.Model):
    path = db.StringProperty()
    rev = db.StringProperty(indexed=False)
    size = db.IntegerProperty(indexed=False)
    state = db.IntegerProperty(required=True)
    netprint_id = db.StringProperty()
    # netprint_name = db.StringProperty()
    last_modified = db.DateTimeProperty(required=True)

    def __repr__(self):
        return '<%s %r %s>' % (self.__class__.__name__,
                               self.path,
                               self.netprint_id,)

    def as_netprint_name(self, with_extension=False):
        return normalize_name(self.path, ext=with_extension)

    @property
    def local_last_modified(self):
        country = self.parent().country
        if country in TZ_MAP:
            tzinfo = tz.gettz(TZ_MAP[country])
            utc = tz.gettz('UTC')
            return self.last_modified.replace(tzinfo=utc).astimezone(tzinfo)
        else:
            return self.last_modified


class OAuthRequestToken(object):
    key = None
    token = None

    def __init__(self, key=None, token=None):
        self.key = key
        self.token = token

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
