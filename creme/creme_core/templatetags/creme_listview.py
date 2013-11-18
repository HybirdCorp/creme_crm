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

from django.db import models
from django.template import Library
from django.utils.translation import ugettext as _

from ..core.entity_cell import (EntityCellRegularField, EntityCellCustomField,
        EntityCellFunctionField, EntityCellRelation)
from ..models import CustomField
from ..models.fields import EntityCTypeForeignKey
from ..gui.list_view_import import import_form_registry
from ..utils import creme_entity_content_types, build_ct_choices
from ..utils.meta import get_model_field_info
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
        #permission = efilter.can_edit_or_delete(context['request'].user)[0]
        permission = efilter.can_edit_or_delete(context['user'])[0]
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
    #context['can_edit_or_delete'] = hfilter.can_edit_or_delete(context['request'].user)[0]
    context['can_edit_or_delete'] = hfilter.can_edit_or_delete(context['user'])[0]
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

#TODO: add methods to EntityCells ?
@register.inclusion_tag('creme_core/templatetags/listview_columns_header.html', takes_context=True)
def get_listview_columns_header(context):
    model           = context['model']
    header_searches = dict((cell_value, value)
                                for (cell_type, cell_value, value) in context['list_view_state'].research
                          ) #TODO: (type, name as key)
    get_model_field = model._meta.get_field

    for cell in context['cells']:
        if not cell.has_a_filter:
            continue

        search_value = header_searches.get(cell.value, '')
        widget_ctx = {'value': search_value, 'type': 'text'}

        if isinstance(cell, EntityCellRegularField):
            try:
                field_name = cell.value
                if field_name.find('__') > -1:
                    field = None
                    sub_field_obj = get_model_field_info(model, field_name)[1]['field']
                    if isinstance(sub_field_obj, (models.DateField, models.DateTimeField, models.BooleanField)): #TODO: DateTimeField useful ??
                        field = sub_field_obj
                else:
                    field = get_model_field(field_name)
            except models.FieldDoesNotExist:
                continue

            if isinstance(field, models.ForeignKey):
                if cell.filter_string.endswith('__header_filter_search_field__icontains'):
                    if search_value:
                        widget_ctx['value'] = search_value[0]
                else:
                    if isinstance(field, EntityCTypeForeignKey):
                        choices = build_ct_choices(creme_entity_content_types())
                    elif not field.get_tag('enumerable'):
                        #TODO: generalise the system of 'header_filter_search_field' ??
                        continue
                    else:
                        choices = ((o.id, o)
                                        for o in field.rel.to.objects.distinct()
                                            if unicode(o) != ""
                                  )
                    _build_select_search_widget(widget_ctx, search_value, choices)
            elif isinstance(field, models.BooleanField):
                _build_bool_search_widget(widget_ctx, search_value)
            elif isinstance(field, (models.DateField, models.DateTimeField)): #TODO: DateTimeField useful ??
                _build_date_search_widget(widget_ctx, search_value)
            elif search_value:
                widget_ctx['value'] = search_value[0]
        elif isinstance(cell, EntityCellFunctionField):
            choices = cell.function_field.choices
            if choices is not None:
                _build_select_search_widget(widget_ctx, search_value, choices)
            elif search_value:
                widget_ctx['value'] = search_value[0]
        elif isinstance(cell, EntityCellRelation):
            if search_value:
                widget_ctx['value'] = search_value[0]
        elif isinstance(cell, EntityCellCustomField):
            cf = cell.custom_field
            field_type = cf.field_type

            if field_type in (CustomField.ENUM, CustomField.MULTI_ENUM):
                _build_select_search_widget(widget_ctx, search_value,
                                            cf.customfieldenumvalue_set.values_list('id', 'value')
                                           )
            elif field_type == CustomField.DATETIME:
                _build_date_search_widget(widget_ctx, search_value)
            elif field_type == CustomField.BOOL:
                _build_bool_search_widget(widget_ctx, search_value)
            elif search_value:
                widget_ctx['value'] = search_value[0]

        cell.widget_ctx = widget_ctx

    return context

#-----------------------------------------------------------------------------

@register.simple_tag
def get_listview_cell(cell, entity, user):
    try:
        return cell.render_html(entity, user)
    except Exception as e:
        logger.debug('Templatetag "get_listview_cell": %s', e)

    return u""

@register.assignment_tag
def ctype_is_registered_for_import(ctype):
    return import_form_registry.is_registered(ctype)
