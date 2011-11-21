# -*- encoding: utf8 -*-
import os

from unittest2 import TestCase
from nose import SkipTest
from nose.plugins.attrib import attr


def load_fixture(path):
    return file(os.path.join(os.path.dirname(__file__), path))


class ClientTest(TestCase):
    def _getOUT(self, browser=None):
        from netprint import Client
        return Client(browser)

    @attr('unit', 'light')
    def test_login(self):
        from netprint import Client

        class Ok(object):
            status = 200
            reason = 'Ok'

        class browser(object):
            @staticmethod
            def request(url, method='GET', headers=None, body=None):
                if url == Client.login_url and method == 'GET':
                    return Ok, \
                           load_fixture('data/login.html').read()
                elif url == Client.manage_url and method == 'POST':
                    return Ok, \
                           load_fixture('data/main.html').read()

        client = self._getOUT(browser)
        client.login('username', 'password')
        self.assertEqual(client.session_key,
                "9TubQ6yo1iRnWNk6qnYOlll9rbEmOiUfOFcxdcTLPMkA")

    @attr('unit', 'light')
    def test_login_failed(self):
        from urllib2 import URLError
        from netprint import LoginFailure

        class browser(object):
            @staticmethod
            def open(url):
                raise URLError("Login Failed")

        client = self._getOUT(browser)
        self.assertRaises(LoginFailure, client.login, 'username', 'password')

    @attr('unit', 'light')
    def test_check_trim_content(self):
        from BeautifulSoup import BeautifulSoup

        client = self._getOUT()
        client._soup = BeautifulSoup(load_fixture('data/main.html'))
        client._check_displaying_main_page_then_trim()
        self.assertEqual(client._soup.name, 'table')
        self.assertIsNone(client._soup.previousSibling)
        self.assertIsNone(client._soup.parent)
        self.assertIsNone(client._soup.nextSibling)

    @attr('unit', 'light')
    def test_list(self):
        from BeautifulSoup import BeautifulSoup

        client = self._getOUT()
        client._soup = BeautifulSoup(load_fixture('data/main.html'))
        client._check_displaying_main_page_then_trim()
        item_list = client.list()
        self.assertEqual(len(item_list), 1)

        item = item_list[0]
        self.assertEqual(item.id, 'QNA7HNEE')
        self.assertEqual(item.name, unicode('チケット印刷画面', 'utf8'))
        self.assertEqual(item.file_size, '832KB')
        self.assertEqual(item.paper_size, 'A4')
        self.assertEqual(item.page_numbers, 3)
        self.assertEqual(item.valid_date, '2010/10/02')


class FunctionalClientTest(TestCase):
    def setUp(self):
        from google.appengine.ext.testbed import Testbed

        self.testbed = Testbed()
        self.testbed.activate()
        self.testbed.init_urlfetch_stub()

        self.username = os.environ.get('NETPRINT_USERNAME')
        self.password = os.environ.get('NETPRINT_PASSWORD')
        if self.username is None or self.password is None:
            raise SkipTest("Need both "
                           "NETPRINT_USERNAME and NETPRINT_PASSWORD")

    def tearDown(self):
        self.testbed.deactivate()

    def _getOUT(self):
        import httplib2
        from netprint import Client

        httplib2.debuglevel = 1
        return Client(httplib2.Http(),
                      'Mozilla/5.0 '
                      '(Macintosh; U;Intel Mac OS X 10_6_3; ja-jp) '
                      'AppleWebKit/533.16 (KHTML, like Gecko) '
                      'Version/5.0 Safari/533.16')

    @attr('functional', 'heavy')
    def test_login(self):
        client = self._getOUT()
        client.login(self.username, self.password, retry=1)
        self.assertIsNotNone(client.session_key)

    @attr('functional', 'heavy')
    def test_session_error(self):
        from netprint import UnexpectedContent

        client1 = self._getOUT()
        client2 = self._getOUT()
        client1.login(self.username, self.password, 1)
        client2.login(self.username, self.password, 1)
        self.assertNotEqual(client1.session_key, client2.session_key)
        self.assertRaises(UnexpectedContent, client1.reload)

    @attr('functional', 'heavy')
    def test_send_delete(self):
        client = self._getOUT()
        client.login(self.username, self.password, retry=1)

        client.send('tests/data/sudoku01.jpg')
        client.reload()
        self.assertIn('sudoku01', [item.name for item in client.list()])

        client.delete(item)
        client.reload()
        self.assertNotIn('sudoku01', [item.name for item in client.list()])

    @attr('functional', 'heavy')
    def test_send_delete_with_fileobj(self):
        client = self._getOUT()
        client.login(self.username, self.password, retry=1)

        client.send(file('tests/data/sudoku01.jpg'))
        client.reload()
        self.assertIn('sudoku01', [item.name for item in client.list()])

        client.delete(item)
        client.reload()
        self.assertNotIn('sudoku01', [item.name for item in client.list()])
