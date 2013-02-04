# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2012  Hybird
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

from django.utils.translation import ugettext_lazy as _
from django.contrib.contenttypes.models import ContentType

from creme_core.models import Relation, CremeProperty, HistoryLine #CremeEntity
from creme_core.gui.block import SimpleBlock, QuerysetBlock, BlocksManager, list4url


class PropertiesBlock(QuerysetBlock):
    id_           = QuerysetBlock.generate_id('creme_core', 'properties')
    dependencies  = (CremeProperty,)
    verbose_name  = _(u'Properties')
    template_name = 'creme_core/templatetags/block_properties.html'

    def detailview_display(self, context):
        entity = context['object']
        return self._render(self.get_block_template_context(context, entity.properties.select_related('type'),
                                                            update_url='/creme_core/blocks/reload/%s/%s/' % (self.id_, entity.pk),
                                                            ct_id=ContentType.objects.get_for_model(CremeProperty).id,
                                                           ))


class RelationsBlock(QuerysetBlock):
    id_           = QuerysetBlock.generate_id('creme_core', 'relations')
    dependencies  = (Relation,) #NB: (Relation, CremeEntity) but useless
    relation_type_deps = () #voluntarily void -> see detailview_display(): only types not present in another block are displayed
    order_by      = 'type'
    verbose_name  = _(u'Relationships')
    template_name = 'creme_core/templatetags/block_relations.html'

    def detailview_display(self, context):
        entity = context['object']
        user   = context['user']
        relations = entity.relations.select_related('type', 'type__symmetric_type', 'object_entity')
        excluded_types = BlocksManager.get(context).used_relationtypes_ids

        if excluded_types:
            update_url = '/creme_core/blocks/reload/relations_block/%s/%s/' % (entity.pk, ','.join(excluded_types))
            relations  = relations.exclude(type__in=excluded_types)
        else:
            update_url = '/creme_core/blocks/reload/relations_block/%s/' % entity.pk

        btc = self.get_block_template_context(context, relations, update_url=update_url)

        #NB: DB optimisation
        relations = btc['page'].object_list
        Relation.populate_real_object_entities(relations)
        #CremeEntity.populate_credentials([r.object_entity.get_real_entity() for r in relations], user)

        return self._render(btc)


class CustomFieldsBlock(SimpleBlock):
    id_           = SimpleBlock.generate_id('creme_core', 'customfields')
    #dependencies  = ()
    verbose_name  = _(u'Custom fields')
    template_name = 'creme_core/templatetags/block_customfields.html'


class HistoryBlock(QuerysetBlock):
    id_           = QuerysetBlock.generate_id('creme_core', 'history')
    #dependencies  = (HistoryLine, CremeProperty)
    dependencies  = '*'
    read_only     = True
    order_by      = '-date'
    verbose_name  = _(u'History')
    template_name = 'creme_core/templatetags/block_history.html'

    #TODO: factorise (see assistants.block) ??
    @staticmethod
    def _populate_related_real_entities(hlines, user):
        hlines = [hline for hline in hlines if hline.entity_id]
        entities_ids_by_ct = defaultdict(set)
        get_ct = ContentType.objects.get_for_id

        for hline in hlines:
            ct_id = hline.entity_ctype_id
            hline.entity_ctype = get_ct(ct_id)
            entities_ids_by_ct[ct_id].add(hline.entity_id)

        entities_map = {}
        get_ct = ContentType.objects.get_for_id

        for ct_id, entities_ids in entities_ids_by_ct.iteritems():
            entities_map.update(get_ct(ct_id).model_class().objects.in_bulk(entities_ids))

        for hline in hlines:
            hline.entity = entities_map[hline.entity_id]

        #CremeEntity.populate_credentials(entities_map.values(), user) #beware: values() and not itervalues()

    def detailview_display(self, context):
        pk = context['object'].pk
        return self._render(self.get_block_template_context(context, HistoryLine.objects.filter(entity=pk),
                                                            update_url='/creme_core/blocks/reload/%s/%s/' % (self.id_, pk),
                                                           ))

    def portal_display(self, context, ct_ids):
        btc = self.get_block_template_context(context,
                                              HistoryLine.objects.filter(entity_ctype__in=ct_ids),
                                              update_url='/creme_core/blocks/reload/portal/%s/%s/' % (self.id_, list4url(ct_ids)),
                                             )
        self._populate_related_real_entities(btc['page'].object_list, context['request'].user)

        return self._render(btc)

    def home_display(self, context):
        btc = self.get_block_template_context(context,
                                              HistoryLine.objects.exclude(type=HistoryLine.TYPE_SYM_RELATION),
                                              update_url='/creme_core/blocks/reload/home/%s/' % self.id_,
                                             )
        self._populate_related_real_entities(btc['page'].object_list, context['request'].user)

        return self._render(btc)


properties_block   = PropertiesBlock()
relations_block    = RelationsBlock()
customfields_block = CustomFieldsBlock()
history_block      = HistoryBlock()
