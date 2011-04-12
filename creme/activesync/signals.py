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
from logging import error

def _get_mapping_from_creme_entity_id(id_):
    from activesync.models.active_sync import CremeExchangeMapping
    try:
        return CremeExchangeMapping.objects.get(creme_entity_id=id_)
    except CremeExchangeMapping.DoesNotExist, e:
        error(u"Mapping problem detected with creme_entity_id=%s. Error is %s", id_, e)


def post_save_activesync_handler(sender, instance, created, **kwargs):
    #If a Contact is created no operation is needed because AirSync command handle automaticaly
    if not created:#The contact is modified by creme
        c_x_mapping = _get_mapping_from_creme_entity_id(instance.pk)
        if c_x_mapping is not None:
            c_x_mapping.is_creme_modified = True
            c_x_mapping.save()


def post_delete_activesync_handler(sender, instance, **kwargs):
    print "In post_delete_activesync_handler with ", sender, ",", instance
    c_x_mapping = _get_mapping_from_creme_entity_id(instance.pk)
    print "c_x_mapping:", c_x_mapping
    if c_x_mapping is not None:
        c_x_mapping.creme_entity_repr = unicode(instance)
        c_x_mapping.was_deleted = True
        c_x_mapping.save()
