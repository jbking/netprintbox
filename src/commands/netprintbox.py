from commands import dropbox
from dropbox_utils import traverse
from netprint_utils import normalize_name


def _collect_entries(data):
    result = {}

    def __collect_entries(data):
        if not data['is_dir']:
            result[normalize_name(data['path'])] = data

    traverse(__collect_entries, data)
    return result


def _map_netprint_result(data):
    result = {}
    for item in data:
        dict_item = item._asdict()
        result[dict_item['name']] = dict_item
    return result


def sync_dropbox_netprint(dropbox_client, netprint_client, callback):
    item_in_dropbox = _collect_entries(dropbox.ls_rec(dropbox_client, '/'))
    item_in_netprint = _map_netprint_result(netprint_client.list())

    key_in_both = set(item_in_dropbox) & set(item_in_netprint)
    key_in_dropbox_only = set(item_in_dropbox) - set(item_in_netprint)
    key_in_netprint_only = set(item_in_netprint) - set(item_in_dropbox)

    for key in key_in_both:
        callback(dropbox_client,
                 netprint_client,
                 item_in_dropbox[key],
                 item_in_netprint[key])

    for key in key_in_dropbox_only:
        callback(dropbox_client,
                 netprint_client,
                 item_in_dropbox[key],
                 None)

    for key in key_in_netprint_only:
        callback(dropbox_client,
                 netprint_client,
                 None,
                 item_in_netprint[key])


## callback for sync_dropbox_netprint ###############
def put_from_dropbox(dropbox_client, netprint_client,
                     dropbox_item, netprint_item):
    if dropbox_item is not None and netprint_item is None:
        print('Put %s into netprint' % dropbox_item['path'])
        file_obj = dropbox.obtain_file(dropbox_client, dropbox_item['path'])
        netprint_client.send(file_obj)


def delete_from_dropbox(dropbox_client, netprint_client,
                        dropbox_item, netprint_item):
    if dropbox_item is not None and netprint_item is None:
        print('Delete %s from dropbox' % dropbox_item['path'])
        dropbox.delete_file(dropbox_item['path'])
#####################################################
