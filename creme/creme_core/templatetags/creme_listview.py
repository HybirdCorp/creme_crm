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
from django.contrib.contenttypes.models import ContentType

from creme_core.models.header_filter import HeaderFilter, HFI_FIELD, HFI_RELATION, HFI_FUNCTION, HFI_CUSTOM
from creme_core.models import Filter, CustomField, CustomFieldValue
from creme_core.templatetags.creme_core_tags import get_html_field_value


register = template.Library()

@register.inclusion_tag('creme_core/templatetags/listview_filters.html', takes_context=True)
def get_listview_filters(context):
    filters = Filter.objects.filter(model_ct=context['content_type_id']).order_by('name') #TODO: retrieve in a cache...

    context['select_values'] = [{'value': filter_.id, 'text': filter_.name} for filter_ in filters] #TODO: use queryset.values('id', 'name') ??

    return context

@register.inclusion_tag('creme_core/templatetags/listview_headerfilters.html', takes_context=True)
def get_listview_headerfilters(context):
    hfilters = HeaderFilter.objects.filter(entity_type=context['content_type_id']).order_by('name') #TODO: retrieve in a cache...

    context['select_values'] = [{'value': hfilter.id, 'text': hfilter.name} for hfilter in hfilters]

    return context

@register.inclusion_tag('creme_core/templatetags/listview_columns_header.html', takes_context=True)
def get_listview_columns_header(context):
    model               = context['model']
    list_view_state     = context['list_view_state']
    header_filter_items = context['columns']

    research = list_view_state.research

    if research:
        header_searches = dict((name_attribut, value) for (name_attribut, pk, type, pattern, value) in research)
    else:
        header_searches = {}

    header_ctx = {}
    get_model_field = model._meta.get_field

    for item in header_filter_items:
        #TODO : Implement for other type of headers which has a filter ?
        item_value = header_searches.get(item.name, '')

        if item.has_a_filter:
            item_dict = {'value': item_value, 'type': 'text'}

            if item.type == HFI_FIELD:
                try:
                    field = get_model_field(item.name)
                except FieldDoesNotExist:
                    continue

                if isinstance(field, models.ForeignKey):
                    selected_value = item_value[0].decode('utf-8') if len(item_value) >= 1 else None #bof bof

                    item_dict.update(
                            type='select',
                            values=[{
                                        'value':    o.id,
                                        'text':     unicode(o),
                                        'selected': 'selected' if selected_value == unicode(o) else ''
                                    } for o in field.rel.to.objects.distinct().order_by(*field.rel.to._meta.ordering) if unicode(o) != ""
                                ]
                        )
                elif isinstance(field, models.BooleanField):
                    #TODO : Hack or not ? / Remember selected value ?
                    item_dict.update(
                            type='checkbox',
                            values=[{'value':    '1',
                                     'text':     "Oui",
                                     'selected': 'selected' if len(item_value) >= 1 and item_value[0]=='1' else '' },
                                    {'value':    '0',
                                     'text':     "Non",
                                     'selected': 'selected' if len(item_value) >= 1 and item_value[0]=='0' else ''}
                                ]
                        )
                elif isinstance(field, models.DateField) or isinstance(field, models.DateTimeField):
                    item_dict['type'] = 'datefield'
                    try:
                        item_dict['values'] = {'start': item_value[0], 'end': item_value[1]}
                    except IndexError:
                        pass
                elif hasattr(item_value, '__iter__') and len(item_value) >= 1:
                    item_dict['value'] = item_value[0]
            elif item.type == HFI_CUSTOM:
                cf = CustomField.objects.get(pk=item.name)

                if cf.field_type == CustomField.ENUM:
                    selected_value = item_value[0].decode('utf-8') if item_value else None
                    item_dict['type'] = 'select'
                    item_dict['values'] = [{
                                            'value':    id_,
                                            'text':     unicode(cevalue),
                                            'selected': 'selected' if selected_value == cevalue else ''
                                            } for id_, cevalue in cf.customfieldenumvalue_set.values_list('id', 'value')
                                          ]
                elif item_value:
                    item_dict['value'] = item_value[0]

            header_ctx.update({item.name: item_dict})

    context['columns_values'] = header_ctx

    return context

#TODO: relations and custom fields should be retrieved before for all lines and put in a cache...
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
                                    for obj in entity.get_list_object_of_specific_relations(hfi.relation_predicat_id))
            relations_list.append("</ul>")

            return u''.join(relations_list)

        if hfi_type == HFI_CUSTOM:
            return CustomFieldValue.get_pretty_value(hfi.name, entity.id)
    except AttributeError, e:
        debug('Templatetag "hf_get_html_output": %s', e)
        return u""
