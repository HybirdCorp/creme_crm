################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2024-2025  Hybird
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

from django.db.models import signals
from django.dispatch import Signal, receiver

from creme.creme_config.models import AdminHistoryLine
from creme.creme_core.global_info import get_global_info
from creme.creme_core.models import CremePropertyType

# Signal sent when a CustomEntityType instance which is disabled; it means the
# type is available again to represent a new kind of entity, so we have to clean
# the DB to get a "clean" type.
# Provided arguments:
# - "sender" is the CustomEntityType instance.
# - "entity_ctype" is the ContentType instance corresponding to
#   <sender.entity_model> (it's a shortcut).
disable_custom_entity_type = Signal()


@receiver(
    signals.post_save, dispatch_uid='creme_config-history_creation_n_edition',
)
def _handle_history(sender, instance, created, **kwargs):
    from django.contrib.auth import get_user_model

    # TODO: registry to handle cases
    if issubclass(sender, (get_user_model(), CremePropertyType)):
        user = get_global_info('user')

        AdminHistoryLine.objects.create(
            content_type=sender,
            username=user.username if user else '',
            type=AdminHistoryLine.Type.CREATION if created else AdminHistoryLine.Type.EDITION,
        )


@receiver(
    signals.post_delete, dispatch_uid='creme_config-history_deletion',
)
def _handle_deletion_history(sender, instance, **kwargs):
    from django.contrib.auth import get_user_model

    # TODO: registry to handle cases
    if issubclass(sender, (get_user_model(), CremePropertyType)):
        user = get_global_info('user')

        AdminHistoryLine.objects.create(
            content_type=sender,
            username=user.username if user else '',
            type=AdminHistoryLine.Type.DELETION,
        )
