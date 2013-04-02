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

from django.utils.translation import ugettext_lazy as _
from django.db import models

from creme.creme_core.models import CremeModel


__all__ = (
    'MediaCategory',
)


class MediaCategory(CremeModel):
    name      = models.CharField(_(u'Name of media category'), max_length=100)
    is_custom = models.BooleanField(default=True)

    def __unicode__(self):
        return self.name

    class Meta:
        app_label = "media_managers"
        verbose_name = _(u'Media category')
        verbose_name_plural = _(u'Media categories')
