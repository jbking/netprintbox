# -*- coding:utf8 -*-
import logging

from google.appengine.api import taskqueue
from google.appengine.ext import db
import webapp2
import dropbox
import httplib2

import netprint
from netprint_utils import normalize_name
from commands.dropbox import (ls, delete_file as dropbox_delete_file,
                              load_netprint_account_info)
from commands.netprintbox import sync_dropbox_netprint, put_from_dropbox
from commands.netprint import delete_file as netprint_delete_file
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
        callback_url = 'http://%s/dropbox/callback' % str(self.request.host)
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

        uid = str(account_info['uid'])
        q = data.DropboxUser.all().filter('uid = ', uid)
        if q.count() == 0:
            user = data.DropboxUser(uid=uid,
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

        data.OAuthRequestToken.delete(key)

        redirect_url = '/guide/setup?key=%s' % user.access_key
        self.response.status = 302
        self.response.headerlist = [('Location', redirect_url)]


class CronHandler(webapp2.RequestHandler):
    def get(self):
        for key in data.DropboxUser.all(keys_only=True):
            taskqueue.add(url='/task/check', params={'key': key})


class SyncTransaction(object):
    def __init__(self, dropbox_user):
        self.dropbox_user = dropbox_user

    def sync(self, dropbox_client, netprint_client,
                   dropbox_item, netprint_item):
        # detect only situation a file in dropbox but not in netprint.
        if dropbox_item is not None and netprint_item is None:
            path = dropbox_item['path']
            rev = dropbox_item['rev']

            # excludes system generating files at all.
            if path in (settings.ACCOUNT_INFO_PATH, settings.REPORT_PATH):
                return

            def txn():
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
                        # waiting for id assiging.
                        return
                    else:
                        # delete entry from datastore and dropbox otherwise.
                        file_info.delete()
                        dropbox_delete_file(dropbox_client, path)
                        return
                else:
                    raise ValueError("Duplicated path? %s" % path)
                put_from_dropbox(dropbox_client, netprint_client,
                                 dropbox_item, netprint_item)
            db.run_in_transaction(txn)

        if dropbox_item is None and netprint_item is not None:
            """
            Delete file and info.
            """
            def txn():
                netprint_id = netprint_item['id']
                query = data.DropboxFileInfo.all()\
                            .ancestor(self.dropbox_user)\
                            .filter('netprint_id = ', netprint_id)

                for file_info in query:
                    file_info.delete()
                netprint_delete_file(netprint_client, netprint_id)
            db.run_in_transaction(txn)


class QueueWorker(webapp2.RequestHandler):
    def post(self):
        key = self.request.get('key')

        random_sleep()

        user = data.DropboxUser.get(key)
        transaction = SyncTransaction(user)

        session = get_session()
        session.set_token(user.access_key, user.access_secret)
        dropbox_client = dropbox.client.DropboxClient(session)
        (netprint_username, netprint_password) = \
                load_netprint_account_info(dropbox_client)
        netprint_client = netprint.Client(httplib2.Http(),
                                          settings.USER_AGENT)
        netprint_client.login(netprint_username, netprint_password)
        sync_dropbox_netprint(dropbox_client, netprint_client,
                              transaction.sync)

        for item in netprint_client.list():
            file_info = data.DropboxFileInfo.all().ancestor(user)\
                    .filter('netprint_name = ', item.name).get()
            if file_info:
                file_info.netprint_id = item.id
                file_info.put()
            # XXX generate report


class SetupGuide(webapp2.RequestHandler):
    def get(self):
        key = self.request.GET['key']
        q = data.DropboxUser.all().filter('access_key = ', key)
        if q.count() != 1:
            self.ignore()
            return

        user = q.get()

        session = get_session()
        session.set_token(user.access_key, user.access_secret)
        client = dropbox.client.DropboxClient(session)

        try:
            ls(client, settings.ACCOUNT_INFO_PATH)
        except dropbox.rest.ErrorResponse:
            self.step1()
            return

        try:
            load_netprint_account_info(client)
        except dropbox.rest.ErrorResponse:
            self.step1(error=True)
        else:
            self.step2()

    def ignore(self):
        self.response.status = 400

    def step1(self, error=True):
        """ no account info """
        logging.info("SETP1 with error: %s", error)
        # XXX put account.ini template if not exists
        self.response.write('step1')

    def step2(self, error=True):
        """ account info is correct, but not synced yet """
        self.response.write('step2')
