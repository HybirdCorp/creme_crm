# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2020  Hybird
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
################################################################################

from urllib.parse import urlencode
from urllib.request import (
    HTTPBasicAuthHandler,
    HTTPError,
    HTTPPasswordMgrWithDefaultRealm,
    HTTPRedirectHandler,
    Request,
    URLError,
    build_opener,
)


class WSException(Exception):
    pass


class WSRequest(Request):
    def __init__(self, *args, **kwargs):
        self.method = kwargs.pop('method', 'GET')
        Request.__init__(self, *args, **kwargs)

    def get_method(self):
        return self.method if self.method else 'GET'


class WSRedirectHandler(HTTPRedirectHandler):
    def http_error_301(self, req, fp, code, msg, headers):
        result = HTTPRedirectHandler.http_error_301(self, req, fp, code, msg, headers)
        result.status = code
        return result

    def http_error_302(self, req, fp, code, msg, headers):
        result = HTTPRedirectHandler.http_error_302(self, req, fp, code, msg, headers)
        result.status = code
        return result

    def http_error_default(self, req, fp, code, msg, headers):
        result = HTTPError(req.get_full_url(), code, msg, headers, fp)
        result.status = code
        return result


class WSBackEnd:
    def __init__(self):
        self.connected = False
        self.opener = None
        self.url = None

    def open(self, url='', user=None, password=None, auth=HTTPBasicAuthHandler):
        if self.connected:
            raise WSException('Already connected')

        try:
            passwords = HTTPPasswordMgrWithDefaultRealm()
            passwords.add_password(None, url, user, password)

            if user and password:
                self.opener = build_opener(WSRedirectHandler(), auth(passwords))
            else:
                self.opener = build_opener(WSRedirectHandler())

            self.opener.open(url)

            # remove this. (urllib2 ugly code !)
            # install_opener(self.opener)

            self.connected = True
            self.url = url
        except (HTTPError, URLError) as e:
            raise WSException(f'Connection error to {url}', e) from e

        return self

    def close(self):
        if not self.connected:
            raise WSException('Not connected')

        self.opener.close()
        self.opener = None

        self.url = None
        self.connected = False

        return self

    def _send(self, request, code=200):
        if not self.connected:
            raise WSException('Not connected')

        try:
            # get from urllib2 ugly code ! (see urllib2.urlopen())
            return self.opener.open(request)
        except HTTPError as e:
            if e.code is not code:
                raise WSException('Request send error', e) from e

            return e.read()
        except URLError as e:
            raise WSException('Request send error', e) from e

    def _encode(self, data):
        return urlencode({key: value for key, value in data.items() if value is not None}, True)

    def _new_request(self, url, get=None, post=None, method=None):
        url = (
            self.url.rstrip('/')
            + '/'
            + url.lstrip('/')
            + (('?' + self._encode(get)) if get else '')
        )
        request = WSRequest(url, method=method)
        request.data = self._encode(post) if post else None
        return request

    def post(self, url, **kwargs):
        return self._send(self._new_request(url, post=kwargs, method='POST'), code=201)

    def get(self, url, **kwargs):
        return self._send(self._new_request(url, get=kwargs))

    def put(self, url, **kwargs):
        return self._send(self._new_request(url, post=kwargs, method='PUT'))

    def delete(self, url, **kwargs):
        return self._send(self._new_request(url, get=kwargs, method='DELETE'), code=204)
