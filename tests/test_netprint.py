# -*- encoding: utf8 -*-
from __future__ import with_statement
import os
import py
from mechanize import make_response
from netprint import (Client, UnexpectedContent,
                      PaperSize, Color, ReservationNumber,
                      NeedSecret, NeedMargin, NeedNotification)
from mocker import ANY

def test_login(context):
    mocker = context.mocker()

    client = context.get_netprint_client()
    client.browser = mocker.proxy(client.browser)

    with mocker.order():
        client.browser.open(Client.login_url)
        mocker.call(with_loading_fixture('data/login.html'), with_object=True)
        client.browser.select_form(nr=0)
        mocker.passthrough()

    client.browser['i'] = 'foo'
    mocker.passthrough()
    client.browser['p'] = 'bar'
    mocker.passthrough()

    with mocker.order():
        client.browser.submit()
        mocker.call(with_loading_fixture('data/main.html'), with_object=True)
        client.browser.select_form(name='m1form')
        mocker.passthrough()

    client.browser['s']
    mocker.result('a_valid_session')
    client.browser.response()
    mocker.passthrough()
    mocker.replay()

    client.login('foo', 'bar')
    assert client.session_key == 'a_valid_session'

    mocker.verify()
    mocker.restore()

def test_actual_login(context):
    if not context.need_connect():
        py.test.skip("The connection is disabled by not specifying username and password")
    client = context.get_netprint_client()
    client.login(context.config.option.username,
                 context.config.option.password)
    assert client.session_key is not None

def test_check_content(context):
    client = context.get_netprint_client()
    with_loading_fixture('data/main.html')(client.browser)
    client._make_soup()
    client._check_displaying_main_page_then_trim()
    assert client._soup.name == 'table'
    assert client._soup.previousSibling == None
    assert client._soup.parent == None
    assert client._soup.nextSibling == None

def test_list(context):
    client = context.get_netprint_client()
    with_loading_fixture('data/main.html')(client.browser)
    client._make_soup()
    client._check_displaying_main_page_then_trim()
    item_list = client.list()
    assert len(item_list) == 1

    item = item_list[0]
    assert item.id == 'QNA7HNEE'
    assert item.name == unicode('チケット印刷画面', 'utf8')
    assert item.file_size == '832KB'
    assert item.paper_size == 'A4'
    assert item.page_numbers == 3
    assert item.valid_date == '2010/10/02'

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

def test_actual_send_delete(context):
    if not context.need_connect():
        py.test.skip("The connection is disabled by not specifying username and password")
    client = context.get_netprint_client()
    client.login(context.config.option.username,
                 context.config.option.password)

    client.send('tests/data/sudoku01.jpg', file_name='test01.jpg')
    client.reload()
    assert 'test01' in [item.name for item in client.list()]

    client.delete(item)
    client.reload()
    assert 'test01' not in [item.name for item in client.list()]

def test_session_error(context):
    if not context.need_connect():
        py.test.skip("The connection is disabled by not specifying username and password")
    client1 = context.get_netprint_client()
    client1.login(context.config.option.username,
                  context.config.option.password)
    client2 = context.get_netprint_client()
    client2.login(context.config.option.username,
                  context.config.option.password)
    with py.test.raises(UnexpectedContent):
        client1.reload()

def with_loading_fixture(path):
    def f(browser, *args, **kwg):
        response = make_response(
            file(os.path.join(os.path.dirname(__file__), path)).read(),
            [("Content-Type", "text/html")],
            '', 200, "OK")
        browser.set_response(response)
    return f
