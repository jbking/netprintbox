# -*- encoding: utf8 -*-

"""
netprint: A client module for the Net print (http://www.printing.ne.jp)
"""

__author__ = "MURAOKA Yusuke"
__copyright__ = "Copyright 2010 - 2011, MURAOKA Yusuke"
__license__ = "New BSD"
__version__ = "0.1"
__email__ = "yusuke@jbking.org"


import os
import time
import re
import logging
from urllib import urlencode
from collections import namedtuple
from StringIO import StringIO

from BeautifulSoup import BeautifulSoup
import httplib2

from utils import is_multipart, encode_multipart_data, OS_FILESYSTEM_ENCODING


header_row = [unicode(s, 'utf8') for s in
              ("ファイル名", "プリント", "予約番号",
               "ファイル", "サイズ", "用　紙", "サイズ",
               "ページ", "有効期限")]


# const #######################################
class PaperSize:
    A4, A3, B4, B5, L = range(5)


class Color:
    gray, choice_at_printing, color = range(3)


class ReservationNumber:
    AlphaNum, Num = range(2)


class NeedSecret:
    No, Yes = range(2)


class NeedMargin:
    No, Yes = range(2)


class NeedNotification:
    No, Yes = range(2)
###############################################


FORMENCODE_HEADERS = {
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    "Accept-Language": "ja",
    "Accept-Charset": "utf-8"}


MULTIPART_HEADERS = {
    "Content-Type": 'multipart/form-data; boundary=',
    "Accept-Language": "ja"}


# exceptions ##################################
class LoginFailure(Exception):
    pass


class Reload(Exception):
    pass


class UnexpectedContent(ValueError):
    """
    If raising this exception, first, please login again. Because the session key of current session might be expired.
    Otherwise the content of the target site may be changed.
    """
###############################################


MAX_RETRY = 3


class DictCache(object):
    def __init__(self, safe=httplib2.safename):
        self.data = {}
        self.safe = safe

    def get(self, key):
        key = self.safe(key)
        return self.data.get(key, None)

    def set(self, key, value):
        key = self.safe(key)
        self.data[key] = value

    def delete(self, key):
        key = self.safe(key)
        if key in self.data:
            del self.data[key]


