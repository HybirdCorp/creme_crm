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

from django.contrib.contenttypes.models import ContentType

from creme_core.utils import create_or_update_models_instance as create
from creme_core.utils.meta import get_verbose_field_name
from creme_core.models import SearchConfigItem, SearchField
from creme_core.models.header_filter import HeaderFilterItem, HeaderFilter, HFI_FIELD
from creme_core.management.commands.creme_populate import BasePopulator

from recurrents.models import RecurrentGenerator, Periodicity


class Populator(BasePopulator):
    dependencies = ['creme.core']

    def populate(self, *args, **kwargs):
        #TODO: i18n
        create(Periodicity, 1, name=u'Quotidienne',   value_in_days=1,   description=u'Tous les jours')
        create(Periodicity, 2, name=u'Hebdomadaire',  value_in_days=7,   description=u'Toutes les semaines')
        create(Periodicity, 3, name=u'Mensuelle',     value_in_days=30,  description=u'Tous les mois')
        create(Periodicity, 4, name=u'Trimestrielle', value_in_days=90,  description=u'Tous les trimestres')
        create(Periodicity, 5, name=u'Semestrielle',  value_in_days=180, description=u'Tous les semestres')
        create(Periodicity, 6, name=u'Annuelle',      value_in_days=365, description=u'Tous les ans')

        hf_id = create(HeaderFilter, 'recurrents-hf', name=u'Vue des générateurs', entity_type_id=ContentType.objects.get_for_model(RecurrentGenerator).id, is_custom=False).id
        pref = 'recurrents-hfi_'
        create(HeaderFilterItem, pref + 'name', order=1, name='name', title=u'Nom', type=HFI_FIELD, header_filter_id=hf_id, has_a_filter=True, editable=True, sortable=True, filter_string="name__icontains")

        model = RecurrentGenerator
        sci = create(SearchConfigItem, content_type_id=ContentType.objects.get_for_model(model).id)
        SCI_pk = sci.pk
        sci_fields = ['name', 'description', 'periodicity__name', 'ct__name']
        for i, field in enumerate(sci_fields):
            create(SearchField, field=field, field_verbose_name=get_verbose_field_name(model, field), order=i, search_config_item_id=SCI_pk)
