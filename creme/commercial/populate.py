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

from creme_core.models import RelationType, BlockConfigItem, CremePropertyType, \
                              SearchConfigItem
from creme_core.models.header_filter import HeaderFilterItem, HeaderFilter, HFI_FIELD
from creme_core.utils import create_or_update_models_instance as create
from creme_core.management.commands.creme_populate import BasePopulator

from commercial.models import Act
from commercial.blocks import approaches_block
from commercial.constants import PROP_IS_A_SALESMAN, REL_OBJ_SOLD_BY, REL_SUB_SOLD_BY


class Populator(BasePopulator):
    dependencies = ['creme.core']

    def populate(self, *args, **kwargs):
        RelationType.create((REL_SUB_SOLD_BY, _(u'has sold')),
                            (REL_OBJ_SOLD_BY, _(u'has been sold by')))


        CremePropertyType.create(PROP_IS_A_SALESMAN, _(u'is a salesman'))

        create(BlockConfigItem, 'commercial-approaches_block', content_type=None, block_id=approaches_block.id_, order=10,  on_portal=False)

        hf_id = create(HeaderFilter, 'commercial-hf_act', name=_(u"Com Action view"), entity_type_id=ContentType.objects.get_for_model(Act).id, is_custom=False).id
        pref  = 'commercial-hfi_act_'
        create(HeaderFilterItem, pref + 'name',        order=1, name='name',        title=_(u'Name'),           type=HFI_FIELD, header_filter_id=hf_id, has_a_filter=True, editable=True, sortable=True, filter_string="name__icontains")
        create(HeaderFilterItem, pref + 'ca_expected', order=2, name='ca_expected', title=_(u'Expected sales'), type=HFI_FIELD, header_filter_id=hf_id, has_a_filter=True, editable=True, sortable=True, filter_string="ca_expected__icontains")
        create(HeaderFilterItem, pref + 'due_date',    order=3, name='due_date',    title=_(u'Due date'),       type=HFI_FIELD, header_filter_id=hf_id, has_a_filter=True, editable=True, sortable=True, filter_string="due_date__range")

        SearchConfigItem.create(Act, ['name', 'ca_expected', 'cost', 'target', 'goal', 'aim'])
