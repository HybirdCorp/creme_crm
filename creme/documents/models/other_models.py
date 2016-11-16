# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2016  Hybird
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

import uuid

from django.db.models import CharField, BooleanField, UUIDField
from django.utils.translation import ugettext_lazy as _

from creme.creme_core.models import CremeModel

from ..constants import MIMETYPE_PREFIX_IMG


class FolderCategory(CremeModel):
    name      = CharField(_(u'Category name'), max_length=100, unique=True)
    is_custom = BooleanField(default=True).set_tags(viewable=False)  # Used by creme_config

    class Meta:
        app_label = 'documents'
        verbose_name = _(u'Folder category')
        verbose_name_plural = _(u'Folder categories')
        ordering = ('name',)

    def __unicode__(self):
        return self.name


class DocumentCategory(CremeModel):
    name      = CharField(_(u'Name'), max_length=100, unique=True)
    uuid      = UUIDField(default=uuid.uuid4, editable=False).set_tags(viewable=False)
    is_custom = BooleanField(default=True).set_tags(viewable=False)

    class Meta:
        app_label = 'documents'
        verbose_name = _(u'Document category')
        verbose_name_plural = _(u'Document categories')
        ordering = ('name',)

    def __unicode__(self):
        return self.name


class MimeType(CremeModel):
    name = CharField(_(u'Name'), max_length=100, unique=True)

    class Meta:
        app_label = 'documents'
        verbose_name = _(u'MIME type')
        verbose_name_plural = _(u'MIME types')
        ordering = ('name',)

    def __unicode__(self):
        return self.name

    @property
    def is_image(self):
        return self.name.startswith(MIMETYPE_PREFIX_IMG)
