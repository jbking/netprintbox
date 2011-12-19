# -*- encoding: utf8 -*-

"""
netprint: A client module for the Net print (http://www.printing.ne.jp)
"""

__author__ = "MURAOKA Yusuke"
__copyright__ = "Copyright 2010 - 2011, MURAOKA Yusuke"
__license__ = "New BSD"
__version__ = "0.1"
__email__ = "yusuke@jbking.org"


from collections import namedtuple
import mimetypes
import os
import random
from StringIO import StringIO
import time
from urllib import urlencode

from BeautifulSoup import BeautifulSoup
import httplib2


header_row = [u"ファイル名", u"プリント", u"予約番号",
              u"ファイル", u"サイズ", u"用　紙", u"サイズ",
              u"ページ", u"有効期限"]


# enums #######################################
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


class SendingTarget(object):
    NORMAL = 'https://www.printing.ne.jp/cgi-bin/mn.cgi'
    OFFICE = 'https://www2.printing.ne.jp/cgi-bin/mn.cgi'
###############################################


FORMENCODE_HEADERS = {
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    "Accept-Language": "ja",
    "Accept-Charset": "utf-8",
}


MULTIPART_HEADERS = {
    "Content-Type": 'multipart/form-data; boundary=',
    "Accept-Language": "ja",
}


# exceptions ##################################
class LoginFailure(Exception):
    pass


class Reload(Exception):
    pass


class UnexpectedContent(ValueError):
    """
    If raising this exception, first, please login again.
    Because the session key of current session might be expired.
    Otherwise the content of the target site may be changed.
    """


class UnknownExtension(ValueError):
    pass
###############################################


# utilities ###################################
def is_file_like(obj):
    return (getattr(obj, 'read', None) is not None
        and getattr(obj, 'name', None) is not None)


def is_multipart(data):
    for obj in data.values():
        if is_file_like(obj):
            return True
    else:
        return False


def encode_multipart_data(data):
    getRandomChar = lambda: chr(random.choice(range(97, 123)))
    randomChar = [getRandomChar() for _ in xrange(20)]
    boundary = "----------%s" % "".join(randomChar)
    lines = ["--" + boundary]
    for key, value in data.iteritems():
        header = 'Content-Disposition: form-data; name="%s"' % key
        if is_file_like(value):
            header += '; filename="%s"' % value.name
            lines.append(header)
            mtypes = mimetypes.guess_type(value.name)
            if mtypes:
                contentType = mtypes[0]
                header = "Content-Type: %s" % contentType
                lines.append(header)
            lines.append("Content-Transfer-Encoding: binary")
            data = value.read()
        else:
            lines.append(header)
            if isinstance(value, unicode):
                data = value.encode("utf-8")  # XXX
            else:
                data = str(value)

        lines.append("")
        lines.append(data)
        lines.append("--" + boundary)
    lines[-1] += "--"

    return "\r\n".join(lines), boundary


def get_sending_target(file_name):
    """Returns the target host which the file should be sent.

    Because there are hosts which are switched by file format."""
    """
    日本語Windows®上で使用する次のアプリケーションが対象です。Mac OSのアプリケーションには対応していません。
    ・Microsoft® Word 97/98/2000/2002/2003/2007/2010 日本語（拡張子「.doc」「.docx」「.rtf」）
    ・Microsoft® Excel 97/2000/2002/2003/2007/2010 日本語(拡張子「.xls」「.xlsx」)
    ・Microsoft® PowerPoint® 97/2000/2002/2003/2007/2010 日本語(拡張子「.ppt」「.pptx」)
    ・DocuWorks Ver.3.0以降 (拡張子「.xdw」)
    ・JPEG (拡張子「.jpg」「.jpe」、「.jpeg」)
    ・TIFF (拡張子「.tif」)
    ・PDF Ver1.3/1.4/1.5/1.6/1.7（拡張子「.pdf」）

        if(filename.match(/\.(docx|pptx|xlsx)$/i)){
            curfrm.action="https://www2.printing.ne.jp/cgi-bin/mn.cgi";
            curfrm.submit();
        }else{
            curfrm.action="https://www.printing.ne.jp/cgi-bin/mn.cgi";
            curfrm.submit();
        }
    """
    ext = os.path.splitext(file_name)[1]
    if ext in ('.docx', '.pptx', '.xlsx'):
        return SendingTarget.OFFICE
    elif ext in ('.doc', '.rtf', '.xls', '.ppt',
                 '.xdw', '.jpg', '.jpe', '.jpeg',
                 '.tif', '.pdf'):
        return SendingTarget.NORMAL
    else:
        raise UnknownExtension("Unknown extension '%s'" % ext)
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

    url = 'https://www.printing.ne.jp/cgi-bin/mn.cgi'

    def __init__(self, http_obj=None, user_agent=None):
        if http_obj is None:
            cache = DictCache()
            http_obj = httplib2.Http(cache=cache)
        self.http_obj = http_obj
        self.user_agent = user_agent
        self._soup = None
        self._encoding = None

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
            s = s.decode('utf-8')
        if isinstance(s, unicode):
            # to netprint encoding
            assert self._encoding is not None
            s = s.encode(self._encoding, 'replace')
        return s

    def login(self, username, password, retry=3):
        """
        Login to the Net print service.
        """
        try:
            (_, content) = self._request(self.url,
                    method='POST',
                    body={'i': username, 'p': password})

            soup = BeautifulSoup(content)
            session_field = soup.find('input', attrs={'name': 's'})
            assert session_field is not None

            self.session_key = session_field['value']
        except:
            raise LoginFailure("username or password is wrong.")
        self._soup = soup  # update soup.
        self._encoding = self._soup.originalEncoding
        self._check_displaying_main_page_then_trim()

    def go_home(self):
        (_, content) = self._request(
                self.url + '?s=' + self.session_key)
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
                item_list.append(Item(unicode(column_list[2].string),
                                      unicode(column_list[1].string),
                                      unicode(column_list[3].string),
                                      unicode(column_list[4].string),
                                      int(column_list[5].string),
                                      unicode(column_list[6].string),
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

        (_, content) = self._request(self.url, body={
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

        if isinstance(path_or_file, basestring):
            path = path_or_file
            f = file(path)
        elif is_file_like(path_or_file):
            f = path_or_file
        else:
            raise ValueError("unknown value of path_or_file")

        # wrap to set the name.
        name = self.ensure_encoding(os.path.split(f.name)[-1])
        f = StringIO(f.read())
        f.name = name

        if paper_size == PaperSize.L and color != Color.color:
            raise ValueError("L size printing only accept color")
        if need_secret == NeedSecret.Yes and secret_code is None:
            raise ValueError("need secret_code")

        if need_notification == NeedNotification.Yes and mail_address is None:
            raise ValueError("need mail_address")

        sending_url = get_sending_target(f.name)
        self._request(sending_url, body=dict(
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
            duplextype=9,  # unknown
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
