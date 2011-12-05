# -*- coding:utf8 -*-
import logging
import random
from StringIO import StringIO

from google.appengine.api import taskqueue
from webob import exc
import webapp2
import dropbox

import settings
from netprintbox.data import DropboxUser
from netprintbox.utils import load_template
from netprintbox.service import DropboxService, NetprintboxService
from settings import SLEEP_WAIT


class AuthHandler(webapp2.RequestHandler):
    def get(self):
        callback_url = 'http://%s/dropbox/callback' % self.request.host
        authz_url = DropboxService.build_authorize_url(callback_url)
        raise exc.HTTPFound(location=authz_url)


class AuthCallbackHandler(webapp2.RequestHandler):
    def get(self):
        request_key = self.request.GET['oauth_token']
        user = DropboxService.setup_user(request_key)
        setup_url = '/guide/setup?key=%s' % user.access_key
        raise exc.HTTPFound(location=setup_url)


class CronHandler(webapp2.RequestHandler):
    def get(self):
        for key in DropboxUser.all(keys_only=True):
            # XXX check the need to sync?
            taskqueue.add(url='/task/check', params={'key': key},
                          countdown=random.randint(0, SLEEP_WAIT))


class QueueWorker(webapp2.RequestHandler):
    def post(self):
        user_key = self.request.get('key')
        service = NetprintboxService(user_key)
        service.sync()
        service.make_report()


class SetupGuide(webapp2.RequestHandler):
    def get(self):
        key = self.request.GET['key']
        q = DropboxUser.all().filter('access_key = ', key)
        if q.count() != 1:
            raise exc.HTTPUnauthorized

        user = q.get()
        service = NetprintboxService(user)

        need_to_create_account_info = False
        try:
            info = service.dropbox.list(settings.ACCOUNT_INFO_PATH)
            need_to_create_account_info = info.get('is_deleted', False)
        except dropbox.rest.ErrorResponse:
            need_to_create_account_info = True
        if need_to_create_account_info:
            service.dropbox.put(settings.ACCOUNT_INFO_PATH, StringIO(
            "[netprint]\n"
            "username=\n"
            "password="))
            self.step1(key)
            return

        try:
            service.load_netprint_account_info()
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
        response = exc.HTTPOk()
        response.body = template.substitute(key=key, error=error)
        raise response

    def step2(self, error=True):
        """ account info is correct, but not synced yet """
        template = load_template('step2.html')
        response = exc.HTTPOk()
        response.body = template.substitute(error=error)
        raise response
