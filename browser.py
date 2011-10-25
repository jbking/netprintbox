import urllib2
import copy
import mechanize
import mechanize._response

class GAEMechanizeHTTPHandler(mechanize.BaseHandler):

    def __init__(self, gae_http_handler, debuglevel=0):
        self._debuglevel = debuglevel
        self._gae_http_handler = gae_http_handler

    def http_open(self, req):
        return self._gae_http_handler.http_open(req)

def make_gae_handler():
    return urllib2.HTTPHandler()

def make_http_handler():
    gae_handler = make_gae_handler()
    return GAEMechanizeHTTPHandler(gae_handler)

class GAEBrowser(mechanize.Browser):
    handler_classes = copy.copy(mechanize.Browser.handler_classes)
    handler_classes["http"] = make_http_handler

__all__ = ['GAEBrowser']
