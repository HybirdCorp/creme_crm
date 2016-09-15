# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2015-2016  Hybird
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

from django.conf import settings
from django.db.models.signals import post_save, post_delete
from django.db.utils import DatabaseError
from django.dispatch import receiver

from creme.creme_core.models import CremeEntity
from creme.creme_core.utils import update_model_instance
from creme.creme_core.signals import pre_merge_related

from . import get_address_model, get_contact_model
from .models.contact import _create_linked_contact

logger = logging.getLogger(__name__)


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def sync_with_user(sender, instance, created, **kwargs):
    if instance.is_team:
        return

    if getattr(instance, '_disable_sync_with_contact', False):
        return

    try:
        if created:
            # instance._linked_contact_cache = _create_linked_contact(instance)
            instance._linked_contact_cache = get_contact_model()._create_linked_contact(instance)
        else:
            update_model_instance(instance.linked_contact,
                                  last_name=instance.last_name,
                                  first_name=instance.first_name,
                                  email=instance.email,
                                 )
    except DatabaseError as e:
        logger.warn('Can not create linked contact for this user: %s (if it is the first user,'
                    ' do not worry because it is normal) (%s)', instance, e
                   )


@receiver(post_delete, sender=CremeEntity)
def dispose_addresses(sender, instance, **kwargs):
    get_address_model().objects.filter(object_id=instance.id).delete()


@receiver(pre_merge_related)
def handle_merge(sender, other_entity, **kwargs):
    for address in other_entity.other_addresses:
        address.owner = sender
        address.save()
