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
from django.db import models
from django.utils.html import escape
from django.utils.translation import ugettext as _
from django.contrib.contenttypes.models import ContentType

from creme_core.models.header_filter import HeaderFilter, HFI_FIELD, HFI_RELATION, HFI_FUNCTION, HFI_CUSTOM
from creme_core.models import Filter, CustomField
from creme_core.templatetags.creme_core_tags import get_html_field_value


register = template.Library()

@register.inclusion_tag('creme_core/templatetags/listview_filters.html', takes_context=True)
def get_listview_filters(context):
    filters = Filter.objects.filter(model_ct=context['content_type_id']).order_by('name') #TODO: retrieve in a cache...

    context['select_values'] = [{'value': filter_.id, 'text': filter_.name} for filter_ in filters] #TODO: use queryset.values('id', 'name') ??

    return context

@register.inclusion_tag('creme_core/templatetags/listview_headerfilters.html', takes_context=True)
def get_listview_headerfilters(context):
    hfilters = context['header_filters']

    context['select_values'] = [{'value': hfilter.id, 'text': hfilter.name} for hfilter in hfilters]
    context['hfilter']       = hfilters.selected

    return context

def _build_bool_search_widget(item_ctx, search_value):
    #TODO : Hack or not ? / Remember selected value ?
    selected_value = search_value[0] if search_value else None
    item_ctx['type'] = 'checkbox'
    item_ctx['values'] = [{
                            'value':    '1',
                            'text':     _("Oui"),
                            'selected': 'selected' if selected_value == '1' else ''
                           }, {
                            'value':    '0',
                            'text':     _("Non"),
                            'selected': 'selected' if selected_value == '0' else ''
                           }
                ]

def _build_date_search_widget(item_ctx, search_value):
    #TODO: Needs datetime validation
    item_ctx['type'] = 'datefield'
    if search_value:
        if len(search_value) > 1:
            item_ctx['values'] = {'start': search_value[0], 'end': search_value[1]}
        elif len(search_value) == 1:
            item_ctx['values'] = {'start': search_value[0], 'end': search_value[0]}

def _build_select_search_widget(item_ctx, search_value, choices):
    selected_value = unicode(search_value[0].decode('utf-8')) if search_value else None #bof bof
    item_ctx['type'] = 'select'
    item_ctx['values'] = [{
                            'value':    id_,
                            'text':     unicode(val),
                            'selected': 'selected' if selected_value == unicode(val) else ''
                          } for id_, val in choices
                         ]

@register.inclusion_tag('creme_core/templatetags/listview_columns_header.html', takes_context=True)
def get_listview_columns_header(context):
    model               = context['model']
    list_view_state     = context['list_view_state']
    header_filter_items = context['columns']

    header_searches = dict((name_attribut, value) for (name_attribut, pk, type, pattern, value) in list_view_state.research)
    header_ctx = {}
    get_model_field = model._meta.get_field

    for item in header_filter_items:
        if not item.has_a_filter:
            continue

        item_value = header_searches.get(item.name, '') #TODO: rename....
        item_dict = {'value': item_value, 'type': 'text'}
        item_type = item.type

        if item_type == HFI_FIELD:
            try:
                field = get_model_field(item.name)
            except FieldDoesNotExist:
                continue

            if isinstance(field, models.ForeignKey):
                _build_select_search_widget(item_dict, item_value,
                                            ((o.id, o) for o in field.rel.to.objects.distinct().order_by(*field.rel.to._meta.ordering) if unicode(o) != ""))
            elif isinstance(field, models.BooleanField):
                _build_bool_search_widget(item_dict, item_value)
            elif isinstance(field, (models.DateField, models.DateTimeField)):
                _build_date_search_widget(item_dict, item_value)
            #elif hasattr(item_value, '__iter__') and len(item_value) >= 1: #TODO: "elif item_value"
            elif item_value:
                item_dict['value'] = item_value[0]
        elif item_type == HFI_FUNCTION:
            #if hasattr(item_value, '__iter__') and len(item_value) >= 1:
            if item_value:
                item_dict['value'] = item_value[0]
        elif item_type == HFI_RELATION:
            #if hasattr(item_value, '__iter__') and len(item_value) >= 1:
            if item_value:
                item_dict['value'] = item_value[0]
        elif item_type == HFI_CUSTOM:
            cf = item.get_customfield()
            field_type = cf.field_type

            if field_type in (CustomField.ENUM, CustomField.MULTI_ENUM):
                _build_select_search_widget(item_dict, item_value, cf.customfieldenumvalue_set.values_list('id', 'value'))
            elif field_type == CustomField.DATE:
                _build_date_search_widget(item_dict, item_value)
            elif field_type == CustomField.BOOL:
                _build_bool_search_widget(item_dict, item_value)
            elif item_value:
                item_dict['value'] = item_value[0]

        header_ctx.update({item.name: item_dict})

    context['columns_values'] = header_ctx

    return context

@register.filter(name="hf_get_html_output")
def get_html_output(hfi, entity):
    hfi_type = hfi.type

    try:
        if hfi_type == HFI_FIELD:
            return get_html_field_value(entity, hfi.name)

        if hfi_type == HFI_FUNCTION:
            return getattr(entity, hfi.name)()

        if hfi_type == HFI_RELATION:
            relations_list = ["<ul>"]
            relations_list.extend(u'<li><a href="%s">%s</a></li>' % (obj.get_absolute_url(), escape(obj))
                                    for obj in entity.get_related_entities(hfi.relation_predicat_id, True))
            relations_list.append("</ul>")

            return u''.join(relations_list)

        if hfi_type == HFI_CUSTOM:
            return entity.get_custom_value(hfi.get_customfield())
    except AttributeError, e:
        debug('Templatetag "hf_get_html_output": %s', e)
        return u""
