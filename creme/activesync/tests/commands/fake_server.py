# -*- coding: utf-8 -*-

import BaseHTTPServer
from StringIO import StringIO
import sys
import os

from django.core.files import File

from activesync.wbxml import WBXMLEncoder
from activesync.wbxml.dtd import AirsyncDTD_Reverse


DEFAULT_CHUNK_SIZE = File.DEFAULT_CHUNK_SIZE

class PostAwareHTTPRequestHandler(BaseHTTPServer.BaseHTTPRequestHandler):
    def _open_n_read_encode(self, filename, mode='r'):
        path = filename
        content = StringIO()

        with open(path, mode) as f:
            for ch in f.read(DEFAULT_CHUNK_SIZE):
                content.write(ch)

        return_content = content.getvalue()

        content.close()
        encode = WBXMLEncoder(AirsyncDTD_Reverse).encode
        return encode(return_content)

    def do_POST(self, *args, **kwargs):
        test_files = self.headers.get('test_files').split(';')

        if not test_files:
            self.send_error(404, "test_files header not found")
            return

        if self.server.test_files is None:
            for test_file in test_files:
                if not os.path.exists(test_file):
                    self.send_error(404, "Test file <%s> not found" % test_file)
                    return

            self.server.test_files = test_files

        encoded = self._open_n_read_encode(self.server.test_files[self.server.test_index])

        self.send_response(200)
        self.send_header("Content-type", "application/vnd.ms-sync.wbxml")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)


class SimpleASHTTPServer(BaseHTTPServer.HTTPServer):
    test_index = 0
    test_files = None

    def __init__(self, port):
        #Always localhost
#        super(SimpleASHTTPServer, self).__init__(('', port), PostAwareHTTPRequestHandler)
        BaseHTTPServer.HTTPServer.__init__(self, ('', port), PostAwareHTTPRequestHandler)

    def run(self):
        self.serve_forever()

    def stop(self):
        self.shutdown()

    def finish_request(self, request, client_address):
        """Finish one request by instantiating RequestHandlerClass."""
        self.RequestHandlerClass(request, client_address, self)
        self.test_index += 1
