# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2021  Hybird
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

from django.db import models
from django.utils.translation import gettext_lazy as _

from .base import CremeModel


# TODO: add the possibility to choose a default currency which will be used everywhere in the CRM
class Currency(CremeModel):
    name = models.CharField(_('Currency'), max_length=100)
    local_symbol = models.CharField(_('Local symbol'), max_length=100)
    international_symbol = models.CharField(_('International symbol'), max_length=100)

    # Used by creme_config
    is_custom = models.BooleanField(default=True).set_tags(viewable=False)

    creation_label = _('Create a currency')

    def __str__(self):
        return self.name

    class Meta:
        app_label = 'creme_core'
        verbose_name = _('Currency')
        verbose_name_plural = _('Currencies')
        ordering = ('name',)
