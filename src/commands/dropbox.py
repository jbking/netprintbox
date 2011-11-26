import logging
from ConfigParser import ConfigParser
from StringIO import StringIO

import settings
from dropbox_utils import traverse, ensure_binary_string


def ls(client, path):
    path = ensure_binary_string(path)
    logging.debug(u"Listing metadata of: %r", path)
    return client.metadata(path)


def ls_rec(client, path):
    result = ls(client, path)
    if result['is_dir']:
        def _ls_rec(data):
            if data['is_dir']:
                data.update(ls(client, data['path']))

        traverse(_ls_rec, result)
    return result


def obtain_file(client, path):
    path = ensure_binary_string(path)
    logging.debug(u"Obtaining file: %r", path)
    res = client.get_file(path)
    file_obj = StringIO(res.read())
    file_obj.name = path
    return file_obj


def put_file(client, path, file_obj, overwrite=True):
    path = ensure_binary_string(path)
    logging.debug(u"Putting file: %r", path)
    return client.put_file(path, file_obj, overwrite=overwrite)


def delete_file(client, path):
    path = ensure_binary_string(path)
    logging.debug(u"Deleting file: %r", path)
    return client.file_delete(path)


def load_netprint_account_info(client, path=settings.ACCOUNT_INFO_PATH):
    config = ConfigParser()
    config.readfp(obtain_file(client, path))
    username = config.get('netprint', 'username')
    password = config.get('netprint', 'password')
    if username.strip() and password.strip():
        return (username, password)
    else:
        raise ValueError
