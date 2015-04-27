# -*- coding: utf-8  -*-
"""Module for anyhttp."""
#
# (C) John Vandenberg, 2015
#
# Distributed under the terms of the MIT license.
#
import sys
import types

from io import StringIO, BytesIO
from warnings import warn

if sys.version_info[0] > 2:
    from urllib.parse import urlparse
else:
    from urlparse import urlparse

if sys.version_info[0] > 2:
    basestring = (str, )
    unicode = str
    type_type = type
else:
    type_type = (type, types.ClassType)

loaded_http_packages = None
available_http_packages = None

http = None
verbose = False


class Http(object):

    def __init__(self, package):
        self.package = package

    def raw(self, url):
        raise NotImplementedError('%s raw() not defined' % self.package)

    def get_text(self, url):
        raw = self.raw(url)
        if verbose:
            if isinstance(raw, (bytes, str, unicode)):
                print('%s.raw: type: %s'
                      % (self.__class__.__name__, type(raw)))
            else:
                print('%s.raw: type: %s : %r'
                      % (self.__class__.__name__, type(raw), raw))

        if not isinstance(raw, (bytes, str, unicode)):
            if verbose:
                if hasattr(raw, '__dict__'):
                    print('%s.raw __dict__: %s'
                          % (self.__class__.__name__, raw.__dict__))
            out = unicode(raw)
            if verbose:
                if out == repr(raw) and verbose:
                    print('%s.get resulted in repr: %s'
                          % (self.__class__.__name__, out))
        else:
            out = raw

        if isinstance(out, bytes):
            out = raw.decode('utf8')

        if verbose:
            print('%s.get: type: %r' % (self.__class__.__name__, type(out)))
        return out

    def get_binary(self, url):
        return self.raw(url)

    @classmethod
    def _extract_raw(cls, value):
        return value


class PackageGet(Http):

    def raw(self, url):
        result = self.package.get(url)
        return self._extract_raw(result)


class PackageGetContents(PackageGet):

    """requests pattern."""

    @classmethod
    def _extract_raw(cls, value):
        return value.content


class addinfourl(Http):

    @classmethod
    def _extract_raw(cls, value):
        value = super(addinfourl, cls)._extract_raw(value)
        return value.read()


class urlopen(addinfourl, Http):

    def raw(self, url):
        result = self.package.urlopen(url)
        return self._extract_raw(result)


class ClassHttp(Http):

    cls = None

    def __init__(self, package):
        super(ClassHttp, self).__init__(package)
        if isinstance(self.cls, basestring):
            self.cls = getattr(package, self.cls)


class SingleSiteClass(ClassHttp):

    def __init__(self, package):
        self._url = None
        super(SingleSiteClass, self).__init__(package)

    def cls_init(self, url):
        self._url = None
        if verbose:
            print('%s.cls_init(%s)' % (self.__class__.__name__, url))
        self.http = self.cls(url)

    def get_baseurl(self, url):
        if not self._url:
            self._url = urlparse(url)
        return self._url.scheme + '://' + self._url.netloc

    def get_host_port(self, url):
        if not self._url:
            self._url = urlparse(url)
        return (self._url.netloc, self._url.port)

    def get_path(self, url):
        if not self._url:
            self._url = urlparse(url)
        return self._url.path


class BaseurlSiteClass(SingleSiteClass):

    def cls_init(self, url):
        url = self.get_baseurl(url)
        super(BaseurlSiteClass, self).cls_init(url)


class MultiuseClass(ClassHttp):

    def __init__(self, package):
        result = super(MultiuseClass, self).__init__(package)
        self.http = self.cls()


class httplib2(MultiuseClass):

    cls = 'Http'

    @classmethod
    def _extract_raw(cls, value):
        return value[-1]

    def raw(self, url):
        result = self.http.request(url, method='GET')
        return self._extract_raw(result)


class urllib3(MultiuseClass):

    cls = 'PoolManager'

    def raw(self, url):
        return self.http.request(method='GET', url=url).data


