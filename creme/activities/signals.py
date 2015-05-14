# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2015  Hybird
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

from functools import partial

from django.conf import settings
from django.db.models.signals import pre_delete, post_delete, post_save
from django.dispatch import receiver

from creme.creme_core.constants import PROP_IS_MANAGED_BY_CREME
from creme.creme_core.models import Relation

from creme.persons.constants import REL_OBJ_EMPLOYED_BY, REL_OBJ_MANAGES
#from creme.persons.models import Organisation
from creme.persons import get_organisation_model

from .constants import REL_SUB_PART_2_ACTIVITY, REL_OBJ_PART_2_ACTIVITY, REL_SUB_ACTIVITY_SUBJECT
from .models import Calendar


Organisation = get_organisation_model()


@receiver(post_delete, sender=Relation)
def _set_null_calendar_on_delete_participant(sender, instance, **kwargs):
    type_id = instance.type_id

    if type_id == REL_SUB_PART_2_ACTIVITY:
        contact  = instance.subject_entity.get_real_entity()
        activity = instance.object_entity.get_real_entity()
    elif type_id == REL_OBJ_PART_2_ACTIVITY:
        contact  = instance.object_entity.get_real_entity()
        activity = instance.subject_entity.get_real_entity()
    else:
        return

    if contact.is_user:
        # Why only from default calendar?
        # activity.calendars.remove(Calendar.get_user_default_calendar(contact.is_user))
        for calendar_id in activity.calendars.filter(user=contact.is_user).values_list('id', flat=True): 
            activity.calendars.remove(calendar_id)

@receiver(post_save, sender=Relation)
def _set_orga_as_subject(sender, instance, **kwargs):
    if instance.type_id != REL_SUB_PART_2_ACTIVITY:
        return

    #NB: when a Relation is created, it is saved twice in order to set the link
    #    with its symmetric instance
    if instance.symmetric_relation_id is None:
        return

    activity = instance.object_entity.get_real_entity()

    if not activity.is_auto_orga_subject_enabled():
        return

    create_rel = partial(Relation.objects.get_or_create,
                         type_id=REL_SUB_ACTIVITY_SUBJECT,
                         object_entity=activity,
                         defaults={'user': instance.user},
                        )

    for orga in Organisation.objects.filter(relations__type__in=(REL_OBJ_EMPLOYED_BY, REL_OBJ_MANAGES),
                                            relations__object_entity=instance.subject_entity_id,
                                           ) \
                                    .exclude(is_deleted=False,
                                             properties__type=PROP_IS_MANAGED_BY_CREME,
                                            ):
        create_rel(subject_entity=orga)

#@receiver(pre_delete, sender=User)
@receiver(pre_delete, sender=settings.AUTH_USER_MODEL)
def _transfer_default_calendar(sender, instance, **kwargs):
    # NB: when a User is deleted, his Calendars are given to another User, who
    #     has at this moment 2 default Calendars. When get_user_default_calendar()
    #     fixes the problem, the Calendar chosen to be the default one can be
    #     different from the original default Calendar (ie: the default Calendar
    #     of this User can change 'silently').
    Calendar.objects.filter(user=instance, is_default=True).update(is_default=False)
