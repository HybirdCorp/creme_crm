# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2013  Hybird
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

import logging

from django.template import Library
from django.db import models
from django.utils.html import escape
from django.utils.translation import ugettext as _

from ..models.header_filter import HFI_FIELD, HFI_RELATION, HFI_FUNCTION, HFI_CUSTOM, HFI_VOLATILE
from ..models import CustomField
from ..utils.meta import get_model_field_info
from ..gui.field_printers import field_printers_registry
from ..gui.list_view_import import import_form_registry
from .creme_widgets import widget_entity_hyperlink


logger = logging.getLogger(__name__)
register = Library()


@register.inclusion_tag('creme_core/templatetags/listview_entityfilters.html', takes_context=True)
def get_listview_entity_filters(context):
    efilters = context['entity_filters']
    efilter  = efilters.selected

    context['efilter'] = efilter

    if efilter:
        efilter_id = efilter.id
        permission = efilter.can_edit_or_delete(context['request'].user)[0]
    else:
        efilter_id = 0
        permission = False

    context['efilter_id'] = efilter_id
    context['can_edit_or_delete'] = permission
    context['select_values'] = [{'value': ef.id, 'text': ef.name} for ef in efilters]

    return context

@register.inclusion_tag('creme_core/templatetags/listview_headerfilters.html', takes_context=True)
def get_listview_headerfilters(context):
    hfilters = context['header_filters']
    hfilter  = hfilters.selected

    context['hfilter'] = hfilter
    context['can_edit_or_delete'] = hfilter.can_edit_or_delete(context['request'].user)[0]
    context['select_values'] = [{'value': hf.id, 'text': hf.name} for hf in hfilters]

    return context

#get_listview_columns_header####################################################

def _build_bool_search_widget(widget_ctx, search_value):
    #TODO : Hack or not ? / Remember selected value ?
    selected_value = search_value[0] if search_value else None
    widget_ctx['type'] = 'checkbox'
    widget_ctx['values'] = [{'value':    '1',
                             'text':     _("Yes"),
                             'selected': 'selected' if selected_value == '1' else ''
                            },
                            {'value':    '0',
                             'text':     _("No"),
                             'selected': 'selected' if selected_value == '0' else ''
                            }
                           ]

def _build_date_search_widget(widget_ctx, search_value):
    #TODO: Needs datetime validation
    widget_ctx['type'] = 'datefield'
    if search_value:
        widget_ctx['values'] = {'start': search_value[0], 'end': search_value[-1]}

def _build_select_search_widget(widget_ctx, search_value, choices):
    selected_value = unicode(search_value[0].decode('utf-8')) if search_value else None #bof bof
    widget_ctx['type'] = 'select'
    widget_ctx['values'] = [{'value':    id_,
                             'text':     unicode(val),
                             'selected': 'selected' if selected_value == unicode(id_) else ''
                            } for id_, val in choices
                           ]

@register.inclusion_tag('creme_core/templatetags/listview_columns_header.html', takes_context=True)
def get_listview_columns_header(context):
    model           = context['model']
    header_searches = dict((attr_name, value) for (attr_name, pk, type, pattern, value) in context['list_view_state'].research)
    get_model_field = model._meta.get_field

    for item in context['columns']:
        if not item.has_a_filter:
            continue

        item_value = header_searches.get(item.name, '')
        widget_ctx = {'value': item_value, 'type': 'text'}
        item_type = item.type

        if item_type == HFI_FIELD:
            try:
                field_name = item.name
                if field_name.find('__') > -1:
                    field = None
                    sub_field_obj = get_model_field_info(model, field_name)[1]['field']
                    if isinstance(sub_field_obj, (models.DateField, models.DateTimeField, models.BooleanField)):
                        field = sub_field_obj
                else:
                    field = get_model_field(field_name)
            except models.FieldDoesNotExist:
                continue

            if isinstance(field, models.ForeignKey):
                _build_select_search_widget(widget_ctx, item_value,
                                            ((o.id, o) for o in field.rel.to.objects.distinct().order_by(*field.rel.to._meta.ordering) if unicode(o) != ""))
            elif isinstance(field, models.BooleanField):
                _build_bool_search_widget(widget_ctx, item_value)
            elif isinstance(field, (models.DateField, models.DateTimeField)):
                _build_date_search_widget(widget_ctx, item_value)
            elif item_value:
                widget_ctx['value'] = item_value[0]
        elif item_type == HFI_FUNCTION:
            choices = item.get_functionfield().choices
            if choices is not None:
                _build_select_search_widget(widget_ctx, item_value, choices)
            elif item_value:
                widget_ctx['value'] = item_value[0]
        elif item_type == HFI_RELATION:
            if item_value:
                widget_ctx['value'] = item_value[0]
        elif item_type == HFI_CUSTOM:
            cf = item.get_customfield()
            field_type = cf.field_type

            if field_type in (CustomField.ENUM, CustomField.MULTI_ENUM):
                _build_select_search_widget(widget_ctx, item_value, cf.customfieldenumvalue_set.values_list('id', 'value'))
            elif field_type == CustomField.DATE:
                _build_date_search_widget(widget_ctx, item_value)
            elif field_type == CustomField.BOOL:
                _build_bool_search_widget(widget_ctx, item_value)
            elif item_value:
                widget_ctx['value'] = item_value[0]

        item.widget_ctx = widget_ctx

    return context

#get_listview_cell##############################################################

def _render_relations(entity, hfi, user):
    relations_list = ['<ul>']
    #append = relations_list.append

    #for e in entity.get_related_entities(hfi.relation_predicat_id, True):
        #if e.can_view(user):
            #append(u'<li><a href="%s">%s</a></li>' % (e.get_absolute_url(), escape(unicode(e))))
        #else:
            #append(u'<li>%s</li>' % escape(e.allowed_unicode(user)))
    relations_list.extend(u'<li>%s</li>' % widget_entity_hyperlink(e, user)
                            for e in entity.get_related_entities(hfi.relation_predicat_id, True)
                         )

    #append("</ul>")
    relations_list.append('</ul>')

    return u''.join(relations_list)

_GET_HTML_FIELD_VALUE = field_printers_registry.get_html_field_value

_RENDER_FUNCS = { #TODO: use a method in HeaderFilterItem ??
    HFI_FIELD:    lambda entity, hfi, user: _GET_HTML_FIELD_VALUE(entity, hfi.name, user),
    HFI_FUNCTION: lambda entity, hfi, user: hfi.get_functionfield()(entity).for_html(),
    HFI_RELATION: _render_relations,
    HFI_CUSTOM:   lambda entity, hfi, user: escape(entity.get_custom_value(hfi.get_customfield())),
    HFI_VOLATILE: lambda entity, hfi, user: hfi.volatile_render(entity),
}

@register.simple_tag
def get_listview_cell(hfi, entity, user):
    try:
        render_func = _RENDER_FUNCS.get(hfi.type)
        if render_func:
            return render_func(entity, hfi, user)
    except AttributeError as e:
        logger.debug('Templatetag "get_listview_cell": %s', e)

    return u""

@register.assignment_tag
def ctype_is_registered_for_import(ctype):
    return import_form_registry.is_registered(ctype)
