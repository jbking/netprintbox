from ConfigParser import ConfigParser
from StringIO import StringIO
from dropbox_utils import traverse


def ls(client, path):
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
    res = client.get_file(path)
    file_obj = StringIO(res.read())
    file_obj.name = path
    return file_obj


def put_file(client, path, file_obj, overwrite=True):
    return client.put_file(path, file_obj, overwrite=overwrite)


def delete_file(client, path):
    return client.file_delete(path)


def load_netprint_account_info(client, path='/account.ini'):
    config = ConfigParser()
    config.readfp(obtain_file(client, path))
    return (config.get('netprint', 'username'),
            config.get('netprint', 'password'))

