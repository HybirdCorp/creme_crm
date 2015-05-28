# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2015  Hybird
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
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from creme.creme_core.models import Relation

from creme.persons import get_contact_model
from creme.persons.constants import REL_SUB_EMPLOYED_BY

from creme.activities import get_activity_model
#from creme.activities.models import Activity

from .models import CremeExchangeMapping


logger = logging.getLogger(__name__)
Contact = get_contact_model()
Activity = get_activity_model()


def _get_mapping_from_creme_entity_id(id_):
    try:
        return CremeExchangeMapping.objects.get(creme_entity_id=id_)
    except CremeExchangeMapping.DoesNotExist as e:
        logger.debug(u"Mapping problem detected with creme_entity_id=%s. Error is %s", id_, e)

@receiver(post_save, sender=Contact)
@receiver(post_save, sender=Activity)
def post_save_activesync_handler(sender, instance, created, **kwargs):
    # If a Contact is created no operation is needed because AirSync command handles automatically.
    if not created: #The contact is modified by Creme
        c_x_mapping = _get_mapping_from_creme_entity_id(instance.pk)

        if c_x_mapping is not None:
            c_x_mapping.is_creme_modified = True
            c_x_mapping.save() #TODO: only 'is_creme_modified' field ??

@receiver(post_delete, sender=Contact)
@receiver(post_delete, sender=Activity)
def post_delete_activesync_handler(sender, instance, **kwargs):
    c_x_mapping = _get_mapping_from_creme_entity_id(instance.pk)

    if c_x_mapping is not None:
        c_x_mapping.creme_entity_repr = unicode(instance)
        c_x_mapping.creme_entity_ct = ContentType.objects.get_for_model(instance)
        c_x_mapping.was_deleted = True
        c_x_mapping.save()

# Catching the save of the relation between a Contact and his employer
@receiver(post_save, sender=Relation)
def post_save_relation_employed_by(sender, instance, **kwargs):
    if instance.type_id == REL_SUB_EMPLOYED_BY:
        post_save_activesync_handler(Contact, instance.subject_entity, False)

# Catching the delete of the relation between a Contact and his employer
@receiver(post_delete, sender=Relation)
def post_delete_relation_employed_by(sender, instance, **kwargs):
    if instance.type_id == REL_SUB_EMPLOYED_BY:
        # We just say to the mapping that the contact was modified,
        # so we use the post_save_activesync_handler and not the delete one.
        post_save_activesync_handler(Contact, instance.subject_entity, False)
