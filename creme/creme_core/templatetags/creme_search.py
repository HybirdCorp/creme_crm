# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2021  Hybird
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

from ..core.search import Searcher
from ..registry import creme_registry
from ..utils.unicode_collation import collator
from ..views import search as search_views

register = template.Library()


@register.inclusion_tag('creme_core/templatetags/search-form.html')
def search_form(*, user, selected_ct_id, search_terms):
    get_ct = ContentType.objects.get_for_model
    content_types = [
        {
            'id':           get_ct(model).id,
            'verbose_name': str(model._meta.verbose_name),
        } for model in Searcher(creme_registry.iter_entity_models(), user).models
    ]
    sort_key = collator.sort_key
    content_types.sort(key=lambda k: sort_key(k['verbose_name']))

    return {
        'min_length':     search_views.MIN_RESEARCH_LENGTH,
        'content_types':  content_types,
        'selected_ct_id': selected_ct_id,
        'search_terms':   search_terms,
    }
