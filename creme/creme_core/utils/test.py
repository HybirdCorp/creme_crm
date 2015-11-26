# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2015  Hybird
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

from __future__ import print_function

from os.path import dirname
from unittest.loader import TestLoader

from django.apps import apps
from django.test.runner import DiscoverRunner


class CremeTestLoader(TestLoader):
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
                    print('"%s" is ignored because app seems not installed.' % dir_path)

                return False

        return match


class CremeDiscoverRunner(DiscoverRunner):
    test_loader = CremeTestLoader()
