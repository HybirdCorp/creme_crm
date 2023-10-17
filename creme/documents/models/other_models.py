################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2025  Hybird
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

from __future__ import annotations

from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext_lazy

import creme.creme_core.models as core_models

from ..constants import MIMETYPE_PREFIX_IMG


class FolderCategory(core_models.MinionModel):
    name = models.CharField(_('Category name'), max_length=100, unique=True)

    creation_label = pgettext_lazy('documents-folder_category', 'Create a category')

    class Meta:
        app_label = 'documents'
        verbose_name = _('Folder category')
        verbose_name_plural = _('Folder categories')
        ordering = ('name',)

    def __str__(self):
        return self.name


class DocumentCategory(core_models.MinionModel):
    name = models.CharField(_('Name'), max_length=100, unique=True)

    creation_label = pgettext_lazy('documents-doc_category', 'Create a category')

    class Meta:
        app_label = 'documents'
        verbose_name = _('Document category')
        verbose_name_plural = _('Document categories')
        ordering = ('name',)

    def __str__(self):
        return self.name


class MimeTypeManager(models.Manager):
    def get_by_portable_key(self, key: str) -> MimeType:
        return self.get_or_create(name=key)[0]


class MimeType(core_models.CremeModel):
    name = models.CharField(_('Name'), max_length=100, unique=True)

    objects = MimeTypeManager()

    class Meta:
        app_label = 'documents'
        verbose_name = _('MIME type')
        verbose_name_plural = _('MIME types')
        ordering = ('name',)

    def __str__(self):
        return self.name

    @property
    def is_image(self):
        return self.name.startswith(MIMETYPE_PREFIX_IMG)

    def portable_key(self) -> str:
        return self.name
