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
from datetime import datetime
from xml.sax.saxutils import escape
from activesync.models.other_models import EntityASData
from creme_core.utils.dates import get_utc_dt_from_creme_dt, get_dt_to_iso8601_str
from creme_core.utils.meta import get_field_infos

from django.db import models

def _format_value_for_AS(field_class, field_value):
    if field_class is not None:
        if issubclass(field_class, models.BooleanField):
            return 1 if field_value else 0

        if issubclass(field_class, models.DateField):
            if field_value:
                field_value = datetime(*field_value.timetuple()[:6])
                field_class = models.DateTimeField

        if issubclass(field_class, (models.DateTimeField, models.DateField)):
            if field_value:
                field_value = get_utc_dt_from_creme_dt(field_value)
                return get_dt_to_iso8601_str(field_value)
            return None

    return field_value


def serialize_entity(entity, mapping):
    """Serialize an entity in xml respecting namespaces prefixes
       TODO/NB: Need to send an empty value when the entity hasn't a value ?
       TODO: Add the possibility to subset entity fields ?
    """
    from activesync.mappings import CREME_AS_MAPPING#TODO: Remove the cyclic import
    xml = []
    xml_append = xml.append

    reverse_ns   = dict((v, "A%s" % i) for i, v in enumerate(mapping.keys()))
    namespaces = reverse_ns

    pre_serialization = CREME_AS_MAPPING[entity.__class__]['pre_serialization']

    for ns, values in mapping.iteritems():
        prefix = namespaces.get(ns)
        for c_field, xml_field in values.iteritems():
            value   = None
            f_class = None
            
            if callable(c_field):
                value = c_field(entity)
            else:
                f_class, value = get_field_infos(entity, c_field)

            value = _format_value_for_AS(f_class, value)

            if value in (None, ''):
                try:
                    value = EntityASData.objects.get(entity=entity, field_name=xml_field).field_value
                except EntityASData.DoesNotExist:
                    pass

            value = pre_serialization(value, c_field, xml_field, f_class, entity)


            if value:
                try:
                    value = escape(value)
                except Exception:
                    pass
                xml_append("<%(prefix)s%(tag)s>%(value)s</%(prefix)s%(tag)s>" %
                           {
                            'prefix': '%s:' % prefix if prefix else '',
                            'tag': xml_field,
                            'value': value #Problems with unicode
                            }
                           )
    return "".join(xml)