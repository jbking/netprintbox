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

import tempita
import settings

from netprintbox.template_utils import get_namespace as get_template_namespace


def load_template(path, namespace={}):
    n = get_template_namespace()
    n.update(namespace)
    return tempita.HTMLTemplate(
            open(os.path.join(settings.TEMPLATE_PATH, path)).read(),
            namespace=n)


def normalize_name(path):
    return os.path.basename(path).split(os.path.extsep)[0]


def is_generated_file(path):
    return path in (settings.ACCOUNT_INFO_PATH, settings.REPORT_PATH)


def get_namespace():
    return os.environ.get('CURRENT_VERSION_ID')
