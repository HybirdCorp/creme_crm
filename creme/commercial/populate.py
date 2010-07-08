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

from creme_core.models import RelationType, BlockConfigItem, CremePropertyType, \
                              SearchConfigItem, SearchField
from creme_core.models.header_filter import HeaderFilterItem, HeaderFilter, HFI_FIELD
from creme_core.utils import create_or_update_models_instance as create
from creme_core.utils.meta import get_verbose_field_name
from creme_core.management.commands.creme_populate import BasePopulator

from commercial.models import Act
from commercial.blocks import approaches_block
from commercial.constants import PROP_IS_A_SALESMAN, REL_OBJ_SOLD_BY, REL_SUB_SOLD_BY


class Populator(BasePopulator):
    dependencies = ['creme.core']

    def populate(self, *args, **kwargs):
        RelationType.create((REL_SUB_SOLD_BY, u'a vendu'),
                            (REL_OBJ_SOLD_BY, u'a été vendu par'))


        CremePropertyType.create(PROP_IS_A_SALESMAN, u'est un commercial')

        create(BlockConfigItem, 'commercial-approaches_block', content_type=None, block_id=approaches_block.id_, order=10,  on_portal=False)

        hf_id = create(HeaderFilter, 'commercial-hf_act', name=u"Vue d'Action Com", entity_type_id=ContentType.objects.get_for_model(Act).id, is_custom=False).id
        pref  = 'commercial-hfi_act_'
        create(HeaderFilterItem, pref + 'name',        order=1, name='name',        title=u'Nom',       type=HFI_FIELD, header_filter_id=hf_id, has_a_filter=True, editable=True, sortable=True, filter_string="name__icontains")
        create(HeaderFilterItem, pref + 'ca_expected', order=2, name='ca_expected', title=u'CA espéré', type=HFI_FIELD, header_filter_id=hf_id, has_a_filter=True, editable=True, sortable=True, filter_string="ca_expected__icontains")
        create(HeaderFilterItem, pref + 'due_date',    order=3, name='due_date',    title=u'Échéance',  type=HFI_FIELD, header_filter_id=hf_id, has_a_filter=True, editable=True, sortable=True, filter_string="due_date__range")

        model = Act
        sci = create(SearchConfigItem, content_type_id=ContentType.objects.get_for_model(model).id)
        SCI_pk = sci.pk
        sci_fields = ['name', 'ca_expected', 'cost', 'target', 'goal', 'aim']
        for i, field in enumerate(sci_fields):
            create(SearchField, field=field, field_verbose_name=get_verbose_field_name(model, field), order=i, search_config_item_id=SCI_pk)
