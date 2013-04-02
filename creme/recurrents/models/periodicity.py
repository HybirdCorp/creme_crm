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

from django.db.models import CharField, TextField, PositiveIntegerField
from django.utils.translation import ugettext_lazy as _

from creme.creme_core.models import CremeModel


class Periodicity(CremeModel):
    name            = CharField(_(u"Name of the periodicity"), max_length=100, blank=True, null=True)
    value_in_days   = PositiveIntegerField(_(u'Duration of the period (in days)'), blank=True, null=True) #TODO: rename to 'period' ???
    description     = TextField(_(u"Description of the time unit"), blank=True, null=True)

    class Meta:
        app_label = 'recurrents'
        verbose_name = _(u'Periodicity of generator recurennce')
        verbose_name_plural = _(u'Periodicities of generator recurennce')

    def __unicode__(self):
        return self.name
