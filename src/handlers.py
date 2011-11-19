import logging

from google.appengine.api import taskqueue
import webapp2
import dropbox
import httplib2

import netprint
from commands.dropbox import delete_file, load_netprint_account_info
from commands.netprintbox import sync_dropbox_netprint, put_from_dropbox
import settings
import data
from utils import random_sleep


if settings.DEBUG:
    httplib2.debuglevel = 1


def get_session():
    return dropbox.session.DropboxSession(settings.DROPBOX_APP_KEY,
                                          settings.DROPBOX_APP_SECRET,
                                          settings.DROPBOX_ACCESS_TYPE)


class AuthHandler(webapp2.RequestHandler):
    def get(self):
        session = get_session()
        request_token = session.obtain_request_token()
        token = data.OAuthRequestToken()
        token.key = request_token.key
        token.token = str(request_token)
        token.put()
        callback_url = 'http://localhost:8080/dropbox_callback'
        authz_url = session.build_authorize_url(request_token, callback_url)
        self.response.status = 302
        self.response.headerlist = [('Location', authz_url)]


class AuthCallbackHandler(webapp2.RequestHandler):
    def get(self):
        key = self.request.GET['oauth_token']
        request_token = data.OAuthRequestToken.get(key)

        session = get_session()
        session.obtain_access_token(request_token)
        client = dropbox.client.DropboxClient(session)
        account_info = client.account_info()

        user = data.DropboxUser(uid=str(account_info['uid']),
                                email=account_info['email'],
                                display_name=account_info['display_name'],
                                access_key=session.token.key,
                                access_secret=session.token.secret)
        user.put()

        data.OAuthRequestToken.delete(key)

        self.response.status = 200
        self.response.write("Saved :)")


class CronHandler(webapp2.RequestHandler):
    def get(self):
        for key in data.DropboxUser.all(keys_only=True):
            taskqueue.add(url='/task/check', params={'key': key})


# XXX need user ref to ignore filename conflict.
def custom_put(dropbox_client, netprint_client,
               dropbox_item, netprint_item):
    # detect only situation a file in dropbox but not in netprint.
    if dropbox_item is not None and netprint_item is None:
        path = dropbox_item['path']
        rev = dropbox_item['rev']

        # excludes system generating files at all.
        if path in ('/account.ini', '/report.txt'):
            return

        query = data.DropboxFileInfo.all().filter('path = ', path)
        # XXX transaction control
        if query.count() == 0:
            info = data.DropboxFileInfo(path=path,
                                        rev=rev)
            info.put()
        elif query.count() == 1:
            # Current strategy for existing entry:
            # 1. upload new one if file is updated.
            # 2. delete entry from datastore and dropbox otherwise.
            info = query.get()
            if info.rev == rev:
                info.delete()
                delete_file(dropbox_client, path)
                return
            info.rev = rev
            info.put()
        else:
            raise ValueError("Duplicated path? %s" % path)
        put_from_dropbox(dropbox_client, netprint_client,
                         dropbox_item, netprint_item)


class QueueWorker(webapp2.RequestHandler):
    def post(self):
        if settings.DEBUG:
            logging.getLogger().setLevel(logging.DEBUG)

        key = self.request.get('key')

        random_sleep()

        user = data.DropboxUser.get(key)
        session = get_session()
        session.set_token(user.access_key, user.access_secret)

        dropbox_client = dropbox.client.DropboxClient(session)
        (netprint_username, netprint_password) = \
                load_netprint_account_info(dropbox_client)
        netprint_client = netprint.Client(httplib2.Http(),
                                          settings.USER_AGENT)
        netprint_client.login(netprint_username, netprint_password)
        sync_dropbox_netprint(dropbox_client, netprint_client, custom_put)

        for item in netprint_client.list():
            logging.debug(item._asdict())
