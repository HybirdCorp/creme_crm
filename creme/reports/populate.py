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

from creme_core.models.header_filter import HeaderFilterItem, HeaderFilter, HFI_FIELD
from creme_core.utils import create_or_update_models_instance as create
from creme_core.management.commands.creme_populate import BasePopulator

from models import Report, Operation, Graph


class Populator(BasePopulator):
    dependencies = ['creme.core']

    def populate(self, *args, **kwargs):
        create(Operation, 1, name=_(u"Somme"),   operator="Sum", operator_pattern='%s__sum')
        create(Operation, 2, name=_(u"Minimum"), operator="Min", operator_pattern='%s__min')
        create(Operation, 3, name=_(u"Maximum"), operator="Max", operator_pattern='%s__max')
        create(Operation, 4, name=_(u"Moyenne"), operator="Avg", operator_pattern='%s__avg')

        get_ct = ContentType.objects.get_for_model

        hf_id = create(HeaderFilter, 'reports-hf', name=u'Vue de Rapport', entity_type_id=get_ct(Report).id, is_custom=False).id
        pref  = 'reports-hfi_' #'reports-hfi_report_' instead...
        create(HeaderFilterItem, pref + 'name', order=1, name='name', title=_(u'Nom'),      type=HFI_FIELD, header_filter_id=hf_id, has_a_filter=True, editable=True, sortable=True, filter_string="name__icontains")
        create(HeaderFilterItem, pref + 'ct',   order=2, name='ct',   title=_(u'Resource'), type=HFI_FIELD, header_filter_id=hf_id, has_a_filter=True, editable=True, sortable=True, filter_string="ct__name__icontains")

        hf_id = create(HeaderFilter, 'reports-hf', name=u'Vue de Graphe', entity_type_id=get_ct(Graph).id, is_custom=False).id
        pref  = 'reports-hfi_graph_'
        create(HeaderFilterItem, pref + 'name', order=1, name='name', title=_(u'Nom'), type=HFI_FIELD, header_filter_id=hf_id, has_a_filter=True, editable=True, sortable=True, filter_string="name__icontains")
