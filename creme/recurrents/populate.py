# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2011  Hybird
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

from django.utils.translation import ugettext as _

from creme_core.utils import create_or_update as create
from creme_core.models import SearchConfigItem, HeaderFilterItem, HeaderFilter
from creme_core.management.commands.creme_populate import BasePopulator

from recurrents.models import RecurrentGenerator, Periodicity


class Populator(BasePopulator):
    dependencies = ['creme_core']

    def populate(self, *args, **kwargs):
        create(Periodicity, 1, name=_(u'Daily'),     value_in_days=1,   description=_(u'Every day'))
        create(Periodicity, 2, name=_(u'Weekly'),    value_in_days=7,   description=_(u'Every week'))
        create(Periodicity, 3, name=_(u'Monthly'),   value_in_days=30,  description=_(u'Every month'))
        create(Periodicity, 4, name=_(u'Quarterly'), value_in_days=90,  description=_(u'Every trimester'))
        create(Periodicity, 5, name=_(u'Biannual'),  value_in_days=180, description=_(u'Every semester'))
        create(Periodicity, 6, name=_(u'Annual'),    value_in_days=365, description=_(u'Every year'))

        hf = HeaderFilter.create(pk='recurrents-hf', name=_(u'Generator view'), model=RecurrentGenerator)
        hf.set_items([HeaderFilterItem.build_4_field(model=RecurrentGenerator, name='name')])

        SearchConfigItem.create(RecurrentGenerator, ['name', 'description', 'periodicity__name', 'ct__name'])

