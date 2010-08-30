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

from creme_core.models import SearchConfigItem
from creme_core.models.header_filter import HeaderFilterItem, HeaderFilter, HFI_FIELD
from creme_core.utils import create_or_update_models_instance as create
from creme_core.management.commands.creme_populate import BasePopulator

from models import Report


class Populator(BasePopulator):
    dependencies = ['creme.core']

    def populate(self, *args, **kwargs):

        get_ct = ContentType.objects.get_for_model

        hf_id = create(HeaderFilter, 'reports-hf', name=_(u'Report view'), entity_type_id=get_ct(Report).id, is_custom=False).id
        pref  = 'reports-hfi_report_' 
        create(HeaderFilterItem, pref + 'name', order=1, name='name', title=_(u'Name'),        type=HFI_FIELD, header_filter_id=hf_id, has_a_filter=True, editable=True, sortable=True, filter_string="name__icontains")
        create(HeaderFilterItem, pref + 'ct',   order=2, name='ct',   title=_(u"Entity type"), type=HFI_FIELD, header_filter_id=hf_id, has_a_filter=True, editable=True, sortable=True, filter_string="ct__name__icontains")

        SearchConfigItem.create(Report, ['name', 'ct__name'])

