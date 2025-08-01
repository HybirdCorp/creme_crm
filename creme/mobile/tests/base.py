from datetime import timedelta
from random import randint

from django.urls import reverse
from django.utils.timezone import now

from creme import activities, persons
from creme.activities.constants import (
    REL_SUB_PART_2_ACTIVITY,
    UUID_SUBTYPE_MEETING_NETWORK,
    UUID_SUBTYPE_PHONECALL_OUTGOING,
)
from creme.activities.models import ActivitySubType
from creme.creme_core.models import Relation
from creme.creme_core.tests.base import CremeTestCase

Contact = persons.get_contact_model()
Organisation = persons.get_organisation_model()
Activity = activities.get_activity_model()


class MobileBaseTestCase(CremeTestCase):
    PORTAL_URL = reverse('mobile__portal')

    def login_as_mobile_user(self, *, allowed_apps=(), **kwargs):
        return super().login_as_standard(
            allowed_apps=['activities', 'persons', *allowed_apps],
            **kwargs
        )

    def _create_floating(self, user, title, participant, status=None):
        sub_type = self.get_object_or_fail(ActivitySubType, uuid=UUID_SUBTYPE_MEETING_NETWORK)
        activity = Activity.objects.create(
            user=user, title=title,
            type_id=sub_type.type_id,
            sub_type=sub_type,
            status=status,
            floating_type=Activity.FloatingType.FLOATING,
        )

        Relation.objects.create(
            subject_entity=participant, user=user,
            type_id=REL_SUB_PART_2_ACTIVITY,
            object_entity=activity,
        )

        return activity

    def _create_pcall(self, user, title, start=None, participant=None, status=None,
                      **kwargs):
        if start is None:
            start = self.create_datetime(year=2014, month=1, day=6, hour=8) \
                        .replace(month=randint(1, 12))

        sub_type = self.get_object_or_fail(ActivitySubType, uuid=UUID_SUBTYPE_PHONECALL_OUTGOING)
        activity = Activity.objects.create(
            user=user, title=title,
            type_id=sub_type.type_id,
            sub_type=sub_type,
            status=status,
            start=start,
            end=start + timedelta(hours=1),
            **kwargs
        )

        if participant is not None:
            Relation.objects.create(
                subject_entity=participant, user=user,
                type_id=REL_SUB_PART_2_ACTIVITY,
                object_entity=activity,
            )

        return activity

    def _create_meeting(self, user, title, start=None, end=None,
                        participant=None, status=None,
                        **kwargs):
        if start is None:
            start = now()

        if end is None:
            end = start + timedelta(hours=1)

        sub_type = self.get_object_or_fail(ActivitySubType, uuid=UUID_SUBTYPE_MEETING_NETWORK)
        activity = Activity.objects.create(
            user=user, title=title,
            type_id=sub_type.type_id,
            sub_type=sub_type,
            status=status,
            start=start,
            end=end,
            **kwargs
        )

        if participant is not None:
            Relation.objects.create(
                subject_entity=participant, user=user,
                type_id=REL_SUB_PART_2_ACTIVITY,
                object_entity=activity,
            )

        return activity
