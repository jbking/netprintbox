# -*- encoding: utf8 -*-
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
import os
import re

import tempita

from netprintbox.settings import (
        TEMPLATE_PATH, ACCOUNT_INFO_PATH, REPORT_PATH)
from netprintbox.template_utils import get_namespace as get_template_namespace


def load_template(path, namespace={}, request=None):
    n = get_template_namespace(request=request)
    n.update(namespace)
    return tempita.HTMLTemplate(
            open(os.path.join(TEMPLATE_PATH, path)).read(),
            namespace=n)


def normalize_name(path, ext=False):
    if path[0] == '/':
        path = path[1:]
    path = path.replace('_', '__')
    path = re.sub(u'[/(「＜＞＆”’」)]', '_', path)
    if not ext:
        path = os.path.splitext(path)[0]
    return path


def is_generated_file(path):
    return path in (ACCOUNT_INFO_PATH, REPORT_PATH)


def get_namespace():
    return os.environ.get('CURRENT_VERSION_ID')
