################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2025  Hybird
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

from ..models.utils import model_verbose_name
from ..views import search as search_views

register = template.Library()


@register.inclusion_tag('creme_core/templatetags/search-form.html')
def search_form(*, models, selected_ct_id, search_terms):
    get_ct = ContentType.objects.get_for_model
    content_types = [
        {
            'id': get_ct(model).id,
            'verbose_name': model_verbose_name(model),
        } for model in models
    ]

    return {
        'min_length':     search_views.MIN_SEARCH_LENGTH,
        'content_types':  content_types,
        'selected_ct_id': selected_ct_id,
        'search_terms':   search_terms,
    }
