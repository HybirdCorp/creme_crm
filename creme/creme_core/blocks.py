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

from django.utils.translation import ugettext_lazy as _
from django.contrib.contenttypes.models import ContentType

from creme_core.models import CremeEntity, Relation, CremeProperty #EntityCredentials
from creme_core.gui.block import Block, QuerysetBlock, BlocksManager


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
    verbose_name  = _(u'Relations')
    template_name = 'creme_core/templatetags/block_relations.html'

    def detailview_display(self, context):
        entity = context['object']
        user   = context['user']
        relations = entity.relations.select_related('type', 'type__symmetric_type', 'object_entity')
        #relations = EntityCredentials.filter_relations(user, relations)
        excluded_types = BlocksManager.get(context).get_used_relationtypes_ids()

        if excluded_types:
            update_url = '/creme_core/blocks/reload/relations_block/%s/%s/' % (entity.pk, ','.join(excluded_types))
            relations  = relations.exclude(type__in=excluded_types)
        else:
            update_url = '/creme_core/blocks/reload/relations_block/%s/' % entity.pk

        btc = self.get_block_template_context(context, relations, update_url=update_url)

        #NB: DB optimisation
        relations = btc['page'].object_list
        Relation.populate_real_object_entities(relations)
        CremeEntity.populate_credentials([r.object_entity.get_real_entity() for r in relations], user)

        return self._render(btc)


class CustomFieldsBlock(Block):
    id_           = Block.generate_id('creme_core', 'customfields')
    #dependencies  = ()
    verbose_name  = u'Custom fields'
    template_name = 'creme_core/templatetags/block_customfields.html'


properties_block   = PropertiesBlock()
relations_block    = RelationsBlock()
customfields_block = CustomFieldsBlock()