class Client(object):

    url_prefix = 'https://www.printing.ne.jp'
    login_url = url_prefix + '/login.html'
    manage_url = url_prefix + '/cgi-bin/mn.cgi'

    def __init__(self, http_obj=None, user_agent=None):
        if http_obj is None:
            cache = DictCache()
            http_obj = httplib2.Http(cache=cache)
        self.http_obj = http_obj
        self.user_agent = user_agent
        self._soup = None

    def _request(self, uri, method='GET', headers=None, body=None,
            status=(200, 304), **kwargs):
        """
        Request on HTTP.

        Assume that using httplib2.Http, so even status is 304 by response,
        content must exist.
        """
        uri = str(uri)
        if headers is not None:
            headers = headers.copy()
        else:
            headers = {}
        if self.user_agent is not None:
            headers['User-Agent'] = self.user_agent
        if isinstance(body, dict):
            if method not in ('POST', 'PUT'):
                method = 'POST'
            if is_multipart(body):
                body, boundary = encode_multipart_data(body)
                headers.update(MULTIPART_HEADERS)
                headers['Content-Type'] = MULTIPART_HEADERS['Content-Type'] + \
                                          boundary
            else:
                body = urlencode(body, True)
                headers.update(FORMENCODE_HEADERS)
        (response, content) = self.http_obj.request(uri,
                method=method, headers=headers, body=body, **kwargs)
        assert response.status in status, \
               "%s %s" % (response.status, response.reason)
        return (response, content)

    def ensure_encoding(self, s):
        if isinstance(s, str):
            # to unicode
            s = s.decode(OS_FILESYSTEM_ENCODING)
        if isinstance(s, unicode):
            # to netprint encoding
            s = s.encode(self._encoding, 'replace')
        return s

    def login(self, username, password, retry=3):
        """
        Login to the Net print service.
        """
        for _ in range(retry):
            try:
                (_, content) = self._request(self.login_url)

                soup = BeautifulSoup(content)
                form = soup.find('form')
                assert form.find('input', attrs=dict(name='i')) is not None
                assert form.find('input', attrs=dict(name='p')) is not None

                submit_url = form['action']
                post_data = dict(i=username, p=password)
                (_, content) = self._request(submit_url,
                                             body=post_data)

                soup = BeautifulSoup(content)
                form = soup.find('form', attrs=dict(name='m1form'))
                session_field = form.find('input', attrs=dict(name='s'))
                assert session_field is not None

                self.session_key = session_field['value']
                break
            except:
                logging.exception("login failed")
        else:
            raise LoginFailure("login failed")
        self._soup = soup  # update soup.
        self._encoding = self._soup.originalEncoding
        self._check_displaying_main_page_then_trim()

    def go_home(self):
        (_, content) = self._request(
                self.manage_url + '?s=' + self.session_key)
        self._soup = BeautifulSoup(content)  # update soup.
        self._encoding = self._soup.originalEncoding

    def reload(self):
        self.go_home()
        self._check_displaying_main_page_then_trim()

    def _check_displaying_main_page_then_trim(self):
        if self._soup is None:
            raise ValueError("need soup")

        ns_list = self._soup.findAll(text=u"ファイル名")
        if len(ns_list) != 1:
            raise UnexpectedContent

        ns = ns_list[0]
        if ns.findParent('tr')\
                .findAll(text=lambda ns: len(ns.strip()) > 0) != header_row:
            raise UnexpectedContent

        # trim
        self._soup = ns.findParent('table')
        self._soup.extract()

    def list(self, retry=0):
        try:
            item_list = []
            for row in self._soup.findAll('tr')[1:]:
                column_list = row.findAll('td')
                try:
                    id = column_list[2].string
                    if id is None:
                        raise Reload
                except IndexError:
                    raise Reload
                item_list.append(Item(column_list[2].string,
                                      column_list[1].string,
                                      column_list[3].string,
                                      column_list[4].string,
                                      int(column_list[5].string),
                                      column_list[6].string,
                                     ))
            return item_list
        except Reload:
            if retry < MAX_RETRY:
                time.sleep(1)
                self.reload()
                return self.list(retry=retry + 1)
            else:
                raise

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

        (_, content) = self._request(self.manage_url, body={
            'c': 0,  # unknown
            's': self.session_key,
            'fc': id_set,
            'delete.x': 1,
            'delete.y': 1})

        soup = BeautifulSoup(content)
        if (soup.find('input', attrs={'name': 'delexec'}) is None
            or len(soup.findAll('form')) != 1):
            raise UnexpectedContent

        (_, content) = self._request(self.manage_url, body={
            'c': 0,  # unknown
            's': self.session_key,
            'fc': id_set,
            'delexec.x': 1,
            'delexec.y': 1})

    def send(self, path_or_file,
             paper_size=PaperSize.A4,
             color=Color.choice_at_printing,
             reserversion_number=ReservationNumber.AlphaNum,
             need_secret=NeedSecret.No,
             secret_code=None,
             need_margin=NeedMargin.No,
             need_notification=NeedNotification.No,
             mail_address=None):
        """
        send a file to Netprint.
        """

        f = None
        if isinstance(path_or_file, basestring):
            path = path_or_file
            f = file(path)
        elif hasattr(path_or_file, 'read'):
            f = path_or_file
            if getattr(f, 'name', None) is None:
                raise ValueError("file like object needs its name")
        else:
            raise ValueError("unknown value of path_or_file")

        name = self.ensure_encoding(os.path.split(f.name)[-1])
        f = StringIO(f.read())
        f.name = name

        if paper_size == PaperSize.L and color != Color.color:
            raise ValueError("L size printing only accept color")
        if need_secret == NeedSecret.Yes and secret_code is None:
            raise ValueError("need secret_code")

        if need_notification == NeedNotification.Yes and mail_address is None:
            raise ValueError("need mail_address")

        self.go_home()

        new_file_list = self._soup(alt=re.compile(u'^新規ファイル'))
        if len(new_file_list) != 1:
            raise UnexpectedContent
        link = new_file_list[0].parent['href']

        (_, content) = self._request(self.url_prefix + link)
        # XXX: Ignore invalid characters to
        #      BeautifulSoup recognize the content correctly.
        content = content.decode(self._encoding, 'replace')
        soup = BeautifulSoup(content)

        # Now must be on a file entry page
        if not (soup.find(text=u'新規ファイルの登録') is not None
                and len(soup.findAll('form')) == 2):
            raise UnexpectedContent

        self._request(self.url_prefix + link, body=dict(
            s=self.session_key,
            c=0,  # unknown
            m=2,  # unknown
            re=1,  # unknown
            file1=f,
            papersize=paper_size,
            color=color,
            number=reserversion_number,
            secretcodesw=need_secret,
            secretcode=secret_code or '',
            magnification=need_margin,
            mailsw=need_notification,
            mailaddr=mail_address or ''))


Item = namedtuple('Item',
    'id '
    'name '
    'file_size '
    'paper_size '
    'page_numbers '
    'valid_date ')
