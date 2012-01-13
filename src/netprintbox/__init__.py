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


def includeme(config):
    # dropbox authz
    config.add_route('authorize', '/dropbox/authorize')
    config.add_route('authorize_callback', '/dropbox/callback')
    config.add_route('login_callback', '/dropbox/login/callback')
    config.add_route('login', '/dropbox/login')

    # task
    TASK_PREFIX = '/task'
    config.add_route('sync_all', TASK_PREFIX + '/sync')
    config.add_route('sync_for_user', TASK_PREFIX + '/check')
    config.add_route('make_report_for_user', TASK_PREFIX + '/make_report')

    # setup
    config.add_route('setup_guide', '/guide/setup')

    # feature
    config.add_route('top', '/')
    config.add_route('list_file', '/list')
    config.add_route('pin', '/pin')
    config.add_route('do_sync_for_user', '/sync')
    config.add_route('logout', '/login')

    config.scan('netprintbox.views')
