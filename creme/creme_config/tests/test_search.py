from functools import partial

from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from django.utils.translation import gettext as _

from creme.creme_core.core.entity_cell import (
    EntityCellCustomField,
    EntityCellRegularField,
)
from creme.creme_core.models import (
    CustomField,
    FakeContact,
    FakeInvoice,
    FakeInvoiceLine,
    FakeOrganisation,
    FieldsConfig,
    SearchConfigItem,
)
from creme.creme_core.tests.base import CremeTestCase
from creme.creme_core.tests.views.base import BrickTestCaseMixin
from creme.creme_core.utils.content_type import entity_ctypes
from creme.creme_core.utils.unicode_collation import collator

from ..bricks import SearchConfigBrick


class SearchConfigTestCase(BrickTestCaseMixin, CremeTestCase):
    PORTAL_URL = reverse('creme_config__search')

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        SearchConfigItem.objects.all().delete()  # TODO: backup ?

        get_ct = ContentType.objects.get_for_model
        cls.ct_contact = get_ct(FakeContact)
        cls.ct_orga    = get_ct(FakeOrganisation)

        cls.role = cls.create_role()

    def setUp(self):
        super().setUp()
        self.login_as_root()

    @staticmethod
    def _build_add_url(ctype):
        return reverse('creme_config__create_search_config', args=(ctype.id,))

    @staticmethod
    def _build_edit_url(sci):
        return reverse('creme_config__edit_search_config', args=(sci.id,))

    @staticmethod
    def _get_first_entity_ctype():
        ctypes = [*entity_ctypes()]
        ctypes.sort(key=lambda ct: collator.sort_key(str(ct)))

        return ctypes[0]

    def test_portal01(self):
        ctype = self._get_first_entity_ctype()
        self.assertFalse(SearchConfigItem.objects.filter(content_type=ctype))

        response = self.assertGET200(self.PORTAL_URL)
        self.assertTemplateUsed(response, 'creme_config/portals/search.html')
        self.assertTemplateUsed(response, 'creme_config/bricks/search-config.html')
        self.assertEqual(
            reverse('creme_core__reload_bricks'),
            response.context.get('bricks_reload_url'),
        )

        brick_node = self.get_brick_node(
            self.get_html_tree(response.content), brick=SearchConfigBrick,
        )
        title_node = self.get_html_node_or_fail(
            brick_node, ".//div[@class='search-config-group-title']",
        )
        self.assertEqual([str(ctype)], [text.strip() for text in title_node.itertext()])

        # Missing default configurations are built
        sci = self.get_object_or_fail(SearchConfigItem, content_type=ctype)
        self.assertIsNone(sci.role)
        self.assertFalse(sci.superuser)
        self.assertTrue(sci.all_fields)

    def test_portal02(self):
        "Missing default configurations are built, even when configs for users exist."
        ctype = self._get_first_entity_ctype()
        self.assertFalse(SearchConfigItem.objects.filter(content_type=ctype))

        SearchConfigItem.objects.create(content_type=ctype, superuser=True)

        self.assertGET200(self.PORTAL_URL)
        self.get_object_or_fail(
            SearchConfigItem,
            content_type=ctype, role=None, superuser=False,
        )

    def test_add01(self):
        role = self.role
        ct = self.ct_contact
        self.assertFalse(
            SearchConfigItem.objects.filter(content_type=ct, role=None, superuser=True)
        )

        url = self._build_add_url(ct)
        context = self.assertGET200(url).context
        self.assertEqual(
            _('New search configuration for «{model}»').format(model='Test Contact'),
            context.get('title'),
        )

        with self.assertNoException():
            cells_f = context['form'].fields['cells']

        self.assertFalse(cells_f.initial)

        fname1 = 'last_name'
        fname2 = 'civility__title'
        fname3 = 'sector__title'
        fname4 = 'languages__name'
        self.assertNoFormError(self.client.post(
            url,
            data={
                'role': role.id,

                'cells': f'regular_field-{fname1},'
                         f'regular_field-{fname2},'
                         f'regular_field-{fname3},'
                         f'regular_field-{fname4}'
            },
        ))

        sc_item = self.get_alone_element(SearchConfigItem.objects.filter(content_type=ct))
        self.assertEqual(role, sc_item.role)
        self.assertFalse(sc_item.superuser)
        self.assertFalse(sc_item.disabled)
        self.assertListEqual(
            [
                EntityCellRegularField.build(FakeContact, name)
                for name in (fname1, fname2, fname3, fname4)
            ],
            [*sc_item.cells],
        )

    def test_add02(self):
        "Other CT, superusers."
        ct = self.ct_orga
        self.assertFalse(SearchConfigItem.objects.filter(content_type=ct, superuser=True))

        self.assertNoFormError(self.client.post(
            self._build_add_url(ct), data={'role': ''}),
        )
        sc_item = self.get_object_or_fail(
            SearchConfigItem, content_type=ct, superuser=True, role=None,
        )
        self.assertTrue(sc_item.all_fields)

    def test_add03(self):
        "Unique configuration."
        role = self.role
        ct = self.ct_contact
        SearchConfigItem.objects.create(content_type=ct, role=role)

        role2 = self.create_role(name='CEO')

        response = self.assertGET200(self._build_add_url(ct))

        with self.assertNoException():
            role_f = response.context['form'].fields['role']
            choices = role_f.choices

        self.assertEqual(f"*{_('Superuser')}*", role_f.empty_label)

        self.assertInChoices(value=role2.id, label=str(role2), choices=choices)
        self.assertNotInChoices(value=role.id, choices=choices)

    def test_add04(self):
        "Unique configuration (super-user)."
        SearchConfigItem.objects.builder(
            model=FakeContact, role='superuser',
            fields=['first_name', 'last_name'],
        ).get_or_create()

        response = self.assertGET200(self._build_add_url(self.ct_contact))

        with self.assertNoException():
            role_f = response.context['form'].fields['role']

        self.assertIsNone(role_f.empty_label)

    def test_add_regular_fields_errors01(self):
        "Forbidden fields."
        url = self._build_add_url(self.ct_contact)

        def post(field_name, msg_fmt=None):
            response = self.assertPOST200(
                url, data={'cells': f'regular_field-{field_name}'}
            )
            if not msg_fmt:
                msg_fmt = _('This value is invalid: %(value)s')
            self.assertFormError(
                self.get_form_or_fail(response),
                field='cells',
                errors=msg_fmt % {'value': field_name},
            )

        post('birthday')
        post('is_a_nerd')
        leaf_msg_fmt = _('This field has sub-field & cannot be selected: %(value)s')
        post('sector', msg_fmt=leaf_msg_fmt)  # FK
        post('languages', msg_fmt=leaf_msg_fmt)  # M2M
        post('image__user')
        post('image__user__username')

    def test_add_regular_fields_errors02(self):
        "Fields with 'choices' are not valid."
        field_name = 'discount_unit'
        model_field = FakeInvoiceLine._meta.get_field(field_name)
        self.assertTrue(model_field.choices)

        response = self.assertPOST200(
            self._build_add_url(ContentType.objects.get_for_model(FakeInvoiceLine)),
            data={'cells': f'regular_field-{field_name}'}
        )
        self.assertFormError(
            self.get_form_or_fail(response),
            field='cells',
            errors=_('This value is invalid: %(value)s') % {'value': field_name},
        )

    def test_add_regular_fields_errors03(self):
        "Exclude DatePeriodField."
        field_name = 'periodicity'
        response = self.assertPOST200(
            self._build_add_url(ContentType.objects.get_for_model(FakeInvoice)),
            data={'cells': f'regular_field-{field_name}'}
        )
        self.assertFormError(
            self.get_form_or_fail(response),
            field='cells',
            errors=_('This value is invalid: %(value)s') % {'value': field_name},
        )

    def test_add_custom_fields(self):
        ct = self.ct_orga
        create_cfield = partial(CustomField.objects.create, content_type=ct)
        cfield1 = create_cfield(name='ID number', field_type=CustomField.STR)
        cfield2 = create_cfield(name='2nd site',  field_type=CustomField.URL)
        cfield3 = create_cfield(name='Degree',    field_type=CustomField.ENUM)
        cfield4 = create_cfield(name='Hobbies',   field_type=CustomField.MULTI_ENUM)

        self.assertNoFormError(self.client.post(
            self._build_add_url(ct),
            data={
                'cells': f'custom_field-{cfield1.id},'
                         f'custom_field-{cfield2.id},'
                         f'custom_field-{cfield3.id},'
                         f'custom_field-{cfield4.id}'
            },
        ))

        sc_item = self.get_alone_element(SearchConfigItem.objects.filter(content_type=ct))
        self.assertListEqual(
            [
                EntityCellCustomField(cf)
                for cf in (cfield1, cfield2, cfield3, cfield4)
            ],
            [*sc_item.cells],
        )

    def test_add_custom_fields_errors(self):
        "Forbidden types."
        ct = self.ct_orga

        def post(cfield):
            response = self.assertPOST200(
                self._build_add_url(ct),
                data={'cells': f'custom_field-{cfield.id}'},
            )
            self.assertFormError(
                self.get_form_or_fail(response),
                field='cells',
                errors=_('This value is invalid: %(value)s') % {'value': cfield.id},
            )

        create_cfield = partial(CustomField.objects.create, content_type=ct)
        post(create_cfield(name='To be sold?',  field_type=CustomField.BOOL))
        post(create_cfield(name='Inauguration', field_type=CustomField.DATE))
        post(create_cfield(name='Next fiesta',  field_type=CustomField.DATETIME))

    def _edit_config(self, url, sci, *field_ids, disabled=''):
        cell_keys = [
            f'regular_field-{field_id}'
            for field_id in field_ids
        ]

        response = self.client.post(
            url, data={'disabled': disabled, 'cells': ','.join(cell_keys)},
        )
        self.assertNoFormError(response)

        sci = self.refresh(sci)
        self.assertListEqual(cell_keys, [c.key for c in sci.cells])

        return sci

    def test_edit01(self):
        sci = SearchConfigItem.objects.builder(
            model=FakeContact, fields=['last_name'],
        ).get_or_create()[0]
        self.assertIsNone(sci.role)

        url = self._build_edit_url(sci)
        response = self.assertGET200(url)
        self.assertTemplateUsed(response, 'creme_core/generics/blockform/edit-popup.html')

        context = response.context
        self.assertEqual(_('Edit «{object}»').format(object=sci), context.get('title'))

        with self.assertNoException():
            cells_f = context['form'].fields['cells']

        self.assertListEqual(
            [EntityCellRegularField.build(FakeContact, 'last_name')],
            cells_f.initial,
        )

        fname1 = 'last_name'
        fname2 = 'first_name'
        sci = self._edit_config(url, sci, fname1, fname2)
        self.assertFalse(sci.disabled)

    def test_edit02(self):
        "Other CT + role + exclude BooleanField."
        sci = SearchConfigItem.objects.create(content_type=self.ct_orga, role=self.role)
        self._edit_config(self._build_edit_url(sci), sci, 'name', 'description')

    def test_edit_disabled(self):
        sci = SearchConfigItem.objects.create(content_type=self.ct_contact)
        url = self._build_edit_url(sci)

        sci = self._edit_config(url, sci, 'last_name', disabled='on')
        self.assertTrue(sci.disabled)

    def test_edit_fields_config01(self):
        "With FieldsConfig."
        model = FakeContact
        hidden_fname1 = 'position'
        hidden_fname2 = 'description'  # NB: in CremeEntity
        FieldsConfig.objects.create(
            content_type=model,
            descriptions=[
                (hidden_fname1, {FieldsConfig.HIDDEN: True}),
                (hidden_fname2, {FieldsConfig.HIDDEN: True}),
            ],
        )
        sci = SearchConfigItem.objects.builder(
            model=model, fields=['first_name'],
        ).get_or_create()[0]

        url = self._build_edit_url(sci)

        def post(hidden_name):
            response = self.assertPOST200(
                url,
                data={'cells': f'regular_field-{hidden_name}'}
            )
            self.assertFormError(
                self.get_form_or_fail(response),
                field='cells',
                errors=_('This value is invalid: %(value)s') % {'value': hidden_name},
            )

        post(hidden_fname1)
        post(hidden_fname2)

        # ---
        field_name = 'last_name'
        sci = self._edit_config(url, sci, field_name)
        self.assertListEqual(
            [f'regular_field-{field_name}'],
            [c.key for c in self.refresh(sci).cells],
        )

    def test_edit_fields_config02(self):
        "With FieldsConfig + selected hidden fields."
        model = FakeContact
        hidden_fname1 = 'description'
        hidden_fname2 = 'position'
        hidden_sub_fname2 = hidden_fname2 + '__title'
        sci = SearchConfigItem.objects.builder(
            model=model,
            fields=['first_name', hidden_fname1, hidden_sub_fname2],
        ).get_or_create()[0]

        FieldsConfig.objects.create(
            content_type=model,
            descriptions=[
                (hidden_fname1, {FieldsConfig.HIDDEN: True}),
                (hidden_fname2, {FieldsConfig.HIDDEN: True}),
            ],
        )

        field_name = 'last_name'
        sci = self._edit_config(
            self._build_edit_url(sci), sci, field_name, hidden_sub_fname2,
        )
        self.assertListEqual(
            [f'regular_field-{field_name}', f'regular_field-{hidden_sub_fname2}'],
            [c.key for c in self.refresh(sci).cells],
        )

    def test_delete01(self):
        sci = SearchConfigItem.objects.builder(
            model=FakeContact, role=self.role, fields=['first_name', 'last_name'],
        ).get_or_create()[0]
        self.assertPOST200(reverse('creme_config__delete_search_config'), data={'id': sci.id})
        self.assertDoesNotExist(sci)

    def test_delete02(self):
        "Superusers."
        sci = SearchConfigItem.objects.builder(
            model=FakeContact, role='superuser', fields=['first_name', 'last_name'],
        ).get_or_create()[0]
        self.assertPOST200(reverse('creme_config__delete_search_config'), data={'id': sci.id})
        self.assertDoesNotExist(sci)

    def test_delete03(self):
        "Cannot delete the default configuration."
        sci = SearchConfigItem.objects.builder(
            model=FakeContact, fields=['first_name', 'last_name'],
        ).get_or_create()[0]
        self.assertPOST409(reverse('creme_config__delete_search_config'), data={'id': sci.id})
        self.assertStillExists(sci)
