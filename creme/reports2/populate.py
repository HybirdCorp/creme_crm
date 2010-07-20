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

from django.utils.translation import ugettext as _
from django.contrib.contenttypes.models import ContentType

from creme_core.models import SearchConfigItem, SearchField
from creme_core.models.header_filter import HeaderFilterItem, HeaderFilter, HFI_FIELD
from creme_core.utils import create_or_update_models_instance as create
from creme_core.utils.meta import get_verbose_field_name
from creme_core.management.commands.creme_populate import BasePopulator

from models import Report2


class Populator(BasePopulator):
    dependencies = ['creme.core']

    def populate(self, *args, **kwargs):

        get_ct = ContentType.objects.get_for_model

        hf_id = create(HeaderFilter, 'reports2-hf', name=u'Vue de Rapport', entity_type_id=get_ct(Report2).id, is_custom=False).id
        pref  = 'reports2-hfi_report2_' 
        create(HeaderFilterItem, pref + 'name', order=1, name='name', title=_(u'Nom'),      type=HFI_FIELD, header_filter_id=hf_id, has_a_filter=True, editable=True, sortable=True, filter_string="name__icontains")
        create(HeaderFilterItem, pref + 'ct',   order=2, name='ct',   title=_(u"Type d'entité"), type=HFI_FIELD, header_filter_id=hf_id, has_a_filter=True, editable=True, sortable=True, filter_string="ct__name__icontains")


        model = Report2
        sci = create(SearchConfigItem, content_type_id=ContentType.objects.get_for_model(model).id)
        SCI_pk = sci.pk
        sci_fields = ['name', 'ct__name']
        for i, field in enumerate(sci_fields):
            create(SearchField, field=field, field_verbose_name=get_verbose_field_name(model, field), order=i, search_config_item_id=SCI_pk)

