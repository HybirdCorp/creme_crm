from django.urls import reverse
from django.utils.translation import gettext as _

from creme.creme_core.gui import actions
from creme.creme_core.models import EntityFilter, RelationType

from .. import constants, setting_keys
from ..actions import BulkExportICalAction
from ..models import ActivitySubType, ActivityType
from .base import Activity, _ActivitiesTestCase


class ActivitiesAppTestCase(_ActivitiesTestCase):
    # def test_constants(self):  # DEPRECATED
    #     with self.assertWarnsMessage(
    #         expected_warning=DeprecationWarning,
    #         expected_message='"NARROW" is deprecated; use Activity.FloatingType.NARROW instead.'
    #     ):
    #         from creme.activities.constants import NARROW
    #     self.assertEqual(1, NARROW)
    #
    #     with self.assertWarnsMessage(
    #             expected_warning=DeprecationWarning,
    #             expected_message='"FLOATING_TIME" is deprecated; '
    #                              'use Activity.FloatingType.FLOATING_TIME instead.',
    #     ):
    #         from creme.activities.constants import FLOATING_TIME
    #     self.assertEqual(2, FLOATING_TIME)
    #
    #     with self.assertWarnsMessage(
    #             expected_warning=DeprecationWarning,
    #             expected_message='"FLOATING" is deprecated; '
    #                              'use Activity.FloatingType.FLOATING instead.',
    #     ):
    #         from creme.activities.constants import FLOATING
    #     self.assertEqual(3, FLOATING)

    def test_populate__relation_types(self):
        rtypes_pks = [
            constants.REL_SUB_LINKED_2_ACTIVITY,
            constants.REL_SUB_ACTIVITY_SUBJECT,
            constants.REL_SUB_PART_2_ACTIVITY,
        ]
        self.assertEqual(
            len(rtypes_pks), RelationType.objects.filter(pk__in=rtypes_pks).count(),
        )

    def test_populate__activity_types(self):
        acttypes_uuids = [
            constants.UUID_TYPE_TASK,
            constants.UUID_TYPE_MEETING,
            constants.UUID_TYPE_PHONECALL,
            constants.UUID_TYPE_GATHERING,
            constants.UUID_TYPE_SHOW,
            constants.UUID_TYPE_DEMO,
            constants.UUID_TYPE_UNAVAILABILITY,
        ]
        self.assertEqual(
            len(acttypes_uuids),
            ActivityType.objects.filter(uuid__in=acttypes_uuids).count(),
        )

        subtype_uuids = [
            constants.UUID_SUBTYPE_PHONECALL_INCOMING,
            constants.UUID_SUBTYPE_PHONECALL_OUTGOING,
            constants.UUID_SUBTYPE_PHONECALL_CONFERENCE,
            constants.UUID_SUBTYPE_MEETING_NETWORK,
            constants.UUID_SUBTYPE_MEETING_QUALIFICATION,
        ]
        self.assertEqual(
            len(subtype_uuids),
            ActivitySubType.objects.filter(uuid__in=subtype_uuids).count(),
        )

    def test_populate__setting_values(self):
        self.assertSettingValueEqual(key=setting_keys.review_key, value=True)
        self.assertSettingValueEqual(key=setting_keys.auto_subjects_key, value=True)

        self.assertSettingValueEqual(
            key=setting_keys.unsuccessful_subtype_key,
            value=constants.UUID_SUBTYPE_PHONECALL_OUTGOING,
        )
        self.assertSettingValueEqual(
            key=setting_keys.unsuccessful_title_key,
            value=_('Unsuccessful call'),
        )
        self.assertSettingValueEqual(
            key=setting_keys.unsuccessful_status_key,
            value=constants.UUID_STATUS_UNSUCCESSFUL,
        )
        self.assertSettingValueEqual(
            key=setting_keys.unsuccessful_duration_key, value=3,
        )

    def test_populate__filters(self):
        user = self.login_as_root_and_get()
        acts = [
            self._create_meeting(
                user=user, title='Meeting01',
                subtype=constants.UUID_SUBTYPE_MEETING_NETWORK, hour=14,
            ),
            self._create_meeting(
                user=user, title='Meeting02',
                subtype=constants.UUID_SUBTYPE_MEETING_REVIVAL, hour=15,
            ),
            self._create_phonecall(
                user=user, title='Call01',
                subtype=constants.UUID_SUBTYPE_PHONECALL_OUTGOING, hour=14,
            ),
            self._create_phonecall(
                user=user, title='Call02',
                subtype=constants.UUID_SUBTYPE_PHONECALL_OUTGOING, hour=15,
            ),
            self._create_task(user=user, title='Task01', day=1),
            self._create_task(user=user, title='Task02', day=2),
        ]

        def check_content(efilter, *expected_titles):
            titles = {*efilter.filter(Activity.objects.all()).values_list('title', flat=True)}

            for activity in acts:
                title = activity.title
                if title in expected_titles:
                    self.assertIn(title, titles)
                else:
                    self.assertNotIn(title, titles)

        efilter = self.get_object_or_fail(EntityFilter, pk=constants.EFILTER_MEETINGS)
        self.assertFalse(efilter.is_custom)
        check_content(efilter, 'Meeting01', 'Meeting02')

        efilter = self.get_object_or_fail(EntityFilter, pk=constants.EFILTER_PHONECALLS)
        check_content(efilter, 'Call01', 'Call02')

        efilter = self.get_object_or_fail(EntityFilter, pk=constants.EFILTER_TASKS)
        check_content(efilter, 'Task01', 'Task02')

    def test_listview_bulk_actions(self):
        user = self.login_as_root_and_get()
        export_action = self.get_alone_element(
            action
            for action in actions.action_registry.bulk_actions(user=user, model=Activity)
            if isinstance(action, BulkExportICalAction)
        )
        self.assertEqual('activities-export-ical', export_action.type)
        self.assertEqual(reverse('activities__dl_ical'), export_action.url)
        self.assertIsNone(export_action.action_data)
        self.assertTrue(export_action.is_enabled)
        self.assertTrue(export_action.is_visible)
