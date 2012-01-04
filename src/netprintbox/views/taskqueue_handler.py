import random
import logging
from contextlib import contextmanager

from pyramid.view import view_config
from google.appengine.api import taskqueue

from netprintbox.settings import SLEEP_WAIT


@view_config(route_name='sync_all')
def sync_all(request):
    from netprintbox.data import DropboxUser

    for user in DropboxUser.all():
        if not user.is_pending:
            # XXX check the need to sync?
            taskqueue.add(url=request.route_path('sync_for_user'),
                          params={'key': user.key()},
                          countdown=random.randint(0, SLEEP_WAIT))


@contextmanager
def handling_task_exception(user):
    from netprint import UnexpectedContent
    from netprintbox.exceptions import (
            InvalidNetprintAccountInfo,
            OverLimit, PendingUser,
            DropboxServiceUnavailable, DropboxServerError
    )
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


@view_config(route_name='sync_for_user')
def sync_for_user(request):
    from netprintbox.service import NetprintboxService
    from netprintbox.data import DropboxUser

    user_key = request.GET['key']
    user = DropboxUser.get(user_key)
    logging.debug("Checking for: %s", user.email)

    with handling_task_exception(user):
        service = NetprintboxService(user)
        service.sync()
        taskqueue.add(url=request.route_path('make_report_for_user'),
                      params={'key': user_key},
                      countdown=random.randint(0, SLEEP_WAIT))


@view_config(route_name='make_report_for_user')
def make_report_for_user(request):
    from netprintbox.service import NetprintboxService
    from netprintbox.data import DropboxUser

    user_key = request.GET['key']
    user = DropboxUser.get(user_key)
    logging.debug("Making report for: %s", user.email)

    with handling_task_exception(user):
        service = NetprintboxService(user)
        service.make_report()
