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

from django.contrib.contenttypes.models import ContentType

from creme.persons.constants import REL_SUB_EMPLOYED_BY
from creme.persons.models import Contact


logger = logging.getLogger(__name__)


def _get_mapping_from_creme_entity_id(id_):
    from .models import CremeExchangeMapping
    try:
        return CremeExchangeMapping.objects.get(creme_entity_id=id_)
    except CremeExchangeMapping.DoesNotExist as e:
        #logger.error(u"Mapping problem detected with creme_entity_id=%s. Error is %s", id_, e)
        logger.debug(u"Mapping problem detected with creme_entity_id=%s. Error is %s", id_, e)


def post_save_activesync_handler(sender, instance, created, **kwargs):
    #If a Contact is created no operation is needed because AirSync command handle automaticaly
    if not created:#The contact is modified by creme
        c_x_mapping = _get_mapping_from_creme_entity_id(instance.pk)
        if c_x_mapping is not None:
            c_x_mapping.is_creme_modified = True
            c_x_mapping.save()


def post_delete_activesync_handler(sender, instance, **kwargs):
    c_x_mapping = _get_mapping_from_creme_entity_id(instance.pk)

    if c_x_mapping is not None:
        c_x_mapping.creme_entity_repr = unicode(instance)
        c_x_mapping.creme_entity_ct = ContentType.objects.get_for_model(instance)
        c_x_mapping.was_deleted = True
        c_x_mapping.save()


#Catching the save of the relation between a Contact and his employer
def post_save_relation_employed_by(sender, instance, **kwargs):
    if instance.type.id == REL_SUB_EMPLOYED_BY:
        contact = instance.subject_entity
        post_save_activesync_handler(Contact, contact, False)

#Catching the delete of the relation between a Contact and his employer
def post_delete_relation_employed_by(sender, instance, **kwargs):
    if instance.type_id == REL_SUB_EMPLOYED_BY:
        contact = instance.subject_entity
        #We just say to the mapping that the contact was modified so we use the post_save_activesync_handler and not the delete one
        post_save_activesync_handler(Contact, contact, False)
