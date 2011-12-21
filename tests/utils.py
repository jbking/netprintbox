from datetime import datetime

from netprint import Item
from netprintbox import data


def create_user(**kwargs):
    default = {
            'uid': 'uid',
            'email': 'email',
            'display_name': 'display_name',
            'access_key': 'access_key',
            'access_secret': 'access_secret',
            'country': 'JP',
        }
    params = dict(default)
    params.update(kwargs)
    user = data.DropboxUser(**params)
    user.put()
    return user


def create_file_info(user, **kwargs):
    default = {
            'path': '/A4/path.doc',
            'rev': 'rev',
            'size': 1,
            'state': data.FileState.NEED_NETPRINT_ID,
            'netprint_name': 'A4_path',
            'last_modified': datetime.now(),
        }
    params = dict(default)
    params['parent'] = user
    params.update(kwargs)
    file_info = data.DropboxFileInfo(**params)
    file_info.put()
    return file_info


def create_netprint_item(**kwargs):
    default = {
            'id': 'id',
            'name': 'name',
            'file_size': '0MB',
            'paper_size': 'A4',
            'page_numbers': 1,
            'valid_date': '1900/01/01',
        }
    params = dict(default)
    params.update(kwargs)
    return Item(**params)


def create_dropbox_item(**kwargs):
    default = {
            'is_dir': False,
            'path': 'path',
            'bytes': 0,
            'rev': 'rev',
            'modified': "Sat, 21 Aug 2010 22:31:20 +0000"}
    params = dict(default)
    params.update(kwargs)
    return params


def get_blank_request():
    from netprintbox.main import app
    from webapp2 import Request

    request = Request.blank('/')
    request.app = app
    return request


def set_request_local(request=None):
    from webapp2 import _local
    if request is None:
        request = get_blank_request()
    _local.request = request
