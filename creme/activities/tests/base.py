from json import dumps as json_dump
from unittest import skipIf

from django.urls import reverse

from creme import persons
from creme.activities.constants import (
    UUID_SUBTYPE_MEETING_NETWORK,
    UUID_TYPE_MEETING,
)
from creme.activities.models import ActivitySubType, ActivityType, Calendar
from creme.creme_core.tests.base import CremeTestCase

from .. import activity_model_is_custom, get_activity_model

skip_activities_tests = activity_model_is_custom()
Activity = get_activity_model()

Contact = persons.get_contact_model()
Organisation = persons.get_organisation_model()


def skipIfCustomActivity(test_func):
    return skipIf(skip_activities_tests, 'Custom Activity model in use')(test_func)


class _ActivitiesTestCase(CremeTestCase):
    ACTIVITY_CREATION_URL = reverse('activities__create_activity')

    EXTRA_START_KEY = 'cform_extra-activities_start'
    EXTRA_END_KEY   = 'cform_extra-activities_end'

    EXTRA_SUBTYPE_KEY = 'cform_extra-activities_subtype'

    EXTRA_MYPART_KEY    = 'cform_extra-activities_my_participation'
    EXTRA_PARTUSERS_KEY = 'cform_extra-activities_users'
    EXTRA_OTHERPART_KEY = 'cform_extra-activities_others_participants'
    EXTRA_SUBJECTS_KEY  = 'cform_extra-activities_subjects'
    EXTRA_LINKED_KEY    = 'cform_extra-activities_linked'

    EXTRA_ALERTDT_KEY     = 'cform_extra-activities_alert_datetime'
    EXTRA_ALERTPERIOD_KEY = 'cform_extra-activities_alert_period'
    EXTRA_MESSAGES_KEY    = 'cform_extra-activities_user_messages'

    def login_as_activities_user(self, *, allowed_apps=(), **kwargs):
        return self.login_as_standard(
            allowed_apps=['persons', 'activities', *allowed_apps],
            **kwargs
        )

    @staticmethod
    def _acttype_field_value(atype_id, subtype_id=None):
        return json_dump({'type': atype_id, 'sub_type': subtype_id})

    def assertUserHasDefaultCalendar(self, user):
        return self.get_object_or_fail(Calendar, is_default=True, user=user)

    def _create_activity_by_view(self,
                                 user,
                                 title='My task',
                                 subtype=UUID_SUBTYPE_MEETING_NETWORK,
                                 **kwargs):
        if isinstance(subtype, str):
            subtype = ActivitySubType.objects.get(uuid=subtype)

        data = {
            'user': user.pk,
            'title': title,

            self.EXTRA_SUBTYPE_KEY: subtype.id,

            f'{self.EXTRA_MYPART_KEY}_0': True,
            f'{self.EXTRA_MYPART_KEY}_1': Calendar.objects.get_default_calendar(user).pk,
        }
        data.update(kwargs)

        self.assertNoFormError(
            self.client.post(self.ACTIVITY_CREATION_URL, follow=True, data=data),
        )

        return self.get_object_or_fail(Activity, title=title)

    def _create_meeting(self,
                        user,
                        title='Meeting01',
                        subtype=UUID_SUBTYPE_MEETING_NETWORK,
                        hour=14,
                        **kwargs):
        create_dt = self.create_datetime
        return Activity.objects.create(
            user=user,
            title=title,
            type=ActivityType.objects.get(uuid=UUID_TYPE_MEETING),
            sub_type=(
                ActivitySubType.objects.get(uuid=subtype)
                if isinstance(subtype, str) else
                subtype
            ),
            start=create_dt(year=2013, month=4, day=1, hour=hour,     minute=0),
            end=create_dt(year=2013,   month=4, day=1, hour=hour + 1, minute=0),
            **kwargs
        )

    def _get_type(self, uid: str) -> ActivityType:
        return self.get_object_or_fail(ActivityType, uuid=uid)

    def _get_sub_type(self, uid: str) -> ActivitySubType:
        return self.get_object_or_fail(ActivitySubType, uuid=uid)
