from unittest import TestCase
from nose.plugins.attrib import attr


class TopTest(TestCase):
    def _getAUT(self):
        from main import app
        return app

    @attr('functional', 'light')
    def test_guide(self):
        app = self._getAUT()
        response = app.get_response('/')
        self.assertEqual(response.status_int, 200)
