# -*- encoding: utf8 -*-

"""
netprint: A client module for the Net print (http://www.printing.ne.jp)
"""

__author__ = "MURAOKA Yusuke"
__copyright__ = "Copyright 2010, MURAOKA Yusuke"
__license__ = "New BSD"
__version__ = "0.1"
__email__ = "yusuke.muraoka@gmail.com"

import os
from enum import Enum
from BeautifulSoup import BeautifulSoup
import logging

header_row = [unicode(s, 'utf8') for s in ("ファイル名", "プリント", "予約番号", "ファイル", "サイズ", "用　紙", "サイズ", "ページ", "有効期限")]

# enums
PaperSize = Enum("Paper size", "A4 A3 B4 B5 L".split())
Color = Enum("Color mode", "gray choice_at_printing color".split())
ReservationNumber = Enum("Reserversion number type", "AlphaNum Num".split())
NeedSecret = Enum("Need secret code or not", "No Yes".split())
NeedMargin = Enum("Need margin to result or not", "No Yes".split())
NeedNotification = Enum("Need notification at entry or not", "No Yes".split())

class LoginFailure(Exception): pass
class UnexpectedContent(ValueError):
    """
    If raising this exception, first, please login again. Because the session key of current session might be expired.
    Otherwise the content of the target site may be changed.
    """

class Client(object):

    root_url = 'https://www.printing.ne.jp/'
    login_url = root_url + 'login.html'
    manage_url = root_url + 'cgi-bin/mn.cgi'

    def __init__(self, browser):
        self.browser = browser

    def set_debug(self, flag=True):
        self.browser.set_debug_http(flag)
        self.browser.set_debug_redirects(flag)
        self.browser.set_debug_responses(flag)

    def login(self, username, password):
        """
        Login to the Net print service.
        """
        # This implementation trying to get session key (like cookie but...) 3 times.
        for _ in range(3):
            try:
                self.browser.open(self.login_url)
                assert len(list(self.browser.forms())) == 1
                self.browser.select_form(nr=0)
                self.browser['i'] = username
                self.browser['p'] = password
                self.browser.submit()
                self.browser.select_form(name='m1form')
                self.session_key = self.browser['s']
                break
            except:
                logging.exception("login failed")
        else:
            raise LoginFailure("login failed")
        self._make_soup()
        self._check_displaying_main_page_then_trim()

    def go_home(self):
        self.browser.open(self.manage_url + '?s=' + self.session_key)

    def reload(self):
        self.go_home()
        self._make_soup()
        self._check_displaying_main_page_then_trim()

    def _make_soup(self):
        response = self.browser.response()
        self._soup = BeautifulSoup(response.get_data())

    def _check_displaying_main_page_then_trim(self):
        if self._soup is None:
            raise ValueError("need soup")

        ns_list = self._soup.findAll(text=u"ファイル名")
        if len(ns_list) != 1:
            raise UnexpectedContent

        ns = ns_list[0]
        if ns.findParent('tr').findAll(text=lambda ns: len(ns.strip()) > 0) != header_row:
            raise UnexpectedContent

        self._soup = ns.findParent('table')
        self._soup.extract()

    def list(self):
        item_list = []
        for row in self._soup.findAll('tr')[1:]:
            column_list = row.findAll('td')
            item_list.append(Item(column_list[2].string,
                                  column_list[1].string,
                                  column_list[3].string,
                                  column_list[4].string,
                                  int(column_list[5].string),
                                  column_list[6].string,
                                 ))
        return item_list

    def delete(self, *item_or_id):
        """
        delete a file on Netprint.
        """

        id_set = set()
        for i in item_or_id:
            if isinstance(i, Item):
                id_set.add(i.id)
            else:
                id_set.add(i)

        self.go_home()

        # XXX an hack for duplicate name attributes of an image button.
        res = self.browser.response()
        data = res.get_data()
        data = data.replace(' name="Image1"', '')
        res.set_data(data)
        self.browser.set_response(res)

        self.browser.select_form(nr=2)
        self.browser['fc'] = id_set
        self.browser.submit(name='delete')

        if (self.browser.response().get_data().find(unicode('ファイルを削除します', 'utf8').encode('sjis')) == -1
            or len(list(self.browser.forms())) != 1):
            raise UnexpectedContent

        self.browser.select_form(nr=0)
        self.browser.submit()

    def send(self, path_or_file, file_name=None,
            paper_size=PaperSize.A4,
            color=Color.choice_at_printing,
            reserversion_number=ReservationNumber.AlphaNum,
            need_secret=NeedSecret.No,
            secret_code=None,
            need_margin=NeedMargin.No,
            need_notification=NeedNotification.No,
            mail_address=None
           ):
        """
        send a file to Netprint.

        Current values are bellow:
            papersize=0(A4) 1(A3) 2(B4) 3(B5) 4(L size)
            color=1(choice at printing) 2(color) or 0(gray)
            number=0(alphanum) or 1(num)
            secretcodesw=0(no secret) or 1(secret)
            secretcode=the password
            magnification=1(without margin) or 0(with margin)
            mailsw=0(no need notification) or 1(need notification)
            mailaddr=the mail address
        """

        f = None
        if isinstance(path_or_file, str):
            path = path_or_file
            f = file(path)
            if file_name is None:
                file_name = os.path.basename(path)
        elif hasattr(path_or_file, 'read'):
            f = path_or_file
            if file_name is None:
                raise ValueError("file like object needs its name")
        else:
            raise ValueError("unknown value of path_or_file")

        if paper_size == PaperSize.L and color != Color.color:
            raise ValueError("L size printing only accept color")
        if need_secret == NeedSecret.Yes and secret_code is None:
            raise ValueError("need secret_code")

        if need_notification == NeedNotification.Yes and mail_address is None:
            raise ValueError("need mail_address")

        self.go_home()

        link_list = list(self.browser.links(text_regex=unicode('^新規ファイル', 'utf8').encode('sjis')))

        if len(link_list) != 1:
            raise UnexpectedContent
        link = link_list[0]
        self.browser.follow_link(link)

        # Now must be on a file entry page
        if (self.browser.response().get_data().find(unicode('新規ファイルの登録', 'utf8').encode('sjis')) == -1
            or len(list(self.browser.forms())) != 2):
            raise UnexpectedContent

        self.browser.select_form(nr=1)

        self.browser.form.add_file(f, filename=file_name)
        self.browser['papersize'] = [str(paper_size)]
        self.browser['color'] = [str(color)]
        self.browser['number'] = [str(reserversion_number)]
        self.browser['secretcodesw'] = [str(need_secret)]
        self.browser['secretcode'] = secret_code or ''
        self.browser.form.find_control('magnification').readonly = False
        self.browser['magnification'] = str(need_margin)
        self.browser['mailsw'] = [str(need_notification)]
        self.browser['mailaddr'] = mail_address or ''
        self.browser.submit()

class Item(object):

    def __init__(self, id, name, file_size, paper_size, page_numbers, valid_date):
        self.id = id
        self.name = name
        self.file_size = file_size
        self.paper_size = paper_size
        self.page_numbers = page_numbers
        self.valid_date = valid_date

    def __repr__(self):
        _class = self.__class__
        return '<%s.%s object id:"%s" name:"%s">' % (_class.__module__,
                                                     _class.__name__,
                                                     self.id,
                                                     self.name)
