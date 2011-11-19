import sys
sys.path.insert(0, 'bundle')
sys.path.insert(0, 'src')

import webapp2
from commands.netprintbox import sync_dropbox_netprint, put_from_dropbox
import handlers


def custom_put(dropbox_client, netprint_client,
               dropbox_item, netprint_item):
    excludes = ['/account.ini', '/report.txt']
    if ((dropbox_item is not None and dropbox_item['path'] not in excludes)
        and netprint_item is None):
        put_from_dropbox(dropbox_client, netprint_client,
                         dropbox_item, netprint_item)


def main(dropbox_client, netprint_client):
    sync_dropbox_netprint(dropbox_client, netprint_client, custom_put)


app = webapp2.WSGIApplication([
    (r'/dropbox', handlers.AuthHandler),
    (r'/dropbox_callback', handlers.AuthCallbackHandler),
    ])
