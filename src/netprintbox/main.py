import logging

import webapp2
import httplib2

from netprintbox import handlers

if logging.getLogger().level <= logging.DEBUG:
    httplib2.debuglevel = 1


app = webapp2.WSGIApplication([
    (r'/dropbox/authorize', handlers.AuthHandler),
    (r'/dropbox/callback', handlers.AuthCallbackHandler),
    (r'/task/sync', handlers.CronHandler),
    (r'/task/check', handlers.SyncWorker),
    (r'/task/make_report', handlers.MakeReportHandler),
    (r'/guide/setup', handlers.SetupGuide),
    (r'/', handlers.TopHandler),
    ])
