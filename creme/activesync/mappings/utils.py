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
from creme_core.utils.meta import get_field_infos

from django.db.models import BooleanField

def _format_value_for_AS(field_class, field_value):
    if field_class is not None:
        if issubclass(field_class, BooleanField):
            return 1 if field_value else 0


def serialize_entity(entity, mapping):
    """Serialize an entity in xml respecting namespaces prefixes
       TODO/NB: Need to send an empty value when the entity hasn't a value ?
       TODO: Add the possibility to subset entity fields ?
    """
    xml = []
    xml_append = xml.append

    reverse_ns   = dict((v, "A%s" % i) for i, v in enumerate(mapping.keys()))
    namespaces = reverse_ns

    for ns, values in mapping.iteritems():
        prefix = namespaces.get(ns)
        for c_field, xml_field in values.iteritems():
            value = None
            if callable(c_field):
                value = c_field(entity)
            else:
                f_class, value = get_field_infos(entity, c_field)

            value = _format_value_for_AS(f_class, value)

            if value:
                xml_append("<%(prefix)s%(tag)s>%(value)s</%(prefix)s%(tag)s>" %
                           {
                            'prefix': '%s:' % prefix if prefix else '',
                            'tag': xml_field,
                            'value': value #Problems with unicode
                            }
                           )
    return "".join(xml)