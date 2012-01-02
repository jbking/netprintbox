import json
from unittest import TestCase

from nose.plugins.attrib import attr

from utils import create_user, create_file_info, get_blank_request, uri_for


class PinHandlerTest(TestCase):
    def setUp(self):
        from google.appengine.ext.testbed import Testbed

        self.testbed = Testbed()
        self.testbed.activate()
        self.testbed.init_datastore_v3_stub()

    def tearDown(self):
        self.testbed.deactivate()

    def _getAUT(self):
        from netprintbox.main import app
        return app

    @attr('functional', 'light')
    def test_it(self):
        from netprintbox.data import DropboxFileInfo

        report_token = 'a_token'
        user = create_user(report_token=report_token)
        file_info = create_file_info(user)
        app = self._getAUT()
        uri = uri_for('pin')

        def post(key, pin, expected):
            data = {'file_key': key, 'pin': pin,
                    'report_token': report_token}
            request = get_blank_request(uri)
            request.method = 'POST'
            request.content_type = 'application/json'
            request.body = json.dumps(data)
            response = request.get_response(app)
            self.assertEqual(response.status_int, 200)
            self.assertEqual(response.headers['Access-Control-Allow-Origin'],
                             '*')
            self.assertEqual(response.headers['Content-Type'],
                             'application/json')
            result = json.loads(response.body)
            self.assertEqual(result['pin'], pin)

            modified_file_info = DropboxFileInfo.get(key)
            self.assertEqual(modified_file_info.pin, expected)

        file_key = str(file_info.key())
        post(file_key, 'on', True)
        post(file_key, 'off', False)
