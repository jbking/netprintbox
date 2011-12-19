from collections import OrderedDict

import webapp2


def categorize_by(key, item_list, reverse=False):
    """ Categorize item list(list of dict) by the key.

    An utility function for template. """
    _dict = {}
    for item in item_list:
        _dict.setdefault(item[key], []).append(item)
    return OrderedDict(sorted(_dict.items(), key=lambda t: t[0],
                              reverse=reverse))


def get_namespace():
    return {
            'categorize_by': categorize_by,
            'uri_for': webapp2.uri_for,
            }
