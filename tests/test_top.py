from pyramid import testing
from nose.plugins.attrib import attr

from utils import TestBase


class TopTest(TestBase):
    @attr('integration', 'light')
    def test_guide(self):
        from netprintbox.views import top
        request = testing.DummyRequest()
        response = top(request)
        self.assertEqual(response.status_int, 200)
