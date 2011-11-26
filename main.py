import sys
sys.path.insert(0, 'bundle')
sys.path.insert(0, 'src')

import webapp2
import httplib2

import handlers
import settings


if settings.DEBUG:
    httplib2.debuglevel = 1


app = webapp2.WSGIApplication([
    (r'/dropbox/authorize', handlers.AuthHandler),
    (r'/dropbox/callback', handlers.AuthCallbackHandler),
    (r'/task/sync', handlers.CronHandler),
    (r'/task/check', handlers.QueueWorker),
    (r'/guide/setup', handlers.SetupGuide),
    ])
