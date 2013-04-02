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

from django import template
from django.contrib.contenttypes.models import ContentType

from creme.creme_core.registry import creme_registry


register = template.Library()

@register.inclusion_tag('creme_core/templatetags/search_panel.html', takes_context=True)
def get_search_panel(context, target_node_id='sub_content'):
    get_ct = ContentType.objects.get_for_model
    content_types = [{'id':           get_ct(model).id,
                      'verbose_name': model._meta.verbose_name,
                     } for model in creme_registry.iter_entity_models()
                    ]
    content_types.sort(key=lambda k: k['verbose_name'])

    context.update({
            'content_types':  content_types,
            'target_node_id': target_node_id, #Ajax version / set your target html node's id
        })

    return context
