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
    CustomEntityType,
    CustomField,
    EntityFilter,
    FakeContact,
    FakeMailingList,
    FakeOrganisation,
    FakeProduct,
    FieldsConfig,
    HeaderFilter,
    RelationType,
    SettingValue,
)
from creme.creme_core.setting_keys import global_filters_edition_key
from creme.creme_core.tests.base import CremeTestCase
from creme.creme_core.tests.fake_constants import FAKE_REL_SUB_EMPLOYED_BY


class HeaderFilterViewsTestCase(CremeTestCase):
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
        return reverse('creme_core__hfilters', query={'ct_id': ctype.id})

    @override_settings(FILTERS_INITIAL_PRIVATE=False)
    def test_create01(self):
        self.login_as_root()

        self.assertFalse(
            SettingValue.objects.get_4_key(global_filters_edition_key).value
        )

        ct = ContentType.objects.get_for_model(FakeMailingList)
        self.assertFalse(HeaderFilter.objects.filter(entity_type=ct))

        url = self._build_add_url(ct)
        response = self.client.get(url)
        self.assertTemplateUsed(response, 'creme_core/forms/header-filter.html')
        self.assertContains(
            response,
            _('Create a view of list for «%(ctype)s»') % {'ctype': 'Test Mailing list'},
        )

        with self.assertNoException():
            form = response.context['form']
            user_f = form.fields['user']

        self.assertIs(form.initial.get('is_private'), False)
        self.assertEqual(
            _(
                'If you assign an owner, only the owner can edit or delete the view; '
                'views without owner can only be edited/deleted by superusers'
            ),
            user_f.help_text,
        )

        # POST ---
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

        # List-view ---
        context = self.assertGET200(lv_url).context
        selected_hfilter = context['header_filters'].selected
        self.assertIsInstance(selected_hfilter, HeaderFilter)
        self.assertEqual(hfilter.id, selected_hfilter.id)
        self.assertEqual(hfilter.id, context['list_view_state'].header_filter_id)

    def test_create02(self):
        user = self.login_as_root_and_get()
        lv_url = FakeContact.get_lv_absolute_url()

        setting_value = SettingValue.objects.get_4_key(global_filters_edition_key)
        setting_value.value = True
        setting_value.save()

        # Create a view to post the entity filter
        HeaderFilter.objects.proxy(
            id='creme_core-tests_views_header_filter_test_create02',
            name='A FakeContact view',  # Starts with "A" => first
            model=FakeContact,
            cells=[
                (EntityCellRegularField, 'last_name'),
                (EntityCellRegularField, 'first_name'),
                (EntityCellRegularField, 'email'),
            ],
        ).get_or_create()

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
        response1 = self.assertPOST200(lv_url, data={'filter': efilter.id})
        self.assertEqual(efilter.id, response1.context['list_view_state'].entity_filter_id)

        # GET ---
        ct = self.contact_ct
        loves = RelationType.objects.builder(
            id='test-subject_love', predicate='Is loving',
        ).symmetric(id='test-object_love', predicate='Is loved by').get_or_create()[0]
        customfield = CustomField.objects.create(
            name='Size (cm)',
            field_type=CustomField.INT,
            content_type=ct,
        )
        funcfield = function_field_registry.get(FakeContact, 'get_pretty_properties')

        url = self._build_add_url(ct)
        context2 = self.assertGET200(url).context

        with self.assertNoException():
            fields = context2['form'].fields
            cells_f = fields['cells']
            user_f = fields['user']

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
            cells_f.initial,
        )
        self.assertEqual(
            _(
                'If you assign an owner, only the owner can edit or delete the view; '
                'views without owner can be edited/deleted by all users'
            ),
            user_f.help_text,
        )

        # POST ---
        field_name = 'first_name'
        name = 'DefaultHeaderFilter'
        response3 = self.client.post(
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
        self.assertNoFormError(response3)

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

        self.assertRedirects(response3, lv_url)

        # List-view ---
        context4 = self.assertGET200(lv_url).context
        selected_hfilter = context4['header_filters'].selected
        self.assertIsInstance(selected_hfilter, HeaderFilter)
        self.assertEqual(hfilter.id, selected_hfilter.id)

        lvs = context4['list_view_state']
        self.assertEqual(hfilter.id, lvs.header_filter_id)
        self.assertEqual(efilter.id, lvs.entity_filter_id)

    def test_create__app_credentials(self):
        "Check app credentials."
        user = self.login_as_standard(allowed_apps=['documents'])

        uri = self._build_add_url(self.contact_ct)
        self.assertGET403(uri)

        # ---
        role = user.role
        role.allowed_apps = ['documents', 'creme_core']
        role.save()
        self.assertGET200(uri)

    def test_create__private_for_other(self):
        "Cannot create a private filter for another user (but OK with one of our teams)."
        user = self.login_as_root_and_get()
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

    def test_create__callback(self):
        "Use cancel_url for redirection."
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

    def test_create__staff_user(self):
        "A staff user can create a private filter for another user."
        self.login_as_super(is_staff=True)

        name = 'DefaultHeaderFilter'
        response = self.client.post(
            self._build_add_url(self.contact_ct),
            follow=True,
            data={
                'name': name,
                'user': self.get_root_user().id,
                'is_private': 'on',
                'cells': 'regular_field-first_name',
            },
        )
        self.assertNoFormError(response)
        self.get_object_or_fail(HeaderFilter, name=name)

    def test_create__error__not_entity_type(self):
        self.login_as_root()
        self.assertGET409(self._build_add_url(ContentType.objects.get_for_model(RelationType)))

    def test_create__error__field_is_hidden(self):
        "FieldsConfig: hidden field."
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
            self.get_form_or_fail(response),
            field='cells',
            errors=_('This value is invalid: %(value)s') % {'value': hidden_fname},
        )

    def test_create__error__disabled_relationtype(self):
        self.login_as_root()

        disabled_rtype = RelationType.objects.builder(
            id='test-subject_disabled', predicate='disabled',
            enabled=False,  # <==
        ).symmetric(id='test-object_disabled', predicate='whatever').get_or_create()[0]
        response = self.assertPOST200(
            self._build_add_url(self.contact_ct),
            data={'cells': f'relation-{disabled_rtype.id}'},
        )
        self.assertFormError(
            self.get_form_or_fail(response),
            field='cells',
            errors=_('This type of relationship is disabled.'),
        )

    @override_settings(FILTERS_INITIAL_PRIVATE=True)
    def test_create__settings(self):
        "Use FILTERS_INITIAL_PRIVATE."
        self.login_as_root()

        response = self.assertGET200(self._build_add_url(self.contact_ct))
        self.assertIs(self.get_form_or_fail(response).initial.get('is_private'), True)

    def test_create__missing_lv_absolute_url(self):
        "Missing get_lv_absolute_url() class-method."
        with self.assertRaises(AttributeError):
            FakeProduct.get_lv_absolute_url()

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

    def test_create__custom_entity(self):
        self.login_as_root()

        ce_type = self.get_object_or_fail(CustomEntityType, id=1)
        ce_type.enabled = True
        ce_type.name = 'Shop'
        ce_type.plural_name = 'Shops'
        ce_type.save()

        model = ce_type.entity_model
        ct = ContentType.objects.get_for_model(model)
        name = 'Complete view'
        self.assertNoFormError(self.client.post(
            self._build_add_url(ct),
            follow=True,
            data={
                'name':  'Complete view',
                'cells': 'regular_field-name,regular_field-description',
            },
        ))

        hfilter = self.get_alone_element(HeaderFilter.objects.filter(entity_type=ct))
        self.assertEqual(name, hfilter.name)
        self.assertListEqual(
            [
                EntityCellRegularField.build(model, 'name'),
                EntityCellRegularField.build(model, 'description'),
            ],
            hfilter.cells,
        )

    def test_edit(self):
        self.login_as_root()

        field1 = 'first_name'
        hf = HeaderFilter.objects.proxy(
            id='tests-hf_contact', name='Contact view',
            model=FakeContact, is_custom=True,
            cells=[(EntityCellRegularField, field1)],
        ).get_or_create()[0]

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

    def test_edit__not_custom(self):
        "Not custom -> can be still edited."
        self.login_as_root()

        name = 'Contact view'
        field1 = 'first_name'
        hf = HeaderFilter.objects.proxy(
            id='tests-hf_contact', name=name,
            model=FakeContact, is_custom=False,
            cells=[(EntityCellRegularField, field1)],
        ).get_or_create()[0]

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

    def test_edit__error__not_owner(self):
        "Cannot edit HeaderFilter that belongs to another user."
        self.login_as_standard()

        hf = HeaderFilter.objects.proxy(
            id='tests-hf_contact', name='Contact view', model=FakeContact,
            is_custom=True, user=self.get_root_user(), cells=[],
        ).get_or_create()[0]
        self.assertGET403(hf.get_edit_absolute_url())

    def test_edit__error__app_credentials(self):
        "User do not have the app credentials."
        user = self.login_as_standard(allowed_apps=['documents'])

        hf = HeaderFilter.objects.proxy(
            id='tests-hf_contact', name='Contact view',
            model=FakeContact, is_custom=True, user=user, cells=[],
        ).get_or_create()[0]
        self.assertGET403(hf.get_edit_absolute_url())

    def test_edit__teammate(self):
        "User belongs to the team -> OK."
        user = self.login_as_standard()
        my_team = self.create_team('TeamTitan', user)

        hf = HeaderFilter.objects.proxy(
            id='tests-hf_contact', name='Contact view',
            model=FakeContact, is_custom=True, user=my_team, cells=[],
        ).get_or_create()[0]
        self.assertGET200(hf.get_edit_absolute_url())

    def test_edit__error__not_teammate(self):
        "User does not belong to the team -> error."
        user = self.login_as_standard()

        my_team = self.create_team('TeamTitan')  # 'user' is not a teammate
        self.create_team('A-team', user)

        hf = HeaderFilter.objects.proxy(
            id='tests-hf_contact', name='Contact view',
            model=FakeContact, is_custom=True, user=my_team, cells=[],
        ).get_or_create()[0]
        self.assertGET403(hf.get_edit_absolute_url())

    def test_edit__error__forbidden_private(self):
        "Private filter -> cannot be edited by another user (even a super-user)."
        self.login_as_root()

        hf = HeaderFilter.objects.proxy(
            id='tests-hf_contact', name='Contact view',
            model=FakeContact, is_custom=True,
            is_private=True, user=self.create_user(), cells=[],
        ).get_or_create()[0]
        self.assertGET403(hf.get_edit_absolute_url())

    def test_edit__staff_user(self):
        "Staff users can edit all HeaderFilters + private filters must be assigned."
        self.login_as_super(is_staff=True)

        hf = HeaderFilter.objects.proxy(
            id='tests-hf_contact', name='Contact view',
            model=FakeContact, is_custom=True,
            is_private=True, user=self.get_root_user(), cells=[],
        ).get_or_create()[0]
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
            self.get_form_or_fail(response),
            field='user',
            errors=_('A private view of list must be assigned to a user/team.'),
        )

    def test_edit__not_custom_private(self):
        "Not custom filter cannot be private + callback URL."
        user = self.login_as_root_and_get()

        hf = HeaderFilter.objects.proxy(
            id='tests-hf_contact', name='Contact view',
            model=FakeContact, is_custom=False, cells=[],
        ).get_or_create()[0]
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

    def test_edit__hidden_fields(self):
        self.login_as_root()

        valid_fname = 'last_name'
        hidden_fname1 = 'phone'
        hidden_fname2 = 'birthday'
        hf = HeaderFilter.objects.proxy(
            id='tests-hf_contact', name='Contact view',
            model=FakeContact, is_custom=True,
            cells=[
                (EntityCellRegularField, valid_fname),
                (EntityCellRegularField, hidden_fname1),
            ],
        ).get_or_create()[0]
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

    def test_edit__disabled_rtypes(self):
        self.login_as_root()

        rtype1 = RelationType.objects.builder(
            id='test-subject_loves', predicate='is loving',
        ).symmetric(id='test-object_loves', predicate='is loved by').get_or_create()[0]
        disabled_rtype1 = RelationType.objects.builder(
            id='test-subject_disabled1', predicate='disabled #1',
            enabled=False,
        ).symmetric(id='test-object_disabled1', predicate='whatever #1').get_or_create()[0]
        disabled_rtype2 = RelationType.objects.builder(
            id='test-subject_disabled2', predicate='disabled #2',
            enabled=False,
        ).symmetric(id='test-object_disabled2', predicate='whatever #2').get_or_create()[0]

        build_cell = partial(EntityCellRelation, model=FakeContact)
        hf = HeaderFilter.objects.proxy(
            id='tests-hf_contact', name='Contact view',
            model=FakeContact, is_custom=True,
            cells=[
                build_cell(rtype=rtype1),
                build_cell(rtype=disabled_rtype1),
            ],
        ).get_or_create()[0]

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

    def test_clone(self):
        user = self.login_as_root_and_get()

        # GET (404) ---
        pk = 'tests-hf_contact'
        url = reverse('creme_core__clone_hfilter', args=(pk,))
        self.assertGET404(url)

        # GET ---
        cells = [
            EntityCellRegularField.build(model=FakeContact, name='first_name'),
            EntityCellFunctionField(
                model=FakeContact,
                func_field=function_field_registry.get(FakeContact, 'get_pretty_properties'),
            ),
        ]
        source_hf = HeaderFilter.objects.proxy(
            id=pk, name='A contact view', model=FakeContact, cells=cells,
        ).get_or_create()[0]
        self.assertFalse(source_hf.is_custom)
        self.assertFalse(source_hf.is_private)

        lv_url = FakeContact.get_lv_absolute_url()
        lv_response1 = self.assertGET200(lv_url)
        self.assertEqual(source_hf.id, lv_response1.context['list_view_state'].header_filter_id)

        # --------------------------
        GET_response = self.assertGET200(url)
        self.assertTemplateUsed(GET_response, 'creme_core/forms/header-filter.html')
        self.assertContains(
            GET_response,
            _('Create a view of list for «%(ctype)s»') % {'ctype': 'Test Contact'},
        )

        with self.assertNoException():
            context1 = GET_response.context
            submit_label = context1['submit_label']

            form1 = context1['form']
            edited_instance_id = form1.instance.id

            fields1 = form1.fields
            cells_f = fields1['cells']
            user_f = fields1['user']
            is_private_f = fields1['is_private']

        self.assertEqual(HeaderFilter.save_label, submit_label)
        self.assertEqual('', edited_instance_id)
        self.assertEqual(cells, cells_f.initial)
        self.assertEqual(user.id, user_f.initial)
        self.assertTrue(is_private_f.initial)

        # POST ---
        field_name1 = 'first_name'
        field_name2 = 'last_name'
        name = 'Cloned filter'
        POST_response = self.client.post(
            url,
            follow=True,
            data={
                'name': name,
                'user': user.id,
                'is_private': 'on',
                'cells': f'regular_field-{field_name1},regular_field-{field_name2}',
            },
        )
        self.assertNoFormError(POST_response)

        hfilter = self.get_object_or_fail(HeaderFilter, name=name)
        self.assertNotEqual(source_hf.id, hfilter.id)
        self.assertEqual(user, hfilter.user)
        self.assertTrue(hfilter.is_private)
        self.assertTrue(hfilter.is_custom)
        self.assertListEqual(
            [
                EntityCellRegularField.build(FakeContact, field_name1),
                EntityCellRegularField.build(FakeContact, field_name2),
            ],
            hfilter.cells,
        )

        self.assertRedirects(POST_response, lv_url)

        # List-view ---
        lv_context2 = self.assertGET200(lv_url).context
        self.assertEqual(hfilter.id, lv_context2['header_filters'].selected.id)
        self.assertEqual(hfilter.id, lv_context2['list_view_state'].header_filter_id)

    def test_clone__apps_credentials(self):
        self.login_as_standard(allowed_apps=['persons'])

        source_hf = HeaderFilter.objects.proxy(
            id='tests-hf_contact', name='A contact view', model=FakeContact,
            cells=[(EntityCellRegularField, 'last_name')],
        ).get_or_create()[0]
        self.assertGET403(reverse('creme_core__clone_hfilter', args=(source_hf.id,)))

    def test_clone__custom_entity(self):
        user = self.login_as_root_and_get()

        ce_type = self.get_object_or_fail(CustomEntityType, id=1)
        ce_type.enabled = True
        ce_type.name = 'Shop'
        ce_type.plural_name = 'Shops'
        ce_type.save()

        model = ce_type.entity_model

        ffield = function_field_registry.get(model, 'get_pretty_properties')
        cells = [
            EntityCellRegularField.build(model=model, name='name'),
            EntityCellFunctionField(model=model, func_field=ffield),
        ]
        source_hf = HeaderFilter.objects.proxy(
            id='creme_core-userhf_creme_core-customeentity1-1',
            name='Source view', model=model, cells=cells,
        ).get_or_create()[0]

        name = 'Cloned filter'
        self.assertNoFormError(self.client.post(
            reverse('creme_core__clone_hfilter', args=(source_hf.id,)),
            follow=True,
            data={
                'name': name,
                'user': user.id,
                'is_private': 'on',
                'cells': f'{cells[0].key},{cells[1].key},regular_field-description',
            },
        ))

        hfilter = self.get_object_or_fail(HeaderFilter, name=name)
        self.assertEqual(name, hfilter.name)
        self.assertListEqual(
            [
                EntityCellRegularField.build(model, 'name'),
                EntityCellFunctionField(model=model, func_field=ffield),
                EntityCellRegularField.build(model, 'description'),
            ],
            hfilter.cells,
        )

    def test_delete(self):
        self.login_as_root()

        hf = HeaderFilter.objects.proxy(
            id='tests-hf_contact', name='Contact view',
            model=FakeContact, is_custom=True,
            cells=[(EntityCellRegularField, 'first_name')],
        ).get_or_create()[0]
        self.assertPOST200(self.DELETE_URL, follow=True, data={'id': hf.id})
        self.assertDoesNotExist(hf)

    def test_delete__not_custom(self):
        "Not custom -> not deletable."
        self.login_as_root()

        hf = HeaderFilter.objects.proxy(
            id='tests-hf_contact', name='Contact view',
            model=FakeContact, is_custom=False, cells=[],
        ).get_or_create()[0]
        self.assertPOST403(self.DELETE_URL, data={'id': hf.id})
        self.assertStillExists(hf)

    def test_delete__not_owner(self):
        "Belongs to another user."
        self.login_as_standard()

        hf = HeaderFilter.objects.proxy(
            id='tests-hf_contact', name='Contact view', model=FakeContact,
            is_custom=True, user=self.get_root_user(), cells=[],
        ).get_or_create()[0]
        self.assertPOST403(self.DELETE_URL, data={'id': hf.id})
        self.assertStillExists(hf)

    def test_delete__teammate(self):
        "The user belongs to the owner team -> OK."
        model = FakeContact
        user = self.login_as_standard(listable_models=[model])
        my_team = self.create_team('TeamTitan', user)

        hf = HeaderFilter.objects.proxy(
            id='tests-hf_contact', name='Contact view',
            model=model, is_custom=True, user=my_team, cells=[],
        ).get_or_create()[0]
        self.assertPOST200(self.DELETE_URL, data={'id': hf.id}, follow=True)
        self.assertDoesNotExist(hf)

    def test_delete__not_teammate(self):
        "Belongs to a team (not mine) -> KO."
        user = self.login_as_standard()

        a_team = self.create_team('TeamTitan', self.get_root_user())
        self.create_team('A-team', user)

        hf = HeaderFilter.objects.proxy(
            id='tests-hf_contact', name='Contact view',
            model=FakeContact, is_custom=True, user=a_team, cells=[],
        ).get_or_create()[0]
        self.assertPOST403(self.DELETE_URL, data={'id': hf.id}, follow=True)
        self.assertStillExists(hf)

    def test_delete__superuser(self):
        "Logged as superuser."
        self.login_as_root()

        hf = HeaderFilter.objects.proxy(
            id='tests-hf_contact', name='Contact view', model=FakeContact,
            is_custom=True, user=self.create_user(), cells=[],
        ).get_or_create()[0]
        self.assertPOST200(self.DELETE_URL, data={'id': hf.id}, follow=True)
        self.assertDoesNotExist(hf)

    def test_hfilters_for_ctype01(self):
        self.login_as_root()

        response = self.assertGET200(
            self._build_get4ctype_url(ContentType.objects.get_for_model(FakeMailingList))
        )
        self.assertListEqual([], response.json())

    def test_hfilters_for_ctype02(self):
        user = self.login_as_root_and_get()

        name1 = 'ML view01'
        name2 = 'ML view02'
        name3 = 'ML view03'
        pk_fmt = 'tests-hf_ml{}'.format
        hf1 = HeaderFilter.objects.proxy(
            id=pk_fmt(1), name=name1, model=FakeMailingList, cells=[],
        ).get_or_create()[0]
        hf2 = HeaderFilter.objects.proxy(
            id=pk_fmt(2), name=name2, model=FakeMailingList, is_custom=True, cells=[],
        ).get_or_create()[0]
        HeaderFilter.objects.proxy(
            id='tests-hf_orga01', name='Orga view', model=FakeOrganisation,
            is_custom=True, cells=[],
        ).get_or_create()
        hf3 = HeaderFilter.objects.proxy(
            id=pk_fmt(3),  name=name3, model=FakeMailingList,  is_custom=True,
            is_private=True, user=user, cells=[],
        ).get_or_create()[0]
        HeaderFilter.objects.proxy(
            id=pk_fmt(4), name='Private', model=FakeMailingList, is_custom=True,
            is_private=True, user=self.create_user(), cells=[],
        ).get_or_create()

        response = self.assertGET200(
            self._build_get4ctype_url(ContentType.objects.get_for_model(FakeMailingList))
        )
        self.assertListEqual(
            [[hf1.id, name1], [hf2.id, name2], [hf3.id, name3]],
            response.json(),
        )

    def test_hfilters_for_ctype03(self):
        "No app credentials."
        self.login_as_standard(allowed_apps=['documents'])
        self.assertGET403(self._build_get4ctype_url(self.contact_ct))
