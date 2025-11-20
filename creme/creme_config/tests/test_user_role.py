from functools import partial
from json import dumps as json_dump

# from parameterized import parameterized
from django.contrib.contenttypes.models import ContentType
from django.forms import BooleanField, CharField
from django.urls import reverse
from django.utils.timezone import now
from django.utils.translation import gettext as _
from django.utils.translation import ngettext

import creme.creme_core.bricks as core_bricks
from creme.activities.models import Activity
from creme.creme_core.auth.entity_credentials import EntityCredentials
from creme.creme_core.constants import UUID_CHANNEL_ADMIN
from creme.creme_core.core.entity_cell import EntityCellRegularField
from creme.creme_core.core.entity_filter import (
    EF_CREDENTIALS,
    condition_handler,
    operands,
    operators,
)
from creme.creme_core.creme_jobs.deletor import deletor_type
from creme.creme_core.forms.base import LAYOUT_REGULAR
from creme.creme_core.forms.widgets import Label
from creme.creme_core.gui.menu import ContainerEntry, Separator0Entry
from creme.creme_core.menu import CremeEntry, JobsEntry
from creme.creme_core.models import (
    BrickDetailviewLocation,
    BrickHomeLocation,
    CremeEntity,
    CremePropertyType,
    CremeUser,
    CustomField,
    CustomFormConfigItem,
    DeletionCommand,
    EntityFilter,
    EntityFilterCondition,
    FakeActivity,
    FakeContact,
    FakeDocument,
    FakeOrganisation,
    Job,
    MenuConfigItem,
    Notification,
    NotificationChannel,
    RelationType,
    SearchConfigItem,
    SetCredentials,
    UserRole,
)
from creme.creme_core.tests.base import CremeTestCase, skipIfNotInstalled
from creme.creme_core.tests.fake_custom_forms import (
    FAKEORGANISATION_CREATION_CFORM,
)
from creme.creme_core.tests.views.base import BrickTestCaseMixin
from creme.documents.models import Document
from creme.persons.models import Address, Contact, Organisation

from ..auth import role_config_perm, user_config_perm
from ..bricks import UserRolesBrick
from ..notification import RoleSwitchContent


