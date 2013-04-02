# -*- coding: utf-8 -*-

from __future__ import print_function

from threading import Thread

from django.contrib.auth.models import User
from django.test import TestCase

from .fake_server import SimpleASHTTPServer


def start_server(port, testcase):
    server = SimpleASHTTPServer(port)
    testcase.server = server
    server.run()

class BaseASTestCase(TestCase):
    def setUp(self):
        self.port  = 8003
        self.url   = 'http://127.0.0.1:%s' % self.port
        self.server = None
        self.thread_httpd = Thread(target=start_server, kwargs={'port': self.port, 'testcase': self})
        print("Starting server")
        self.thread_httpd.start()
        self.user = User.objects.create(username='name')
        self.params = (self.url, '', '', 1, self.user)

    def tearDown(self):
        print("Ending server")
        if self.server is not None:
            self.server.stop()
            self.server = None
        self.thread_httpd._Thread__stop()
