# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2015-2018  Hybird
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

# from __future__ import print_function

from os.path import dirname
from shutil import rmtree
from tempfile import mkdtemp
import unittest

from django.apps import apps
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.core.management import call_command
from django.test.runner import DiscoverRunner, ParallelTestSuite, _init_worker

from ..management.commands.creme_populate import Command as PopulateCommand
from ..utils.system import python_subprocess


def http_port():
    return getattr(settings, 'TEST_HTTP_SERVER_PORT', '8000')


class CremeTestSuite(unittest.TestSuite):
    """This test suite populates the DB in the Creme way."""
    def run(self, *args, **kwargs):
        call_command(PopulateCommand(), verbosity=0)
        ContentType.objects.clear_cache()  # The cache seems corrupted when we switch to the test DB

        return super(CremeTestSuite, self).run(*args, **kwargs)


def creme_init_worker(counter):
    _init_worker(counter)
    call_command(PopulateCommand(), verbosity=0)
    ContentType.objects.clear_cache()  # The cache seems corrupted when we switch to the test DB


class CremeParallelTestSuite(ParallelTestSuite):
    """This test suite populates the DB in the Creme way (parallel version)."""
    init_worker = creme_init_worker


class CremeTestLoader(unittest.TestLoader):
    suiteClass = CremeTestSuite

    def __init__(self):
        super(CremeTestLoader, self).__init__()
        self._allowed_paths = [app_conf.path for app_conf in apps.get_app_configs()]
        self._ignored_dir_paths = set()

    def _match_path(self, path, full_path, pattern):
        match = super(CremeTestLoader, self)._match_path(path, full_path, pattern)

        if match:
            dir_path = dirname(full_path)
            path_is_ok = dir_path.startswith

            if not any(path_is_ok(allowed_path) for allowed_path in self._allowed_paths):
                if dir_path not in self._ignored_dir_paths:
                    self._ignored_dir_paths.add(dir_path)
                    print('"{}" is ignored because app seems not installed.'.format(dir_path))

                return False

        return match


class CremeDiscoverRunner(DiscoverRunner):
    """This test runner
    - overrides settings.MEDIA_ROOT with a temporary directory ; so files created by the tests can be easily removed.
    - launches an HTTP server which serves static files, in order to test code which retrieve HTTP resources.
    """
    test_suite = CremeTestSuite
    parallel_test_suite = CremeParallelTestSuite
    test_loader = CremeTestLoader()

    def __init__(self, *args, **kwargs):
        super(CremeDiscoverRunner, self).__init__(*args, **kwargs)
        self._mock_media_path = None
        self._original_media_root = settings.MEDIA_ROOT
        self._http_server = None

    def setup_test_environment(self, **kwargs):
        super(CremeDiscoverRunner, self).setup_test_environment(**kwargs)
        self._mock_media_path = settings.MEDIA_ROOT = mkdtemp(prefix='creme_test_media')
        self._http_server = python_subprocess(
            'import http.server;'
            'from socketserver import TCPServer;'
            'TCPServer.allow_reuse_address = True;'
            'httpd = TCPServer(("localhost", {port}), http.server.SimpleHTTPRequestHandler);'
            'print("Test HTTP server: serving localhost at port {port}");'
            'httpd.serve_forever()'.format(port=http_port())
        )

    def teardown_test_environment(self, **kwargs):
        super(CremeDiscoverRunner, self).teardown_test_environment(**kwargs)
        settings.MEDIA_ROOT = self._original_media_root

        if self._mock_media_path:
            rmtree(self._mock_media_path)

        if self._http_server is not None:
            self._http_server.terminate()

    # def setup_databases(self, *args, **kwargs):
    #     res = super(CremeDiscoverRunner, self).setup_databases(*args, **kwargs)
    #     # PopulateCommand().execute(verbosity=0)
    #     call_command(PopulateCommand(), verbosity=0)
    #
    #     ContentType.objects.clear_cache()  # The cache seems corrupted when we switch to the test DB
    #
    #     return res
