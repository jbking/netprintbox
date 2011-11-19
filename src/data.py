from google.appengine.ext import db


class DropboxUser(db.Model):
    uid = db.StringProperty(required=True)
    email = db.StringProperty(required=True)
    display_name = db.StringProperty(indexed=False)
    access_key = db.StringProperty(required=True, indexed=False)
    access_secret = db.StringProperty(required=True, indexed=False)


class DropboxFileInfo(db.Model):
    path = db.StringProperty(required=True)
    modified = db.DateTimeProperty(required=True, indexed=False)
