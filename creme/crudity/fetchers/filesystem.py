# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2017  Hybird
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

import logging
import os.path

from django.conf import settings

from .base import CrudityFetcher


logger = logging.getLogger(__name__)


class FileSystemFetcher(CrudityFetcher):
    class FileSystemFetcherError(Exception):
        pass

    def __init__(self, setting_name='CRUDITY_FILESYS_FETCHER_DIR', *args, **kwargs):
        super(FileSystemFetcher, self).__init__(*args, **kwargs)
        self.setting_name = setting_name

    def fetch(self, *args, **kwargs):
        paths = []

        try:
            dir_path = self._get_path()
        except self.FileSystemFetcherError as e:
            logger.warn('FileSystemFetcher.fetch(): %s', e)
        else:
            for filename in os.listdir(dir_path):
                path = os.path.join(dir_path, filename)

                if not os.path.isdir(path):
                    paths.append(path)

        return paths

    def _get_path(self):
        setting_name = self.setting_name
        dir_path = getattr(settings, setting_name, None)

        if not dir_path:
            raise self.FileSystemFetcherError('setting.{} has not been set.'.format(setting_name))

        if not os.path.exists(dir_path):
            raise self.FileSystemFetcherError('settings.{} = "{}" does not exist.'.format(setting_name, dir_path))

        if not os.path.isdir(dir_path):
            raise self.FileSystemFetcherError('settings.{} = "{}" is not a directory.'.format(setting_name, dir_path))

        # TODO: credentials ??

        return dir_path