"""

def test_send(context):
    mocker = context.mocker()

    client = context.get_netprint_client()
    client.browser = mocker.proxy(client.browser)
    client.session_key = 'a_valid_session'

    with mocker.order():
        client.browser.open(Client.manage_url + '?s=a_valid_session')
        mocker.call(with_loading_fixture('data/main.html'), with_object=True)
        mock_link = mocker.mock()
        client.browser.links(text_regex=unicode('^新規ファイル', 'utf8').encode('sjis'))
        mocker.result([mock_link])
        client.browser.follow_link(mock_link)
        mocker.call(with_loading_fixture('data/entry.html'), with_object=True)

    client.browser.response()
    mocker.passthrough()
    client.browser.forms()
    mocker.passthrough()
    client.browser.select_form(nr=1)
    mocker.passthrough()
    # f = mocker.mock(StringIO)
    # client.browser.form.add_file(f, filename=file_name)
    client.browser['papersize'] = [str(PaperSize.A4)]
    mocker.passthrough()
    client.browser['color'] = [str(Color.choice_at_printing)]
    mocker.passthrough()
    client.browser['number'] = [str(ReservationNumber.Num)]
    mocker.passthrough()
    client.browser['secretcodesw'] = [str(NeedSecret.Yes)]
    mocker.passthrough()
    client.browser['secretcode'] = 'secret_code_XXX'
    mocker.passthrough()
    client.browser['magnification'] = str(NeedMargin.No)
    mocker.passthrough()
    client.browser['mailsw'] = [str(NeedNotification.No)]
    mocker.passthrough()
    client.browser['mailaddr'] = ''
    mocker.passthrough()
    client.browser.submit()
    mocker.replay()

    client.send(file('/dev/null'), file_name='test01.jpg',
                reserversion_number=ReservationNumber.Num,
                need_secret=NeedSecret.Yes, secret_code='secret_code_XXX')

    mocker.verify()
    mocker.restore()

def test_delete(context):
    mocker = context.mocker()

    client = context.get_netprint_client()
    client.browser = mocker.proxy(client.browser)
    client.session_key = 'a_valid_session'

    with mocker.order():
        client.browser.open(Client.manage_url + '?s=a_valid_session')
        mocker.call(with_loading_fixture('data/main.html'), with_object=True)
        client.browser.response()
        mocker.passthrough()
        client.browser.set_response(ANY)
        mocker.passthrough()
        client.browser.select_form(nr=2)
        mocker.passthrough()
        client.browser['fc'] = set(['QNA7HNEE'])
        mocker.passthrough()
        client.browser.submit(name='delete')
        mocker.call(with_loading_fixture('data/confirm_delete.html'), with_object=True)

    client.browser.response()
    mocker.passthrough()
    client.browser.forms()
    mocker.passthrough()
    client.browser.select_form(nr=0)
    mocker.passthrough()
    client.browser.submit()
    mocker.replay()

    client.delete('QNA7HNEE')

    mocker.verify()
    mocker.restore()
"""
