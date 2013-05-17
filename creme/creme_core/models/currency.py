# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2013  Hybird
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

from django.db.models.fields import BooleanField, CharField
from django.utils.translation import ugettext_lazy as _

from .base import CremeModel


# TODO add the possibility to choose a default currency which will be used everywhere in the CRM
class Currency(CremeModel):
    name                    = CharField(_(u'Currency'), max_length=100)
    local_symbol            = CharField(_(u'Local symbol'), max_length=100)
    international_symbol    = CharField(_(u'International symbol'), max_length=100)
    is_custom               = BooleanField(default=True).set_tags(viewable=False) #used by creme_config

    def __unicode__(self):
        return self.name

    class Meta:
        app_label = 'creme_core'
        verbose_name = _(u'Currency')
        verbose_name_plural = _(u'Currency')