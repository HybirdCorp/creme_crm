################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2017-2023  Hybird
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

# import os.path
import logging

# from django.conf import settings
from django.utils.translation import gettext as _

# from .base import CrudityFetcher
from .base import NEWCrudityFetcher

logger = logging.getLogger(__name__)


# class FileSystemFetcher(CrudityFetcher):
#     class FileSystemFetcherError(Exception):
#         pass
#
#     def __init__(self, setting_name='CRUDITY_FILESYS_FETCHER_DIR', *args, **kwargs):
#         super().__init__(*args, **kwargs)
#         self.setting_name = setting_name
#
#     def fetch(self, *args, **kwargs):
#         paths = []
#
#         try:
#             dir_path = self._get_path()
#         except self.FileSystemFetcherError as e:
#             logger.warning('FileSystemFetcher.fetch(): %s', e)
#         else:
#             for filename in os.listdir(dir_path):
#                 path = os.path.join(dir_path, filename)
#
#                 if not os.path.isdir(path):
#                     paths.append(path)
#
#         return paths
#
#     def _get_path(self):
#         setting_name = self.setting_name
#         # todo: validate it's a str
#         dir_path = getattr(settings, setting_name, None)
#
#         if not dir_path:
#             raise self.FileSystemFetcherError(
#                 f'setting.{setting_name} has not been set.'
#             )
#
#         if not os.path.exists(dir_path):
#             raise self.FileSystemFetcherError(
#                 f'settings.{setting_name} = "{dir_path}" does not exist.'
#             )
#
#         if not os.path.isdir(dir_path):
#             raise self.FileSystemFetcherError(
#                 f'settings.{setting_name} = "{dir_path}" is not a directory.'
#             )
#
#         # todo: credentials ??
#
#         return dir_path


class NEWFileSystemFetcher(NEWCrudityFetcher):
    id = NEWCrudityFetcher.generate_id('crudity', 'filesystem')
    verbose_name = _("Files on the server's file system")

    @classmethod
    def options_form(cls, **kwargs):
        from ..forms.fetchers.filesystem import FileSystemFetcherOptionsForm

        return FileSystemFetcherOptionsForm(**kwargs)

    def verbose_options(self):
        yield _('Directory: {}').format(self.options.get('path'))
