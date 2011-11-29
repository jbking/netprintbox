# -*- coding:utf8 -*-
import logging
from StringIO import StringIO

from google.appengine.api import taskqueue
from webob import exc
import webapp2
import dropbox
import httplib2

import netprint
from netprintbox import data
from netprintbox.transaction import SyncTransaction
from dropbox_commands import ls, load_netprint_account_info, put_file
from netprintbox_commands import sync_dropbox_netprint
import settings
from utils import random_sleep, load_template
from dropbox_utils import get_session


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

        item_list = []
        for item in netprint_client.list():
            item_dict = item._asdict()
            file_info = user.own_files()\
                        .filter('netprint_name = ', item.name).get()
            if file_info:
                file_info.netprint_id = item.id
                file_info.put()
                item_dict['managed'] = True
            else:
                item_dict['managed'] = False
            item_list.append(item_dict)
        # XXX don't make report when no changes.
        template = load_template('report.html')
        put_file(dropbox_client, settings.REPORT_PATH,
                 StringIO(template.substitute(item_list=item_list)))


class SetupGuide(webapp2.RequestHandler):
    def get(self):
        key = self.request.GET['key']
        q = data.DropboxUser.all().filter('access_key = ', key)
        if q.count() != 1:
            raise exc.HTTPUnauthorized

        user = q.get()

        session = get_session()
        session.set_token(user.access_key, user.access_secret)
        client = dropbox.client.DropboxClient(session)

        create_account_info = False
        try:
            info = ls(client, settings.ACCOUNT_INFO_PATH)
            create_account_info = info.get('is_deleted', False)
        except dropbox.rest.ErrorResponse:
            create_account_info = True
        if create_account_info:
            put_file(client, settings.ACCOUNT_INFO_PATH, StringIO(""
"""[netprint]
username=
password=
"""))
            self.step1(key)
            return

        try:
            load_netprint_account_info(client)
        except (dropbox.rest.ErrorResponse, ValueError):
            self.step1(key, error=True)
        else:
            user = q.get()
            taskqueue.add(url='/task/check', params={'key': user.key})
            self.step2()

    def step1(self, key, error=False):
        """ no account info """
        logging.info("SETP1 with error: %s", error)
        template = load_template('step1.html')
        self.response.write(template.substitute(key=key, error=error))

    def step2(self, error=True):
        """ account info is correct, but not synced yet """
        template = load_template('step2.html')
        self.response.write(template.substitute(error=error))
