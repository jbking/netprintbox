# -*- encoding:utf8 -*-
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
from contextlib import contextmanager
import logging
import random
from StringIO import StringIO

from google.appengine.api import taskqueue
from webob import exc
import webapp2 as w

import settings
from netprint import UnexpectedContent
from netprintbox.data import DropboxUser
from netprintbox.exceptions import (
        InvalidNetprintAccountInfo,
        OverLimit, PendingUser,
        DropboxServiceUnavailable, DropboxServerError
)
from netprintbox.utils import load_template
from settings import SLEEP_WAIT


class AuthHandler(w.RequestHandler):
    def get(self):
        from netprintbox.service import DropboxService

        callback_url = self.uri_for('authorize_callback', _full=True)
        authz_url = DropboxService.build_authorize_url(callback_url)
        raise exc.HTTPFound(location=authz_url)


class AuthCallbackHandler(w.RequestHandler):
    def get(self):
        from netprintbox.service import DropboxService

        request_key = self.request.GET['oauth_token']
        user = DropboxService.setup_user(request_key)
        setup_url = self.uri_for('setup_guide', key=user.access_key)
        raise exc.HTTPFound(location=setup_url)


class CronHandler(w.RequestHandler):
    def get(self):
        for user in DropboxUser.all():
            if not user.is_pending:
                # XXX check the need to sync?
                taskqueue.add(url=self.uri_for('check_for_user'),
                              params={'key': user.key()},
                              countdown=random.randint(0, SLEEP_WAIT))


@contextmanager
def handling_task_exception(user):
    try:
        yield
    except (PendingUser, OverLimit):
        logging.exception('user: %s', user.email)
    except (DropboxServiceUnavailable, DropboxServerError):
        logging.exception('user: %s', user.email)
    except (InvalidNetprintAccountInfo,):
        logging.exception('user: %s', user.email)
    except (UnexpectedContent,):
        logging.exception('user: %s', user.email)
    except:
        logging.exception('unexpected exception: %s', user.email)


class SyncWorker(w.RequestHandler):
    def post(self):
        from netprintbox.service import NetprintboxService

        user_key = self.request.get('key')
        user = DropboxUser.get(user_key)
        logging.debug("Checking for: %s", user.email)

        with handling_task_exception(user):
            service = NetprintboxService(user)
            service.sync()
            taskqueue.add(url=self.uri_for('make_report_for_user'),
                          params={'key': user_key},
                          countdown=random.randint(0, SLEEP_WAIT))


class MakeReportHandler(w.RequestHandler):
    def post(self):
        from netprintbox.service import NetprintboxService

        user_key = self.request.get('key')
        user = DropboxUser.get(user_key)
        logging.debug("Making report for: %s", user.email)

        with handling_task_exception(user):
            service = NetprintboxService(user)
            service.make_report()


class SetupGuide(w.RequestHandler):
    def get(self):
        from netprintbox.service import NetprintboxService, NetprintService
        from netprintbox.exceptions import (
                DropboxNotFound, InvalidNetprintAccountInfo)

        key = self.request.GET['key']
        q = DropboxUser.all().filter('access_key = ', key)
        if q.count() != 1:
            raise exc.HTTPUnauthorized

        user = q.get()
        service = NetprintboxService(user)

        if user.is_pending:
            self.need_reauthorize()

        need_to_create_account_info = False
        try:
            info = service.dropbox.list(settings.ACCOUNT_INFO_PATH)
            need_to_create_account_info = info.get('is_deleted', False)
        except DropboxNotFound:
            need_to_create_account_info = True
        if need_to_create_account_info:
            service.dropbox.put(settings.ACCOUNT_INFO_PATH, StringIO(
            "[netprint]\n"
            "username=\n"
            "password="))
            self.step1(key)
            return

        try:
            (username, password) = service.load_netprint_account_info()
            netprint_service = NetprintService(username, password)
            netprint_service.client
        except (DropboxNotFound, InvalidNetprintAccountInfo):
            self.step1(key, error=True)
        else:
            user = q.get()
            taskqueue.add(url=self.uri_for('check_for_user'),
                          params={'key': user.key()})
            self.step2()

    def need_reauthorize(self):
        from netprintbox.service import DropboxService

        callback_url = self.uri_for('authorize', _full=True)
        authz_url = DropboxService.build_authorize_url(callback_url)
        raise exc.HTTPFound(location=authz_url)

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


class TopHandler(w.RequestHandler):
    def get(self):
        template = load_template('top.html')
        response = exc.HTTPOk()
        response.body = template.substitute()
        raise response
