from uuid import uuid4

from django.utils.timezone import now
from django.utils.translation import gettext as _

from creme.activities import constants, setting_keys
from creme.activities.buttons import (
    AddMeetingButton,
    AddPhoneCallButton,
    AddRelatedActivityButton,
    AddUnsuccessfulPhoneCallButton,
)
from creme.activities.models import ActivitySubType, Status
from creme.activities.tests.base import Activity, Contact, _ActivitiesTestCase
from creme.creme_core.models import SettingValue
from creme.persons.tests.base import skipIfCustomContact


@skipIfCustomContact
class AddRelatedActivityButtonsTestCase(_ActivitiesTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.root = root = cls.get_root_user()
        cls.contact = Contact.objects.create(
            user=root, first_name='John', last_name='Doe',
        )

    def test_no_fixed_type(self):
        button = AddRelatedActivityButton()
        ctxt = button.get_context(
            entity=self.contact, request=self.build_request(user=self.root),
        )
        self.assertEqual(_('Create a related activity'), ctxt.get('verbose_name'))
        self.assertEqual('activities/buttons/add-related.html', ctxt.get('template_name'))
        self.assertIn('description', ctxt)
        self.assertIsNone(ctxt.get('type_uuid', -1))
        self.assertNotIn('permission_error', ctxt)

        icon = ctxt.get('icon')
        self.assertIsNotNone(icon)
        self.assertEqual(_('Activity'), icon.label)
        self.assertIn('images/calendar', icon.url)

    def test_no_fixed_type__creation_perm(self):
        user = self.create_user(role=self.create_role(
            allowed_apps=['activities', 'persons'],
            # creatable_models=[Activity],  #<===
        ))
        self.add_credentials(user.role, all='*')

        ctxt = AddRelatedActivityButton().get_context(
            entity=self.contact, request=self.build_request(user=user),
        )
        self.assertEqual(
            _('You are not allowed to create: {}').format(_('Activity')),
            ctxt.get('permission_error'),
        )

    def test_no_fixed_type__linking_perm(self):
        user = self.create_user(role=self.create_role(
            allowed_apps=['activities', 'persons'],
            creatable_models=[Activity],
        ))
        self.add_credentials(user.role, all='!LINK')

        ctxt = AddRelatedActivityButton().get_context(
            entity=self.contact, request=self.build_request(user=user),
        )
        self.assertEqual(
            _('You are not allowed to link this entity: {}').format(self.contact),
            ctxt.get('permission_error'),
        )

    def test_meeting(self):
        ctxt = AddMeetingButton().get_context(
            entity=self.contact, request=self.build_request(user=self.root),
        )
        self.assertEqual(_('Create a related meeting'), ctxt.get('verbose_name'))
        self.assertEqual('activities/buttons/add-related.html', ctxt.get('template_name'))
        self.assertIn('description', ctxt)
        self.assertNotIn('permission_error', ctxt)
        self.assertEqual(constants.UUID_TYPE_MEETING, ctxt.get('type_uuid'))

        icon = ctxt.get('icon')
        self.assertIsNotNone(icon)
        self.assertEqual(_('Meeting'), icon.label)
        self.assertIn('images/meeting', icon.url)

    def test_meeting__disabled_type(self):
        atype = self._get_type(constants.UUID_TYPE_MEETING)

        try:
            atype.disabled = now()
            atype.save()

            ctxt = AddMeetingButton().get_context(
                entity=self.contact, request=self.build_request(user=self.root),
            )
        finally:
            atype.disabled = None
            atype.save()

        self.assertEqual(atype.message_for_disabled, ctxt.get('permission_error'))

    def test_phone_call(self):
        ctxt = AddPhoneCallButton().get_context(
            entity=self.contact, request=self.build_request(user=self.root),
        )
        self.assertEqual(_('Create a related phone call'), ctxt.get('verbose_name'))
        self.assertEqual('activities/buttons/add-related.html', ctxt.get('template_name'))
        self.assertIn('description', ctxt)
        self.assertNotIn('permission_error', ctxt)
        self.assertEqual(constants.UUID_TYPE_PHONECALL, ctxt.get('type_uuid'))

        icon = ctxt.get('icon')
        self.assertIsNotNone(icon)
        self.assertEqual(_('Phone call'), icon.label)
        self.assertIn('images/phone', icon.url)

    def test_deleted_type(self):
        class DeletedTypeButton(AddRelatedActivityButton):
            id = AddRelatedActivityButton.generate_id('activities', 'add_deleted')
            verbose_name = 'Create a ...'
            # description = ...
            activity_type_uuid = str(uuid4())

        ctxt = DeletedTypeButton().get_context(
            entity=self.contact, request=self.build_request(user=self.root),
        )
        self.assertEqual(
            _(
                'It seems the instance of model «{model}» with uuid "{uuid}" '
                'has been deleted; please contact your administrator.'
            ).format(
                model=_('Type of activity'),
                uuid=DeletedTypeButton.activity_type_uuid,
            ),
            ctxt.get('permission_error'),
        )

    def test_unsuccessful(self):
        button = AddUnsuccessfulPhoneCallButton()
        ctxt = button.get_context(
            entity=self.contact, request=self.build_request(user=self.root),
        )
        self.assertEqual(
            _('Create an unsuccessful phone call'), ctxt.get('verbose_name'),
        )
        self.assertEqual(
            'activities/buttons/add-unsuccessful-phonecall.html',
            ctxt.get('template_name')
        )
        self.assertIn('description', ctxt)
        self.assertNotIn('permission_error', ctxt)

        icon = ctxt.get('icon')
        self.assertIsNotNone(icon)
        self.assertEqual(_('Phone call'), icon.label)
        self.assertIn('images/phone', icon.url)

    def test_unsuccessful__disabled_type(self):
        button = AddUnsuccessfulPhoneCallButton()
        atype = self._get_type(constants.UUID_TYPE_PHONECALL)

        try:
            atype.disabled = now()
            atype.save()

            ctxt = button.get_context(
                entity=self.contact, request=self.build_request(user=self.root),
            )
        finally:
            atype.disabled = None
            atype.save()

        self.assertEqual(atype.message_for_disabled, ctxt.get('permission_error'))

    def test_unsuccessful__disabled_subtype(self):
        button = AddUnsuccessfulPhoneCallButton()

        sub_type = ActivitySubType.objects.create(
            type=self._get_type(constants.UUID_TYPE_PHONECALL),
            name='SMS', disabled=now(),
        )
        SettingValue.objects.set_4_key(
            key=setting_keys.unsuccessful_subtype_key, value=str(sub_type.uuid),
        )

        ctxt = button.get_context(
            entity=self.contact, request=self.build_request(user=self.root),
        )
        self.assertEqual(sub_type.message_for_disabled, ctxt.get('permission_error'))

    def test_unsuccessful__disabled_status(self):
        button = AddUnsuccessfulPhoneCallButton()

        status = Status.objects.create(name='No success', disabled=now())
        SettingValue.objects.set_4_key(
            key=setting_keys.unsuccessful_status_key, value=str(status.uuid),
        )

        ctxt = button.get_context(
            entity=self.contact, request=self.build_request(user=self.root),
        )
        self.assertEqual(status.message_for_disabled, ctxt.get('permission_error'))
