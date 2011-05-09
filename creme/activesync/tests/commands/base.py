# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2010  Hybird
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

from threading import Thread
from django.contrib.auth.models import User

from django.test import TestCase

from activesync.tests.commands.fake_server import SimpleASHTTPServer

def start_server(port, server):
    server = SimpleASHTTPServer(port)
    server.run()

class BaseASTestCase(TestCase):

    def setUp(self):
        self.port  = 8003
        self.url   = 'http://127.0.0.1:%s' % self.port
        self.server = None
        self.thread_httpd = Thread(target=start_server, kwargs={'port': self.port, 'server': self.server})
        print "Starting server"
        self.thread_httpd.start()
        self.user = User.objects.create(username='name')
        self.params = (self.url, '', '', 1, self.user)

    def tearDown(self):
        print "Ending server"
        if self.server is not None:
            self.server.stop()
            self.server = None
        self.thread_httpd._Thread__stop()