class pycurl(MultiuseClass):

    cls = 'Curl'

    def raw(self, url):
        import pycurl  # noqa
        instance = self.http
        instance.setopt(pycurl.URL, url)
        result = BytesIO()
        instance.setopt(pycurl.WRITEDATA, result)
        instance.perform()
        return result.getvalue()


class fido(Http):

    def raw(self, url):
        result = self.package.fetch(url)
        result = result.result()
        result = result.body
        return result


class async_http(SingleSiteClass):

    cls = 'AsyncHTTPRequest'

    def raw(self, url):
        self.cls_init(url)
        import asyncore
        asyncore.loop()
        return self.http._get_data()


class webob(SingleSiteClass):

    cls = 'BaseRequest'

    def cls_init(self, url):
        self._url = None
        self.http = self.cls.blank(path=url)

    def raw(self, url):
        self.cls_init(url)
        return self.http.get_response().body


class urlfetch(PackageGet):

    @classmethod
    def _extract_raw(cls, value):
        return value.body


class httputils(PackageGet):

    @classmethod
    def _extract_raw(cls, value):
        return value['body']


class ihttp(PackageGet):

    @classmethod
    def _extract_raw(cls, value):
        return value[-1]


class tornado(MultiuseClass):

    cls = 'HTTPClient'

    def raw(self, url):
        result = self.http.fetch(url)
        return result.body


class ultralite(MultiuseClass):

    cls = 'Ultralite'

    def raw(self, url):
        result = self.http.get(url)
        return result.content


class basic_http(SingleSiteClass):

    cls = 'BasicHttp'

    def cls_init(self, url):
        self._url = None
        self.http = self.cls(url)

    def raw(self, url):
        self.cls_init(url)

        result = self.http.GET()
        return result['body']


class reqres(addinfourl, PackageGet):

    pass


class tinydav(SingleSiteClass):

    cls = 'HTTPClient'

    def cls_init(self, url):
        self._url = None
        self.http = self.cls.fromurl(url)

    def raw(self, url):
        self.cls_init(url)

        path = self.get_path(url)
        result = self.http.get(path)
        return result.content


class pylhttp(MultiuseClass):

    cls = 'Client'

    def raw(self, url):
        result = self.http.request(url)
        return result.content


class HostPortConnectionClass(SingleSiteClass):

    def cls_init(self, url):
        self._url = None
        (host, port) = self.get_host_port(url)
        self.http = self.cls(host, port)


class hyper(HostPortConnectionClass):

    cls = 'HTTP11Connection'

    def raw(self, url):
        self.cls_init(url)

        path = self.get_path(url)
        result = self.http.request(method='GET', url=path)
        result = self.http.get_response()
        return result.read()


class geventhttpclient(SingleSiteClass):

    cls = 'HTTPClient'

    def cls_init(self, url):
        self._url = None
        self.http = self.cls.from_url(url)

    def raw(self, url):
        self.cls_init(url)

        path = self.get_path(url)
        result = self.http.get(path)
        return result.read()


class bolacha(httplib2):

    cls = 'Bolacha'


class streaming_httplib2(addinfourl, httplib2):

    pass


class asynchttp(httplib2):

    @classmethod
    def _extract_raw(cls, value):
        value = super(asynchttp, cls)._extract_raw(value)
        return str(value)


class httxlib(addinfourl, SingleSiteClass):

    cls = 'HttxConnection'

    def raw(self, url):
        self.cls_init(url)
        from httxlib import HttxRequest
        request = HttxRequest(url)
        response = self.http.request(request)
        result = self.http.getresponse(response)
        return result.body


class dugong(HostPortConnectionClass):

    cls = 'HTTPConnection'

    def raw(self, url):
        self.cls_init(url)
        path = self.get_path(url)
        self.http.send_request('GET', path)
        resp = self.http.read_response()
        result = self.http.readall()
        return bytes(result)


