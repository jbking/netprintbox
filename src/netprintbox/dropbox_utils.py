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

ENCODING = 'utf8'


def ensure_binary_string(s):
    if isinstance(s, unicode):
        return s.encode(ENCODING)
    else:
        return s


def traverse(func, data):
    func(data)
    for item in data['contents']:
        if item['is_dir']:
            traverse(func, item)
        else:
            func(item)
