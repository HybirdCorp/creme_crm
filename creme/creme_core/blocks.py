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

from django.utils.translation import ugettext_lazy as _

from creme_core.gui.block import Block


class PropertiesBlock(Block):
    id_           = Block.generate_id('creme_core', 'properties')
    verbose_name  = _(u'Properties')
    template_name = 'creme_core/templatetags/block_properties.html'

    def detailview_display(self, context):
        entity = context['object']
        return self._render(self.get_block_template_context(context, entity.properties.all(),
                                                            update_url='/creme_core/properties/reload/%s/' % entity.pk))


class RelationsBlock(Block):
    id_           = Block.generate_id('creme_core', 'relations')
    order_by      = 'type'
    verbose_name  = _(u'Relations')
    template_name = 'creme_core/templatetags/block_relations.html'

    def detailview_display(self, context):
        entity = context['object']
        return self._render(self.get_block_template_context(context, entity.new_relations.filter(type__display_with_other=True),
                                                            update_url='/creme_core/relations/reload/%s/' % entity.pk))

properties_block = PropertiesBlock()
relations_block  = RelationsBlock()
