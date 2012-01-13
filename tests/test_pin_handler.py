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

        token = 'a_token'
        user = create_user()
        file_info = create_file_info(user)

        def post(key, pin, expected):
            data = {'file_key': key, 'pin': pin,
                    'token': token}

            class session(object):
                def get_csrf_token(self):
                    return token

                def __getitem__(self, key):
                    if key == 'netprintbox.dropbox_user.key':
                        return str(user.key())
                    else:
                        raise KeyError

            request = testing.DummyRequest(
                    headers={'Content-Type': 'application/json'},
                    body=json.dumps(data))
            request.session = session()
            response = pin_view(request)
            self.assertEqual(response.status_int, 200)
            result = json.loads(response.body)
            self.assertEqual(result['pin'], expected)

            modified_file_info = DropboxFileInfo.get(key)
            self.assertEqual(modified_file_info.pin, expected)

        file_key = str(file_info.key())
        post(file_key, 'on', True)
        post(file_key, 'off', False)