# API wrappers

class drest_request(MultiuseClass):

    cls = 'RequestHandler'

    def raw(self, url):
        self.http._meta.trailing_slash = False
        self.http._meta.deserialize = False
        result = self.http.make_request(method='GET', url=url)
        return result.data


class drest(BaseurlSiteClass):

    """Does not work: adds '/'."""

    cls = 'API'

    def raw(self, url):
        self.cls_init(url)
        self.http._meta.trailing_slash = False
        self.http._meta.deserialize = False

        path = self.get_path(url)
        print(path)
        result = self.http.make_request(method='GET', path=path)
        return result.data


requests = PackageGetContents

package_handlers = {
    'requests': requests,
    'httplib2': httplib2,
    'urllib3': urllib3,
    'pycurl': pycurl,
    'fido': fido,
    'httq': requests,
    'async_http': async_http,
    'webob': webob,
    'urlfetch': urlfetch,
    'simplefetch': requests,
    'httputils': httputils,
    'tornado.httpclient': tornado,
    'ihttp': ihttp,
    'basic_http': basic_http,
    'unirest': urlfetch,
    'httpstream': requests,
    'http1': urlfetch,
    'reqres': reqres,
    'tinydav': tinydav,
    'ultralite': ultralite,
    'urlgrabber': urlopen,
    'dogbutler': requests,
    'pylhttp': pylhttp,
    'hyper': hyper,
    'asynchttp': asynchttp,
    'geventhttpclient': geventhttpclient,
    'streaming_httplib2': streaming_httplib2,
    'bolacha': bolacha,
    'drest.request': drest_request,
    'httxlib': httxlib,
    'dugong': dugong,
}

if sys.version_info[0] > 2:
    from . import py3_clients
    package_handlers['aiohttp'] = py3_clients.aiohttp
    package_handlers['yieldfrom.http.client'] = py3_clients.yieldfrom

httplib2_derivatives = [
    'tinfoilhat', 'streaming_httplib2', 'bolacha',
    # jaraco.httplib2 appears to be a completely merged fork
    'jaraco.httplib2',
    'drest.request',
    ]

for package in httplib2_derivatives:
    if package not in package_handlers:
        package_handlers[package] = httplib2

known_http_packages = set(package_handlers.keys())

py2_http_packages = set([
    # bug in deps code:
    'geventhttpclient',
    # bug in package setup:
    'urllib4.client', 'ourl',
    # bug in package code:
    'tinfoilhat', 'asynchttp', 'async_http', 'dogbutler', 'ihttp', 'fido',
    'simplefetch', 'httxlib',
    # reason to be determined:
    'streaming_httplib2', 'bolacha', 'httpclient', 'http1', 'basic_http',
    'pylhttp', 'urlgrabber', 'httputils', 'unirest',
    ])

py3_http_packages = set([
    'ultralite', 'dugong', 'yieldfrom.http.client',
    ])


def detect_loaded_package():
    global loaded_http_packages

    all_packages = set(sys.modules)
    loaded_http_packages = known_http_packages & set(all_packages)
    if verbose:
        print('loaded', loaded_http_packages)


def choose_loaded_package(detect=True):
    loaded_http_packages or detect_loaded_package()
    for package_name in loaded_http_packages:
        try:
            package = sys.modules[package_name]
            http = package_handlers.get(package_name, None)
            if http:
                http = http(package)

            if verbose:
                print('using handler %s' % http)
            return http
        except KeyError:
            warn('anyhttp: %s not found' % package)


def choose_package():
    global http
    http = choose_loaded_package()
    if not http:
        # TODO: try loading packages
        raise RuntimeError('no http packages found')


def get_text(url):
    http or choose_package()
    if not http:
        raise RuntimeError('no http packages found')
    return http.get_text(url)


def get_binary(url):
    http or choose_package()
    if not http:
        raise RuntimeError('no http packages found')
    return http.get_binary(url)


get_bin = get_binary