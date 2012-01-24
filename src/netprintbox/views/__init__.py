"""
    Netprintbox
    Copyright (C) 2012  MURAOKA Yusuke <yusuke@jbking.org>

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
    token = data['token']
    if token != request.session.get_csrf_token():
        raise exc.HTTPForbidden("CSRF token is unmatch.")

    key = request.session['netprintbox.dropbox_user.key']
    user = DropboxUser.get(key)

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

    data = {
        'key': str(file_info.key()),
        'path': file_info.path,
        'netprint_id': file_info.netprint_id,
        'netprint_name': file_info.as_netprint_name(),
        'pin': file_info.pin,
        }

    response = request.response
    response.headers['Content-Type'] = 'application/json'
    response.body = json.dumps(data)
    return response


@view_config(route_name='do_dropbox_sync_for_user', request_method='POST')
def do_dropbox_sync_for_user(request):
    data = json.loads(request.body)
    token = data['token']
    if token != request.session.get_csrf_token():
        raise exc.HTTPForbidden("CSRF token is unmatch.")

    key = request.session['netprintbox.dropbox_user.key']
    taskqueue.add(url=request.route_path('dropbox_sync_for_user'),
                  params={'key': key},
                  countdown=random.randint(0, SLEEP_WAIT))

    response = request.response
    response.headers['Content-Type'] = 'application/json'
    response.body = json.dumps({'message': 'ok'})
    return response


@view_config(route_name='do_sync_for_user', request_method='POST')
def do_sync_for_user(request):
    data = json.loads(request.body)
    token = data['token']
    if token != request.session.get_csrf_token():
        raise exc.HTTPForbidden("CSRF token is unmatch.")

    key = request.session['netprintbox.dropbox_user.key']
    taskqueue.add(url=request.route_path('sync_for_user'),
                  params={'key': key},
                  countdown=random.randint(0, SLEEP_WAIT))

    response = request.response
    response.headers['Content-Type'] = 'application/json'
    response.body = json.dumps({'message': 'ok'})
    return response


@view_config(route_name='list_file', request_method='GET')
def list_file(request):
    from netprintbox.data import DropboxUser

    key = request.session['netprintbox.dropbox_user.key']
    user = DropboxUser.get(key)

    data = [{
        'key': str(file_info.key()),
        'path': file_info.path,
        'netprint_id': file_info.netprint_id,
        'netprint_name': file_info.as_netprint_name(),
        'pin': file_info.pin,
        }
        for file_info in user.own_files()]
    template = load_template('list_file.html', request=request)
    response = request.response
    response.body = template.substitute(
            json_data=json.dumps(data),
            csrf_token=request.session.new_csrf_token())
    return response


@view_config(route_name='top', request_method='GET')
def top(request):
    template = load_template('top.html', request=request)
    response = request.response
    response.body = template.substitute()
    return response
