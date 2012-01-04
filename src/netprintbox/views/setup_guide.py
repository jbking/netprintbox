from StringIO import StringIO

from google.appengine.api import taskqueue
from webob import exc
from pyramid.view import view_config

from netprintbox.utils import load_template
from netprintbox.settings import ACCOUNT_INFO_PATH


def need_reauthorize(request):
    url = request.route_path('authorize')
    raise exc.HTTPFound(location=url)


def step1(request, key, error=False):
    """ no account info """
    template = load_template('step1.html', request=request)
    response = request.response
    response.body = template.substitute(key=key, error=error)
    return response


def step2(request):
    """ account info is correct """
    template = load_template('step2.html', request=request)
    response = request.response
    response.body = template.substitute()
    return response


@view_config(route_name='setup_guide', request_method='GET')
def setup_guide(request):
    from netprintbox.service import NetprintboxService, NetprintService
    from netprintbox.data import DropboxUser
    from netprintbox.exceptions import (
            DropboxNotFound, InvalidNetprintAccountInfo)

    key = request.GET['key']
    q = DropboxUser.all().filter('access_key = ', key)
    if q.count() != 1:
        raise exc.HTTPUnauthorized

    user = q.get()
    service = NetprintboxService(user)

    if user.is_pending:
        need_reauthorize(request)

    need_to_create_account_info = False
    try:
        info = service.dropbox.list(ACCOUNT_INFO_PATH)
        need_to_create_account_info = info.get('is_deleted', False)
    except DropboxNotFound:
        need_to_create_account_info = True
    if need_to_create_account_info:
        service.dropbox.put(ACCOUNT_INFO_PATH, StringIO(
        "[netprint]\n"
        "username=\n"
        "password="))
        return step1(request, key)

    try:
        (username, password) = service.load_netprint_account_info()
        netprint_service = NetprintService(username, password)
        netprint_service.client
    except (DropboxNotFound, InvalidNetprintAccountInfo):
        return step1(request, key, error=True)
    else:
        user = q.get()
        taskqueue.add(url=request.route_url('check_for_user'),
                      params={'key': user.key()})
        return step2(request)
