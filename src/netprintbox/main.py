import os
import webapp2 as w

routes = (
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
)

# Into debug mode when this is running under SDK.
debug = os.environ.get('SERVER_SOFTWARE', '').startswith('Dev')


class CustomApplication(w.WSGIApplication):
    def __call__(self, environ, start_response):
        # lazy fixing sys.path for execution in taskqueue.
        from bootstrap import fix_sys_path
        fix_sys_path()

        import httplib2
        if debug:
            httplib2.debuglevel = 1

        return super(CustomApplication, self).\
                __call__(environ, start_response)

from netprintbox.main import routes
app = CustomApplication(routes, debug=debug)
