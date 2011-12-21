import webapp2 as w

app = w.WSGIApplication([
    w.Route('/dropbox/authorize', 'netprintbox.handlers.AuthHandler',
            name='authorize'),
    w.Route(r'/dropbox/callback', 'netprintbox.handlers.AuthCallbackHandler',
            name='authorize_callback'),
    w.Route(r'/task/sync', 'netprintbox.handlers.CronHandler',
            name='sync_all'),
    w.Route(r'/task/check', 'netprintbox.handlers.SyncWorker',
            name='check_for_user'),
    w.Route(r'/task/make_report', 'netprintbox.handlers.MakeReportHandler',
            name='make_report_for_user'),
    w.Route(r'/guide/setup', 'netprintbox.handlers.SetupGuide',
            name='setup_guide'),
    w.Route(r'/', 'netprintbox.handlers.TopHandler',
            name='top'),
    ])
