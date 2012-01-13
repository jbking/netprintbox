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
