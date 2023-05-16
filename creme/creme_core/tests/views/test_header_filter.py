from functools import partial

from django.contrib.contenttypes.models import ContentType
from django.test import override_settings
from django.urls import reverse
from django.utils.translation import gettext as _

from creme.creme_core.core.entity_cell import (
    EntityCellCustomField,
    EntityCellFunctionField,
    EntityCellRegularField,
    EntityCellRelation,
)
from creme.creme_core.core.entity_filter.condition_handler import (
    RegularFieldConditionHandler,
)
from creme.creme_core.core.entity_filter.operators import EQUALS
from creme.creme_core.core.function_field import function_field_registry
from creme.creme_core.models import (
    CustomField,
    EntityFilter,
    FakeContact,
    FakeMailingList,
    FakeOrganisation,
    FakeProduct,
    FieldsConfig,
    HeaderFilter,
    RelationType,
)
from creme.creme_core.tests.fake_constants import FAKE_REL_SUB_EMPLOYED_BY
from creme.creme_core.tests.views.base import ViewsTestCase


class HeaderFilterViewsTestCase(ViewsTestCase):
    DELETE_URL = reverse('creme_core__delete_hfilter')

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.contact_ct = ContentType.objects.get_for_model(FakeContact)

    @staticmethod
    def _build_add_url(ctype):
        return reverse('creme_core__create_hfilter', args=(ctype.id,))

    @staticmethod
    def _build_get4ctype_url(ctype):
        return '{}?ct_id={}'.format(reverse('creme_core__hfilters'), ctype.id)

    @override_settings(FILTERS_INITIAL_PRIVATE=False)
    def test_create01(self):
        # self.login()
        self.login_as_root()

        ct = ContentType.objects.get_for_model(FakeMailingList)
        self.assertFalse(HeaderFilter.objects.filter(entity_type=ct))

        url = self._build_add_url(ct)
        response = self.client.get(url)
        self.assertTemplateUsed(response, 'creme_core/forms/header-filter.html')
        self.assertContains(
            response,
            _('Create a view of list for «%(ctype)s»') % {'ctype': 'Test Mailing list'},
        )
        self.assertIs(response.context['form'].initial.get('is_private'), False)

        name = 'DefaultHeaderFilter'
        response = self.client.post(
            url,
            data={
                'name':  name,
                'cells': 'regular_field-created',
            },
        )
        self.assertNoFormError(response, status=302)

        hfilter = self.get_alone_element(HeaderFilter.objects.filter(entity_type=ct))
        self.assertEqual(name, hfilter.name)
        self.assertIsNone(hfilter.user)
        self.assertTrue(hfilter.is_custom)
        self.assertFalse(hfilter.is_private)

        cells = hfilter.cells
        self.assertListEqual(
            [EntityCellRegularField.build(FakeMailingList, 'created')],
            cells,
        )
        self.assertIs(cells[0].is_hidden, False)

        lv_url = FakeMailingList.get_lv_absolute_url()
        self.assertRedirects(response, lv_url)

        # --
        context = self.assertGET200(lv_url).context
        selected_hfilter = context['header_filters'].selected
        self.assertIsInstance(selected_hfilter, HeaderFilter)
        self.assertEqual(hfilter.id, selected_hfilter.id)
        self.assertEqual(hfilter.id, context['list_view_state'].header_filter_id)

    def test_create02(self):
        # user = self.login()
        user = self.login_as_root_and_get()

        lv_url = FakeContact.get_lv_absolute_url()

        # Create a view to post the entity filter
        HeaderFilter.objects.create_if_needed(
            pk='creme_core-tests_views_header_filter_test_create02',
            name='A FakeContact view',  # Starts with "A" => first
            model=FakeContact,
            cells_desc=[
                (EntityCellRegularField, {'name': 'last_name'}),
                (EntityCellRegularField, {'name': 'first_name'}),
                (EntityCellRegularField, {'name': 'email'}),
            ],
        )

        # Set a filter in the session (should be kept)
        efilter = EntityFilter.objects.smart_update_or_create(
            'creme_core-tests_views_header_filter_test_create02',
            name='Misato', model=FakeContact,
            is_custom=True,
            conditions=[
                RegularFieldConditionHandler.build_condition(
                    model=FakeContact, field_name='first_name',
                    operator=EQUALS, values=['Misato'],
                ),
            ],
        )
        response = self.assertPOST200(lv_url, data={'filter': efilter.id})
        self.assertEqual(efilter.id, response.context['list_view_state'].entity_filter_id)

        # --
        ct = self.contact_ct
        loves = RelationType.objects.smart_update_or_create(
            ('test-subject_love', 'Is loving'),
            ('test-object_love',  'Is loved by')
        )[0]
        customfield = CustomField.objects.create(
            name='Size (cm)',
            field_type=CustomField.INT,
            content_type=ct,
        )
        funcfield = function_field_registry.get(FakeContact, 'get_pretty_properties')

        url = self._build_add_url(ct)
        response = self.assertGET200(url)

        with self.assertNoException():
            cells_f = response.context['form'].fields['cells']

        build_4_field = partial(EntityCellRegularField.build, model=FakeContact)
        self.assertListEqual(
            [
                build_4_field(name='first_name'),
                build_4_field(name='last_name'),
                EntityCellRelation(
                    model=FakeContact,
                    rtype=RelationType.objects.get(pk=FAKE_REL_SUB_EMPLOYED_BY),
                ),
            ],
            cells_f.initial
        )

        field_name = 'first_name'
        name = 'DefaultHeaderFilter'
        response = self.client.post(
            url, follow=True,
            data={
                'name': name,
                'user': user.id,
                'is_private': 'on',
                'cells': f'relation-{loves.id},'
                         f'regular_field-{field_name},'
                         f'function_field-{funcfield.name},'
                         f'custom_field-{customfield.id}',
            },
        )
        self.assertNoFormError(response)

        hfilter = self.get_object_or_fail(HeaderFilter, name=name)
        self.assertEqual(user, hfilter.user)
        self.assertTrue(hfilter.is_private)
        self.assertListEqual(
            [
                EntityCellRelation(model=FakeContact, rtype=loves),
                EntityCellRegularField.build(FakeContact, field_name),
                EntityCellFunctionField(model=FakeContact, func_field=funcfield),
                EntityCellCustomField(customfield),
            ],
            hfilter.cells
        )

        self.assertRedirects(response, lv_url)

        # --
        context = self.assertGET200(lv_url).context
        selected_hfilter = context['header_filters'].selected
        self.assertIsInstance(selected_hfilter, HeaderFilter)
        self.assertEqual(hfilter.id, selected_hfilter.id)

        lvs = context['list_view_state']
        self.assertEqual(hfilter.id, lvs.header_filter_id)
        self.assertEqual(efilter.id, lvs.entity_filter_id)

    def test_create03(self):
        "Check app credentials."
        # user = self.login(is_superuser=False, allowed_apps=['documents'])
        user = self.login_as_standard(allowed_apps=['documents'])

        uri = self._build_add_url(self.contact_ct)
        self.assertGET403(uri)

        # ---
        role = user.role
        role.allowed_apps = ['documents', 'creme_core']
        role.save()
        self.assertGET200(uri)

    def test_create04(self):
        "Cannot create a private filter for another user (but OK with one of our teams)."
        # user = self.login()
        user = self.login_as_root_and_get()
        # other_user = self.other_user
        other_user = self.create_user()

        my_team = self.create_team('TeamTitan', user, other_user)
        a_team = self.create_team('A-team', other_user)

        name = 'DefaultHeaderFilter'

        def post(owner):
            return self.assertPOST200(
                self._build_add_url(self.contact_ct),
                follow=True,
                data={
                    'name': name,
                    'user': owner.id,
                    'is_private': 'on',
                    'cells': 'regular_field-first_name',
                },
            )

        response1 = post(other_user)
        msg = _('A private view of list must belong to you (or one of your teams).')
        self.assertFormError(response1.context['form'], field='user', errors=msg)

        response2 = post(a_team)
        self.assertFormError(response2.context['form'], field='user', errors=msg)

        response3 = post(my_team)
        self.assertNoFormError(response3)
        self.get_object_or_fail(HeaderFilter, name=name)

    def test_create05(self):
        "Use cancel_url for redirection."
        # self.login()
        self.login_as_root()

        callback = FakeOrganisation.get_lv_absolute_url()
        response = self.client.post(
            self._build_add_url(self.contact_ct),
            follow=True,
            data={
                'name':      'DefaultHeaderFilter',
                'cells':     'regular_field-first_name',
                'cancel_url': callback,
            },
        )
        self.assertNoFormError(response)
        self.assertRedirects(response, callback)

    def test_create06(self):
        "A staff user can create a private filter for another user."
        # self.login(is_staff=True)
        self.login_as_super(is_staff=True)

        name = 'DefaultHeaderFilter'
        response = self.client.post(
            self._build_add_url(self.contact_ct),
            follow=True,
            data={
                'name': name,
                # 'user': self.other_user.id,
                'user': self.get_root_user().id,
                'is_private': 'on',
                'cells': 'regular_field-first_name',
            },
        )
        self.assertNoFormError(response)
        self.get_object_or_fail(HeaderFilter, name=name)

    def test_create_error01(self):
        "Not an Entity type."
        # self.login()
        self.login_as_root()
        self.assertGET409(self._build_add_url(ContentType.objects.get_for_model(RelationType)))

    def test_create_error02(self):
        "FieldsConfig: hidden field."
        # self.login()
        self.login_as_root()

        hidden_fname = 'phone'
        FieldsConfig.objects.create(
            content_type=FakeContact,
            descriptions=[(hidden_fname, {FieldsConfig.HIDDEN: True})],
        )

        response = self.assertPOST200(
            self._build_add_url(self.contact_ct),
            data={'cells': f'regular_field-{hidden_fname}'},
        )
        self.assertFormError(
            response.context['form'],
            field='cells',
            errors=_('This value is invalid: %(value)s') % {'value': hidden_fname},
        )

    def test_create_error03(self):
        "Disabled RelationType."
        # self.login()
        self.login_as_root()

        disabled_rtype = RelationType.objects.smart_update_or_create(
            ('test-subject_disabled', 'disabled'),
            ('test-object_disabled',  'whatever'),
        )[0]
        disabled_rtype.enabled = False
        disabled_rtype.save()

        response = self.assertPOST200(
            self._build_add_url(self.contact_ct),
            data={'cells': f'relation-{disabled_rtype.id}'},
        )
        self.assertFormError(
            response.context['form'],
            field='cells',
            errors=_('This type of relationship is disabled.'),
        )

    @override_settings(FILTERS_INITIAL_PRIVATE=True)
    def test_create_settings(self):
        "Use FILTERS_INITIAL_PRIVATE."
        # self.login()
        self.login_as_root()

        response = self.assertGET200(self._build_add_url(self.contact_ct))
        self.assertIs(response.context['form'].initial.get('is_private'), True)

    def test_create_missing_lv_absolute_url(self):
        "Missing get_lv_absolute_url() class-method."
        with self.assertRaises(AttributeError):
            FakeProduct.get_lv_absolute_url()

        # self.login()
        self.login_as_root()

        ct = ContentType.objects.get_for_model(FakeProduct)
        self.assertFalse(HeaderFilter.objects.filter(entity_type=ct))

        url = self._build_add_url(ct)
        self.assertGET200(url)

        response = self.client.post(
            url,
            data={
                'name':  'DefaultHeaderFilter',
                'cells': 'regular_field-name',
            },
        )
        self.assertNoFormError(response, status=302)
        self.assertRedirects(response, '/')

    def test_edit01(self):
        # self.login()
        self.login_as_root()

        field1 = 'first_name'
        hf = HeaderFilter.objects.create_if_needed(
            pk='tests-hf_contact', name='Contact view',
            model=FakeContact, is_custom=True,
            cells_desc=[EntityCellRegularField.build(model=FakeContact, name=field1)],
        )

        url = hf.get_edit_absolute_url()
        response = self.client.get(url)
        self.assertTemplateUsed(response, 'creme_core/forms/header-filter.html')
        self.assertContains(
            response,
            _('Edit the view of list «%(view)s»') % {'view': hf.name},
        )

        with self.assertNoException():
            context = response.context
            cells_f      = context['form'].fields['cells']
            submit_label = context['submit_label']

        self.assertListEqual(hf.cells, cells_f.initial)
        self.assertEqual(_('Save the modified view'), submit_label)

        name = 'Entity view v2'
        field2 = 'last_name'
        response = self.client.post(
            url,
            data={
                'name':  name,
                'cells': f'regular_field-{field1},regular_field-{field2}',
            },
        )
        self.assertNoFormError(response, status=302)

        hf = self.refresh(hf)
        self.assertEqual(name, hf.name)
        self.assertTrue(hf.is_custom)
        self.assertListEqual(
            [
                EntityCellRegularField.build(FakeContact, field1),
                EntityCellRegularField.build(FakeContact, field2),
            ],
            hf.cells
        )

        self.assertRedirects(response, FakeContact.get_lv_absolute_url())

    def test_edit02(self):
        "Not custom -> can be still edited."
        # self.login()
        self.login_as_root()

        name = 'Contact view'
        field1 = 'first_name'
        hf = HeaderFilter.objects.create_if_needed(
            pk='tests-hf_contact', name=name,
            model=FakeContact, is_custom=False,
            cells_desc=[EntityCellRegularField.build(model=FakeContact, name=field1)],
        )

        url = hf.get_edit_absolute_url()
        self.assertGET200(url)

        name += ' (edited)'
        field2 = 'last_name'
        response = self.client.post(
            url,
            follow=True,
            data={
                'name':  name,
                'cells': f'regular_field-{field2},regular_field-{field1}',
            },
        )
        self.assertNoFormError(response)

        hf = self.refresh(hf)
        self.assertEqual(name, hf.name)
        self.assertFalse(hf.is_custom)
        self.assertListEqual(
            [
                EntityCellRegularField.build(FakeContact, field2),
                EntityCellRegularField.build(FakeContact, field1),
            ],
            hf.cells,
        )

    def test_edit03(self):
        "Cannot edit HeaderFilter that belongs to another user."
        # self.login(is_superuser=False)
        self.login_as_standard()

        hf = HeaderFilter.objects.create_if_needed(
            pk='tests-hf_contact', name='Contact view',
            # model=FakeContact, is_custom=True, user=self.other_user,
            model=FakeContact, is_custom=True, user=self.get_root_user(),
        )
        self.assertGET403(hf.get_edit_absolute_url())

    def test_edit04(self):
        "User do not have the app credentials"
        # user = self.login(is_superuser=False, allowed_apps=['documents'])
        user = self.login_as_standard(allowed_apps=['documents'])

        hf = HeaderFilter.objects.create_if_needed(
            pk='tests-hf_contact', name='Contact view',
            model=FakeContact, is_custom=True, user=user,
        )
        self.assertGET403(hf.get_edit_absolute_url())

    def test_edit05(self):
        "User belongs to the team -> OK."
        # user = self.login(is_superuser=False)
        user = self.login_as_standard()
        my_team = self.create_team('TeamTitan', user)

        hf = HeaderFilter.objects.create_if_needed(
            pk='tests-hf_contact', name='Contact view',
            model=FakeContact, is_custom=True, user=my_team,
        )
        self.assertGET200(hf.get_edit_absolute_url())

    def test_edit06(self):
        "User does not belong to the team -> error."
        # user = self.login(is_superuser=False)
        user = self.login_as_standard()

        my_team = self.create_team('TeamTitan')  # 'user' is not a teammate
        self.create_team('A-team', user)

        hf = HeaderFilter.objects.create_if_needed(
            pk='tests-hf_contact', name='Contact view',
            model=FakeContact, is_custom=True, user=my_team,
        )
        self.assertGET403(hf.get_edit_absolute_url())

    def test_edit07(self):
        "Private filter -> cannot be edited by another user (even a super-user)."
        # self.login()
        self.login_as_root()

        hf = HeaderFilter.objects.create_if_needed(
            pk='tests-hf_contact', name='Contact view',
            model=FakeContact, is_custom=True,
            # is_private=True, user=self.other_user,
            is_private=True, user=self.create_user(),
        )
        self.assertGET403(hf.get_edit_absolute_url())

    def test_edit08(self):
        "Staff users can edit all HeaderFilters + private filters must be assigned."
        # self.login(is_staff=True)
        self.login_as_super(is_staff=True)

        hf = HeaderFilter.objects.create_if_needed(
            pk='tests-hf_contact', name='Contact view',
            model=FakeContact, is_custom=True,
            # is_private=True, user=self.other_user,
            is_private=True, user=self.get_root_user(),
        )
        url = hf.get_edit_absolute_url()
        self.assertGET200(url)

        response = self.assertPOST200(
            url,
            follow=True,
            data={
                'name':       hf.name,
                'user':       '',
                'is_private': 'on',
                'cells':      'regular_field-last_name',
            },
        )
        self.assertFormError(
            response.context['form'],
            field='user',
            errors=_('A private view of list must be assigned to a user/team.'),
        )

    def test_edit09(self):
        "Not custom filter cannot be private + callback URL."
        # user = self.login()
        user = self.login_as_root_and_get()

        hf = HeaderFilter.objects.create_if_needed(
            pk='tests-hf_contact', name='Contact view',
            model=FakeContact, is_custom=False,
        )
        url = hf.get_edit_absolute_url()
        self.assertGET200(url)

        callback = FakeOrganisation.get_lv_absolute_url()
        response = self.client.post(
            url,
            data={
                'name':       hf.name,
                'user':       user.id,
                'is_private': 'on',  # Should not be used
                'cells':      'regular_field-last_name',
                'cancel_url': callback,
            },
        )
        self.assertNoFormError(response, status=302)
        self.assertFalse(self.refresh(hf).is_private)

        self.assertRedirects(response, callback)

    def test_edit_hidden_fields(self):
        # self.login()
        self.login_as_root()

        valid_fname = 'last_name'
        hidden_fname1 = 'phone'
        hidden_fname2 = 'birthday'
        build_cell = partial(EntityCellRegularField.build, model=FakeContact)
        hf = HeaderFilter.objects.create_if_needed(
            pk='tests-hf_contact', name='Contact view',
            model=FakeContact, is_custom=True,
            cells_desc=[
                build_cell(name=valid_fname),
                build_cell(name=hidden_fname1),
            ],
        )
        FieldsConfig.objects.create(
            content_type=FakeContact,
            descriptions=[
                (hidden_fname1, {FieldsConfig.HIDDEN: True}),
                (hidden_fname2, {FieldsConfig.HIDDEN: True}),
            ],
        )

        url = hf.get_edit_absolute_url()
        response1 = self.assertPOST200(
            url,
            data={'cells': f'regular_field-{hidden_fname2}'},
        )
        self.assertFormError(
            response1.context['form'],
            field='cells',
            errors=_('This value is invalid: %(value)s') % {'value': hidden_fname2},
        )

        # Was already in the HeaderFilter => still proposed
        response2 = self.client.post(
            url,
            follow=True,
            data={
                'name': hf.name,
                'cells': f'regular_field-{hidden_fname1}'
            },
        )
        self.assertNoFormError(response2)

    def test_edit_disabled_rtypes(self):
        # self.login()
        self.login_as_root()

        create_rtype = RelationType.objects.smart_update_or_create
        rtype1 = create_rtype(
            ('test-subject_loves', 'is loving'),
            ('test-object_loves',  'is loved by'),
        )[0]
        disabled_rtype1 = create_rtype(
            ('test-subject_disabled1', 'disabled #1'),
            ('test-object_disabled1',  'whatever #1'),
        )[0]
        disabled_rtype2 = create_rtype(
            ('test-subject_disabled2', 'disabled #2'),
            ('test-object_disabled2', 'whatever #2'),
        )[0]

        build_cell = partial(EntityCellRelation, model=FakeContact)
        hf = HeaderFilter.objects.create_if_needed(
            pk='tests-hf_contact', name='Contact view',
            model=FakeContact, is_custom=True,
            cells_desc=[
                build_cell(rtype=rtype1),
                build_cell(rtype=disabled_rtype1),
            ],
        )

        for disabled in (disabled_rtype1, disabled_rtype2):
            disabled.enabled = False
            disabled.save()

        url = hf.get_edit_absolute_url()
        response1 = self.assertPOST200(
            url,
            data={'cells': f'relation-{disabled_rtype2.id}'},
        )
        self.assertFormError(
            response1.context['form'],
            field='cells',
            errors=_('This type of relationship is disabled.'),
        )

        # Was already in the HeaderFilter => still proposed
        response2 = self.client.post(
            url,
            follow=True,
            data={
                'name': hf.name,
                'cells': f'relation-{disabled_rtype1.id}',
            },
        )
        self.assertNoFormError(response2)

    def test_delete01(self):
        # self.login()
        self.login_as_root()

        hf = HeaderFilter.objects.create_if_needed(
            pk='tests-hf_contact', name='Contact view',
            model=FakeContact, is_custom=True,
            cells_desc=[EntityCellRegularField.build(model=FakeContact, name='first_name')],
        )
        self.assertPOST200(self.DELETE_URL, follow=True, data={'id': hf.id})
        self.assertDoesNotExist(hf)

    def test_delete02(self):
        "Not custom -> not deletable."
        # self.login()
        self.login_as_root()

        hf = HeaderFilter.objects.create_if_needed(
            pk='tests-hf_contact', name='Contact view',
            model=FakeContact, is_custom=False,
        )
        self.client.post(self.DELETE_URL, data={'id': hf.id})
        self.assertStillExists(hf)

    def test_delete03(self):
        "Belongs to another user."
        # self.login(is_superuser=False)
        self.login_as_standard()

        hf = HeaderFilter.objects.create_if_needed(
            pk='tests-hf_contact', name='Contact view',
            # model=FakeContact, is_custom=True, user=self.other_user,
            model=FakeContact, is_custom=True, user=self.get_root_user(),
        )
        self.client.post(self.DELETE_URL, data={'id': hf.id})
        self.assertStillExists(hf)

    def test_delete04(self):
        "The user belongs to the owner team -> OK."
        # user = self.login(is_superuser=False)
        user = self.login_as_standard()
        my_team = self.create_team('TeamTitan', user)

        hf = HeaderFilter.objects.create_if_needed(
            pk='tests-hf_contact', name='Contact view',
            model=FakeContact, is_custom=True, user=my_team,
        )
        self.assertPOST200(self.DELETE_URL, data={'id': hf.id}, follow=True)
        self.assertDoesNotExist(hf)

    def test_delete05(self):
        "Belongs to a team (not mine) -> KO."
        # user = self.login(is_superuser=False)
        user = self.login_as_standard()

        a_team = self.create_team('TeamTitan', self.get_root_user())
        self.create_team('A-team', user)

        hf = HeaderFilter.objects.create_if_needed(
            pk='tests-hf_contact', name='Contact view',
            model=FakeContact, is_custom=True, user=a_team,
        )
        self.client.post(self.DELETE_URL, data={'id': hf.id}, follow=True)
        self.assertStillExists(hf)

    def test_delete06(self):
        "Logged as superuser."
        # self.login()
        self.login_as_root()

        hf = HeaderFilter.objects.create_if_needed(
            pk='tests-hf_contact', name='Contact view',
            # model=FakeContact, is_custom=True, user=self.other_user,
            model=FakeContact, is_custom=True, user=self.create_user(),
        )
        self.client.post(self.DELETE_URL, data={'id': hf.id})
        self.assertDoesNotExist(hf)

    def test_hfilters_for_ctype01(self):
        # self.login()
        self.login_as_root()

        response = self.assertGET200(
            self._build_get4ctype_url(ContentType.objects.get_for_model(FakeMailingList))
        )
        self.assertListEqual([], response.json())

    def test_hfilters_for_ctype02(self):
        # user = self.login()
        user = self.login_as_root_and_get()

        create_hf = HeaderFilter.objects.create_if_needed
        name01 = 'ML view01'
        name02 = 'ML view02'
        name03 = 'ML view03'
        pk_fmt = 'tests-hf_ml{}'.format
        hf01 = create_hf(
            pk=pk_fmt(1), name=name01, model=FakeMailingList,  is_custom=False,
        )
        hf02 = create_hf(
            pk=pk_fmt(2), name=name02, model=FakeMailingList,  is_custom=True,
        )
        create_hf(
            pk='tests-hf_orga01', name='Orga view', model=FakeOrganisation, is_custom=True,
        )
        hf03 = create_hf(
            pk=pk_fmt(3),  name=name03, model=FakeMailingList,  is_custom=True,
            is_private=True, user=user,
        )
        create_hf(
            pk=pk_fmt(4), name='Private', model=FakeMailingList, is_custom=True,
            # is_private=True, user=self.other_user,
            is_private=True, user=self.create_user(),
        )

        response = self.assertGET200(
            self._build_get4ctype_url(ContentType.objects.get_for_model(FakeMailingList))
        )
        self.assertListEqual(
            [[hf01.id, name01], [hf02.id, name02], [hf03.id, name03]],
            response.json()
        )

    def test_hfilters_for_ctype03(self):
        "No app credentials."
        # self.login(is_superuser=False, allowed_apps=['documents'])
        self.login_as_standard(allowed_apps=['documents'])
        self.assertGET403(self._build_get4ctype_url(self.contact_ct))
