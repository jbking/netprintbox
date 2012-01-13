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


from collections import OrderedDict
from pyramid.threadlocal import get_current_request


def categorize_by(key, item_list, reverse=False):
    """ Categorize item list(list of dict) by the key.

    An utility function for template. """
    _dict = {}
    for item in item_list:
        _dict.setdefault(item[key], []).append(item)
    return OrderedDict(sorted(_dict.items(), key=lambda t: t[0],
                              reverse=reverse))


def get_namespace(request=None):
    from netprintbox.data import DropboxUser
    if request is None:
        request = get_current_request()
    if 'netprintbox.dropbox_user.key' in request.session:
        key = request.session['netprintbox.dropbox_user.key']
        user = DropboxUser.get(key)
    else:
        user = None
    return {
            'categorize_by': categorize_by,
            'route_path': request.route_path,
            'route_url': request.route_url,
            'user': user,
            }
