import json

from webob import exc
from pyramid.view import view_config

from netprintbox.utils import load_template

# sub views.
from setup_guide import *
from taskqueue_handler import *
from dropbox_authz import *


@view_config(route_name='pin', request_method='POST')
def pin(request):
    from netprintbox.data import DropboxUser, DropboxFileInfo

    data = json.loads(request.body)
    report_token = data['report_token']
    q = DropboxUser.all().filter('report_token = ', report_token)
    if q.count() == 1:
        user = q.get()
    else:
        raise exc.HTTPUnauthorized("The report_token is not found.")
    file_info = DropboxFileInfo.get(data['file_key'])
    if file_info.parent().uid != user.uid:
        raise exc.HTTPUnauthorized("The file_key is not found.")
    if data['pin'] == 'on':
        file_info.pin = True
    elif data['pin'] == 'off':
        file_info.pin = False
    else:
        raise ValueError
    file_info.put()

    response = request.response
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Content-Type'] = 'application/json'
    response.body = json.dumps({'pin': data['pin']})
    return response


@view_config(route_name='top', request_method='GET')
def top(request):
    template = load_template('top.html', request=request)
    response = request.response
    response.body = template.substitute()
    return response
