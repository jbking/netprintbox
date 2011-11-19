import sys
sys.path.insert(0, 'bundle')
sys.path.insert(0, 'src')

import logging
logging.getLogger().setLevel(logging.DEBUG)
import webapp2
import handlers


app = webapp2.WSGIApplication([
    (r'/dropbox', handlers.AuthHandler),
    (r'/dropbox_callback', handlers.AuthCallbackHandler),
    (r'/task/sync', handlers.CronHandler),
    (r'/task/check', handlers.QueueWorker),
    ])
