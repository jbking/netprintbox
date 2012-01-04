from urlparse import parse_qs

from pyramid import testing
from nose.plugins.attrib import attr
from google.appengine.ext import testbed
from minimock import mock, restore

from utils import create_user, TestBase


class HandlerTestBase(TestBase):
    def setUp(self):
        super(HandlerTestBase, self).setUp()
        self.testbed.init_taskqueue_stub()
        self.testbed.init_datastore_v3_stub()
        self.taskqueue_stub = \
                self.testbed.get_stub(testbed.TASKQUEUE_SERVICE_NAME)

    def tearDown(self):
        super(HandlerTestBase, self).tearDown()
        restore()


class SyncAll(HandlerTestBase):
    @attr('integration', 'light')
    def test_it(self):
        from netprintbox.views import sync_all

        user = create_user()
        request = testing.DummyRequest()
        sync_all(request)

        tasks = self.taskqueue_stub.get_filtered_tasks()
        self.assertEqual(len(tasks), 1)
        task = tasks[0]
        self.assertEqual(task.url, request.route_path('sync_for_user'))
        self.assertEqual(parse_qs(task.payload)['key'][0], str(user.key()))


class SyncForUser(HandlerTestBase):
    def setUp(self):
        super(SyncForUser, self).setUp()

        # mockout
        import netprintbox.service

        class service(object):
            def sync(self):
                self.called = True
        self.service = service()
        mock('netprintbox.service.NetprintboxService',
             returns=self.service)

    @attr('integration', 'light')
    def test_it(self):
        from netprintbox.views import sync_for_user

        user = create_user()
        request = testing.DummyRequest({'key': str(user.key())})
        self.setUpPyramid(request=request)

        sync_for_user(request)

        self.assertTrue(self.service.called)
        tasks = self.taskqueue_stub.get_filtered_tasks()
        self.assertEqual(len(tasks), 1)
        task = tasks[0]
        self.assertEqual(task.url, request.route_path('make_report_for_user'))
        self.assertEqual(parse_qs(task.payload)['key'][0], str(user.key()))


class MakeReportForUser(HandlerTestBase):
    def setUp(self):
        super(MakeReportForUser, self).setUp()

        # mockout
        import netprintbox.service

        class service(object):
            def make_report(self):
                self.called = True
        self.service = service()
        mock('netprintbox.service.NetprintboxService',
             returns=self.service)

    @attr('integration', 'light')
    def test_it(self):
        from netprintbox.views import make_report_for_user

        user = create_user()
        request = testing.DummyRequest({'key': str(user.key())})
        self.setUpPyramid(request=request)

        make_report_for_user(request)

        self.assertTrue(self.service.called)
