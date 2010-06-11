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
from django.utils.html import escape

from creme_core.models.header_filter import HFI_FIELD, HFI_RELATION, HFI_FUNCTION
from creme_core.templatetags.creme_core_tags import get_html_field_value


register = template.Library()

#TODO: use a big try/except ??
@register.filter(name="hf_get_html_output")
def get_html_output(hf, entity): #TODO: rename hf in hfi ???
    if hf.type == HFI_FIELD:
        try :
            return get_html_field_value(entity, hf.name)
        except AttributeError, ae:
            return ""

    if hf.type == HFI_FUNCTION:
        try:
            return entity.__getattribute__(hf.name).__call__() #entity.__getattribute__(hf.name)() ????
        except AttributeError, ae:
            return ""

    if hf.type == HFI_RELATION:
        try :
            objects_relation = entity.get_list_object_of_specific_relations(hf.relation_predicat.id)
            string_relation = u"<ul>"
            for object in objects_relation :
                string_relation += u'<li><a href="%s">%s</a></li>' % (object.get_absolute_url(), escape(object)) #TODO: use join()....
            return string_relation #no </ul> ?!
        except AttributeError, ae:
            return ""
