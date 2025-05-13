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

from django.db.models.signals import post_save
from django.dispatch.dispatcher import receiver

from creme.creme_core.core.entity_cell import CELLS_MAP
from creme.creme_core.models import CremeEntity
from creme.creme_core.utils import update_model_instance
from creme.creme_core.utils.date_period import date_period_registry

from .models import Alert, ToDo

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Alert, dispatch_uid='assistants-refresh_alert_job')
@receiver(post_save, sender=ToDo, dispatch_uid='assistants-refresh_todo_job')
# def _refresh_alert_reminder_job(sender, instance, **kwargs):
def _refresh_reminder_job(sender, instance, **kwargs):
    from creme.creme_core.creme_jobs import reminder_type

    if instance.to_be_reminded:
        reminder_type.refresh_job()


# NB: "@receiver(post_save, sender=CremeEntity)" does not work
#     (the signal is sent for final class & strict class comparison is done)
@receiver(post_save, dispatch_uid='assistants-update_alert_trigger')
def _update_alert_trigger_date(sender, instance, created, **kwargs):
    if created:
        # The instance has just been created, no alert can exist yet
        return

    if not isinstance(instance, CremeEntity):
        return

    # TODO: exclude 'modified' from available fields & activate this code?
    # NB: Sadly this optimisation does not work because CremeEntity.modified is
    #     updated at each edition.
    # IDEA: we could regroup the queries by using the Workflow post-processing
    # from django.db.models import DateField
    # from ..creme_core.core.field_tags import FieldTag
    # from ..creme_core.core.snapshot import Snapshot
    # snapshot = Snapshot.get_for_instance(instance)
    # if snapshot is None:
    #     # Instance has been created & modified in the same request;
    #     # we assume no Alert is created in the same request AND needs to update
    #     # its trigger date (the date-field would have been modified after the
    #     # Alert has been created => ewwwww...)
    #     return
    # if not any(
    #     isinstance(diff.field, DateField) and diff.field.get_tag(FieldTag.VIEWABLE)
    #     for diff in snapshot.compare(instance)
    # ):
    #     return

    for alert in Alert.objects.filter(
        entity_id=instance.id,
        trigger_offset__has_key='cell',
        is_validated=False,
    ):
        offset_dict = alert.trigger_offset

        cell = CELLS_MAP.build_cell_from_dict(
            model=type(instance),
            dict_cell=offset_dict['cell'],
        )
        if cell is None:
            logger.critical(
                'Signal handler _update_alert_trigger_date: offset cell is '
                'invalid in the Alert id="%s" : %s',
                alert.id, offset_dict,
            )
            continue

        period = date_period_registry.deserialize(offset_dict['period'])
        if period is None:
            logger.critical(
                'Signal handler _update_alert_trigger_date: offset period is '
                'invalid in the Alert id="%s" : %s',
                alert.id, offset_dict,
            )
            continue

        sign = offset_dict['sign']
        if sign not in (1, -1):
            logger.critical(
                'Signal handler _update_alert_trigger_date: offset sign is '
                'invalid in the Alert id="%s" : %s',
                alert.id, offset_dict,
            )
            continue

        update_model_instance(
            alert,
            trigger_date=alert.trigger_date_from_offset(
                cell=cell, sign=sign, period=period,
            ),
        )
