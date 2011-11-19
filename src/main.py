from commands import dropbox
from dropbox_utils import traverse
from netprint_utils import normalize_name


def collect_entries(data):
    result = {}

    def _collect_entries(data):
        if not data['is_dir']:
            result[normalize_name(data['path'])] = data

    traverse(_collect_entries, data)
    return result


def map_netprint_result(data):
    result = {}
    for item in data:
        dict_item = item._asdict()
        result[dict_item['name']] = dict_item
    return result


def transfer_from_dropbox(dropbox_client, netprint_client):
    item_in_dropbox = collect_entries(dropbox.ls_rec(dropbox_client, '/'))
    item_in_netprint = map_netprint_result(netprint_client.list())
    for (item_name, item) in item_in_dropbox.items():
        if item_name not in item_in_netprint:
            file_obj = dropbox.obtain_file(dropbox_client, item['path'])
            netprint_client.send(file_obj)
