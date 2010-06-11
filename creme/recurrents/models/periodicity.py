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

from creme_core.models import CremeModel


class Periodicity(CremeModel):
    name            = CharField(_(u"Nom de la fréquence"), max_length=100, blank=True, null=True)
    value_in_days   = PositiveIntegerField(_(u'Valeur de la fréquence en jour'), blank=True, null=True)
    description     = TextField(_(u"Description de l'unité de temps"), blank=True, null=True)

    class Meta:
        app_label = 'recurrents'
        verbose_name = _(u'Périodicité de la récurrence des générateurs')
        verbose_name_plural = _(u'Périodicités de la récurrence des générateurs')

    def __unicode__(self):
        return self.name
