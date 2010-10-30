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

from collections import defaultdict

from django.contrib.contenttypes.models import ContentType
from django.utils.translation import ugettext_lazy as _

from creme_core.gui.block import QuerysetBlock, list4url

from commercial.models import CommercialApproach


class ApproachesBlock(QuerysetBlock):
    id_           = QuerysetBlock.generate_id('commercial', 'approaches')
    dependencies  = (CommercialApproach,)
    order_by      = 'title'
    verbose_name  = _(u'Commercial Approaches')
    template_name = 'commercial/templatetags/block_approaches.html'
    configurable  = True

    #TODO: factorise with assistants blocks (CremeEntity method ??)
    @staticmethod
    def _populate_related_real_entities(comapps, user):
        entities_ids_by_ct = defaultdict(set)

        for comapp in comapps:
            entities_ids_by_ct[comapp.entity_content_type_id].add(comapp.entity_id)

        entities_map = {}
        get_ct = ContentType.objects.get_for_id

        for ct_id, entities_ids in entities_ids_by_ct.iteritems():
            entities_map.update(get_ct(ct_id).model_class().objects.in_bulk(entities_ids))

        for comapp in comapps:
            comapp.creme_entity = entities_map[comapp.entity_id]

    def detailview_display(self, context):
        pk = context['object'].pk
        return self._render(self.get_block_template_context(context, CommercialApproach.get_approaches(pk),
                                                            update_url='/creme_core/blocks/reload/%s/%s/' % (self.id_, pk),
                                                           ))

    def portal_display(self, context, ct_ids):
        btc = self.get_block_template_context(context,
                                              CommercialApproach.get_approaches_for_ctypes(ct_ids),
                                              update_url='/creme_core/blocks/reload/portal/%s/%s/' % (self.id_, list4url(ct_ids)),
                                             )
        self._populate_related_real_entities(btc['page'].object_list, context['request'].user)

        return self._render(btc)

    def home_display(self, context):
        btc = self.get_block_template_context(context, CommercialApproach.get_approaches(),
                                              update_url='/creme_core/blocks/reload/home/%s/' % self.id_,
                                             )
        self._populate_related_real_entities(btc['page'].object_list, context['request'].user)

        return self._render(btc)


approaches_block = ApproachesBlock()
