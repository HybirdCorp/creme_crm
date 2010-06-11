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

from logging import debug

from django import template
from django.contrib.contenttypes.models import ContentType

from creme_core.models import Filter, HeaderFilter


register = template.Library()

@register.inclusion_tag('creme_core/templatetags/list_view_filters_select.html')
def generate_listview_filters_select(content_type_id, selected_filter_id=""):
    all_filters   = Filter.objects.filter(model_ct__id=content_type_id).order_by('name')
    select_values = [{'value': filter_.id, 'text': filter_.name} for filter_ in all_filters] #TODO: use queryset.values('id', 'name')

    return {'select_values': select_values, 'content_type_id': content_type_id, 'selected_filter_id': selected_filter_id}

@register.inclusion_tag('creme_core/templatetags/list_view_header_filters_select.html')
def generate_listview_header_filters_select(content_type_id, selected_hfilter_id=""):
    all_hfilters  = HeaderFilter.objects.filter(entity_type__id=content_type_id).order_by('name')
    select_values = [{'value': hfilter.id, 'text': hfilter.name} for hfilter in all_hfilters]

    return {'select_values': select_values, 'content_type_id': content_type_id, "selected_hfilter_id": selected_hfilter_id}
