# -*- coding: utf-8 -*-

from functools import partial
from json import dumps as json_dump

from django.contrib.contenttypes.models import ContentType
from django.forms import CharField
from django.urls import reverse
from django.utils.translation import gettext as _
from parameterized import parameterized

from creme.activities.models import Activity
from creme.creme_core.auth.entity_credentials import EntityCredentials
from creme.creme_core.core.entity_filter import (
    EF_CREDENTIALS,
    condition_handler,
    operands,
    operators,
)
from creme.creme_core.creme_jobs.deletor import deletor_type
from creme.creme_core.forms.widgets import Label
from creme.creme_core.models import CremeEntity, CremePropertyType
from creme.creme_core.models import CremeUser as User
from creme.creme_core.models import (
    CustomField,
    DeletionCommand,
    EntityFilter,
    EntityFilterCondition,
    FakeContact,
    FakeOrganisation,
    Job,
    RelationType,
    SetCredentials,
    UserRole,
)
from creme.creme_core.tests.base import CremeTestCase, skipIfNotInstalled
from creme.creme_core.tests.views.base import BrickTestCaseMixin
from creme.documents.models import Document
from creme.persons.models import Address, Contact, Organisation

from ..bricks import UserRolesBrick


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
    def _build_del_role_url(role):
        return reverse('creme_config__delete_role', args=(role.id,))

    def login_not_as_superuser(self):
        apps = ('creme_config',)
        self.login(is_superuser=False, allowed_apps=apps, admin_4_apps=apps)

    @parameterized.expand([
        (False,),
        (True,),
    ])
    def test_portal(self, superuser):
        self.login(is_superuser=superuser, admin_4_apps=['creme_config'])

        response = self.assertGET200(reverse('creme_config__roles'))
        self.assertTemplateUsed(response, 'creme_config/portals/user-role.html')
        self.assertEqual(
            reverse('creme_core__reload_bricks'),
            response.context.get('bricks_reload_url'),
        )

        brick_node = self.get_brick_node(
            self.get_html_tree(response.content), UserRolesBrick.id_,
        )
        self.assertEqual(
            _('{count} Role').format(count=1),
            self.get_brick_title(brick_node),
        )
        self.assertBrickHeaderHasButton(
            self.get_brick_header_buttons(brick_node),
            url=self.ROLE_CREATION_URL,
            label=_('New role'),
        )
        self.assertListEqual(
            [self.role.name],
            [n.text for n in brick_node.findall('.//td[@class="role-name"]')],
        )

    @skipIfNotInstalled('creme.persons')
    @skipIfNotInstalled('creme.documents')
    @skipIfNotInstalled('creme.activities')
    def test_creation_wizard01(self):
        "No EntityFilter."
        self.login()
        url = self.ROLE_CREATION_URL
        name = 'Basic role'
        apps = ['persons', 'documents']
        adm_apps = ['persons']

        # Step 1
        response = self.assertGET200(url)
        context1 = response.context
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
        response = self.client.post(
            url,
            data={
                step_key: '0',
                '0-name': name,
                '0-allowed_apps': apps,
            },
        )
        self.assertNoFormError(response)

        # Step 2
        with self.assertNoException():
            adm_app_labels = response.context['form'].fields['admin_4_apps'].choices

        self.assertInChoices(
            value=apps[0], label=_('Accounts and Contacts'), choices=adm_app_labels,
        )
        self.assertInChoices(
            value=apps[1], label=_('Documents'), choices=adm_app_labels,
        )
        self.assertNotInChoices(value='activities', choices=adm_app_labels)

        response = self.client.post(
            url,
            data={
                step_key: '1',
                '1-admin_4_apps': adm_apps,
            },
        )
        self.assertNoFormError(response)

        # Step 3
        with self.assertNoException():
            creatable_ctypes = {*response.context['form'].fields['creatable_ctypes'].ctypes}

        get_ct = ContentType.objects.get_for_model
        ct_contact = get_ct(Contact)
        ct_doc = get_ct(Document)

        self.assertIn(ct_contact, creatable_ctypes)
        self.assertIn(get_ct(Organisation), creatable_ctypes)
        self.assertNotIn(get_ct(Address), creatable_ctypes)  # Not CremeEntity
        self.assertIn(ct_doc, creatable_ctypes)
        self.assertNotIn(get_ct(Activity), creatable_ctypes)  # App not allowed

        response = self.client.post(
            url,
            data={
                step_key: '2',
                '2-creatable_ctypes': [ct_contact.id, ct_doc.id],
            },
        )
        self.assertNoFormError(response)

        # Step 4
        with self.assertNoException():
            exp_ctypes = response.context['form'].fields['exportable_ctypes'].ctypes

        self.assertIn(ct_contact, exp_ctypes)
        self.assertIn(get_ct(Organisation), exp_ctypes)
        self.assertNotIn(get_ct(Address), exp_ctypes)  # Not CremeEntity
        self.assertIn(ct_doc, exp_ctypes)
        self.assertNotIn(get_ct(Activity), exp_ctypes)  # App not allowed

        response = self.client.post(
            url,
            data={
                step_key: '3',
                '3-exportable_ctypes': [ct_contact.id],
            },
        )
        self.assertNoFormError(response)

        # Step 5
        context5 = response.context

        with self.assertNoException():
            cred_ctypes = {*context5['form'].fields['ctype'].ctypes}

        self.assertIn(ct_contact, cred_ctypes)
        self.assertIn(get_ct(Organisation), cred_ctypes)
        self.assertNotIn(get_ct(Address), cred_ctypes)  # Not CremeEntity
        self.assertIn(ct_doc, cred_ctypes)
        self.assertNotIn(get_ct(Activity), cred_ctypes)  # App not allowed

        set_type = SetCredentials.ESET_ALL
        response = self.client.post(
            url,
            data={
                step_key: '4',
                '4-can_change': True,

                '4-set_type': set_type,
                '4-ctype':    ct_contact.id,

                '4-forbidden': 'False',
            },
        )
        self.assertNoFormError(response)

        # Step 6
        context6 = response.context
        self.assertEqual(_('Save the role'), context6.get('submit_label'))

        with self.assertNoException():
            fields6 = response.context['form'].fields
            label_field = fields6['no_filter_label']

        self.assertEqual(1, len(fields6))

        self.assertIsInstance(label_field, CharField)
        self.assertIsInstance(label_field.widget, Label)
        self.assertEqual(_('Conditions'), label_field.label)
        self.assertEqual(
            _('No filter, no condition.'),
            label_field.initial
        )

        response = self.client.post(url, data={step_key: '5'})
        self.assertNoFormError(response)

        role = self.get_object_or_fail(UserRole, name=name)
        self.assertEqual({*apps},     role.allowed_apps)
        self.assertEqual({*adm_apps}, role.admin_4_apps)

        self.assertSetEqual({ct_contact, ct_doc}, {*role.creatable_ctypes.all()})
        self.assertListEqual([ct_contact],        [*role.exportable_ctypes.all()])

        setcreds = role.credentials.all()
        self.assertEqual(1, len(setcreds))

        creds = setcreds[0]
        self.assertEqual(EntityCredentials.VIEW | EntityCredentials.CHANGE, creds.value)
        self.assertEqual(set_type, creds.set_type)
        self.assertEqual(ct_contact, creds.ctype)
        self.assertFalse(creds.forbidden)

    @skipIfNotInstalled('creme.persons')
    def test_creation_wizard02(self):
        "With EntityFilter."
        self.login()
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
            url, data={step_key: '3', '3-exportable_ctypes': []},
        )
        self.assertNoFormError(response)

        # Step 5 ---
        ct_contact = ContentType.objects.get_for_model(Contact)
        set_type = SetCredentials.ESET_FILTER
        response = self.client.post(
            url,
            data={
                step_key: '4',
                '4-can_link': True,

                '4-set_type': set_type,
                '4-ctype':    ct_contact.id,
                '4-forbidden': 'True',
            },
        )
        self.assertNoFormError(response)

        # Step 6 ---
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
                step_key: '5',
                '5-name': filter_name,
                '5-use_or': 'True',
                '5-regularfieldcondition': json_dump([{
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

        setcreds = role.credentials.all()
        self.assertEqual(1, len(setcreds))

        creds = setcreds[0]
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

        conditions = efilter.get_conditions()
        self.assertEqual(1, len(conditions))

        condition = conditions[0]
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

    def test_creation_wizard03(self):
        "With EntityFilter on CremeEntity."
        self.login()
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
            url, data={step_key: '3', '3-exportable_ctypes': []},
        )
        self.assertNoFormError(response)

        # Step 5 ---
        set_type = SetCredentials.ESET_FILTER
        response = self.client.post(
            url,
            data={
                step_key: '4',
                '4-can_link': True,

                '4-set_type': set_type,
                '4-forbidden': 'False',
            },
        )
        self.assertNoFormError(response)

        # Step 6 ---
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
                step_key: '5',
                '5-name': filter_name,
                '5-use_or': 'True',
                '5-regularfieldcondition': json_dump([{
                    'field':    {'name': filter_field_name},
                    'operator': {'id': str(filter_operator_id)},
                    'value':    filter_field_value,
                }]),
            },
        )
        self.assertNoFormError(response)

        role = self.get_object_or_fail(UserRole, name=name)
        setcreds = role.credentials.all()
        self.assertEqual(1, len(setcreds))

        creds = setcreds[0]
        self.assertIsNone(creds.ctype)  # CremeEntity

        efilter = creds.efilter
        self.assertIsNotNone(efilter)
        self.assertEqual(CremeEntity, efilter.entity_type.model_class())

        conditions = efilter.get_conditions()
        self.assertEqual(1, len(conditions))

        condition = conditions[0]
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

    def test_creation_wizard04(self):
        "Not super-user."
        self.login_not_as_superuser()
        self.assertGET403(self.ROLE_CREATION_URL)

    def test_add_credentials01(self):
        user = self.login()

        role = UserRole(name='CEO')
        role.allowed_apps = ['creme_core']
        role.save()

        other_user = User.objects.create(username='chloe', role=role)
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

        setcreds = role.credentials.all()
        self.assertEqual(1, len(setcreds))

        creds = setcreds[0]
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
    def test_add_credentials02(self):
        "Specific CType + ESET_OWN."
        self.login()

        role = UserRole(name='CEO')
        role.allowed_apps = ['persons']
        role.save()

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

        setcreds = role.credentials.all()
        self.assertEqual(1, len(setcreds))

        creds = setcreds[0]
        self.assertEqual(EntityCredentials.VIEW | EntityCredentials.CHANGE, creds.value)
        self.assertEqual(SetCredentials.ESET_OWN, creds.set_type)
        self.assertEqual(ct_contact.id,           creds.ctype_id)

    def test_add_credentials03(self):
        "Not super-user => error."
        self.login_not_as_superuser()

        role = UserRole(name='CEO')
        role.allowed_apps = ['persons']
        role.save()

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
    def test_add_credentials04(self):
        "Forbidden."
        self.login()

        role = UserRole.objects.create(name='CEO', allowed_apps=['persons'])

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

        setcreds = role.credentials.all()
        self.assertEqual(1, len(setcreds))

        creds = setcreds[0]
        self.assertEqual(EntityCredentials.VIEW | EntityCredentials.CHANGE, creds.value)
        self.assertEqual(set_type,      creds.set_type)
        self.assertEqual(ct_contact.id, creds.ctype_id)
        self.assertTrue(creds.forbidden)

    @skipIfNotInstalled('creme.persons')
    def test_add_credentials05(self):
        "No action => Validation error."
        self.login()

        role = UserRole(name='CEO')
        role.allowed_apps = ['persons']
        role.save()

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
            response, 'form', None, _('No action has been selected.'),
        )

    def test_add_credentials_with_filter01(self):
        self.login()

        role = UserRole.objects.create(name='CEO', allowed_apps=['creme_core'])
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

        setcreds = role.credentials.all()
        self.assertEqual(1, len(setcreds))

        creds = setcreds[0]
        self.assertEqual(EntityCredentials.VIEW | EntityCredentials.CHANGE, creds.value)
        self.assertEqual(set_type, creds.set_type)
        self.assertEqual(ctype.id, creds.ctype_id)

        efilter = creds.efilter
        self.assertIsInstance(efilter, EntityFilter)
        self.assertEqual(name, efilter.name)
        self.assertTrue(efilter.is_custom)
        self.assertFalse(efilter.use_or)
        self.assertEqual(f'creme_core-credentials_{role.id}-1', efilter.id)
        self.assertEqual(EF_CREDENTIALS, efilter.filter_type)

        conditions = efilter.conditions.all()
        self.assertEqual(1, len(conditions))

        condition = conditions[0]
        self.assertEqual(
            condition_handler.RegularFieldConditionHandler.type_id,
            condition.type,
        )
        self.assertEqual(field_name, condition.name)
        self.assertDictEqual(
            {'operator': operator, 'values': [value]},
            condition.value,
        )

    def test_add_credentials_with_filter02(self):
        """Other values (ctype, use_or, perms, forbidden...)
        + condition on custom field, relations & properties.
        """
        self.login()
        ctype = ContentType.objects.get_for_model(FakeOrganisation)

        rtype = RelationType.objects.smart_update_or_create(
            ('test-subject_recruited', 'Has recruited'),
            ('test-object_recruited',  'Has been recruited by'),
        )[0]
        ptype = CremePropertyType.objects.smart_update_or_create(
            str_pk='test-prop_is_secret', text='Is secret',
        )
        custom_field = CustomField.objects.create(
            name='Number of agents', content_type=ctype,
            field_type=CustomField.INT,
        )

        role = UserRole.objects.create(name='CEO', allowed_apps=['creme_core'])
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

        setcreds = role.credentials.all()
        self.assertEqual(1, len(setcreds))

        creds = setcreds[0]
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
        self.assertEqual(str(custom_field.id), condition1.name)
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
        self.assertEqual(ptype.id, condition3.name)
        self.assertIs(condition3.value, True)

    def test_add_credentials_with_filter03(self):
        "Filter without specific ContentType."
        self.login()

        role = UserRole.objects.create(name='CEO', allowed_apps=['creme_core'])
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

        setcreds = role.credentials.all()
        self.assertEqual(1, len(setcreds))

        creds = setcreds[0]
        self.assertEqual(
            EntityCredentials.VIEW | EntityCredentials.CHANGE | EntityCredentials.DELETE,
            creds.value,
        )
        self.assertEqual(set_type, creds.set_type)
        self.assertIsNone(creds.ctype_id)

        efilter = creds.efilter
        self.assertIsInstance(efilter, EntityFilter)

        conditions = efilter.conditions.all()
        self.assertEqual(1, len(conditions))

        condition = conditions[0]
        self.assertEqual(
            condition_handler.RegularFieldConditionHandler.type_id,
            condition.type,
        )
        self.assertEqual(field_name, condition.name)
        self.assertDictEqual(
            {'operator': operator, 'values': [value]},
            condition.value,
        )

    def test_add_credentials_with_filter04(self):
        "No condition => error."
        self.login()

        role = UserRole.objects.create(name='CEO', allowed_apps=['creme_core'])
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
            response, 'form', None,
            _('The filter must have at least one condition.'),
        )

    @skipIfNotInstalled('creme.persons')
    @skipIfNotInstalled('creme.activities')
    def test_edit_credentials01(self):
        self.login()

        role = UserRole.objects.create(name='CEO', allowed_apps=['persons'])

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

    def test_edit_credentials02(self):
        "Not super-user => error."
        self.login_not_as_superuser()
        role = UserRole.objects.create(name='CEO')
        creds = SetCredentials.objects.create(
            role=role, set_type=SetCredentials.ESET_ALL, value=EntityCredentials.VIEW,
        )
        self.assertGET403(reverse('creme_config__edit_role_credentials', args=(creds.id,)))

    def test_edit_credentials_with_filter01(self):
        "Add filter."
        self.login()

        role = UserRole.objects.create(name='CEO', allowed_apps=['creme_core'])
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

        setcreds = role.credentials.all()
        self.assertEqual(1, len(setcreds))

        efilter = setcreds[0].efilter
        self.assertIsInstance(efilter, EntityFilter)
        self.assertEqual(name, efilter.name)
        self.assertTrue(efilter.use_or)
        self.assertEqual(
            f'creme_core-credentials_{role.id}-1',
            efilter.id,
        )
        self.assertEqual(EF_CREDENTIALS, efilter.filter_type)

        conditions = efilter.conditions.all()
        self.assertEqual(1, len(conditions))

        condition = conditions[0]
        self.assertEqual(
            condition_handler.RegularFieldConditionHandler.type_id,
            condition.type,
        )
        self.assertEqual('last_name', condition.name)
        self.assertDictEqual(
            {'operator': operator, 'values': [value]},
            condition.value,
        )

    def test_edit_credentials_with_filter02(self):
        "Change filter conditions + conditions on CustomField/Relation/CremeProperty."
        self.login()

        rtype = RelationType.objects.smart_update_or_create(
            ('test-subject_recruited', 'Has been recruited by'),
            ('test-object_recruited',  'Has recruited'),
        )[0]
        ptype = CremePropertyType.objects.smart_update_or_create(
            str_pk='test-prop_is_nice', text='Is nice',
        )
        custom_field = CustomField.objects.create(
            name='Number of ties', content_type=FakeContact,
            field_type=CustomField.INT,
        )

        role = UserRole.objects.create(name='CEO', allowed_apps=['creme_core'])
        efilter1 = EntityFilter.objects.create(
            id='creme_core-test_credentials_edition02',
            name='Agencies',
            entity_type=FakeContact,
            filter_type=EF_CREDENTIALS,
            use_or=True,
        )
        efilter1.set_conditions(
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

        setcreds = role.credentials.all()
        self.assertEqual(1, len(setcreds))

        set_cred2 = setcreds[0]
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
        self.assertEqual(str(custom_field.id), condition1.name)
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
        self.assertEqual(ptype.id, condition3.name)
        self.assertIs(condition3.value, True)

    def test_edit_credentials_with_filter03(self):
        "Change existing ctype & filter + conditions on CustomField/Relation/CremeProperty."
        self.login()

        ptype = CremePropertyType.objects.smart_update_or_create(
            str_pk='test-prop_is_secret', text='Is secret',
        )

        role = UserRole.objects.create(name='CEO', allowed_apps=['creme_core'])
        efilter1 = EntityFilter.objects.create(
            id='creme_core-test_credentials_edition02',
            name='Agencies',
            entity_type=FakeContact,
            filter_type=EF_CREDENTIALS,
            use_or=False,
        )
        efilter1.set_conditions(
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

        setcreds = role.credentials.all()
        self.assertEqual(1, len(setcreds))

        setcred = setcreds[0]
        self.assertEqual(ctype, setcred.ctype)

        efilter2 = setcred.efilter
        self.assertIsNotNone(efilter2)
        self.assertEqual(name, efilter2.name)
        self.assertEqual(ctype, efilter2.entity_type)
        self.assertTrue(efilter2.use_or)
        self.assertEqual(EF_CREDENTIALS, efilter2.filter_type)
        self.assertEqual(efilter1.id, efilter2.id)

        conditions = efilter2.conditions.all()
        self.assertEqual(1, len(conditions))

        condition = conditions[0]
        self.assertEqual(
            condition_handler.PropertyConditionHandler.type_id,
            condition.type,
        )
        self.assertEqual(ptype.id, condition.name)
        self.assertIs(condition.value, True)

    def test_edit_credentials_with_filter04(self):
        "Remove filter if no more needed."
        self.login()

        role = UserRole.objects.create(name='CEO', allowed_apps=['creme_core'])

        efilter = EntityFilter.objects.create(
            id='creme_config-test_user_role',
            entity_type=FakeContact,
            filter_type=EF_CREDENTIALS,
        )
        efilter.set_conditions(
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
            ['no_filter_label'], [*response.context['form'].fields.keys()],
        )

        # POST (step 2) ---
        response = self.client.post(url, data={step_key: '1'})
        self.assertNoFormError(response)

        creds = self.refresh(creds)
        self.assertIsNone(creds.efilter)
        self.assertEqual(set_type, creds.set_type)

        self.assertDoesNotExist(efilter)
        self.assertFalse(EntityFilterCondition.objects.filter(id__in=cond_ids))

    def test_edit_credentials_with_filter05(self):
        "Content type is CremeEntity."
        self.login()
        ptype = CremePropertyType.objects.smart_update_or_create(
            str_pk='test-prop_is_secret', text='Is secret',
        )

        role = UserRole.objects.create(name='CEO', allowed_apps=['creme_core'])
        efilter1 = EntityFilter.objects.create(
            id='creme_core-test_credentials_edition04',
            name='My entities',
            entity_type=CremeEntity,
            filter_type=EF_CREDENTIALS,
        )
        efilter1.set_conditions(
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

        setcreds = role.credentials.all()
        self.assertEqual(1, len(setcreds))
        self.assertIsNone(setcreds[0].ctype)

        efilter2 = setcreds[0].efilter
        self.assertIsNotNone(efilter2)
        self.assertEqual(
            ContentType.objects.get_for_model(CremeEntity),
            efilter2.entity_type,
        )
        self.assertEqual(name, efilter2.name)
        self.assertTrue(efilter2.use_or)

        conditions = efilter2.conditions.all()
        self.assertEqual(1, len(conditions))

        condition = conditions[0]
        self.assertEqual(
            condition_handler.PropertyConditionHandler.type_id,
            condition.type,
        )
        self.assertEqual(ptype.id, condition.name)
        self.assertIs(condition.value, True)

    def test_edit_credentials_with_filter06(self):
        "Add filter to CremeEntity."
        self.login()

        role = UserRole.objects.create(name='CEO', allowed_apps=['creme_core'])
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

        setcreds = role.credentials.all()
        self.assertEqual(1, len(setcreds))

        efilter = setcreds[0].efilter
        self.assertEqual(name, efilter.name)
        self.assertEqual(
            ContentType.objects.get_for_model(CremeEntity),
            efilter.entity_type,
        )

        conditions = efilter.conditions.all()
        self.assertEqual(1, len(conditions))

        condition = conditions[0]
        self.assertEqual(
            condition_handler.RegularFieldConditionHandler.type_id,
            condition.type,
        )
        self.assertEqual(field_name, condition.name)
        self.assertDictEqual(
            {'operator': operator, 'values': [value]}, condition.value,
        )

    def test_edit_credentials_with_filter07(self):
        "From CremeEntity to child class => keep information as initial."
        self.login()

        role = UserRole.objects.create(name='CEO', allowed_apps=['creme_core'])
        efilter1 = EntityFilter.objects.create(
            id='creme_core-test_credentials_edition04',
            name='My entities',
            entity_type=CremeEntity,
            filter_type=EF_CREDENTIALS,
        )
        efilter1.set_conditions(
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

    def test_delete_credentials01(self):
        self.login()

        role = UserRole(name='CEO')
        role.allowed_apps = ['persons']
        role.save()

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

    def test_delete_credentials02(self):
        self.login_not_as_superuser()

        sc = SetCredentials.objects.create(
            role=self.role, set_type=SetCredentials.ESET_ALL, value=EntityCredentials.VIEW,
        )
        self.assertPOST403(self.DEL_CREDS_URL, data={'id': sc.id})

    @skipIfNotInstalled('creme.persons')
    @skipIfNotInstalled('creme.documents')
    @skipIfNotInstalled('creme.activities')
    def test_edition_wizard01(self):
        self.login()

        role = UserRole.objects.create(name='CEO', allowed_apps=['persons'])
        SetCredentials.objects.create(
            role=role, value=EntityCredentials.VIEW, set_type=SetCredentials.ESET_ALL,
        )

        name = role.name + ' edited'
        apps = ['persons', 'documents']
        adm_apps = ['persons']

        url = self._build_wizard_edit_url(role)

        # Step 1 ---
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

        # Step 2 ---
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

        # Step 3 ---
        with self.assertNoException():
            creatable_ctypes = {*response3.context['form'].fields['creatable_ctypes'].ctypes}

        get_ct = ContentType.objects.get_for_model
        ct_contact = get_ct(Contact)
        ct_doc = get_ct(Document)

        self.assertIn(ct_contact, creatable_ctypes)
        self.assertIn(get_ct(Organisation), creatable_ctypes)
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

        # Step 4 ---
        context4 = response4.context
        self.assertEqual(_('Save the modifications'), context4.get('submit_label'))

        with self.assertNoException():
            exp_ctypes = context4['form'].fields['exportable_ctypes'].ctypes

        self.assertIn(ct_contact, exp_ctypes)
        self.assertIn(get_ct(Organisation), exp_ctypes)
        self.assertNotIn(get_ct(Address), exp_ctypes)  # Not CremeEntity
        self.assertIn(ct_doc, exp_ctypes)
        self.assertNotIn(get_ct(Activity), exp_ctypes)  # App not allowed

        self.assertNoFormError(self.client.post(
            url,
            data={
                step_key: '3',
                '3-exportable_ctypes': [ct_contact.id],
            },
        ))

        role = self.refresh(role)
        self.assertEqual(name, role.name)
        self.assertSetEqual({*apps},     role.allowed_apps)
        self.assertSetEqual({*adm_apps}, role.admin_4_apps)

        self.assertSetEqual({ct_contact, ct_doc}, {*role.creatable_ctypes.all()})
        self.assertListEqual([ct_contact],        [*role.exportable_ctypes.all()])
        self.assertEqual(1, role.credentials.count())

    def test_edition_wizard02(self):
        "Not super-user."
        self.login_not_as_superuser()

        role = UserRole.objects.create(name='CEO')
        self.assertGET403(self._build_wizard_edit_url(role))

    def test_delete01(self):
        "Not superuser -> error."
        self.login_not_as_superuser()

        url = self._build_del_role_url(self.role)
        self.assertGET403(url)
        self.assertPOST403(url)

    def test_delete02(self):
        "Role is not used."
        user = self.login()

        role = UserRole.objects.create(name='CEO')
        creds = SetCredentials.objects.create(
            role=role, set_type=SetCredentials.ESET_ALL, value=EntityCredentials.VIEW,
        )

        url = self._build_del_role_url(role)
        response = self.assertGET200(url)
        self.assertTemplateUsed(response, 'creme_core/generics/blockform/delete-popup.html')

        context = response.context
        self.assertEqual(
            _('Delete role «{object}»').format(object=role), context.get('title')
        )
        self.assertEqual(_('Delete the role'), context.get('submit_label'))

        with self.assertNoException():
            fields = context['form'].fields
            info = fields['info']

        self.assertFalse(info.required)
        self.assertNotIn('to_role', fields)

        response = self.client.post(url)
        self.assertNoFormError(response)
        self.assertTemplateUsed(response, 'creme_config/deletion-job-popup.html')

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

    def test_delete03(self):
        "To replace by another role."
        user = self.login()

        replacing_role = self.role
        role_2_del = UserRole.objects.create(name='CEO')
        other_role = UserRole.objects.create(name='Coder')
        user_2_update = User.objects.create(username='chloe', role=role_2_del)  # <= role is used

        url = self._build_del_role_url(role_2_del)
        response = self.assertGET200(url)

        with self.assertNoException():
            fields = response.context['form'].fields
            choices = [*fields['to_role'].choices]

        self.assertNotIn('info', fields)

        self.assertInChoices(value=replacing_role.id, label=str(replacing_role), choices=choices)
        self.assertInChoices(value=other_role.id,     label=str(other_role),     choices=choices)
        self.assertNotInChoices(value=role_2_del.id, choices=choices)

        response = self.client.post(url, data={'to_role': replacing_role.id})
        self.assertNoFormError(response)

        dcom = self.get_deletion_command_or_fail(UserRole)
        self.assertEqual(role_2_del,      dcom.instance_to_delete)
        self.assertEqual(role_2_del.name, dcom.deleted_repr)
        self.assertListEqual(
            [('fixed_value', user.__class__, 'role', replacing_role)],
            [
                (r.type_id, r.model_field.model, r.model_field.name, r.get_value())
                for r in dcom.replacers
            ],
        )
        self.assertEqual(1, dcom.total_count)
        self.assertEqual(0, dcom.updated_count)

        job = dcom.job
        self.assertEqual(deletor_type.id, job.type_id)
        self.assertEqual(user, job.user)

        deletor_type.execute(job)
        self.assertDoesNotExist(role_2_del)
        self.assertEqual(self.refresh(user_2_update).role, replacing_role)

    def test_delete04(self):
        "Role is used -> replacing role is required."
        self.login()

        role = UserRole.objects.create(name='CEO')
        User.objects.create(username='chloe', role=role)  # <= role is used

        response = self.assertPOST200(self._build_del_role_url(role))
        self.assertFormError(response, 'form', 'to_role', _('This field is required.'))

    def test_delete05(self):
        "Uniqueness."
        user = self.login()
        self.assertFalse(DeletionCommand.objects.first())

        job = Job.objects.create(type_id=deletor_type.id, user=user)
        self.assertEqual(Job.STATUS_WAIT, job.status)

        role_2_del1 = UserRole.objects.create(name='CEO')
        dcom = DeletionCommand.objects.create(
            job=job,
            instance_to_delete=role_2_del1,
        )

        role_2_del2 = UserRole.objects.create(name='Coder')
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
