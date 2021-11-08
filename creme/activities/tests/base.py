# -*- coding: utf-8 -*-

from functools import partial
from json import dumps as json_dump
from unittest import skipIf

from django.urls import reverse

from creme.activities.constants import (
    ACTIVITYSUBTYPE_MEETING_NETWORK,
    ACTIVITYTYPE_MEETING,
    ACTIVITYTYPE_TASK,
)
from creme.activities.models import Calendar
from creme.creme_core.auth.entity_credentials import EntityCredentials
from creme.creme_core.models import SetCredentials
from creme.creme_core.tests.base import CremeTestCase
from creme.persons import get_contact_model, get_organisation_model

from .. import activity_model_is_custom, get_activity_model

skip_activities_tests = activity_model_is_custom()
Activity = get_activity_model()

Contact = get_contact_model()
Organisation = get_organisation_model()


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

    def login(self, is_superuser=True, is_staff=False,
              allowed_apps=('activities', 'persons'), *args, **kwargs):
        return super().login(
            is_superuser=is_superuser,
            is_staff=is_staff,
            allowed_apps=allowed_apps,
            *args, **kwargs
        )

    @staticmethod
    def _acttype_field_value(atype_id, subtype_id=None):
        return json_dump({'type': atype_id, 'sub_type': subtype_id})

    def assertUserHasDefaultCalendar(self, user):
        return self.get_object_or_fail(Calendar, is_default=True, user=user)

    def _build_nolink_setcreds(self):
        create_sc = partial(SetCredentials.objects.create, role=self.role)
        create_sc(value=EntityCredentials.LINK, set_type=SetCredentials.ESET_OWN)
        create_sc(
            value=(
                EntityCredentials.VIEW
                | EntityCredentials.CHANGE
                | EntityCredentials.DELETE
                | EntityCredentials.UNLINK
            ),  # Not LINK
            set_type=SetCredentials.ESET_ALL,
        )

    def _create_activity_by_view(self, title='My task',
                                 atype_id=ACTIVITYTYPE_TASK, subtype_id=None,
                                 **kwargs):
        user = self.login()

        data = {
            'user': user.pk,
            'title': title,

            self.EXTRA_SUBTYPE_KEY: self._acttype_field_value(atype_id, subtype_id),

            f'{self.EXTRA_MYPART_KEY}_0': True,
            f'{self.EXTRA_MYPART_KEY}_1': Calendar.objects.get_default_calendar(user).pk,
        }
        data.update(kwargs)

        self.assertNoFormError(
            self.client.post(self.ACTIVITY_CREATION_URL, follow=True, data=data),
        )

        return self.get_object_or_fail(Activity, title=title)

    def _create_meeting(
            self,
            title='Meeting01',
            subtype_id=ACTIVITYSUBTYPE_MEETING_NETWORK,
            hour=14):
        create_dt = self.create_datetime
        return Activity.objects.create(
            user=self.user, title=title,
            type_id=ACTIVITYTYPE_MEETING, sub_type_id=subtype_id,
            start=create_dt(year=2013, month=4, day=1, hour=hour,     minute=0),
            end=create_dt(year=2013,   month=4, day=1, hour=hour + 1, minute=0),
        )
