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


from webob import exc
from pyramid.view import view_config


@view_config(route_name='authorize', request_method='GET')
def authorize(request):
    from netprintbox.service import DropboxService

    callback_url = request.route_url('authorize_callback')
    authz_url = DropboxService.build_authorize_url(callback_url)
    return exc.HTTPFound(location=authz_url)


@view_config(route_name='authorize_callback', request_method='GET')
def authorize_callback(request):
    from netprintbox.service import DropboxService

    request_key = request.GET['oauth_token']
    user = DropboxService.setup_user(request_key)
    request.session['netprintbox.dropbox_user.key'] = str(user.key())
    setup_url = request.route_path('setup_guide')
    return exc.HTTPFound(location=setup_url)


@view_config(route_name='login', request_method='GET')
def login(request):
    from netprintbox.service import DropboxService

    callback_url = request.route_url('login_callback')
    authz_url = DropboxService.build_authorize_url(callback_url)
    return exc.HTTPFound(location=authz_url)


@view_config(route_name='logout', request_method='GET')
def logout(request):
    request.session.invalidate()
    url = request.route_path('top')
    return exc.HTTPFound(location=url)


@view_config(route_name='login_callback', request_method='GET')
def login_callback(request):
    from netprintbox.service import DropboxService

    request_key = request.GET['oauth_token']
    user = DropboxService.setup_user(request_key)
    request.session['netprintbox.dropbox_user.key'] = str(user.key())
    url = request.route_path('top')
    return exc.HTTPFound(location=url)
