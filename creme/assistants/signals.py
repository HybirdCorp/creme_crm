################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2015-2025  Hybird
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

from django.db.models import DateField
from django.db.models.signals import post_save
from django.dispatch.dispatcher import receiver

from creme.creme_core.core.entity_cell import CELLS_MAP
from creme.creme_core.core.field_tags import FieldTag
from creme.creme_core.core.snapshot import Snapshot
from creme.creme_core.models import CremeEntity
from creme.creme_core.signals import pre_merge_related
from creme.creme_core.utils import update_model_instance
from creme.creme_core.utils.date_period import date_period_registry

from .models import Alert, ToDo

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Alert, dispatch_uid='assistants-refresh_alert_job')
@receiver(post_save, sender=ToDo, dispatch_uid='assistants-refresh_todo_job')
def _refresh_reminder_job(sender, instance, **kwargs):
    from creme.creme_core.creme_jobs import reminder_type

    if instance.to_be_reminded:
        reminder_type.refresh_job()


# TODO: build a correct abstraction (DateOffset class?)
def __get_date_offset_info(model, offset_dict):
    cell = CELLS_MAP.build_cell_from_dict(
        model=model, dict_cell=offset_dict['cell'],
    )
    if cell is None:
        raise ValueError(f'offset cell <{offset_dict}> is invalid')

    period = date_period_registry.deserialize(offset_dict['period'])
    if period is None:
        raise ValueError(f'offset period <{offset_dict}> is invalid')

    sign = offset_dict['sign']
    if sign not in (1, -1):
        raise ValueError(f'offset sign <{offset_dict}> is invalid')

    return cell, sign, period


# NB: "@receiver(post_save, sender=CremeEntity)" does not work
#     (the signal is sent for final class & strict class comparison is done)
@receiver(post_save, dispatch_uid='assistants-update_alert_trigger')
def _update_alert_trigger_date(sender, instance, created, **kwargs):
    from creme.assistants.views.alert import AlertCreation

    if created:
        # The instance has just been created, no alert can exist yet
        return

    if not isinstance(instance, CremeEntity):
        return

    # IDEA: we could regroup the queries by using the Workflow post-processing
    snapshot = Snapshot.get_for_instance(instance)
    if snapshot is None:
        # Instance has been created & modified in the same request;
        # we assume no Alert is created in the same request AND needs to update
        # its trigger date (the date-field would have been modified after the
        # Alert has been created => ewwwww...)
        return

    if not any(
        isinstance(diff.field, DateField)
        and diff.field.get_tag(FieldTag.VIEWABLE)
        and diff.field.name not in AlertCreation.form_class.excluded_model_fields
        for diff in snapshot.compare(instance)
    ):
        return

    for alert in Alert.objects.filter(
        entity_id=instance.id,
        trigger_offset__has_key='cell',
        is_validated=False,
    ):
        try:
            cell, sign, period = __get_date_offset_info(
                model=type(instance), offset_dict=alert.trigger_offset,
            )
        except ValueError as e:
            logger.critical(
                'Error in signal handler _update_alert_trigger_date with the '
                'Alert id="%s": %s', alert.id, e,
            )
        else:
            update_model_instance(
                alert,
                trigger_date=alert.trigger_date_from_offset(
                    entity=instance,
                    cell=cell, sign=sign, period=period,
                ),
            )


# TODO: factorise better
# This handler is called when "sender" (entity #1) is merged with "other_entity"
# ('sender' is kept, 'other_entity' will be removed)
#  - BEFORE the instances referencing 'other_entity' are modified to reference 'sender'.
#  - AFTER 'sender' has been updated to store its final fields.
@receiver(pre_merge_related, dispatch_uid='assistants-merge_alert_trigger')
def _merge_alert_trigger_date(sender, other_entity, **kwargs):
    for alert in Alert.objects.filter(
        entity_id=other_entity.id,
        trigger_offset__has_key='cell',
        is_validated=False,
    ):
        try:
            cell, sign, period = __get_date_offset_info(
                model=type(sender), offset_dict=alert.trigger_offset,
            )
        except ValueError as e:
            logger.critical(
                'Error in signal handler _merge_alert_trigger_date with the '
                'Alert id="%s": %s', alert.id, e,
            )
        else:
            update_model_instance(
                alert,
                trigger_date=alert.trigger_date_from_offset(
                    entity=sender,
                    cell=cell, sign=sign, period=period,
                ),
            )
