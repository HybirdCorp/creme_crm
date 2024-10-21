################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2015-2024  Hybird
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
from django.db.models import signals
from django.db.utils import DatabaseError
from django.dispatch import receiver

from creme.creme_core.utils import update_model_instance

from . import get_contact_model
from .constants import UUID_FIRST_CONTACT

logger = logging.getLogger(__name__)


@receiver(
    signals.post_save,
    sender=settings.AUTH_USER_MODEL, dispatch_uid='persons-synchronise_user_n_contact',
)
def sync_with_user(sender, instance, created, **kwargs):
    # TODO: factorise (see <_get_linked_contact()>)
    if instance.is_team or instance.is_staff:
        return

    if getattr(instance, '_disable_sync_with_contact', False):
        return

    try:
        if created:
            kwargs = {'uuid': UUID_FIRST_CONTACT} if instance.id == 1 else {}
            instance._linked_contact_cache = \
                get_contact_model()._create_linked_contact(instance, **kwargs)
        else:
            update_model_instance(
                instance.linked_contact,
                last_name=instance.last_name,
                first_name=instance.first_name,
                email=instance.email,
            )
    except DatabaseError as e:
        logger.warning(
            'Can not create linked contact for this user: %s (if it is the first user,'
            ' do not worry because it is normal) (%s)', instance, e
        )
