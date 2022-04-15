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

from django.conf import settings
from django.db.models import signals
from django.dispatch import receiver

import creme.persons.constants as persons_constants
from creme.creme_core.models import Relation
from creme.persons import get_organisation_model

from .constants import (
    REL_OBJ_PART_2_ACTIVITY,
    REL_SUB_ACTIVITY_SUBJECT,
    REL_SUB_PART_2_ACTIVITY,
)
from .models import Calendar
from .utils import is_auto_orga_subject_enabled

logger = logging.getLogger(__name__)
Organisation = get_organisation_model()


@receiver(
    signals.post_delete,
    sender=Relation, dispatch_uid='activities-update_activity_calendars',
)
def _set_null_calendar_on_delete_participant(sender, instance, **kwargs):
    type_id = instance.type_id

    if type_id == REL_SUB_PART_2_ACTIVITY:
        contact  = instance.subject_entity.get_real_entity()
        activity = instance.real_object
    elif type_id == REL_OBJ_PART_2_ACTIVITY:
        contact  = instance.real_object
        activity = instance.subject_entity.get_real_entity()
    else:
        return

    if contact.is_user:
        for calendar_id in activity.calendars.filter(
            user=contact.is_user,
        ).values_list('id', flat=True):
            activity.calendars.remove(calendar_id)


# TODO: convert as Workflow? it would need a "multi-sources" action
@receiver(
    signals.post_save,
    sender=Relation, dispatch_uid='activities-manage_auto_subject_organisation',
)
def _set_orga_as_subject(sender, instance, **kwargs):
    if instance.type_id != REL_SUB_PART_2_ACTIVITY:
        return

    # NB: when a Relation is created, it is saved twice in order to set the link
    #     with its symmetric instance
    if instance.symmetric_relation_id is None:
        return

    activity = instance.real_object

    if not is_auto_orga_subject_enabled():
        return

    user = instance.user
    Relation.objects.safe_multi_save(
        Relation(
            subject_entity=orga,
            type_id=REL_SUB_ACTIVITY_SUBJECT,
            object_entity=activity,
            user=user,
        ) for orga in Organisation.objects.filter(
            relations__type__in=(
                persons_constants.REL_OBJ_EMPLOYED_BY,
                persons_constants.REL_OBJ_MANAGES,
            ),
            relations__object_entity=instance.subject_entity_id,
        ).exclude(is_deleted=True).exclude(is_managed=True)
    )


@receiver(
    signals.post_save,
    sender=settings.AUTH_USER_MODEL, dispatch_uid='activities-create_default_calendar',
)
def _create_default_calendar(sender, instance, created, **kwargs):
    if created and not instance.is_staff and instance.is_active:
        is_public = settings.ACTIVITIES_DEFAULT_CALENDAR_IS_PUBLIC

        if is_public is None:
            pass
        elif isinstance(is_public, bool):
            Calendar.objects.create_default_calendar(user=instance, is_public=is_public)
        else:
            logger.critical(
                'settings.ACTIVITIES_DEFAULT_CALENDAR_IS_PUBLIC must be True/False/None.'
                'The default calendar for the user <%s> is not created.', instance
            )


@receiver(
    signals.pre_delete,
    sender=settings.AUTH_USER_MODEL, dispatch_uid='activities-transfer_default_calendar',
)
def _transfer_default_calendar(sender, instance, **kwargs):
    # NB: when a User is deleted, his Calendars are given to another User, who
    #     has at this moment 2 default Calendars. When get_user_default_calendar()
    #     fixes the problem, the Calendar chosen to be the default one can be
    #     different from the original default Calendar (i.e. the default Calendar
    #     of this User can change 'silently').
    Calendar.objects.filter(user=instance, is_default=True).update(is_default=False)
