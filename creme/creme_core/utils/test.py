################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2015-2023  Hybird
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

# import os
import pathlib
import unittest
from shutil import rmtree
from tempfile import mkdtemp

from django.apps import apps
from django.conf import settings
from django.core.mail.backends import locmem
from django.core.management import call_command
from django.test.runner import DiscoverRunner, ParallelTestSuite, _init_worker

# from ..utils.system import python_subprocess
from ..management.commands.creme_populate import Command as PopulateCommand

# def http_port():
#     return getattr(settings, 'TEST_HTTP_SERVER_PORT', '8001')


def reset_contenttype_cache():
    """Reset content type cache.
    The import is here to prevent issues if django.setup() was not called
    before the creme.utils.test import : could happen if 'spawn' is used
    for multiprocessing on Windows or OSX.
    """
    from django.contrib.contenttypes.models import ContentType
    ContentType.objects.clear_cache()


def check_runner_can_fork(runner):
    """Check if the system can create 'fork'.
    - A fork will clone the process and continue with the context of the fork point.
    - A spawn will create a new python machine and import again all the libraries.
      Does not work with the hacks on connections done by the test runner.
    Obviously, Windows only support 'spawn'...
    """
    import multiprocessing

    if runner.parallel > 1 and 'fork' not in multiprocessing.get_all_start_methods():
        raise ValueError(
            f"You cannot use --parallel={runner.parallel}; Your system does not support 'fork'"
        )


def creme_test_populate():
    """Run creme_populate of the test database"""
    from django.db import connection

    print(f"Populate test database '{connection.settings_dict['NAME']}'...")
    populate_command = PopulateCommand()
    populate_command.requires_system_checks = False
    populate_command.requires_migrations_checks = False
    call_command(populate_command, verbosity=0)
    # The cache seems corrupted when we switch to the test DB
    reset_contenttype_cache()


# def creme_init_worker(counter):
def creme_init_worker(counter,
                      initial_settings=None,
                      serialized_contents=None,
                      process_setup=None,
                      process_setup_args=None,
                      debug_mode=None,
                      ):
    # _init_worker(counter)
    _init_worker(
        counter=counter,
        initial_settings=initial_settings,
        serialized_contents=serialized_contents,
        process_setup=process_setup,
        process_setup_args=process_setup_args,
        debug_mode=debug_mode,
    )
    creme_test_populate()


class CremeParallelTestSuite(ParallelTestSuite):
    """This test suite populates the DB in the Creme way (parallel version)."""
    init_worker = creme_init_worker


class CremeTestLoader(unittest.TestLoader):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._allowed_paths = [app_conf.path for app_conf in apps.get_app_configs()]
        self._ignored_dir_paths = set()

    def is_path_relative_to(self, path, parent_path):
        try:
            path.relative_to(parent_path)
            return True
        except ValueError:
            return False

    def _match_path(self, path, full_path, pattern):
        match = super()._match_path(path, full_path, pattern)

        if match:
            dir_path = pathlib.Path(full_path).parent
            path_is_ok = self.is_path_relative_to

            if not any(path_is_ok(dir_path, allowed_path) for allowed_path in self._allowed_paths):
                if dir_path not in self._ignored_dir_paths:
                    self._ignored_dir_paths.add(dir_path)
                    print(f'"{dir_path}" is ignored because app seems not installed.')

                return False

        return match


class EmailBackend(locmem.EmailBackend):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.args = args
        self.kwargs = kwargs


class CremeDiscoverRunner(DiscoverRunner):
    """This test runner:
    - overrides settings.MEDIA_ROOT with a temporary directory ;
      so files created by the tests can be easily removed.
    """
    # - launches an HTTP server which serves static files, in order to test code
    #   which retrieve HTTP resources.

    parallel_test_suite = CremeParallelTestSuite

    # Not "django.core.mail.backends.locmem.EmailBackend"
    EMAIL_BACKEND = 'creme.creme_core.utils.test.EmailBackend'

    def __init__(self, *args, **kwargs):
        # Create the instance here to prevent issues if django.setup() was not called
        # before the creme.utils.test import : could happen if 'spawn' is used
        # for multiprocessing on Windows or OSX.
        self.test_loader = CremeTestLoader()

        super().__init__(*args, **kwargs)
        check_runner_can_fork(self)

        self._mock_media_path = None
        self._original_media_root = settings.MEDIA_ROOT
        # self._http_server = None

    def setup_test_environment(self, **kwargs):
        super().setup_test_environment(**kwargs)
        self.log('Creating mock media directory...')
        self._mock_media_path = settings.MEDIA_ROOT = mkdtemp(prefix='creme_test_media')
        self.log(f' ... {self._mock_media_path} created.')
        # script = (
        #     'import http.server;'
        #     'import os;'
        #     'from socketserver import TCPServer;'
        #     'os.chdir(r"{path}");'
        #     'TCPServer.allow_reuse_address = True;'
        #     'httpd = TCPServer(("localhost", {port}), http.server.SimpleHTTPRequestHandler);'
        #     'print(r"Test HTTP server: serving localhost:{path} at port {port} with process ID:", os.getpid());'  # NOQA
        #     'httpd.serve_forever()'
        # ).format(
        #     path=os.fspath(pathlib.Path(settings.CREME_ROOT).parent),
        #     port=http_port(),
        # )
        #
        # self._http_server = python_subprocess(script)
        settings.EMAIL_BACKEND = self.EMAIL_BACKEND

    def setup_databases(self, **kwargs):
        ret = super().setup_databases(**kwargs)
        creme_test_populate()

        return ret

    def _clean_mock_media(self):
        if self._mock_media_path:
            settings.MEDIA_ROOT = self._original_media_root

            self.log('Deleting mock media directory...')
            rmtree(self._mock_media_path)
            self._mock_media_path = None

    # def _clean_http_server(self):
    #     if self._http_server is not None:
    #         print('Shutting down HTTP server...')
    #         self._http_server.terminate()
    #         self._http_server.wait()
    #         self._http_server = None

    def teardown_test_environment(self, **kwargs):
        super().teardown_test_environment(**kwargs)
        self._clean_mock_media()
        # self._clean_http_server()

    def build_suite(self, *args, **kwargs):
        try:
            return super().build_suite(*args, **kwargs)
        except Exception:
            self._clean_mock_media()
            # self._clean_http_server()

            raise
