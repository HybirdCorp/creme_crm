from datetime import timedelta
from uuid import uuid4

from django.urls import reverse
from django.utils.timezone import now
from django.utils.translation import gettext as _
from django.utils.translation import ngettext

from creme.creme_core.models import ButtonMenuItem, SettingValue
from creme.creme_core.tests.views import base as view_base
from creme.persons.tests.base import skipIfCustomContact

from .. import buttons, constants, setting_keys
from ..bricks import UnsuccessfulButtonConfigBrick
from ..models import ActivitySubType, Calendar, Status
from .base import (
    Activity,
    Contact,
    Organisation,
    _ActivitiesTestCase,
    skipIfCustomActivity,
)


@skipIfCustomActivity
@skipIfCustomContact
class UnsuccessfulPhoneCallTestCase(view_base.BrickTestCaseMixin,
                                    view_base.ButtonTestCaseMixin,
                                    _ActivitiesTestCase):
    EDIT_CONFIG_URL = reverse('activities__edit_unsuccessful_call_settings')

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.contact = Contact.objects.create(
            user=cls.get_root_user(), first_name='Musashi', last_name='Miyamoto',
        )

    def _build_add_url(self, contact):
        return reverse('activities__create_unsuccessful_phone_call', args=(contact.id,))

    def test_populate(self):
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
            key=setting_keys.unsuccessful_duration_key,
            value=3,
        )

    def test_config__brick(self):
        self.login_as_root()

        response = self.assertGET200(
            reverse('creme_config__app_portal', args=('activities',)),
        )
        brick_node = self.get_brick_node(
            self.get_html_tree(response.content), brick=UnsuccessfulButtonConfigBrick,
        )
        self.assertEqual(
            _('Configuration of the button «Create an unsuccessful phone call»'),
            self.get_brick_title(brick_node),
        )
        # TODO: test brick content

    def test_config__edition_default(self):
        self.login_as_standard(allowed_apps=['activities'], admin_4_apps=['activities'])

        url = self.EDIT_CONFIG_URL
        context1 = self.assertGET200(url).context
        self.assertEqual(_('Edit the configuration of the button'), context1.get('title'))
        self.assertEqual(_('Save the modifications'), context1.get('submit_label'))

        with self.assertNoException():
            fields = context1['form'].fields
            sub_type_f = fields['sub_type']
            sub_type_choices = [(choice.value, choice.label) for choice in sub_type_f.choices]
            title_f = fields['title']
            status_f = fields['status']
            duration_f = fields['duration']

        stype1 = self.get_object_or_fail(
            ActivitySubType, uuid=constants.UUID_SUBTYPE_PHONECALL_OUTGOING,
        )
        stype2 = self.get_object_or_fail(
            ActivitySubType, uuid=constants.UUID_SUBTYPE_PHONECALL_INCOMING,
        )
        stype3 = self.get_object_or_fail(
            ActivitySubType, uuid=constants.UUID_SUBTYPE_MEETING_MEETING,
        )
        self.assertInChoices(value=stype1.id, label=stype1.name, choices=sub_type_choices)
        self.assertInChoices(value=stype2.id, label=stype2.name, choices=sub_type_choices)
        self.assertNotInChoices(value=stype3.id, choices=sub_type_choices)
        self.assertEqual(stype1.id, sub_type_f.initial)

        self.assertEqual(_('Unsuccessful call'), title_f.initial)

        status1 = self.get_object_or_fail(Status, uuid=constants.UUID_STATUS_UNSUCCESSFUL)
        self.assertEqual(status1.id, status_f.initial)

        self.assertEqual(3, duration_f.initial)

        # ---
        status2 = self.get_object_or_fail(Status, uuid=constants.UUID_STATUS_PLANNED)
        title = 'Fail'
        self.assertNoFormError(self.client.post(
            url,
            data={
                'sub_type': stype2.id,
                'title': title,
                'status': status2.id,
                'duration': '2',
            },
        ))

        self.assertSettingValueEqual(
            key=setting_keys.unsuccessful_subtype_key, value=str(stype2.uuid),
        )
        self.assertSettingValueEqual(
            key=setting_keys.unsuccessful_title_key, value=title,
        )
        self.assertSettingValueEqual(
            key=setting_keys.unsuccessful_status_key, value=str(status2.uuid),
        )
        self.assertSettingValueEqual(
            key=setting_keys.unsuccessful_duration_key, value=2,
        )

    def test_config__edition_custom(self):
        self.login_as_root()

        sub_type = ActivitySubType.objects.get(
            uuid=constants.UUID_SUBTYPE_PHONECALL_CONFERENCE,
        )
        SettingValue.objects.set_4_key(
            key=setting_keys.unsuccessful_subtype_key, value=str(sub_type.uuid),
        )

        title = 'Damn it'
        SettingValue.objects.set_4_key(key=setting_keys.unsuccessful_title_key, value=title)

        status = self.get_object_or_fail(Status, uuid=constants.UUID_STATUS_DELAYED)
        SettingValue.objects.set_4_key(
            key=setting_keys.unsuccessful_status_key, value=str(status.uuid),
        )

        duration = 2
        SettingValue.objects.set_4_key(
            key=setting_keys.unsuccessful_duration_key, value=duration,
        )

        context = self.assertGET200(self.EDIT_CONFIG_URL).context

        with self.assertNoException():
            fields = context['form'].fields
            sub_type_f = fields['sub_type']
            title_f = fields['title']
            status_f = fields['status']
            duration_f = fields['duration']

        self.assertEqual(sub_type.id, sub_type_f.initial)
        self.assertEqual(title, title_f.initial)
        self.assertEqual(status.id, status_f.initial)
        self.assertEqual(2, duration_f.initial)

    def test_config__edition_errors(self):
        self.login_as_root()

        url = self.EDIT_CONFIG_URL
        data = {
            'sub_type': self.get_object_or_fail(
                ActivitySubType, uuid=constants.UUID_SUBTYPE_PHONECALL_OUTGOING,
            ).id,
            'title': 'Not successful',
            'status': self.get_object_or_fail(Status, uuid=constants.UUID_STATUS_PLANNED).id,
            'duration': '2',
        }

        response_title1 = self.assertPOST200(url, data={**data, 'title': ''})
        self.assertFormError(
            response_title1.context['form'],
            field='title', errors=_('This field is required.'),
        )

        very_long_title = (
            'A very very very very very long title which should cause a '
            'validation error, because it is longer than the maximum length '
            'of an Activity title'
        )
        response_title2 = self.assertPOST200(url, data={**data, 'title': very_long_title})
        self.assertFormError(
            response_title2.context['form'],
            field='title',
            errors=ngettext(
                'Ensure this value has at most %(limit_value)d character '
                '(it has %(show_value)d).',
                'Ensure this value has at most %(limit_value)d characters '
                '(it has %(show_value)d).',
                100,
            ) % {'limit_value': 100, 'show_value': len(very_long_title)},
        )

        # ---
        response_duration1 = self.assertPOST200(url, data={**data, 'duration': '0'})
        self.assertFormError(
            response_duration1.context['form'],
            field='duration',
            errors=_('Ensure this value is greater than or equal to %(limit_value)s.') % {
                'limit_value': 1,
            },
        )

        response_duration2 = self.assertPOST200(url, data={**data, 'duration': '121'})
        self.assertFormError(
            response_duration2.context['form'],
            field='duration',
            errors=_('Ensure this value is less than or equal to %(limit_value)s.') % {
                'limit_value': 120,
            },
        )

    def test_config__edition_invalid_initial_sub_type(self):
        self.login_as_root()

        sub_type_uuid = uuid4()
        self.assertFalse(ActivitySubType.objects.filter(uuid=sub_type_uuid))

        SettingValue.objects.set_4_key(
            key=setting_keys.unsuccessful_subtype_key, value=str(sub_type_uuid),
        )

        url = self.EDIT_CONFIG_URL
        response1 = self.assertGET200(url)

        with self.assertNoException():
            sub_type_f1 = response1.context['form'].fields['sub_type']
        self.assertIsNone(sub_type_f1.initial)

        # Badly formed UUID (should not happen if you do not edit manually the DB)
        SettingValue.objects.set_4_key(
            # key=constants.SETTING_UNSUCCESSFUL_SUBTYPE_UUID, value='not-a-uuid',
            key=setting_keys.unsuccessful_subtype_key, value='not-a-uuid',
        )

        response2 = self.assertGET200(url)

        with self.assertNoException():
            sub_type_f2 = response2.context['form'].fields['sub_type']
        self.assertIsNone(sub_type_f2.initial)

    def test_config__edition_invalid_initial_status(self):
        self.login_as_root()

        status_uuid = uuid4()
        self.assertFalse(Status.objects.filter(uuid=status_uuid))

        SettingValue.objects.set_4_key(
            key=setting_keys.unsuccessful_status_key, value=str(status_uuid),
        )

        response1 = self.assertGET200(self.EDIT_CONFIG_URL)

        with self.assertNoException():
            status_f1 = response1.context['form'].fields['status']
        self.assertIsNone(status_f1.initial)

        # Badly formed UUID (should not happen if you do not edit manually the DB)
        SettingValue.objects.set_4_key(
            key=setting_keys.unsuccessful_status_key, value='invalid-uuid',
        )

        response2 = self.assertGET200(self.EDIT_CONFIG_URL)

        with self.assertNoException():
            status_f2 = response2.context['form'].fields['status']
        self.assertIsNone(status_f2.initial)

    def test_config__permission(self):
        self.login_as_standard(allowed_apps=['activities'])  # admin_4_apps=['activities']
        self.assertGET403(self.EDIT_CONFIG_URL)

    def test_config__setting_values_are_hidden(self):
        self.login_as_root()

        def assertEditionFailed(key):
            setting_value = self.get_object_or_fail(SettingValue, key_id=key.id)
            self.assertGET409(
                reverse('creme_config__edit_setting', args=(setting_value.id,))
            )

        assertEditionFailed(key=setting_keys.unsuccessful_subtype_key)
        assertEditionFailed(key=setting_keys.unsuccessful_title_key)
        assertEditionFailed(key=setting_keys.unsuccessful_status_key)
        assertEditionFailed(key=setting_keys.unsuccessful_duration_key)

    def test_creation__default(self):
        user = self.login_as_root_and_get()
        activities_count = Activity.objects.count()

        ButtonMenuItem.objects.create(
            button=buttons.AddUnsuccessfulPhoneCallButton, order=1,
        )

        contact = self.contact
        add_url = self._build_add_url(contact)

        detail_response = self.assertGET200(contact.get_absolute_url())
        self.assertTrue(
            [*self.iter_button_nodes(
                self.get_instance_buttons_node(self.get_html_tree(detail_response.content)),
                tags=['a'], href=add_url,
            )],
            msg='<Add call> button not found!',
        )

        self.assertGET405(add_url)

        self.assertPOST200(add_url)
        self.assertEqual(activities_count + 1, Activity.objects.count())

        sub_type = ActivitySubType.objects.get(uuid=constants.UUID_SUBTYPE_PHONECALL_OUTGOING)
        activity = self.get_object_or_fail(
            Activity, type=sub_type.type, sub_type=sub_type, title=_('Unsuccessful call'),
        )
        self.assertEqual(
            self.get_object_or_fail(Status, uuid=constants.UUID_STATUS_UNSUCCESSFUL),
            activity.status,
        )
        self.assertEqual(Activity.FloatingType.NARROW, activity.floating_type)

        end = activity.end
        self.assertDatetimesAlmostEqual(end, now())
        self.assertEqual(end - timedelta(minutes=3), activity.start)

        REL_SUB_PART_2_ACTIVITY = constants.REL_SUB_PART_2_ACTIVITY
        self.assertHaveRelation(user.linked_contact, REL_SUB_PART_2_ACTIVITY, activity)
        self.assertHaveRelation(contact,             REL_SUB_PART_2_ACTIVITY, activity)

        self.assertListEqual(
            [Calendar.objects.get_default_calendar(user)],
            [*activity.calendars.all()],
        )

    def test_creation__custom(self):
        "Custom values stored in SettingValues."
        user = self.login_as_activities_user(creatable_models=[Activity])
        self.add_credentials(user.role, all=['VIEW', 'LINK'])

        sub_type = ActivitySubType.objects.get(
            uuid=constants.UUID_SUBTYPE_PHONECALL_CONFERENCE,
        )
        SettingValue.objects.set_4_key(
            key=setting_keys.unsuccessful_subtype_key, value=str(sub_type.uuid),
        )

        title = 'Damn it'
        SettingValue.objects.set_4_key(key=setting_keys.unsuccessful_title_key, value=title)

        status = self.get_object_or_fail(Status, uuid=constants.UUID_STATUS_DELAYED)
        SettingValue.objects.set_4_key(
            key=setting_keys.unsuccessful_status_key, value=str(status.uuid),
        )

        duration = 2
        SettingValue.objects.set_4_key(
            key=setting_keys.unsuccessful_duration_key, value=duration,
        )

        self.assertPOST200(self._build_add_url(self.contact))

        activity = self.get_object_or_fail(
            Activity, type=sub_type.type, sub_type=sub_type, title=title,
        )
        self.assertEqual(status, activity.status)

        end = activity.end
        self.assertDatetimesAlmostEqual(end, now())
        self.assertEqual(end - timedelta(minutes=duration), activity.start)

    def test_creation__type_error(self):
        self.login_as_root()

        sub_type_uuid = uuid4()
        self.assertFalse(ActivitySubType.objects.filter(uuid=sub_type_uuid))
        SettingValue.objects.set_4_key(
            key=setting_keys.unsuccessful_subtype_key, value=str(sub_type_uuid),
        )

        response = self.client.post(self._build_add_url(self.contact))
        self.assertContains(
            response,
            _(
                'The configuration of the button is broken; '
                'fix it in the configuration of «Activities».'
            ),
            status_code=409,
            html=True,
        )

    def test_creation__status_error(self):
        self.login_as_root()

        status_uuid = uuid4()
        self.assertFalse(Status.objects.filter(uuid=status_uuid))
        SettingValue.objects.set_4_key(
            key=setting_keys.unsuccessful_status_key, value=str(status_uuid),
        )

        response = self.client.post(self._build_add_url(self.contact))
        self.assertContains(
            response,
            _(
                'The configuration of the button is broken; '
                'fix it in the configuration of «Activities».'
            ),
            status_code=409,
            html=True,
        )

    def test_creation__contact_is_self(self):
        user = self.login_as_root_and_get()

        response = self.client.post(self._build_add_url(user.linked_contact))
        self.assertContains(
            response,
            _(
                'The current contact is you; '
                'the button has to be used with a different contact'
            ),
            status_code=409,
            html=True,
        )

    def test_creation__long_title(self):
        self.login_as_root()

        self.assertEqual(100, Activity._meta.get_field('title').max_length)

        title = (
            'A very very very very very long title which will cause an '
            'integrity error if it is not truncated by the view'
        )
        self.assertGreater(len(title), 100)
        SettingValue.objects.set_4_key(key=setting_keys.unsuccessful_title_key, value=title)

        self.assertPOST200(self._build_add_url(self.contact))

        activity = Activity.objects.order_by('-id').first()
        self.assertIsNotNone(activity)
        self.assertEqual(
            'A very very very very very long title which will cause an '
            'integrity error if it is not truncated by…',
            activity.title,
        )

    def test_creation__app_perm(self):
        user = self.login_as_standard(allowed_apps=['persons'])  # 'activities'
        self.add_credentials(user.role, all=['VIEW', 'LINK'])
        self.assertPOST403(self._build_add_url(self.contact))

    def test_creation__creation_perm(self):
        user = self.login_as_standard(allowed_apps=['persons', 'activities'])
        self.add_credentials(user.role, all=['VIEW', 'LINK'])
        self.assertPOST403(self._build_add_url(self.contact))

    def test_creation__link_perm(self):
        user = self.login_as_activities_user(creatable_models=[Activity])
        self.add_credentials(user.role, all='!LINK')
        self.assertPOST403(self._build_add_url(self.contact))

    def test_creation__bad_ctype(self):
        user = self.login_as_root_and_get()
        self.assertPOST404(self._build_add_url(
            Organisation.objects.create(user=user, name='Miyamoto')
        ))
