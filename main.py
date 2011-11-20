import sys
sys.path.insert(0, 'bundle')
sys.path.insert(0, 'src')

import logging
logging.getLogger().setLevel(logging.DEBUG)
import webapp2
import handlers


app = webapp2.WSGIApplication([
    (r'/dropbox/authorize', handlers.AuthHandler),
    (r'/dropbox/callback', handlers.AuthCallbackHandler),
    (r'/task/sync', handlers.CronHandler),
    (r'/task/check', handlers.QueueWorker),
    ])
