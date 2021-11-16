# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2015-2021  Hybird
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

import unittest
from os.path import dirname
from shutil import rmtree
from tempfile import mkdtemp

from django.apps import apps
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.core.management import call_command
from django.test.runner import DiscoverRunner, ParallelTestSuite, _init_worker

from ..management.commands.creme_populate import Command as PopulateCommand
from ..utils.system import python_subprocess


def http_port():
    # return getattr(settings, 'TEST_HTTP_SERVER_PORT', '8000')
    return getattr(settings, 'TEST_HTTP_SERVER_PORT', '8001')


class CremeTestSuite(unittest.TestSuite):
    """This test suite populates the DB in the Creme way."""
    def run(self, *args, **kwargs):
        call_command(PopulateCommand(), verbosity=0)
        # The cache seems corrupted when we switch to the test DB
        ContentType.objects.clear_cache()

        return super().run(*args, **kwargs)


def creme_init_worker(counter):
    _init_worker(counter)
    call_command(PopulateCommand(), verbosity=0)
    # The cache seems corrupted when we switch to the test DB
    ContentType.objects.clear_cache()


class CremeParallelTestSuite(ParallelTestSuite):
    """This test suite populates the DB in the Creme way (parallel version)."""
    init_worker = creme_init_worker


class CremeTestLoader(unittest.TestLoader):
    suiteClass = CremeTestSuite

    def __init__(self):
        super().__init__()
        self._allowed_paths = [app_conf.path for app_conf in apps.get_app_configs()]
        self._ignored_dir_paths = set()

    def _match_path(self, path, full_path, pattern):
        match = super()._match_path(path, full_path, pattern)

        if match:
            dir_path = dirname(full_path)
            path_is_ok = dir_path.startswith

            if not any(path_is_ok(allowed_path) for allowed_path in self._allowed_paths):
                if dir_path not in self._ignored_dir_paths:
                    self._ignored_dir_paths.add(dir_path)
                    print(f'"{dir_path}" is ignored because app seems not installed.')

                return False

        return match


class CremeDiscoverRunner(DiscoverRunner):
    """This test runner
    - overrides settings.MEDIA_ROOT with a temporary directory ;
      so files created by the tests can be easily removed.
    - launches an HTTP server which serves static files, in order to test code
      which retrieve HTTP resources.
    """
    test_suite = CremeTestSuite
    parallel_test_suite = CremeParallelTestSuite
    test_loader = CremeTestLoader()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._mock_media_path = None
        self._original_media_root = settings.MEDIA_ROOT
        self._http_server = None

    def setup_test_environment(self, **kwargs):
        super().setup_test_environment(**kwargs)
        print('Creating mock media directory...')
        self._mock_media_path = settings.MEDIA_ROOT = mkdtemp(prefix='creme_test_media')
        print(f' ... {self._mock_media_path} created.')
        self._http_server = python_subprocess(
            'import http.server;'
            'import os;'
            'from socketserver import TCPServer;'
            'os.chdir("{path}");'
            'TCPServer.allow_reuse_address = True;'
            'httpd = TCPServer(("localhost", {port}), http.server.SimpleHTTPRequestHandler);'
            'print("Test HTTP server: serving localhost:{path} at port {port} with process ID:", os.getpid());'  # NOQA
            'httpd.serve_forever()'.format(
                path=dirname(settings.CREME_ROOT),
                port=http_port(),
            )
        )

    def _clean_mock_media(self):
        if self._mock_media_path:
            settings.MEDIA_ROOT = self._original_media_root

            print('Deleting mock media directory...')
            rmtree(self._mock_media_path)
            self._mock_media_path = None

    def _clean_http_server(self):
        if self._http_server is not None:
            print('Shutting down HTTP server...')
            self._http_server.terminate()
            self._http_server = None

    def teardown_test_environment(self, **kwargs):
        super().teardown_test_environment(**kwargs)
        self._clean_mock_media()
        self._clean_http_server()

    def build_suite(self, *args, **kwargs):
        try:
            return super().build_suite(*args, **kwargs)
        except Exception:
            self._clean_mock_media()
            self._clean_http_server()

            raise
