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
from django.utils.html import escape

from creme_core.models.header_filter import HFI_FIELD, HFI_RELATION, HFI_FUNCTION, HFI_CUSTOM
from creme_core.models import CustomFieldValue
from creme_core.templatetags.creme_core_tags import get_html_field_value


register = template.Library()

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