class UserRoleTestCase(CremeTestCase, BrickTestCaseMixin):
    ROLE_CREATION_URL = reverse('creme_config__create_role')
    DEL_CREDS_URL = reverse('creme_config__remove_role_credentials')

    @staticmethod
    def _build_add_creds_url(role):
        return reverse('creme_config__add_credentials_to_role', args=(role.id,))

    @staticmethod
    def _build_wizard_edit_url(role):
        return reverse('creme_config__edit_role', args=(role.id,))

    @staticmethod
    def _build_activation_url(role_id, activation=True):
        return reverse(
            'creme_config__activate_role' if activation else 'creme_config__deactivate_role',
            args=(role_id,),
        )

    @staticmethod
    def _build_del_role_url(role):
        return reverse('creme_config__delete_role', args=(role.id,))

    def login_with_role_perm(self):
        return self.login_as_standard(special_permissions=[role_config_perm])

    # def login_not_as_superuser(self):
    #     apps = ('creme_config',)
    #     return self.login_as_standard(allowed_apps=apps, admin_4_apps=apps)
    def login_without_role_perm(self):
        return self.login_as_standard(allowed_apps=('creme_config',))

    # @parameterized.expand([False, True])
    # def test_portal(self, superuser):
    def test_portal(self):
        # if superuser:
        #     self.login_as_super()
        # else:
        #     self.login_as_standard(admin_4_apps=['creme_config'])
        user = self.login_with_role_perm()

        # role = UserRole.objects.first()
        role = user.role
        self.assertIsNotNone(role)

        response = self.assertGET200(reverse('creme_config__roles'))
        self.assertTemplateUsed(response, 'creme_config/portals/user-role.html')
        self.assertEqual(
            reverse('creme_core__reload_bricks'),
            response.context.get('bricks_reload_url'),
        )

        brick_node = self.get_brick_node(
            self.get_html_tree(response.content), brick=UserRolesBrick,
        )
        self.assertBrickTitleEqual(
            brick_node,
            # count=1 if superuser else 2,
            count=2,
            title='{count} Role', plural_title='{count} Roles',
        )
        self.assertBrickHeaderHasButton(
            self.get_brick_header_buttons(brick_node),
            url=self.ROLE_CREATION_URL,
            label=_('New role'),
        )
        self.assertIn(
            role.name,
            [n.text for n in brick_node.findall('.//td[@class="role-name"]')],
        )

    def test_portal__forbidden(self):
        self.login_without_role_perm()
        self.assertGET403(reverse('creme_config__roles'))

    @skipIfNotInstalled('creme.persons')
    @skipIfNotInstalled('creme.documents')
    @skipIfNotInstalled('creme.activities')
    def test_creation__no_efilter(self):
        "No EntityFilter."
        # self.login_as_root()
        self.login_with_role_perm()
        url = self.ROLE_CREATION_URL
        name = 'Basic role'
        apps = ['persons', 'documents']
        adm_apps = ['persons']

        # Step 1 (name, apps)
        response1 = self.assertGET200(url)
        context1 = response1.context
        self.assertEqual(_('Next step'), context1.get('submit_label'))

        with self.assertNoException():
            app_labels = context1['form'].fields['allowed_apps'].choices

        self.assertInChoices(
            value=apps[0], label=_('Accounts and Contacts'), choices=app_labels,
        )
        self.assertInChoices(
            value=apps[1], label=_('Documents'), choices=app_labels,
        )
        self.assertInChoices(
            value='activities', label=_('Activities'), choices=app_labels,
        )

        step_key = 'role_creation_wizard-current_step'
        response2 = self.client.post(
            url,
            data={
                step_key: '0',
                '0-name': name,
                '0-allowed_apps': apps,
            },
        )
        self.assertNoFormError(response2)

        # Step 2 (administrated apps)
        with self.assertNoException():
            adm_app_labels = response2.context['form'].fields['admin_4_apps'].choices

        self.assertInChoices(
            value=apps[0], label=_('Accounts and Contacts'), choices=adm_app_labels,
        )
        self.assertInChoices(
            value=apps[1], label=_('Documents'), choices=adm_app_labels,
        )
        self.assertNotInChoices(value='activities', choices=adm_app_labels)

        response3 = self.client.post(
            url,
            data={
                step_key: '1',
                '1-admin_4_apps': adm_apps,
            },
        )
        self.assertNoFormError(response3)

        # Step 3 (creatable models)
        with self.assertNoException():
            creatable_ctypes = {*response3.context['form'].fields['creatable_ctypes'].ctypes}

        get_ct = ContentType.objects.get_for_model
        ct_contact = get_ct(Contact)
        ct_orga = get_ct(Organisation)
        ct_doc = get_ct(Document)

        self.assertIn(ct_contact, creatable_ctypes)
        self.assertIn(ct_orga,    creatable_ctypes)
        self.assertNotIn(get_ct(Address), creatable_ctypes)  # Not CremeEntity
        self.assertIn(ct_doc, creatable_ctypes)
        self.assertNotIn(get_ct(Activity), creatable_ctypes)  # App not allowed

        response4 = self.client.post(
            url,
            data={
                step_key: '2',
                '2-creatable_ctypes': [ct_contact.id, ct_doc.id],
            },
        )
        self.assertNoFormError(response4)

        # Step 4 (listable model)
        with self.assertNoException():
            listable_ctypes = response4.context['form'].fields['listable_ctypes'].ctypes

        self.assertIn(ct_contact, listable_ctypes)
        self.assertIn(ct_orga, listable_ctypes)
        self.assertNotIn(get_ct(Address), listable_ctypes)  # Not CremeEntity
        self.assertIn(ct_doc, listable_ctypes)
        self.assertNotIn(get_ct(Activity), listable_ctypes)  # App not allowed

        response5 = self.client.post(
            url,
            data={
                step_key: '3',
                '3-listable_ctypes': [ct_orga.id],
            },
        )
        self.assertNoFormError(response5)

        # Step 5 (exportable models)
        with self.assertNoException():
            exp_ctypes = response5.context['form'].fields['exportable_ctypes'].ctypes

        self.assertIn(ct_contact, exp_ctypes)
        self.assertIn(get_ct(Organisation), exp_ctypes)
        self.assertNotIn(get_ct(Address), exp_ctypes)  # Not CremeEntity
        self.assertIn(ct_doc, exp_ctypes)
        self.assertNotIn(get_ct(Activity), exp_ctypes)  # App not allowed

        response6 = self.client.post(
            url,
            data={
                step_key: '4',
                '4-exportable_ctypes': [ct_contact.id],
            },
        )
        self.assertNoFormError(response6)

        # Step 6 (special permissions)
        with self.assertNoException():
            special_perm_choices = response6.context['form'].fields['special_perms'].choices

        self.assertInChoices(
            value=role_config_perm.id,
            label=role_config_perm.verbose_name,
            choices=special_perm_choices,
        )
        self.assertInChoices(
            value=user_config_perm.id,
            label=user_config_perm.verbose_name,
            choices=special_perm_choices,
        )

        response7 = self.client.post(
            url,
            data={
                step_key: '5',
                '5-special_perms': [user_config_perm.id, role_config_perm.id],
            },
        )
        self.assertNoFormError(response7)

        # Step 7 (first credentials)
        with self.assertNoException():
            cred_ctypes = {*response7.context['form'].fields['ctype'].ctypes}

        self.assertIn(ct_contact, cred_ctypes)
        self.assertIn(get_ct(Organisation), cred_ctypes)
        self.assertNotIn(get_ct(Address), cred_ctypes)  # Not CremeEntity
        self.assertIn(ct_doc, cred_ctypes)
        self.assertNotIn(get_ct(Activity), cred_ctypes)  # App not allowed

        set_type = SetCredentials.ESET_ALL
        response8 = self.client.post(
            url,
            data={
                step_key: '6',
                '6-can_change': True,

                '6-set_type': set_type,
                '6-ctype':    ct_contact.id,

                '6-forbidden': 'False',
            },
        )
        self.assertNoFormError(response8)

        # Step 8 (filter conditions)
        context8 = response8.context
        self.assertEqual(_('Save the role'), context8.get('submit_label'))

        with self.assertNoException():
            fields8 = context8['form'].fields
            label_field = fields8['no_filter_label']

        self.assertEqual(1, len(fields8))

        self.assertIsInstance(label_field, CharField)
        self.assertIsInstance(label_field.widget, Label)
        self.assertEqual(_('Conditions'), label_field.label)
        self.assertEqual(_('No filter, no condition.'), label_field.initial)

        response8 = self.client.post(url, data={step_key: '7'})
        self.assertNoFormError(response8)

        role = self.get_object_or_fail(UserRole, name=name)
        self.assertSetEqual({*apps},     role.allowed_apps)
        self.assertSetEqual({*adm_apps}, role.admin_4_apps)

        now_value = now()
        self.assertDatetimesAlmostEqual(now_value, role.created)
        self.assertDatetimesAlmostEqual(now_value, role.modified)

        self.assertCountEqual([ct_contact, ct_doc], role.creatable_ctypes.all())
        self.assertCountEqual([ct_orga],            role.listable_ctypes.all())
        self.assertCountEqual([ct_contact],         role.exportable_ctypes.all())

        creds = self.get_alone_element(role.credentials.all())
        self.assertEqual(EntityCredentials.VIEW | EntityCredentials.CHANGE, creds.value)
        self.assertEqual(set_type, creds.set_type)
        self.assertEqual(ct_contact, creds.ctype)
        self.assertFalse(creds.forbidden)

        self.assertCountEqual(
            [user_config_perm, role_config_perm],
            role.special_permissions.values(),
        )

    @skipIfNotInstalled('creme.persons')
    def test_creation__efilter(self):
        "With EntityFilter."
        self.login_as_root()
        url = self.ROLE_CREATION_URL
        name = 'Only persons role'
        apps = ['persons']

        # Step 1 ---
        step_key = 'role_creation_wizard-current_step'
        response = self.client.post(
            url,
            data={
                step_key: '0',
                '0-name': name,
                '0-allowed_apps': apps,
            },
        )
        self.assertNoFormError(response)

        # Step 2 ---
        response = self.client.post(
            url, data={step_key: '1', '1-admin_4_apps': []},
        )
        self.assertNoFormError(response)

        # Step 3 ---
        response = self.client.post(
            url, data={step_key: '2', '2-creatable_ctypes': []},
        )
        self.assertNoFormError(response)

        # Step 4 ---
        response = self.client.post(
            url, data={step_key: '3', '3-listable_ctypes': []},
        )
        self.assertNoFormError(response)

        # Step 5 ---
        response = self.client.post(
            url, data={step_key: '4', '4-exportable_ctypes': []},
        )
        self.assertNoFormError(response)

        # Step 6 ---
        response = self.client.post(
            url, data={step_key: '5', '5-special_perms': []},
        )
        self.assertNoFormError(response)

        # Step 7 ---
        ct_contact = ContentType.objects.get_for_model(Contact)
        set_type = SetCredentials.ESET_FILTER
        response = self.client.post(
            url,
            data={
                step_key: '6',
                '6-can_link': True,

                '6-set_type': set_type,
                '6-ctype':    ct_contact.id,
                '6-forbidden': 'True',
            },
        )
        self.assertNoFormError(response)

        # Step 8 ---
        with self.assertNoException():
            fields6 = response.context['form'].fields
            name_f = fields6['name']
            use_or_choices = fields6['use_or'].choices
            fconds_f = fields6['regularfieldcondition']
            rconds_f = fields6['relationcondition']

        self.assertNotIn('no_filter_label', fields6)
        self.assertIsInstance(name_f, CharField)
        self.assertListEqual(
            [
                (False, _('All the conditions are met')),
                (True,  _('Any condition is met')),
            ],
            use_or_choices,
        )

        self.assertIn('customfieldcondition', fields6)
        self.assertIn('propertycondition',   fields6)

        self.assertEqual(Contact, fconds_f.model)
        self.assertEqual(Contact, rconds_f.model)

        filter_name = 'Named Kajiura'
        filter_operator_id = operators.IEQUALS
        filter_field_name = 'last_name'
        filter_field_value = 'Kajiura'
        response = self.client.post(
            url,
            data={
                step_key: '7',
                '7-name': filter_name,
                '7-use_or': 'True',
                '7-regularfieldcondition': json_dump([{
                    'field':    {'name': filter_field_name},
                    'operator': {'id': str(filter_operator_id)},
                    'value':    filter_field_value,
                }]),
            },
        )
        self.assertNoFormError(response)

        role = self.get_object_or_fail(UserRole, name=name)
        self.assertEqual({*apps}, role.allowed_apps)
        self.assertFalse(role.admin_4_apps)

        self.assertFalse(role.creatable_ctypes.all())
        self.assertFalse(role.exportable_ctypes.all())

        creds = self.get_alone_element(role.credentials.all())
        self.assertEqual(set_type, creds.set_type)
        self.assertEqual(ct_contact, creds.ctype)
        self.assertTrue(creds.forbidden)
        self.assertEqual(
            EntityCredentials.VIEW | EntityCredentials.LINK,
            creds.value,
        )

        efilter = creds.efilter
        self.assertIsNotNone(efilter)
        self.assertEqual(filter_name, efilter.name)
        self.assertTrue(efilter.use_or)

        condition = self.get_alone_element(efilter.get_conditions())
        self.assertEqual(
            condition_handler.RegularFieldConditionHandler.type_id,
            condition.type,
        )
        self.assertEqual(filter_field_name, condition.name)
        self.assertDictEqual(
            {
                'operator': filter_operator_id,
                'values': [filter_field_value],
            },
            condition.value,
        )

    def test_creation__efilter_on_entity(self):
        "With EntityFilter on CremeEntity."
        self.login_as_root()
        url = self.ROLE_CREATION_URL
        name = 'Only persons role'

        # Step 1 ---
        step_key = 'role_creation_wizard-current_step'
        response = self.client.post(
            url,
            data={
                step_key: '0',
                '0-name': name,
                '0-allowed_apps': ['persons'],
            },
        )
        self.assertNoFormError(response)

        # Step 2 ---
        response = self.client.post(
            url, data={step_key: '1', '1-admin_4_apps': []},
        )
        self.assertNoFormError(response)

        # Step 3 ---
        response = self.client.post(
            url, data={step_key: '2', '2-creatable_ctypes': []},
        )
        self.assertNoFormError(response)

        # Step 4 ---
        response = self.client.post(
            url, data={step_key: '3', '3-listable_ctypes': []},
        )
        self.assertNoFormError(response)

        # Step 5 ---
        response = self.client.post(
            url, data={step_key: '4', '4-exportable_ctypes': []},
        )
        self.assertNoFormError(response)

        # Step 6 ---
        response = self.client.post(
            url, data={step_key: '5', '5-special_perms': []},
        )
        self.assertNoFormError(response)

        # Step 7 ---
        set_type = SetCredentials.ESET_FILTER
        response = self.client.post(
            url,
            data={
                step_key: '6',
                '6-can_link': True,

                '6-set_type': set_type,
                '6-forbidden': 'False',
            },
        )
        self.assertNoFormError(response)

        # Step 8 ---
        with self.assertNoException():
            fields6 = response.context['form'].fields
            fconds_f = fields6['regularfieldcondition']

        self.assertNotIn('customfieldcondition', fields6)
        self.assertEqual(CremeEntity, fconds_f.model)

        filter_name = 'Important entities'
        filter_operator_id = operators.ICONTAINS
        filter_field_name = 'description'
        filter_field_value = 'important'
        response = self.client.post(
            url,
            data={
                step_key: '7',
                '7-name': filter_name,
                '7-use_or': 'True',
                '7-regularfieldcondition': json_dump([{
                    'field':    {'name': filter_field_name},
                    'operator': {'id': str(filter_operator_id)},
                    'value':    filter_field_value,
                }]),
            },
        )
        self.assertNoFormError(response)

        role = self.get_object_or_fail(UserRole, name=name)

        creds = self.get_alone_element(role.credentials.all())
        self.assertIsNone(creds.ctype)  # CremeEntity

        efilter = creds.efilter
        self.assertIsNotNone(efilter)
        self.assertEqual(CremeEntity, efilter.entity_type.model_class())

        condition = self.get_alone_element(efilter.get_conditions())
        self.assertEqual(
            condition_handler.RegularFieldConditionHandler.type_id,
            condition.type,
        )
        self.assertEqual(filter_field_name, condition.name)
        self.assertDictEqual(
            {
                'operator': filter_operator_id,
                'values': [filter_field_value],
            },
            condition.value,
        )

    def test_creation__forbidden(self):
        "No role permission."
        # self.login_not_as_superuser()
        self.login_without_role_perm()
        self.assertGET403(self.ROLE_CREATION_URL)

    def test_add_credentials(self):
        # self.login_as_root()
        self.login_with_role_perm()
        user = self.get_root_user()

        role = self.create_role(name='CEO', allowed_apps=['creme_core'])

        other_user = CremeUser.objects.create(username='chloe', role=role)
        contact = FakeContact.objects.create(
            user=user, first_name='Yuki', last_name='Kajiura',
        )
        self.assertFalse(other_user.has_perm_to_view(contact))

        self.assertEqual(0, role.credentials.count())

        # GET (Step 1) ---
        url = self._build_add_creds_url(role)
        response1 = self.assertGET200(url)
        self.assertTemplateUsed(
            response1, 'creme_core/generics/blockform/edit-wizard-popup.html',
        )

        get_ctxt = response1.context.get
        self.assertEqual(
            _('Add credentials to «{object}»').format(object=role),
            get_ctxt('title'),
        )
        self.assertFalse(get_ctxt('help_message'))

        self.assertEqual(_('Next step'), get_ctxt('submit_label'))

        # POST (Step 1) ---
        set_type = SetCredentials.ESET_ALL
        step_key = 'credentials_adding_wizard-current_step'
        response2 = self.client.post(
            url,
            data={
                step_key: '0',

                '0-set_type':  set_type,
                '0-ctype':     '',
                '0-forbidden': 'False',

                '0-can_view':   True,
                '0-can_change': False,
                '0-can_delete': False,
                '0-can_link':   False,
                '0-can_unlink': False,
            },
        )
        self.assertNoFormError(response2)
        self.assertEqual(_('Add the credentials'), response2.context.get('submit_label'))

        # GET (Step 2) ---
        with self.assertNoException():
            fields2 = response2.context['form'].fields
            label_field = fields2['no_filter_label']

        self.assertEqual(1, len(fields2))

        self.assertIsInstance(label_field, CharField)
        self.assertIsInstance(label_field.widget, Label)
        self.assertEqual(_('Conditions'), label_field.label)
        self.assertEqual(
            _('No filter, no condition.'),
            label_field.initial,
        )

        # POST (Step 2) ---
        self.assertNoFormError(self.client.post(
            url,
            data={
                step_key: '1',
                # '1-use_or': 0,
            },
        ))

        creds = self.get_alone_element(role.credentials.all())
        self.assertEqual(EntityCredentials.VIEW, creds.value)
        self.assertEqual(set_type, creds.set_type)
        self.assertIsNone(creds.ctype)
        self.assertFalse(creds.forbidden)
        self.assertIsNone(creds.efilter)

        contact = self.refresh(contact)  # Refresh cache
        other_user = self.refresh(other_user)
        self.assertTrue(other_user.has_perm_to_view(contact))

    @skipIfNotInstalled('creme.persons')
    @skipIfNotInstalled('creme.activities')
    def test_add_credentials__ctype_n_own(self):
        "Specific CType + ESET_OWN."
        self.login_as_root()

        role = self.create_role(name='CEO', allowed_apps=['persons'])

        url = self._build_add_creds_url(role)
        response = self.assertGET200(url)

        with self.assertNoException():
            cred_ctypes = {*response.context['form'].fields['ctype'].ctypes}

        get_ct = ContentType.objects.get_for_model
        ct_contact = get_ct(Contact)

        self.assertIn(ct_contact, cred_ctypes)
        self.assertIn(get_ct(Organisation), cred_ctypes)
        self.assertNotIn(get_ct(Activity), cred_ctypes)  # App not allowed

        # POST (Step 1) ---
        set_type = SetCredentials.ESET_OWN
        step_key = 'credentials_adding_wizard-current_step'
        response = self.client.post(
            url,
            data={
                step_key: '0',

                '0-set_type':  set_type,
                '0-ctype':     ct_contact.id,
                '0-forbidden': 'False',

                '0-can_view':   True,
                '0-can_change': True,
                '0-can_delete': False,
                '0-can_link':   False,
                '0-can_unlink': False,
            },
        )
        self.assertNoFormError(response)

        # POST (Step 2) ---
        response = self.client.post(
            url,
            data={
                step_key: '1',
                # '1-use_or': 1,
            },
        )
        self.assertNoFormError(response)

        creds = self.get_alone_element(role.credentials.all())
        self.assertEqual(EntityCredentials.VIEW | EntityCredentials.CHANGE, creds.value)
        self.assertEqual(SetCredentials.ESET_OWN, creds.set_type)
        self.assertEqual(ct_contact.id,           creds.ctype_id)

    def test_add_credentials__not_superuser(self):
        "No role permission => error."
        # self.login_not_as_superuser()
        self.login_without_role_perm()

        role = self.create_role(name='CEO', allowed_apps=['persons'])

        url = self._build_add_creds_url(role)
        self.assertGET403(url)
        step_key = 'credentials_adding_wizard-current_step'
        self.assertPOST403(
            url,
            data={
                step_key: '0',

                '0-set_type':  SetCredentials.ESET_ALL,
                '0-ctype':     0,
                '0-forbidden': 'False',

                '0-can_view':   True,
                '0-can_change': False,
                '0-can_delete': False,
                '0-can_link':   False,
                '0-can_unlink': False,
            },
        )

    @skipIfNotInstalled('creme.persons')
    def test_add_credentials__forbidden_flag(self):
        self.login_as_root()

        role = self.create_role(name='CEO', allowed_apps=['persons'])

        url = self._build_add_creds_url(role)
        ct_contact = ContentType.objects.get_for_model(Contact)

        # POST (Step 1) ---
        set_type = SetCredentials.ESET_OWN
        step_key = 'credentials_adding_wizard-current_step'
        response = self.client.post(
            url,
            data={
                step_key: '0',

                '0-set_type':  set_type,
                '0-ctype':     ct_contact.id,
                '0-forbidden': 'True',  # <===

                '0-can_view':   True,
                '0-can_change': True,
                '0-can_delete': False,
                '0-can_link':   False,
                '0-can_unlink': False,
            },
        )
        self.assertNoFormError(response)

        # POST (Step 2) ---
        response = self.client.post(
            url,
            data={
                step_key: '1',
                # '1-use_or': 1,
            },
        )
        self.assertNoFormError(response)

        creds = self.get_alone_element(role.credentials.all())
        self.assertEqual(EntityCredentials.VIEW | EntityCredentials.CHANGE, creds.value)
        self.assertEqual(set_type,      creds.set_type)
        self.assertEqual(ct_contact.id, creds.ctype_id)
        self.assertTrue(creds.forbidden)

    @skipIfNotInstalled('creme.persons')
    def test_add_credentials__no_action(self):
        "No action => Validation error."
        self.login_as_root()

        role = self.create_role(name='CEO', allowed_apps=['persons'])

        step_key = 'credentials_adding_wizard-current_step'
        response = self.assertPOST200(
            self._build_add_creds_url(role),
            data={
                step_key: '0',

                '0-set_type':  SetCredentials.ESET_ALL,
                '0-forbidden': 'False',

                '0-can_view':   False,
                '0-can_change': False,
                '0-can_delete': False,
                '0-can_link':   False,
                '0-can_unlink': False,
            },
        )
        self.assertFormError(
            response.context['wizard']['form'],
            field=None, errors=_('No action has been selected.'),
        )

    def test_add_credentials__efilter(self):
        self.login_as_root()

        role = self.create_role(name='CEO', allowed_apps=['creme_core'])
        url = self._build_add_creds_url(role)

        # Step 1 ---
        ctype = ContentType.objects.get_for_model(FakeContact)
        set_type = SetCredentials.ESET_FILTER
        step_key = 'credentials_adding_wizard-current_step'
        response = self.client.post(
            url,
            data={
                step_key: '0',

                '0-set_type':  set_type,
                '0-ctype':     ctype.id,
                '0-forbidden': 'False',

                '0-can_view':   True,
                '0-can_change': True,
                '0-can_delete': False,
                '0-can_link':   False,
                '0-can_unlink': False,
            },
        )
        self.assertNoFormError(response)

        # Step 2 ---
        context = response.context

        with self.assertNoException():
            help_message = context['help_message']

            fields = context['form'].fields
            name_f = fields['name']
            use_or_choices = fields['use_or'].choices
            fconds_f = fields['regularfieldcondition']

        self.assertEqual(
            _(
                'Beware to performances with conditions on custom fields or relationships.'
            ),
            help_message,
        )

        self.assertIsInstance(name_f, CharField)
        self.assertListEqual(
            [
                (False, _('All the conditions are met')),
                (True,  _('Any condition is met')),
            ],
            use_or_choices,
        )

        self.assertIn('customfieldcondition', fields)
        self.assertIn('relationcondition',    fields)
        self.assertIn('propertycondition',    fields)

        self.assertEqual(FakeContact, fconds_f.model)

        # Step 2 (POST form) ---
        name = 'Named Kajiura'
        operator = operators.IEQUALS
        field_name = 'last_name'
        value = 'Kajiura'
        response = self.client.post(
            url,
            data={
                step_key: '1',
                '1-name': name,
                '1-use_or': 'False',
                '1-regularfieldcondition': json_dump([
                    {
                        'field':    {'name': field_name},
                        'operator': {'id': str(operator)},
                        'value':    value,
                    },
                ]),
            },
        )
        self.assertNoFormError(response)

        creds = self.get_alone_element(role.credentials.all())
        self.assertEqual(EntityCredentials.VIEW | EntityCredentials.CHANGE, creds.value)
        self.assertEqual(set_type, creds.set_type)
        self.assertEqual(ctype.id, creds.ctype_id)

        efilter = creds.efilter
        self.assertIsInstance(efilter, EntityFilter)
        self.assertEqual(name, efilter.name)
        self.assertTrue(efilter.is_custom)
        self.assertFalse(efilter.use_or)
        self.assertStartsWith(efilter.id, f'creme_core-credentials_{role.id}-')
        self.assertEqual(EF_CREDENTIALS, efilter.filter_type)

        condition = self.get_alone_element(efilter.conditions.all())
        self.assertEqual(
            condition_handler.RegularFieldConditionHandler.type_id,
            condition.type,
        )
        self.assertEqual(field_name, condition.name)
        self.assertDictEqual(
            {'operator': operator, 'values': [value]},
            condition.value,
        )

    def test_add_credentials__efilter__other_conditions(self):
        """Other values (ctype, use_or, perms, forbidden...)
        + condition on custom field, relations & properties.
        """
        self.login_as_root()
        ctype = ContentType.objects.get_for_model(FakeOrganisation)

        rtype = RelationType.objects.builder(
            id='test-subject_recruited', predicate='Has recruited',
        ).symmetric(
            id='test-object_recruited', predicate='Has been recruited by',
        ).get_or_create()[0]
        ptype = CremePropertyType.objects.create(text='Is secret')
        custom_field = CustomField.objects.create(
            name='Number of agents', content_type=ctype,
            field_type=CustomField.INT,
        )

        role = self.create_role(name='CEO', allowed_apps=['creme_core'])
        url = self._build_add_creds_url(role)

        # Step 1
        set_type = SetCredentials.ESET_FILTER
        step_key = 'credentials_adding_wizard-current_step'
        response = self.client.post(
            url,
            data={
                step_key: '0',

                '0-set_type':  set_type,
                '0-ctype':     ctype.id,
                '0-forbidden': 'True',

                '0-can_view':   False,
                '0-can_change': False,
                '0-can_delete': True,
                '0-can_link':   False,
                '0-can_unlink': False,
            },
        )
        self.assertNoFormError(response)

        # Step 2
        name = 'Complex filter'
        cfield_operator = operators.GT
        cfield_value = 150
        response = self.client.post(
            url,
            data={
                step_key: '1',
                '1-name': name,
                '1-use_or': 'True',
                '1-customfieldcondition': json_dump([{
                    'field':    {'id': str(custom_field.id)},
                    'operator': {'id': str(cfield_operator)},
                    'value':    cfield_value,
                }]),
                '1-relationcondition': json_dump([
                    {'has': True, 'rtype': rtype.id, 'ctype': 0, 'entity': None},
                ]),
                '1-propertycondition': json_dump([
                    {'has': True, 'ptype': ptype.id},
                ]),
            },
        )
        self.assertNoFormError(response)

        creds = self.get_alone_element(role.credentials.all())
        self.assertEqual(EntityCredentials.DELETE, creds.value)
        self.assertEqual(set_type, creds.set_type)
        self.assertEqual(ctype.id, creds.ctype_id)

        efilter = creds.efilter
        self.assertIsNotNone(efilter)
        self.assertEqual(name, efilter.name)
        self.assertTrue(efilter.use_or)

        conditions = efilter.conditions.all()
        self.assertEqual(3, len(conditions))

        condition1 = conditions[0]
        self.assertEqual(
            condition_handler.CustomFieldConditionHandler.type_id,
            condition1.type,
        )
        self.assertEqual(str(custom_field.uuid), condition1.name)
        self.assertDictEqual(
            {
                'operator': cfield_operator,
                'rname':    'customfieldinteger',
                'values':   [str(cfield_value)],
            },
            condition1.value,
        )

        condition2 = conditions[1]
        self.assertEqual(
            condition_handler.RelationConditionHandler.type_id,
            condition2.type,
        )
        self.assertEqual(rtype.id,      condition2.name)
        self.assertEqual({'has': True}, condition2.value)

        condition3 = conditions[2]
        self.assertEqual(
            condition_handler.PropertyConditionHandler.type_id,
            condition3.type,
        )
        self.assertEqual(str(ptype.uuid), condition3.name)
        self.assertDictEqual({'has': True}, condition3.value)

    def test_add_credentials__efilter__no_ctype(self):
        "Filter without specific ContentType."
        self.login_as_root()

        role = self.create_role(name='CEO', allowed_apps=['creme_core'])
        url = self._build_add_creds_url(role)

        # Step 1 ---
        set_type = SetCredentials.ESET_FILTER
        step_key = 'credentials_adding_wizard-current_step'
        response = self.client.post(
            url,
            data={
                step_key: '0',

                '0-set_type':  set_type,
                # '0-ctype':     0,
                '0-forbidden': 'False',

                '0-can_view':   True,
                '0-can_change': True,
                '0-can_delete': True,
                '0-can_link':   False,
                '0-can_unlink': False,
            },
        )
        self.assertNoFormError(response)

        # Step 2 ---
        with self.assertNoException():
            fields = response.context['form'].fields
            fconds_f = fields['regularfieldcondition']

        self.assertIn('use_or',            fields)
        self.assertIn('relationcondition', fields)
        self.assertIn('propertycondition', fields)

        self.assertEqual(CremeEntity, fconds_f.model)

        self.assertNotIn('customfieldcondition', fields)

        # Step 2 (POST form) ---
        name = 'My entities'
        operator = operators.EQUALS
        field_name = 'user'
        value = operands.CurrentUserOperand.type_id
        response = self.client.post(
            url,
            data={
                step_key: '1',
                '1-name': name,
                '1-use_or': 'False',
                '1-regularfieldcondition': json_dump([{
                    'field':    {'name': field_name},
                    'operator': {'id': str(operator)},
                    'value':    value,
                }]),
            },
        )
        self.assertNoFormError(response)

        creds = self.get_alone_element(role.credentials.all())
        self.assertEqual(
            EntityCredentials.VIEW | EntityCredentials.CHANGE | EntityCredentials.DELETE,
            creds.value,
        )
        self.assertEqual(set_type, creds.set_type)
        self.assertIsNone(creds.ctype_id)

        efilter = creds.efilter
        self.assertIsInstance(efilter, EntityFilter)

        condition = self.get_alone_element(efilter.conditions.all())
        self.assertEqual(
            condition_handler.RegularFieldConditionHandler.type_id,
            condition.type,
        )
        self.assertEqual(field_name, condition.name)
        self.assertDictEqual(
            {'operator': operator, 'values': [value]},
            condition.value,
        )

    def test_add_credentials__efilter__no_condition(self):
        "No condition => error."
        self.login_as_root()

        role = self.create_role(name='CEO', allowed_apps=['creme_core'])
        url = self._build_add_creds_url(role)

        # Step 1
        ctype = ContentType.objects.get_for_model(FakeOrganisation)
        set_type = SetCredentials.ESET_FILTER
        step_key = 'credentials_adding_wizard-current_step'
        response = self.client.post(
            url,
            data={
                step_key: '0',

                '0-set_type':  set_type,
                '0-ctype':     ctype.id,
                '0-forbidden': 'False',

                '0-can_view':   True,
                '0-can_change': False,
                '0-can_delete': False,
                '0-can_link':   False,
                '0-can_unlink': False,
            },
        )
        self.assertNoFormError(response)

        # Step 2
        response = self.assertPOST200(
            url,
            data={
                step_key: '1',
                '1-name': 'Empty filter',
                '1-use_or': 'False',
            },
        )
        self.assertFormError(
            response.context['wizard']['form'],
            field=None,
            errors=_('The filter must have at least one condition.'),
        )

    @skipIfNotInstalled('creme.persons')
    @skipIfNotInstalled('creme.activities')
    def test_edit_credentials(self):
        # self.login_as_root()
        self.login_with_role_perm()

        role = self.create_role(name='CEO', allowed_apps=['persons'])
        creds = SetCredentials.objects.create(
            role=role, set_type=SetCredentials.ESET_ALL, value=EntityCredentials.VIEW,
        )

        url = reverse('creme_config__edit_role_credentials', args=(creds.id,))
        response = self.assertGET200(url)
        self.assertTemplateUsed(response, 'creme_core/generics/blockform/edit-wizard-popup.html')

        context = response.context
        self.assertEqual(
            _('Edit credentials for «{role}»').format(role=role),
            context.get('title'),
        )
        self.assertEqual(_('Next step'), context.get('submit_label'))

        with self.assertNoException():
            cred_ctypes = {*context['form'].fields['ctype'].ctypes}

        get_ct = ContentType.objects.get_for_model
        ct_contact = get_ct(Contact)

        self.assertIn(ct_contact, cred_ctypes)
        self.assertIn(get_ct(Organisation), cred_ctypes)
        self.assertNotIn(get_ct(Activity), cred_ctypes)  # App not allowed

        # POST (step 1) ---
        set_type = SetCredentials.ESET_OWN
        step_key = 'credentials_edition_wizard-current_step'
        response = self.client.post(
            url,
            data={
                step_key: '0',

                '0-set_type':  set_type,
                '0-ctype':     ct_contact.id,
                '0-forbidden': 'True',

                '0-can_view':   True,
                '0-can_change': True,
                '0-can_delete': True,
                '0-can_link':   False,
                '0-can_unlink': False,
            },
        )
        self.assertNoFormError(response)

        with self.assertNoException():
            context = response.context
            submit_label2 = context['submit_label']
            fields2 = context['form'].fields
            label_field = fields2['no_filter_label']

        self.assertEqual(_('Save the modifications'), submit_label2)

        self.assertEqual(1, len(fields2))
        self.assertIsInstance(label_field, CharField)
        self.assertIsInstance(label_field.widget, Label)
        self.assertEqual(_('Conditions'), label_field.label)
        self.assertEqual(
            _('No filter, no condition.'),
            label_field.initial,
        )

        # POST (step 2) ---
        response = self.client.post(
            url,
            data={
                step_key: '1',
                # '1-use_or': 0,
            },
        )
        self.assertNoFormError(response)

        creds = self.refresh(creds)
        self.assertEqual(
            EntityCredentials.VIEW | EntityCredentials.CHANGE | EntityCredentials.DELETE,
            creds.value
        )
        self.assertEqual(set_type,      creds.set_type)
        self.assertEqual(ct_contact.id, creds.ctype_id)
        self.assertTrue(creds.forbidden)

    def test_edit_credentials__not_super_user(self):
        "No role permission => error."
        # self.login_not_as_superuser()
        self.login_without_role_perm()
        role = self.create_role(name='CEO')
        creds = SetCredentials.objects.create(
            role=role, set_type=SetCredentials.ESET_ALL, value=EntityCredentials.VIEW,
        )
        self.assertGET403(reverse('creme_config__edit_role_credentials', args=(creds.id,)))

    def test_edit_credentials__efilter__add(self):
        "Add filter."
        self.login_as_root()

        role = self.create_role(name='CEO', allowed_apps=['creme_core'])
        creds = SetCredentials.objects.create(
            role=role, set_type=SetCredentials.ESET_ALL,
            value=EntityCredentials.VIEW, ctype=FakeContact,
        )

        url = reverse('creme_config__edit_role_credentials', args=(creds.id,))

        # POST (step 1) ---
        set_type = SetCredentials.ESET_FILTER
        step_key = 'credentials_edition_wizard-current_step'
        response = self.client.post(
            url,
            data={
                step_key: '0',

                '0-set_type':  set_type,
                '0-ctype':     creds.ctype_id,
                '0-forbidden': 'True',

                '0-can_view':   True,
                '0-can_change': False,
                '0-can_delete': False,
                '0-can_link':   False,
                '0-can_unlink': False,
            },
        )
        self.assertNoFormError(response)

        # POST (step 2) ---
        with self.assertNoException():
            fields = response.context['form'].fields
            use_or_choices = fields['use_or'].choices
            fconds_f = fields['regularfieldcondition']

        self.assertListEqual(
            [
                (False, _('All the conditions are met')),
                (True,  _('Any condition is met')),
            ],
            use_or_choices,
        )

        self.assertIn('customfieldcondition', fields)
        self.assertIn('relationcondition',    fields)
        self.assertIn('propertycondition',    fields)

        self.assertEqual(FakeContact, fconds_f.model)

        # Step 2 (POST form) ---
        name = 'Named "Kajiura"'
        operator = operators.IEQUALS
        field_name = 'last_name'
        value = 'Kajiura'
        response = self.client.post(
            url,
            data={
                step_key: '1',
                '1-name': name,
                '1-use_or': 'True',
                '1-regularfieldcondition': json_dump([
                    {
                        'field':    {'name': field_name},
                        'operator': {'id': str(operator)},
                        'value':    value,
                    },
                ]),
            },
        )
        self.assertNoFormError(response)

        efilter = self.get_alone_element(role.credentials.all()).efilter
        self.assertIsInstance(efilter, EntityFilter)
        self.assertEqual(name, efilter.name)
        self.assertTrue(efilter.use_or)
        self.assertStartsWith(efilter.id, f'creme_core-credentials_{role.id}-')
        self.assertEqual(EF_CREDENTIALS, efilter.filter_type)

        condition = self.get_alone_element(efilter.conditions.all())
        self.assertEqual(
            condition_handler.RegularFieldConditionHandler.type_id,
            condition.type,
        )
        self.assertEqual('last_name', condition.name)
        self.assertDictEqual(
            {'operator': operator, 'values': [value]},
            condition.value,
        )

    def test_edit_credentials__efilter__edit_conditions(self):
        "Change filter conditions + conditions on CustomField/Relation/CremeProperty."
        self.login_as_root()

        rtype = RelationType.objects.builder(
            id='test-subject_recruited', predicate='Has been recruited',
        ).symmetric(
            id='test-object_recruited', predicate='Has recruited by',
        ).get_or_create()[0]
        ptype = CremePropertyType.objects.create(text='Is nice')
        custom_field = CustomField.objects.create(
            name='Number of ties', content_type=FakeContact,
            field_type=CustomField.INT,
        )

        role = self.create_role(name='CEO', allowed_apps=['creme_core'])
        efilter1 = EntityFilter.objects.create(
            id='creme_core-test_credentials_edition02',
            name='Agencies',
            entity_type=FakeContact,
            filter_type=EF_CREDENTIALS,
            use_or=True,
        ).set_conditions(
            [
                condition_handler.RegularFieldConditionHandler.build_condition(
                    model=FakeContact,
                    operator=operators.ISTARTSWITH,
                    field_name='last_name', values=['Agency of'],
                    filter_type=EF_CREDENTIALS,
                ),
            ],
            check_cycles=False,   # There cannot be a cycle without sub-filter.
            check_privacy=False,  # No sense here.
        )

        set_cred1 = SetCredentials.objects.create(
            role=role,
            set_type=SetCredentials.ESET_FILTER,
            value=EntityCredentials.VIEW,
            ctype=FakeContact,
            efilter=efilter1,
        )

        url = reverse('creme_config__edit_role_credentials', args=(set_cred1.id,))

        # POST (step 1) ---
        step_key = 'credentials_edition_wizard-current_step'
        response = self.client.post(
            url,
            data={
                step_key: '0',

                '0-set_type':  set_cred1.set_type,
                '0-ctype':     set_cred1.ctype_id,
                '0-forbidden': 'False',

                '0-can_view':   True,
                '0-can_change': False,
                '0-can_delete': False,
                '0-can_link':   False,
                '0-can_unlink': False,
            },
        )
        self.assertNoFormError(response)

        # Step 2 ---
        with self.assertNoException():
            fields = response.context['form'].fields
            name_f = fields['name']
            use_or_f = fields['use_or']
            fconds_f  = fields['regularfieldcondition']
            cfconds_f = fields['customfieldcondition']

        self.assertEqual(efilter1.name,   name_f.initial)
        self.assertEqual(efilter1.use_or, use_or_f.initial)

        self.assertEqual(FakeContact, fconds_f.model)
        self.assertEqual(efilter1.get_conditions(), fconds_f.initial)

        self.assertEqual(FakeContact, cfconds_f.model)
        self.assertIsNone(cfconds_f.initial)

        # Step 2 (POST form) ---
        name = efilter1.name + ' edited'
        cfield_operator = operators.GT
        cfield_value = 150
        response = self.client.post(
            url,
            data={
                step_key: '1',
                '1-name': name,
                '1-use_or': 'False',
                '1-customfieldcondition': json_dump([{
                    'field':    {'id': str(custom_field.id)},
                    'operator': {'id': str(cfield_operator)},
                    'value':    cfield_value,
                }]),
                '1-relationcondition': json_dump([
                    {'has': True, 'rtype': rtype.id, 'ctype': 0, 'entity': None},
                ]),
                '1-propertycondition': json_dump([
                    {'has': True, 'ptype': ptype.id},
                ]),
            },
        )
        self.assertNoFormError(response)

        set_cred2 = self.get_alone_element(role.credentials.all())
        self.assertEqual(set_cred1.ctype, set_cred2.ctype)

        efilter2 = set_cred2.efilter
        self.assertIsNotNone(efilter2)
        self.assertEqual(name, efilter2.name)
        self.assertEqual(set_cred1.ctype, efilter2.entity_type)
        self.assertFalse(efilter2.use_or)
        self.assertEqual(EF_CREDENTIALS, efilter2.filter_type)
        self.assertEqual(efilter1.id,            efilter2.id)

        conditions = efilter2.conditions.all()
        self.assertEqual(3, len(conditions))

        condition1 = conditions[0]
        self.assertEqual(
            condition_handler.CustomFieldConditionHandler.type_id,
            condition1.type
        )
        self.assertEqual(str(custom_field.uuid), condition1.name)
        self.assertDictEqual(
            {
                'operator': cfield_operator,
                'rname':    'customfieldinteger',
                'values':   [str(cfield_value)],
            },
            condition1.value,
        )

        condition2 = conditions[1]
        self.assertEqual(
            condition_handler.RelationConditionHandler.type_id,
            condition2.type,
        )
        self.assertEqual(rtype.id,      condition2.name)
        self.assertEqual({'has': True}, condition2.value)

        condition3 = conditions[2]
        self.assertEqual(
            condition_handler.PropertyConditionHandler.type_id,
            condition3.type,
        )
        self.assertEqual(str(ptype.uuid), condition3.name)
        self.assertEqual({'has': True}, condition3.value)

    def test_edit_credentials__efilter__change_ctype(self):
        "Change existing ctype & filter + conditions on CustomField/Relation/CremeProperty."
        self.login_as_root()

        ptype = CremePropertyType.objects.create(text='Is secret')

        role = self.create_role(name='CEO', allowed_apps=['creme_core'])
        efilter1 = EntityFilter.objects.create(
            id='creme_core-test_credentials_edition02',
            name='Agencies',
            entity_type=FakeContact,
            filter_type=EF_CREDENTIALS,
            use_or=False,
        ).set_conditions(
            [
                condition_handler.RegularFieldConditionHandler.build_condition(
                    model=FakeContact,
                    operator=operators.ISTARTSWITH,
                    field_name='last_name', values=['Agency of'],
                    filter_type=EF_CREDENTIALS,
                ),
            ],
            check_cycles=False,   # There cannot be a cycle without sub-filter.
            check_privacy=False,  # No sense here.
        )

        creds = SetCredentials.objects.create(
            role=role,
            set_type=SetCredentials.ESET_FILTER,
            value=EntityCredentials.VIEW,
            ctype=FakeContact,
            efilter=efilter1,
        )

        url = reverse('creme_config__edit_role_credentials', args=(creds.id,))

        # POST (step 1) ---
        ctype = ContentType.objects.get_for_model(FakeOrganisation)
        step_key = 'credentials_edition_wizard-current_step'
        response = self.client.post(
            url,
            data={
                step_key: '0',

                '0-set_type':  creds.set_type,
                '0-ctype':     ctype.id,
                '0-forbidden': 'True',

                '0-can_view':   True,
                '0-can_change': False,
                '0-can_delete': False,
                '0-can_link':   False,
                '0-can_unlink': False,
            },
        )
        self.assertNoFormError(response)

        # Step 2 ---
        with self.assertNoException():
            fields = response.context['form'].fields
            name_f = fields['name']
            fconds_f = fields['regularfieldcondition']

        self.assertIsNone(name_f.initial)

        self.assertEqual(FakeOrganisation, fconds_f.model)

        # Step 2 (POST form) ---
        name = 'Agencies organisations'
        response = self.client.post(
            url,
            data={
                step_key: '1',
                '1-name': name,
                '1-use_or': 'True',
                '1-propertycondition': json_dump([
                    {'has': True, 'ptype': ptype.id},
                ]),
            },
        )
        self.assertNoFormError(response)

        setcred = self.get_alone_element(role.credentials.all())
        self.assertEqual(ctype, setcred.ctype)

        efilter2 = setcred.efilter
        self.assertIsNotNone(efilter2)
        self.assertEqual(name, efilter2.name)
        self.assertEqual(ctype, efilter2.entity_type)
        self.assertTrue(efilter2.use_or)
        self.assertEqual(EF_CREDENTIALS, efilter2.filter_type)
        self.assertEqual(efilter1.id, efilter2.id)

        condition = self.get_alone_element(efilter2.conditions.all())
        self.assertEqual(
            condition_handler.PropertyConditionHandler.type_id,
            condition.type,
        )
        self.assertEqual(str(ptype.uuid), condition.name)
        self.assertEqual({'has': True}, condition.value)

    def test_edit_credentials__efilter__remove(self):
        "Remove filter if no more needed."
        self.login_as_root()

        role = self.create_role(name='CEO', allowed_apps=['creme_core'])

        efilter = EntityFilter.objects.create(
            id='creme_config-test_user_role',
            entity_type=FakeContact,
            filter_type=EF_CREDENTIALS,
        ).set_conditions(
            [
                condition_handler.RegularFieldConditionHandler.build_condition(
                    model=FakeContact,
                    operator=operators.EQUALS,
                    field_name='last_name', values=['Agent#'],
                    filter_type=EF_CREDENTIALS,
                ),
            ],
            check_cycles=False,  # There cannot be a cycle without sub-filter.
            check_privacy=False,  # No sense here.
        )
        cond_ids = [cond.id for cond in efilter.get_conditions()]

        creds = SetCredentials.objects.create(
            role=role,
            set_type=SetCredentials.ESET_FILTER,
            value=EntityCredentials.VIEW,
            efilter=efilter,
            ctype=FakeContact,
        )

        url = reverse('creme_config__edit_role_credentials', args=(creds.id,))

        # POST (step 1) ---
        set_type = SetCredentials.ESET_ALL
        step_key = 'credentials_edition_wizard-current_step'
        response = self.client.post(
            url,
            data={
                step_key: '0',

                '0-set_type':  set_type,
                '0-ctype':     creds.ctype_id,
                '0-forbidden': 'True',

                '0-can_view':   True,
            },
        )
        self.assertNoFormError(response)
        self.assertListEqual(
            ['no_filter_label'], [*self.get_form_or_fail(response).fields.keys()],
        )

        # POST (step 2) ---
        response = self.client.post(url, data={step_key: '1'})
        self.assertNoFormError(response)

        creds = self.refresh(creds)
        self.assertIsNone(creds.efilter)
        self.assertEqual(set_type, creds.set_type)

        self.assertDoesNotExist(efilter)
        self.assertFalse(EntityFilterCondition.objects.filter(id__in=cond_ids))

    def test_edit_credentials__efilter__ctype_entity(self):
        "Content type is CremeEntity."
        self.login_as_root()
        ptype = CremePropertyType.objects.create(text='Is secret')

        role = self.create_role(name='CEO', allowed_apps=['creme_core'])
        efilter1 = EntityFilter.objects.create(
            id='creme_core-test_credentials_edition04',
            name='My entities',
            entity_type=CremeEntity,
            filter_type=EF_CREDENTIALS,
        ).set_conditions(
            [
                condition_handler.RegularFieldConditionHandler.build_condition(
                    model=CremeEntity,
                    operator=operators.ICONTAINS,
                    field_name='description', values=['Important'],
                    filter_type=EF_CREDENTIALS,
                ),
            ],
            check_cycles=False,  # There cannot be a cycle without sub-filter.
            check_privacy=False,  # No sense here.
        )

        creds = SetCredentials.objects.create(
            role=role,
            set_type=SetCredentials.ESET_FILTER,
            value=EntityCredentials.VIEW,
            efilter=efilter1,
        )

        url = reverse('creme_config__edit_role_credentials', args=(creds.id,))

        # POST (step 1) ---
        step_key = 'credentials_edition_wizard-current_step'
        response = self.client.post(
            url,
            data={
                step_key: '0',

                '0-set_type':  creds.set_type,
                # '0-ctype':     0,
                '0-forbidden': 'True',

                '0-can_view':   True,
                '0-can_change': True,
                '0-can_link':   True,
            },
        )
        self.assertNoFormError(response)

        # Step 2 ---
        with self.assertNoException():
            fields = response.context['form'].fields
            name_f = fields['name']
            fconds_f = fields['regularfieldcondition']

        self.assertIn('use_or',            fields)
        self.assertIn('relationcondition', fields)
        self.assertIn('propertycondition', fields)

        self.assertNotIn('customfieldcondition', fields)

        self.assertEqual(efilter1.name, name_f.initial)

        self.assertEqual(CremeEntity, fconds_f.model)
        self.assertEqual(efilter1.get_conditions(), fconds_f.initial)

        # Step 2 (POST form) ---
        name = 'My secret entities'
        self.assertNoFormError(self.client.post(
            url,
            data={
                step_key: '1',
                '1-name': name,
                '1-use_or': 'True',
                '1-propertycondition': json_dump([{'has': True, 'ptype': ptype.id}]),
            },
        ))

        setcreds = self.get_alone_element(role.credentials.all())
        self.assertIsNone(setcreds.ctype)

        efilter2 = setcreds.efilter
        self.assertIsNotNone(efilter2)
        self.assertEqual(
            ContentType.objects.get_for_model(CremeEntity),
            efilter2.entity_type,
        )
        self.assertEqual(name, efilter2.name)
        self.assertTrue(efilter2.use_or)

        condition = self.get_alone_element(efilter2.conditions.all())
        self.assertEqual(
            condition_handler.PropertyConditionHandler.type_id,
            condition.type,
        )
        self.assertEqual(str(ptype.uuid), condition.name)
        self.assertEqual({'has': True}, condition.value)

    def test_edit_credentials__efilter__add_on_entity(self):
        "Add filter to CremeEntity."
        self.login_as_root()

        role = self.create_role(name='CEO', allowed_apps=['creme_core'])
        creds = SetCredentials.objects.create(
            role=role,
            set_type=SetCredentials.ESET_ALL,
            value=EntityCredentials.VIEW,
            ctype=FakeContact,
        )

        url = reverse('creme_config__edit_role_credentials', args=(creds.id,))

        # POST (step 1) ---
        set_type = SetCredentials.ESET_FILTER
        step_key = 'credentials_edition_wizard-current_step'
        response = self.client.post(
            url,
            data={
                step_key: '0',

                '0-set_type':  set_type,
                # '0-ctype':     0,
                '0-forbidden': 'True',

                '0-can_view':   True,
            },
        )
        self.assertNoFormError(response)

        # Step 2 (POST form) ---
        name = 'My entities'
        operator = operators.EQUALS
        field_name = 'user'
        value = operands.CurrentUserOperand.type_id
        response = self.client.post(
            url,
            data={
                step_key: '1',
                '1-name': name,
                '1-use_or': 'False',
                '1-regularfieldcondition': json_dump([{
                    'field':    {'name': field_name},
                    'operator': {'id': str(operator)},
                    'value':    value,
                }]),
            },
        )
        self.assertNoFormError(response)

        efilter = self.get_alone_element(role.credentials.all()).efilter
        self.assertEqual(name, efilter.name)
        self.assertEqual(
            ContentType.objects.get_for_model(CremeEntity),
            efilter.entity_type,
        )

        condition = self.get_alone_element(efilter.conditions.all())
        self.assertEqual(
            condition_handler.RegularFieldConditionHandler.type_id,
            condition.type,
        )
        self.assertEqual(field_name, condition.name)
        self.assertDictEqual(
            {'operator': operator, 'values': [value]}, condition.value,
        )

    def test_edit_credentials__efilter__entity_to_child(self):
        "From CremeEntity to child class => keep information as initial."
        self.login_as_root()

        role = self.create_role(name='CEO', allowed_apps=['creme_core'])
        efilter1 = EntityFilter.objects.create(
            id='creme_core-test_credentials_edition04',
            name='My entities',
            entity_type=CremeEntity,
            filter_type=EF_CREDENTIALS,
        ).set_conditions(
            [
                condition_handler.RegularFieldConditionHandler.build_condition(
                    model=CremeEntity,
                    operator=operators.ICONTAINS,
                    field_name='description', values=['Important'],
                    filter_type=EF_CREDENTIALS,
                ),
            ],
            check_cycles=False,  # There cannot be a cycle without sub-filter.
            check_privacy=False,  # No sense here.
        )

        creds = SetCredentials.objects.create(
            role=role,
            set_type=SetCredentials.ESET_FILTER,
            value=EntityCredentials.VIEW,
            efilter=efilter1,
        )

        url = reverse('creme_config__edit_role_credentials', args=(creds.id,))

        # POST (step 1) ---
        ctype = ContentType.objects.get_for_model(FakeContact)
        step_key = 'credentials_edition_wizard-current_step'
        response = self.client.post(
            url,
            data={
                step_key: '0',

                '0-set_type':  creds.set_type,
                '0-ctype':     ctype.id,
                '0-forbidden': 'True',

                '0-can_view':   True,
                '0-can_change': True,
                '0-can_link':   True,
            },
        )
        self.assertNoFormError(response)

        # Step 2 ---
        with self.assertNoException():
            fields = response.context['form'].fields
            name_f = fields['name']
            fconds_f = fields['regularfieldcondition']

        self.assertEqual(efilter1.name, name_f.initial)

        self.assertEqual(FakeContact, fconds_f.model)
        self.assertEqual(efilter1.get_conditions(), fconds_f.initial)

    def test_delete_credentials(self):
        # self.login_as_root()
        self.login_with_role_perm()

        role = self.create_role(name='CEO', allowed_apps=['persons'])

        create_creds = partial(
            SetCredentials.objects.create,
            role=role, set_type=SetCredentials.ESET_ALL,
        )
        sc1 = create_creds(value=EntityCredentials.VIEW)
        sc2 = create_creds(value=EntityCredentials.CHANGE)

        url = self.DEL_CREDS_URL
        self.assertGET405(url)
        self.assertPOST404(url)
        self.assertPOST200(url, data={'id': sc1.id})

        self.assertDoesNotExist(sc1)
        self.assertStillExists(sc2)

    def test_delete_credentials__forbidden(self):
        # self.login_not_as_superuser()
        self.login_without_role_perm()

        role = self.create_role(name='CEO')
        sc = SetCredentials.objects.create(
            role=role, set_type=SetCredentials.ESET_ALL, value=EntityCredentials.VIEW,
        )
        self.assertPOST403(self.DEL_CREDS_URL, data={'id': sc.id})

    @skipIfNotInstalled('creme.persons')
    @skipIfNotInstalled('creme.documents')
    @skipIfNotInstalled('creme.activities')
    def test_edition(self):
        # self.login_as_root()
        self.login_with_role_perm()

        role = self.create_role(
            name='CEO', allowed_apps=['persons'], listable_models=[Contact],
            special_permissions=[user_config_perm],
        )
        SetCredentials.objects.create(
            role=role, value=EntityCredentials.VIEW, set_type=SetCredentials.ESET_ALL,
        )

        name = role.name + ' edited'
        apps = ['persons', 'documents']
        adm_apps = ['persons']

        url = self._build_wizard_edit_url(role)

        # Step 1 (name, apps) ---
        response1 = self.assertGET200(url)
        self.assertTemplateUsed(
            response1, 'creme_core/generics/blockform/edit-wizard-popup.html',
        )

        context1 = response1.context
        self.assertEqual(_('Next step'), context1.get('submit_label'))

        with self.assertNoException():
            app_labels = context1['form'].fields['allowed_apps'].choices

        self.assertInChoices(
            value=apps[0], label=_('Accounts and Contacts'), choices=app_labels,
        )
        self.assertInChoices(
            value=apps[1], label=_('Documents'), choices=app_labels,
        )
        self.assertInChoices(
            value='activities', label=_('Activities'), choices=app_labels,
        )

        step_key = 'role_edition_wizard-current_step'
        response2 = self.client.post(
            url,
            data={
                step_key: '0',
                '0-name': name,
                '0-allowed_apps': apps,
            },
        )
        self.assertNoFormError(response2)

        # Step 2 (administrated app) ---
        with self.assertNoException():
            adm_app_labels = response2.context['form'].fields['admin_4_apps'].choices

        self.assertInChoices(
            value=apps[0], label=_('Accounts and Contacts'), choices=adm_app_labels,
        )
        self.assertInChoices(
            value=apps[1], label=_('Documents'), choices=adm_app_labels,
        )
        self.assertNotInChoices(value='activities', choices=adm_app_labels)

        response3 = self.client.post(
            url,
            data={
                step_key: '1',
                '1-admin_4_apps': adm_apps,
            },
        )
        self.assertNoFormError(response3)

        # Step 3 (creatable models) ---
        with self.assertNoException():
            creatable_ctypes = {*response3.context['form'].fields['creatable_ctypes'].ctypes}

        get_ct = ContentType.objects.get_for_model
        ct_contact = get_ct(Contact)
        ct_orga = get_ct(Organisation)
        ct_doc = get_ct(Document)

        self.assertIn(ct_contact, creatable_ctypes)
        self.assertIn(ct_orga, creatable_ctypes)
        self.assertNotIn(get_ct(Address), creatable_ctypes)  # Not CremeEntity
        self.assertIn(ct_doc, creatable_ctypes)
        self.assertNotIn(get_ct(Activity), creatable_ctypes)  # App not allowed

        response4 = self.client.post(
            url,
            data={
                step_key: '2',
                '2-creatable_ctypes': [ct_contact.id, ct_doc.id],
            },
        )
        self.assertNoFormError(response4)

        # Step 4 (listable models) ---
        context4 = response4.context

        with self.assertNoException():
            form4 = context4['form']
            listable_ctypes = form4.fields['listable_ctypes'].ctypes

        self.assertIn(ct_contact, listable_ctypes)
        self.assertIn(ct_orga, listable_ctypes)
        self.assertNotIn(get_ct(Address), listable_ctypes)  # Not CremeEntity
        self.assertIn(ct_doc, listable_ctypes)
        self.assertNotIn(get_ct(Activity), listable_ctypes)  # App not allowed

        self.assertListEqual([ct_contact], form4.initial.get('listable_ctypes'))

        response5 = self.client.post(
            url, data={step_key: '3', '3-listable_ctypes': [ct_orga.id]},
        )
        self.assertNoFormError(response5)

        # Step 5 (exportable models) ---
        context5 = response5.context
        # self.assertEqual(_('Save the modifications'), context5.get('submit_label'))

        with self.assertNoException():
            exp_ctypes = context5['form'].fields['exportable_ctypes'].ctypes

        self.assertIn(ct_contact, exp_ctypes)
        self.assertIn(ct_orga, exp_ctypes)
        self.assertNotIn(get_ct(Address), exp_ctypes)  # Not CremeEntity
        self.assertIn(ct_doc, exp_ctypes)
        self.assertNotIn(get_ct(Activity), exp_ctypes)  # App not allowed

        response6 = self.client.post(
            url, data={step_key: '4', '4-exportable_ctypes': [ct_contact.id]},
        )
        self.assertNoFormError(response6)

        # Step 6 (special permissions) ---
        context6 = response6.context
        self.assertEqual(_('Save the modifications'), context6.get('submit_label'))

        with self.assertNoException():
            perms_f = context6['form'].fields['special_perms']
            perms_choices = perms_f.choices

        self.assertInChoices(
            value=user_config_perm.id,
            label=user_config_perm.verbose_name,
            choices=perms_choices,
        )
        self.assertInChoices(
            value=role_config_perm.id,
            label=role_config_perm.verbose_name,
            choices=perms_choices,
        )
        self.assertListEqual([user_config_perm.id], [*perms_f.initial])

        self.assertNoFormError(self.client.post(
            url, data={step_key: '5', '5-special_perms': [role_config_perm.id]},
        ))

        role = self.refresh(role)
        self.assertEqual(name, role.name)
        self.assertSetEqual({*apps},     role.allowed_apps)
        self.assertSetEqual({*adm_apps}, role.admin_4_apps)

        self.assertCountEqual([ct_contact, ct_doc], role.creatable_ctypes.all())
        self.assertCountEqual([ct_orga],            role.listable_ctypes.all())
        self.assertCountEqual([ct_contact],         role.exportable_ctypes.all())
        self.assertEqual(1, role.credentials.count())

        self.assertListEqual([role_config_perm], [*role.special_permissions.values()])

    # def test_edition__not_superuser(self):
    def test_edition__forbidden(self):
        # self.login_not_as_superuser()
        self.login_without_role_perm()

        role = self.create_role(name='CEO')
        self.assertGET403(self._build_wizard_edit_url(role))

    def test_delete__forbidden(self):
        "No role permission -> error."
        # self.login_not_as_superuser()
        self.login_without_role_perm()

        role = self.create_role(name='Test')
        url = self._build_del_role_url(role)
        self.assertGET403(url)
        self.assertPOST403(url)

    def test_delete__role_not_used(self):
        "Role is not used."
        # user = self.login_as_root_and_get()
        user = self.login_with_role_perm()

        role = self.create_role(name='CEO')
        creds = SetCredentials.objects.create(
            role=role, set_type=SetCredentials.ESET_ALL, value=EntityCredentials.VIEW,
        )

        url = self._build_del_role_url(role)
        response1 = self.assertGET200(url)
        self.assertTemplateUsed(response1, 'creme_core/generics/blockform/delete-popup.html')

        context = response1.context
        self.assertEqual(
            _('Delete role «{object}»').format(object=role), context.get('title')
        )
        self.assertEqual(_('Delete the role'), context.get('submit_label'))

        with self.assertNoException():
            fields = context['form'].fields
            info_f = fields['info']

        self.assertFalse(info_f.required)
        self.assertNotIn('to_role', fields)

        response2 = self.client.post(url)
        self.assertNoFormError(response2)
        self.assertTemplateUsed(response2, 'creme_config/deletion-job-popup.html')

        dcom = self.get_deletion_command_or_fail(UserRole)
        self.assertEqual(role,      dcom.instance_to_delete)
        self.assertEqual(role.name, dcom.deleted_repr)
        self.assertFalse(dcom.replacers)
        self.assertEqual(0, dcom.total_count)
        self.assertEqual(0, dcom.updated_count)

        job = dcom.job
        self.assertEqual(deletor_type.id, job.type_id)
        self.assertEqual(user, job.user)

        deletor_type.execute(job)
        self.assertDoesNotExist(role)
        self.assertDoesNotExist(creds)

    def test_delete__replace_by_another_one(self):
        "To replace by another role."
        self.login_as_root()
        user = self.get_root_user()

        replacing_role = self.create_role(name='CEO')
        role_to_delete = self.create_role(name='CEO (old)')
        other_role = self.create_role(name='Coder')
        second_role = self.create_role(name='Engineer')
        # Role is used
        user_to_update1 = self.create_user(
            index=0, role=role_to_delete, roles=[role_to_delete, second_role],
        )
        user_to_update2 = self.create_user(
            index=1, role=other_role, roles=[other_role, role_to_delete, replacing_role],
        )

        url = self._build_del_role_url(role_to_delete)
        response = self.assertGET200(url)

        with self.assertNoException():
            fields = response.context['form'].fields
            choices = [*fields['to_role'].choices]

        self.assertNotIn('info', fields)

        self.assertInChoices(value=replacing_role.id, label=str(replacing_role), choices=choices)
        self.assertInChoices(value=other_role.id,     label=str(other_role),     choices=choices)
        self.assertNotInChoices(value=role_to_delete.id, choices=choices)

        response = self.client.post(url, data={'to_role': replacing_role.id})
        self.assertNoFormError(response)

        dcom = self.get_deletion_command_or_fail(UserRole)
        self.assertEqual(role_to_delete,      dcom.instance_to_delete)
        self.assertEqual(role_to_delete.name, dcom.deleted_repr)
        self.assertListEqual(
            [
                ('fixed_value', user.__class__, 'role',  replacing_role),
                ('fixed_value', user.__class__, 'roles', replacing_role),
            ],
            [
                (r.type_id, r.model_field.model, r.model_field.name, r.get_value())
                for r in dcom.replacers
            ],
        )
        self.assertEqual(2, dcom.total_count)
        self.assertEqual(0, dcom.updated_count)

        job = dcom.job
        self.assertEqual(deletor_type.id, job.type_id)
        self.assertEqual(user, job.user)

        deletor_type.execute(job)
        self.assertDoesNotExist(role_to_delete)

        user_to_update1 = self.refresh(user_to_update1)
        self.assertEqual(replacing_role, user_to_update1.role)
        self.assertCountEqual([replacing_role, second_role], user_to_update1.roles.all())

        user_to_update2 = self.refresh(user_to_update2)
        self.assertEqual(other_role, user_to_update2.role)
        self.assertCountEqual([other_role, replacing_role], user_to_update2.roles.all())

    def test_delete__replacing_required__fk(self):
        "Role is used (user.role) -> replacing role is required."
        self.login_as_root()

        role = self.create_role(name='CEO')
        CremeUser.objects.create(username='chloe', role=role)  # <= role is used

        response = self.assertPOST200(self._build_del_role_url(role))
        self.assertFormError(
            self.get_form_or_fail(response),
            field='to_role', errors=_('This field is required.'),
        )

    def test_delete__replacing_required__m2m(self):
        "Role is used (user.roles only) -> replacing role is required."
        self.login_as_root()

        main_role = self.create_role(name='CEO')
        second_role = self.create_role(name='Coder')
        self.create_user(role=main_role, roles=[main_role, second_role])

        response = self.assertPOST200(self._build_del_role_url(second_role))
        self.assertFormError(
            self.get_form_or_fail(response),
            field='to_role', errors=_('This field is required.'),
        )

    def test_delete__uniqueness(self):
        self.login_as_root()
        user = self.get_root_user()
        self.assertFalse(DeletionCommand.objects.first())

        job = Job.objects.create(type_id=deletor_type.id, user=user)
        self.assertEqual(Job.STATUS_WAIT, job.status)

        role_2_del1 = self.create_role(name='CEO')
        dcom = DeletionCommand.objects.create(
            job=job,
            instance_to_delete=role_2_del1,
        )

        role_2_del2 = self.create_role(name='Coder')
        url = self._build_del_role_url(role_2_del2)

        msg = _('A deletion process for a role already exists.')
        self.assertContains(self.client.get(url), msg, status_code=409)

        # ---
        job.status = Job.STATUS_ERROR
        job.save()
        self.assertContains(self.client.get(url), msg, status_code=409)

        # ---
        job.status = Job.STATUS_OK
        job.save()
        response = self.assertGET200(url)
        self.assertIn('form', response.context)
        self.assertDoesNotExist(job)
        self.assertDoesNotExist(dcom)

    def test_activation__role_not_used(self):
        self.login_with_role_perm()

        other_role = self.create_role(name='Deprecated')
        self.assertIsNone(other_role.deactivated_on)

        # ---
        build_url = self._build_activation_url
        deactivation_url = build_url(other_role.id, activation=False)
        self.assertGET405(deactivation_url)
        self.assertPOST200(deactivation_url)
        self.assertDatetimesAlmostEqual(self.refresh(other_role).deactivated_on, now())

        # ---
        activation_url = build_url(other_role.id, activation=True)
        self.assertGET405(activation_url)
        self.assertPOST200(activation_url)
        self.assertIsNone(self.refresh(other_role).deactivated_on)

    def test_activation__forbidden(self):
        "No role special perm => error."
        self.login_without_role_perm()
        other_role = self.create_role(name='Deprecated')
        self.assertPOST403(self._build_activation_url(other_role.id, activation=False))
        self.assertPOST403(self._build_activation_url(other_role.id, activation=True))

    def test_deactivation__current_role(self):
        "Current role => error."
        user = self.login_with_role_perm()
        response = self.client.post(
            self._build_activation_url(user.role_id, activation=False),
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )
        self.assertContains(
            response=response,
            status_code=409,
            text=_("You can't deactivate the role of the current user."),
        )

    def test_deactivation__role_used__no_other_active_role(self):
        self.login_as_root()

        role = self.create_role(name='Deprecated')
        user1 = self.create_user(index=0, role=role)
        deactivation_url = self._build_activation_url(role.id, activation=False)

        # ---
        response1 = self.client.post(
            deactivation_url,
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )
        self.assertContains(
            response=response1,
            status_code=409,
            text=ngettext(
                "This role cannot be deactivated because it is used by {count} "
                "user without secondary active role to switch on: {users}.",
                "This role cannot be deactivated because it is used by {count} "
                "users without secondary active role to switch on: {users}.",
                number=1,
            ).format(count=1, users=f'«{user1}»'),
        )

        # ---
        second_role = self.create_role(name='Already deactivated', deactivated_on=now())
        user2 = self.create_user(index=1, role=role, roles=[role, second_role])

        response2 = self.client.post(
            deactivation_url,
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )
        self.assertContains(
            response=response2,
            status_code=409,
            text=ngettext(
                "This role cannot be deactivated because it is used by {count} "
                "user without secondary active role to switch on: {users}.",
                "This role cannot be deactivated because it is used by {count} "
                "users without secondary active role to switch on: {users}.",
                number=2,
            ).format(count=2, users=f'«{user1}», «{user2}»'),
        )

    def test_deactivation__role_used__other_active_role(self):
        self.login_as_root()

        main_role = self.create_role(name='Deprecated')
        second_role = self.create_role(name='Second')
        third_role = self.create_role(name='Third')
        user = self.create_user(role=main_role, roles=[main_role, second_role, third_role])

        self.assertPOST200(self._build_activation_url(main_role.id, activation=False))
        self.assertDatetimesAlmostEqual(self.refresh(main_role).deactivated_on, now())
        self.assertEqual(second_role, self.refresh(user).role)

        admin_chan = self.get_object_or_fail(NotificationChannel, uuid=UUID_CHANNEL_ADMIN)
        notif = self.get_object_or_fail(
            Notification, user=user, channel=admin_chan,
        )
        self.assertEqual(RoleSwitchContent.id, notif.content_id)
        self.assertDictEqual({}, notif.content_data)

        content = notif.content
        self.assertEqual(_('Role switch'), content.get_subject(user=user))
        body = _(
            'Your role has been switched to another role because it has been disabled.'
        )
        self.assertEqual(body, content.get_body(user=user))
        self.assertEqual(body, content.get_html_body(user=user))

    def test_clone(self):
        # self.login_as_root()
        self.login_with_role_perm()

        role1 = self.create_role(
            name='CEO',
            allowed_apps=['creme_core', 'documents', 'persons'],
            admin_4_apps=['persons'],
            creatable_models=[FakeContact, FakeDocument],
            exportable_models=[FakeContact, FakeOrganisation],
            listable_models=[FakeContact, FakeActivity],
            special_permissions=[user_config_perm],
        )

        efilter1 = EntityFilter.objects.create(
            id='creme_core-test_credentials_edition02',
            name='Agencies',
            entity_type=FakeContact,
            filter_type=EF_CREDENTIALS,
            use_or=True,
        ).set_conditions(
            [
                condition_handler.RegularFieldConditionHandler.build_condition(
                    model=FakeContact,
                    operator=operators.ISTARTSWITH,
                    field_name='last_name', values=['Agency of'],
                    filter_type=EF_CREDENTIALS,
                ),
            ],
            check_cycles=False,   # There cannot be a cycle without sub-filter.
            check_privacy=False,  # No sense here.
        )

        create_creds = partial(SetCredentials.objects.create, role=role1)
        create_creds(
            set_type=SetCredentials.ESET_OWN,
            value=EntityCredentials.VIEW,
        )
        create_creds(
            set_type=SetCredentials.ESET_FILTER,
            value=EntityCredentials.CHANGE,
            ctype=FakeContact,
            forbidden=True,
            efilter=efilter1,
        )

        url = reverse('creme_config__clone_role', args=(role1.id,))
        context1 = self.assertGET200(url).context
        self.assertEqual(
            _('Clone the role «{object}»').format(object=role1.name),
            context1.get('title'),
        )
        self.assertEqual(_('Clone'), context1.get('submit_label'))

        with self.assertNoException():
            form = context1['form']
            fields = form.fields
            name_f = fields['name']

        self.assertEqual(1, len(fields), fields)
        self.assertIsInstance(name_f, CharField)
        self.assertEqual(_('Copy of «{role}»').format(role=role1.name), name_f.initial)

        # ---
        old_count = UserRole.objects.count()
        name = 'My new role'
        self.assertNoFormError(self.client.post(url, data={'name': name}))
        self.assertEqual(old_count + 1, UserRole.objects.count())

        role2 = self.get_object_or_fail(UserRole, name=name)
        self.assertSetEqual({'creme_core', 'documents', 'persons'}, role2.allowed_apps)
        self.assertSetEqual({'persons'},                            role2.admin_4_apps)
        self.assertCountEqual(
            [FakeContact, FakeDocument],
            [ct.model_class() for ct in role2.creatable_ctypes.all()],
        )
        self.assertCountEqual(
            [FakeContact, FakeOrganisation],
            [ct.model_class() for ct in role2.exportable_ctypes.all()],
        )
        self.assertCountEqual(
            [FakeContact, FakeActivity],
            [ct.model_class() for ct in role2.listable_ctypes.all()],
        )
        self.assertListEqual([user_config_perm.id], [*role2.special_permissions])

        all_credentials = role2.credentials.order_by('id')
        self.assertEqual(2, len(all_credentials))

        creds1 = all_credentials[0]
        self.assertIsNotNone(creds1)
        self.assertEqual(EntityCredentials.VIEW, creds1.value)
        self.assertIsNone(creds1.ctype)
        self.assertFalse(creds1.forbidden)
        self.assertIsNone(creds1.efilter)

        creds2 = all_credentials[1]
        self.assertIsNotNone(creds2)
        self.assertEqual(EntityCredentials.CHANGE, creds2.value)
        self.assertEqual(ContentType.objects.get_for_model(FakeContact), creds2.ctype)
        self.assertTrue(creds2.forbidden)

        efilter2 = creds2.efilter
        self.assertIsNotNone(efilter2)
        self.assertNotEqual(efilter1.id, efilter2.id)
        self.assertEqual(efilter1.name,  efilter2.name)
        self.assertEqual(EF_CREDENTIALS, efilter2.filter_type)
        self.assertEqual(1, efilter2.conditions.count())

    def test_clone__detail_brick_config__no_copy(self):
        self.login_as_root()
        role1 = self.create_role(name='Test')

        BrickDetailviewLocation.objects.multi_create(
            defaults={
                'model': FakeContact,
                'zone': BrickDetailviewLocation.LEFT,
                'role': role1,
            },
            data=[
                {'order': 5},
                {'brick': core_bricks.CustomFieldsBrick, 'order': 40},
                {'brick': core_bricks.PropertiesBrick, 'order': 450},
            ],
        )
        old_count = BrickDetailviewLocation.objects.count()

        url = reverse('creme_config__clone_role', args=(role1.id,))
        response1 = self.assertGET200(url)

        with self.assertNoException():
            fields = response1.context['form'].fields
            copy_f = fields['copy_bricks']

        self.assertEqual(2, len(fields), fields)
        self.assertIsInstance(copy_f, BooleanField)
        self.assertFalse(copy_f.initial)

        # ---
        self.assertNoFormError(self.client.post(url, data={'name': 'My new role'}))
        self.assertEqual(old_count, BrickDetailviewLocation.objects.count())

    def test_clone__detail_brick_config__copy(self):
        self.login_as_root()
        role1 = self.create_role(name='Test')

        BrickDetailviewLocation.objects.multi_create(
            defaults={
                'model': FakeContact,
                'zone': BrickDetailviewLocation.LEFT,
                'role': role1,
            },
            data=[
                {'order': 5},
                {'brick': core_bricks.CustomFieldsBrick, 'order': 40},

                {
                    'brick': core_bricks.PropertiesBrick,
                    'order': 450,
                    'zone': BrickDetailviewLocation.RIGHT,
                },
            ],
        )
        old_count = BrickDetailviewLocation.objects.count()

        name = 'My new role'
        self.assertNoFormError(self.client.post(
            reverse('creme_config__clone_role', args=(role1.id,)),
            data={'name': name, 'copy_bricks': 'on'},
        ))
        self.assertEqual(old_count + 3, BrickDetailviewLocation.objects.count())

        role2 = self.get_object_or_fail(UserRole, name=name)
        locations = BrickDetailviewLocation.objects.filter(role=role2)
        self.assertEqual(3, len(locations))

        ct = ContentType.objects.get_for_model(FakeContact)
        location1 = locations[0]
        self.assertEqual(5,                            location1.order)
        self.assertEqual(ct,                           location1.content_type)
        self.assertEqual('model',                      location1.brick_id)
        self.assertEqual(BrickDetailviewLocation.LEFT, location1.zone)

        location2 = locations[1]
        self.assertEqual(40,                               location2.order)
        self.assertEqual(ct,                               location2.content_type)
        self.assertEqual(core_bricks.CustomFieldsBrick.id, location2.brick_id)
        self.assertEqual(BrickDetailviewLocation.LEFT,     location2.zone)

        self.assertEqual(BrickDetailviewLocation.RIGHT, locations[2].zone)

    def test_clone__home_brick_config__no_copy(self):
        self.login_as_root()
        role1 = self.create_role(name='Test')

        create_loc = partial(BrickHomeLocation.objects.create, role=role1)
        create_loc(brick_id=core_bricks.HistoryBrick.id,    order=15)
        create_loc(brick_id=core_bricks.StatisticsBrick.id, order=45)

        old_count = BrickHomeLocation.objects.count()

        url = reverse('creme_config__clone_role', args=(role1.id,))
        response1 = self.assertGET200(url)

        with self.assertNoException():
            fields = response1.context['form'].fields
            copy_f = fields['copy_bricks']

        self.assertEqual(2, len(fields), fields)
        self.assertIsInstance(copy_f, BooleanField)
        self.assertFalse(copy_f.initial)

        # ---
        self.assertNoFormError(self.client.post(url, data={'name': 'My new role'}))
        self.assertEqual(old_count, BrickHomeLocation.objects.count())

    def test_clone__home_brick_config__copy(self):
        self.login_as_root()
        role1 = self.create_role(name='Test')

        create_loc = partial(BrickHomeLocation.objects.create, role=role1)
        create_loc(brick_id=core_bricks.HistoryBrick.id,    order=15)
        create_loc(brick_id=core_bricks.StatisticsBrick.id, order=45)

        old_count = BrickHomeLocation.objects.count()

        name = 'My new role'
        self.assertNoFormError(self.client.post(
            reverse('creme_config__clone_role', args=(role1.id,)),
            data={'name': name, 'copy_bricks': 'on'},
        ))
        self.assertEqual(old_count + 2, BrickHomeLocation.objects.count())

        role2 = self.get_object_or_fail(UserRole, name=name)
        locations = BrickHomeLocation.objects.filter(role=role2, superuser=False)
        self.assertEqual(2, len(locations))

        location1 = locations[0]
        self.assertEqual(15,                          location1.order)
        self.assertEqual(core_bricks.HistoryBrick.id, location1.brick_id)

        location2 = locations[1]
        self.assertEqual(45,                             location2.order)
        self.assertEqual(core_bricks.StatisticsBrick.id, location2.brick_id)

    def test_clone__search_config__no_copy(self):
        self.login_as_root()
        role1 = self.create_role(name='Test')

        SearchConfigItem.objects.builder(
            model=FakeContact, fields=['first_name', 'last_name'], role=role1,
        ).get_or_create()

        old_count = SearchConfigItem.objects.count()

        url = reverse('creme_config__clone_role', args=(role1.id,))
        response1 = self.assertGET200(url)

        with self.assertNoException():
            fields = response1.context['form'].fields
            copy_f = fields['copy_search']

        self.assertEqual(2, len(fields), fields)
        self.assertIsInstance(copy_f, BooleanField)
        self.assertFalse(copy_f.initial)

        # ---
        self.assertNoFormError(self.client.post(url, data={'name': 'My new role'}))
        self.assertEqual(old_count, SearchConfigItem.objects.count())

    def test_clone__search_config__copy(self):
        self.login_as_root()
        role1 = self.create_role(name='Test')

        SearchConfigItem.objects.builder(
            role=role1, model=FakeContact, fields=['first_name', 'last_name'],
        ).get_or_create()
        SearchConfigItem.objects.builder(
            role=role1, model=FakeOrganisation, disabled=True,
        ).get_or_create()

        old_count = SearchConfigItem.objects.count()

        name = 'My new role'
        self.assertNoFormError(self.client.post(
            reverse('creme_config__clone_role', args=(role1.id,)),
            data={'name': name, 'copy_search': 'on'}
        ))
        self.assertEqual(old_count + 2, SearchConfigItem.objects.count())

        role2 = self.get_object_or_fail(UserRole, name=name)

        get_ct = ContentType.objects.get_for_model
        item1 = self.get_object_or_fail(
            SearchConfigItem, role=role2, content_type=get_ct(FakeContact),
        )
        self.assertFalse(item1.disabled)
        self.assertListEqual(
            ['regular_field-first_name', 'regular_field-last_name'],
            [c.key for c in item1.cells],
        )

        item2 = self.get_object_or_fail(
            SearchConfigItem, role=role2, content_type=get_ct(FakeOrganisation),
        )
        self.assertTrue(item2.disabled)
        self.assertFalse([*item2.cells])

    def test_clone__menu__no_copy(self):
        self.login_as_root()
        role1 = self.create_role(name='Test')

        create_mitem = partial(MenuConfigItem.objects.create, role=role1)
        create_mitem(entry_id=CremeEntry.id, order=1)
        create_mitem(entry_id=Separator0Entry.id, order=2)

        tools = create_mitem(
            entry_id=ContainerEntry.id, entry_data={'label': 'Tools'},
            order=100,
        )
        create_mitem(entry_id=JobsEntry.id, parent=tools, order=5)

        old_count = MenuConfigItem.objects.count()

        url = reverse('creme_config__clone_role', args=(role1.id,))
        response1 = self.assertGET200(url)

        with self.assertNoException():
            fields = response1.context['form'].fields
            copy_f = fields['copy_menu']

        self.assertEqual(2, len(fields), fields)
        self.assertIsInstance(copy_f, BooleanField)
        self.assertFalse(copy_f.initial)

        # ---
        self.assertNoFormError(self.client.post(url, data={'name': 'My new role'}))
        self.assertEqual(old_count, MenuConfigItem.objects.count())

    def test_clone__menu__copy(self):
        self.login_as_root()
        role1 = self.create_role(name='Test')

        create_mitem = partial(MenuConfigItem.objects.create, role=role1)
        create_mitem(entry_id=CremeEntry.id, order=1)
        create_mitem(entry_id=Separator0Entry.id, order=2)

        tools = create_mitem(
            entry_id=ContainerEntry.id, entry_data={'label': 'Tools'},
            order=100,
        )
        create_mitem(entry_id=JobsEntry.id, parent=tools, order=5)

        old_count = MenuConfigItem.objects.count()

        name = 'My new role'
        self.assertNoFormError(self.client.post(
            reverse('creme_config__clone_role', args=(role1.id,)),
            data={'name': name, 'copy_menu': 'on'},
        ))
        self.assertEqual(old_count + 4, MenuConfigItem.objects.count())

        role2 = self.get_object_or_fail(UserRole, name=name)

        item1 = self.get_object_or_fail(
            MenuConfigItem, role=role2, entry_id=CremeEntry.id,
        )
        self.assertEqual(1, item1.order)
        self.assertIsNone(item1.parent)
        self.assertFalse(item1.entry_data)

        item2 = self.get_object_or_fail(
            MenuConfigItem, role=role2, entry_id=Separator0Entry.id,
        )
        self.assertEqual(2, item2.order)

        item3 = self.get_object_or_fail(
            MenuConfigItem, role=role2, entry_id=ContainerEntry.id,
        )
        self.assertEqual(100, item3.order)
        self.assertDictEqual({'label': 'Tools'}, item3.entry_data)

        item4 = self.get_object_or_fail(
            MenuConfigItem, role=role2, entry_id=JobsEntry.id,
        )
        self.assertEqual(5,     item4.order)
        self.assertEqual(item3, item4.parent)

    def test_clone__custom_forms__no_copy(self):
        self.login_as_root()
        role1 = self.create_role(name='Test')

        CustomFormConfigItem.objects.create_if_needed(
            descriptor=FAKEORGANISATION_CREATION_CFORM,
            role=role1,
            groups_desc=[
                {
                    'name': 'General',
                    'cells': [
                        (EntityCellRegularField, {'name': 'user'}),
                        (EntityCellRegularField, {'name': 'name'}),
                    ],
                },
            ],
        )

        old_count = CustomFormConfigItem.objects.count()

        url = reverse('creme_config__clone_role', args=(role1.id,))
        response1 = self.assertGET200(url)

        with self.assertNoException():
            fields = response1.context['form'].fields
            copy_f = fields['copy_forms']

        self.assertEqual(2, len(fields), fields)
        self.assertIsInstance(copy_f, BooleanField)
        self.assertFalse(copy_f.initial)

        # ---
        self.assertNoFormError(self.client.post(url, data={'name': 'My new role'}))
        self.assertEqual(old_count, CustomFormConfigItem.objects.count())

    def test_clone__custom_forms__copy(self):
        self.login_as_root()
        role1 = self.create_role(name='Test')

        g_name = 'General'
        CustomFormConfigItem.objects.create_if_needed(
            descriptor=FAKEORGANISATION_CREATION_CFORM,
            role=role1,
            groups_desc=[
                {
                    'name': g_name,
                    'cells': [
                        (EntityCellRegularField, {'name': 'user'}),
                        (EntityCellRegularField, {'name': 'name'}),
                    ],
                },
            ],
        )

        old_count = CustomFormConfigItem.objects.count()

        name = 'My new role'
        self.assertNoFormError(self.client.post(
            reverse('creme_config__clone_role', args=(role1.id,)),
            data={'name': name, 'copy_forms': 'on'}
        ))
        self.assertEqual(old_count + 1, CustomFormConfigItem.objects.count())

        role2 = self.get_object_or_fail(UserRole, name=name)
        item = self.get_object_or_fail(CustomFormConfigItem, role=role2, superuser=False)
        self.assertEqual(FAKEORGANISATION_CREATION_CFORM.id, item.descriptor_id)
        self.assertListEqual(
            [
                {
                    'name': g_name,
                    'layout': LAYOUT_REGULAR,
                    'cells': [
                        {'type': 'regular_field', 'value': 'user'},
                        {'type': 'regular_field', 'value': 'name'},
                    ],
                },
            ],
            item.groups_as_dicts(),
        )
