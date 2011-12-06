import logging
from google.appengine.ext import db
from google.appengine.api import memcache
from oauth.oauth import OAuthToken


class DropboxUser(db.Model):
    uid = db.StringProperty(required=True)
    email = db.StringProperty(required=True)
    display_name = db.StringProperty(indexed=False)
    access_key = db.StringProperty(required=True)
    access_secret = db.StringProperty(required=True, indexed=False)

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
        return OAuthToken.from_string(memcache.get(key))

    def put(self):
        if self.key is None or self.token is None:
            raise ValueError
        logging.debug(u"Saving token: %s", self.token)
        memcache.set(self.key, str(self.token))

    @staticmethod
    def delete(key):
        logging.debug(u"Deleting token by key: %s", key)
        memcache.delete(key)
