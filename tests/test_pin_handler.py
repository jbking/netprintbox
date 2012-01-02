import json

from pyramid import testing
from nose.plugins.attrib import attr

from utils import create_user, create_file_info, TestBase


class PinHandlerTest(TestBase):
    def setUp(self):
        super(PinHandlerTest, self).setUp()
        self.testbed.init_datastore_v3_stub()

    @attr('integration', 'light')
    def test_it(self):
        from netprintbox.data import DropboxFileInfo
        from netprintbox.views import pin as pin_view

        report_token = 'a_token'
        user = create_user(report_token=report_token)
        file_info = create_file_info(user)

        def post(key, pin, expected):
            data = {'file_key': key, 'pin': pin,
                    'report_token': report_token}
            request = testing.DummyRequest(
                    headers={'Content-Type': 'application/json'},
                    body=json.dumps(data))
            response = pin_view(request)
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
