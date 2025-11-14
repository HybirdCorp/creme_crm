from functools import partial

from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from django.utils.translation import gettext as _

from creme.creme_core.core.entity_cell import (
    EntityCellCustomField,
    EntityCellFunctionField,
)
from creme.creme_core.gui.bricks import QuerysetBrick
from creme.creme_core.models import (
    CustomField,
    CustomFieldEnum,
    CustomFieldEnumValue,
    CustomFieldMultiEnum,
    FakeContact,
    FakeOrganisation,
    FakeSector,
    FieldsConfig,
    SearchConfigItem,
)

from ..base import CremeTestCase
from .base import BrickTestCaseMixin


class SearchViewTestCase(BrickTestCaseMixin, CremeTestCase):
    LIGHT_URL = reverse('creme_core__light_search')

    CONTACT_BRICKID = 'found-creme_core-fakecontact-'
    ORGA_BRICKID    = 'found-creme_core-fakeorganisation-'

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.contact_ct_id = ContentType.objects.get_for_model(FakeContact).id

        QuerysetBrick.page_size = 10

        cls._sci_backup = [*SearchConfigItem.objects.all()]
        SearchConfigItem.objects.all().delete()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()

        del QuerysetBrick.page_size
        assert QuerysetBrick.page_size  # In PaginatedBrick

        SearchConfigItem.objects.all().delete()
        SearchConfigItem.objects.bulk_create(cls._sci_backup)

    def assertInstanceLinkNoLabel(self, brick_node, entity):
        link_node = self.get_html_node_or_fail(
            brick_node, f".//a[@href='{entity.get_absolute_url()}']"
        )
        self.assertFalse(link_node.text.strip())

    def get_search_brick_node(self, tree, brick_id_prefix):
        prefix = f'brick-{brick_id_prefix}'

        for div_node in tree.findall('.//div'):
            if (
                'brick' in div_node.attrib.get('class', '')
                and div_node.attrib.get('id', '').startswith(prefix)
            ):
                return div_node

        self.fail(f'No brick found for prefix "{prefix}".')

    def assertNoSearchBrick(self, tree, brick_id_prefix):
        prefix = f'brick-{brick_id_prefix}'

        for div_node in tree.findall('.//div'):
            if (
                'brick' in div_node.attrib.get('class', '')
                and div_node.attrib.get('id', '').startswith(prefix)
            ):
                self.fail(f'A brick unexpectedly found for prefix "{brick_id_prefix}".')

    def _build_contacts(self, user):
        sector = FakeSector.objects.create(title='Linux dev')

        create_contact = partial(FakeContact.objects.create, user=user)
        self.linus = create_contact(
            first_name='Linus',  last_name='Torvalds',
        )
        self.alan = create_contact(
            first_name='Alan', last_name='Cox', description='Cool beard',
        )
        self.linus2 = create_contact(
            first_name='Linus',  last_name='Impostor', is_deleted=True,
        )
        self.andrew = create_contact(
            first_name='Andrew', last_name='Morton', sector=sector,
        )

    def _setup_contacts(self, *, user, disabled=False):
        SearchConfigItem.objects.builder(
            model=FakeContact,
            fields=['first_name', 'last_name', 'sector__title'],
            disabled=disabled,
        ).get_or_create()
        self._build_contacts(user=user)

    def _setup_orgas(self, user):
        SearchConfigItem.objects.builder(
            model=FakeOrganisation, fields=['name'],
        ).get_or_create()

        create_orga = partial(FakeOrganisation.objects.create, user=user)
        self.linusfo = create_orga(name='FoobarLinusFoundation')
        self.coxco   = create_orga(name='StuffCoxCorp')

    def _search(self, searched=None, ct_id=None):
        data = {}

        if searched is not None:
            data['search'] = searched

        if ct_id is not None:
            data['ct_id'] = ct_id

        return self.client.get(reverse('creme_core__search'), data=data)

    def test_search(self):
        user = self.login_as_root_and_get()
        self._setup_contacts(user=user)

        term = 'john'
        response = self._search(term, self.contact_ct_id)
        self.assertEqual(200, response.status_code)
        self.assertTemplateUsed(response, 'creme_core/search_results.html')

        ctxt = response.context
        self.assertEqual(self.contact_ct_id, ctxt.get('selected_ct_id'))
        self.assertEqual(term,               ctxt.get('searched'))

        with self.assertNoException():
            models = ctxt['models']
            verbose_names = ctxt['verbose_names']
            bricks = ctxt['bricks']
            reload_url = ctxt['bricks_reload_url']

        self.assertListEqual([FakeContact], models)
        self.assertListEqual(['Test Contact'], verbose_names)
        self.assertEqual(
            f"{reverse('creme_core__reload_search_brick')}?search={term}",
            reload_url,
        )

        # self.assertIsList(bricks, length=1)
        self.assertIsDict(bricks, length=1)

        main_bricks = bricks.get('main')
        self.assertIsList(main_bricks, length=1)

        # brick = bricks[0]
        brick = main_bricks[0]
        self.assertIsInstance(brick, QuerysetBrick)
        self.assertIn(self.CONTACT_BRICKID, brick.id)
        self.assertEqual(
            'creme_core/bricks/found-entities.html', brick.template_name,
        )

        self.assertNotContains(response, self.linus.get_absolute_url())

    def test_search_regular_fields01(self):
        "Find result in field & sub-field; deleted entities are found too."
        user = self.login_as_root_and_get()
        self._setup_contacts(user=user)

        response = self._search('linu', self.contact_ct_id)
        self.assertEqual(200, response.status_code)

        brick_node = self.get_search_brick_node(
            self.get_html_tree(response.content),
            brick_id_prefix=self.CONTACT_BRICKID,
        )

        self.assertInstanceLinkNoLabel(brick_node, entity=self.linus)
        self.assertInstanceLinkNoLabel(brick_node, entity=self.linus2)  # Deleted
        self.assertInstanceLinkNoLabel(brick_node, entity=self.andrew)  # In sector__title
        self.assertNoInstanceLink(brick_node, entity=self.alan)

    def test_search_regular_fields02(self):
        user = self.login_as_root_and_get()
        self._setup_contacts(user=user)
        self._setup_orgas(user=user)

        response = self._search('cox')
        context = response.context

        # self.assertGreaterEqual(len(context['bricks']), 2)
        self.assertGreaterEqual(len(context['bricks']['main']), 2)

        tree = self.get_html_tree(response.content)
        brick_node1 = self.get_search_brick_node(tree, brick_id_prefix=self.CONTACT_BRICKID)
        self.assertInstanceLinkNoLabel(brick_node1, entity=self.alan)
        self.assertNoInstanceLink(brick_node1, entity=self.linus)
        self.assertNoInstanceLink(brick_node1, entity=self.linus2)

        brick_node2 = self.get_search_brick_node(tree, brick_id_prefix=self.ORGA_BRICKID)
        self.assertInstanceLinkNoLabel(brick_node2, entity=self.coxco)
        self.assertNoInstanceLink(brick_node2, entity=self.linusfo)

        self.assertCountEqual({FakeContact, FakeOrganisation}, context['models'])
        self.assertCountEqual(
            [FakeContact._meta.verbose_name, FakeOrganisation._meta.verbose_name],
            context['verbose_names'],
        )

    def test_search_regular_fields03(self):
        "Error."
        user = self.login_as_root_and_get()
        self._setup_contacts(user=user)
        self._setup_orgas(user=user)

        self.assertEqual(
            _('Please enter at least {count} characters').format(count=3),
            self._search('ox').context['error_message'],
        )
        self.assertEqual(404, self._search('linus', self.UNUSED_PK).status_code)

    def test_search_regular_fields04(self):
        "No config for FakeContact."
        user = self.login_as_root_and_get()
        self._build_contacts(user=user)
        self._setup_orgas(user=user)

        response = self._search('torvalds', self.contact_ct_id)
        self.assertNoSearchBrick(
            self.get_html_tree(response.content),
            brick_id_prefix=self.CONTACT_BRICKID,
        )

    def test_search_regular_fields05(self):
        "Search only in configured fields if the config exists."
        user = self.login_as_root_and_get()
        self._setup_contacts(user=user)
        self._setup_orgas(user=user)

        linus = self.linus
        linus.description = 'He is very smart but wears ugly shorts.'
        linus.save()

        response = self._search('very smart', self.contact_ct_id)
        brick_node = self.get_search_brick_node(
            self.get_html_tree(response.content),
            brick_id_prefix=self.CONTACT_BRICKID,
        )
        self.assertNoInstanceLink(brick_node, entity=linus)

    def test_search_disabled(self):
        user = self.login_as_root_and_get()
        self._setup_contacts(user=user, disabled=True)
        self._setup_orgas(user=user)

        response = self._search('cox')
        context = response.context

        tree = self.get_html_tree(response.content)
        self.get_search_brick_node(tree, brick_id_prefix=self.ORGA_BRICKID)

        self.assertNoSearchBrick(tree, brick_id_prefix=self.CONTACT_BRICKID)

        self.assertListEqual([FakeOrganisation], context['models'])
        self.assertListEqual(
            [FakeOrganisation._meta.verbose_name],
            context['verbose_names'],
        )

    def test_search_for_role(self):
        "Use Role's config if it exists."
        user = self.login_as_standard(allowed_apps=['creme_core'])
        self.add_credentials(user.role, own='*')

        SearchConfigItem.objects.builder(
            model=FakeContact, fields=['description'], role=user.role,
        ).get_or_create()
        self._setup_contacts(user=user)

        response = self._search('bear', self.contact_ct_id)
        self.assertEqual(200, response.status_code)

        tree = self.get_html_tree(response.content)
        self.assertNoInstanceLink(tree, entity=self.linus)
        self.assertNoInstanceLink(tree, entity=self.linus2)
        self.assertInstanceLinkNoLabel(tree, entity=self.alan)

    def test_search_super_user(self):
        "Use Role's config if it exists (super-user)."
        user = self.login_as_root_and_get()

        SearchConfigItem.objects.builder(
            model=FakeContact, fields=['description'], role='superuser',
        ).get_or_create()
        self._setup_contacts(user=user)

        response = self._search('bear', self.contact_ct_id)
        self.assertEqual(200, response.status_code)

        brick_node = self.get_search_brick_node(
            self.get_html_tree(response.content),
            brick_id_prefix=self.CONTACT_BRICKID,
        )
        self.assertNoInstanceLink(brick_node, entity=self.linus)
        self.assertNoInstanceLink(brick_node, entity=self.linus2)
        self.assertInstanceLinkNoLabel(brick_node, entity=self.alan)

    def test_search_fields_config01(self):
        user = self.login_as_root_and_get()

        hidden_fname1 = 'description'
        hidden_fname2 = 'sector'
        SearchConfigItem.objects.builder(
            model=FakeContact,
            fields=[
                'first_name', 'last_name',
                hidden_fname1,
                hidden_fname2 + '__title',
            ],
        ).get_or_create()

        sector = FakeSector.objects.create(title='Linux dev')

        create_contact = partial(FakeContact.objects.create, user=user)
        linus = create_contact(
            first_name='Linus', last_name='Torvalds', description="Alan's friend",
        )
        alan = create_contact(
            first_name='Alan', last_name='Cox', description="Linus' friend",
        )
        andrew = create_contact(
            first_name='Andrew', last_name='Morton', sector=sector,
        )

        FieldsConfig.objects.create(
            content_type=FakeContact,
            descriptions=[
                (hidden_fname1, {FieldsConfig.HIDDEN: True}),
                (hidden_fname2, {FieldsConfig.HIDDEN: True}),
            ],
        )

        response = self._search('Linu', self.contact_ct_id)
        self.assertEqual(200, response.status_code)

        brick_node = self.get_search_brick_node(
            self.get_html_tree(response.content),
            brick_id_prefix=self.CONTACT_BRICKID,
        )
        self.assertInstanceLinkNoLabel(brick_node, entity=linus)
        self.assertNoInstanceLink(brick_node, entity=alan)
        self.assertNoInstanceLink(brick_node, entity=andrew)

        # TODO: assertSearchColumns(....)
        self.assertContains(response, _('First name'))
        self.assertContains(response, _('Last name'))
        self.assertNotContains(response, _('Description'))
        self.assertNotContains(response, _('Sector'))

    def test_search_fields_config02(self):
        "With FieldsConfig: all fields are hidden."
        user = self.login_as_root_and_get()

        hidden_fname = 'description'
        SearchConfigItem.objects.builder(
            model=FakeContact, fields=[hidden_fname],
        ).get_or_create()
        FieldsConfig.objects.create(
            content_type=FakeContact,
            descriptions=[(hidden_fname, {FieldsConfig.HIDDEN: True})],
        )
        self._build_contacts(user=user)

        response = self._search('Cool', self.contact_ct_id)
        self.assertEqual(200, response.status_code)

        brick_node = self.get_search_brick_node(
            self.get_html_tree(response.content),
            brick_id_prefix=self.CONTACT_BRICKID,
        )
        self.assertNoInstanceLink(brick_node, entity=self.linus)
        self.assertNoInstanceLink(brick_node, entity=self.alan)
        self.assertNoInstanceLink(brick_node, entity=self.andrew)

        # TODO: assertBrickIsEmpty(...)
        self.assertContains(
            response,
            _(
                'It seems that all fields are hidden. '
                'Ask your administrator to fix the configuration.'
            ),
        )

    def test_search_error01(self):
        "Model is not a CremeEntity."
        self.login_as_root()

        response = self._search('john', ContentType.objects.get_for_model(ContentType).id)
        self.assertEqual(409, response.status_code)

    def test_search_empty(self):
        "Empty page"
        self.login_as_root()

        response = self._search(searched='', ct_id='')
        self.assertEqual(200, response.status_code)
        self.assertTemplateUsed(response, 'creme_core/search_results.html')

    def test_search_words01(self):
        "String is split."
        user = self.login_as_root_and_get()
        self._setup_contacts(user=user)

        response = self._search('linus torval', self.contact_ct_id)
        self.assertEqual(200, response.status_code)

        brick_node = self.get_search_brick_node(
            self.get_html_tree(response.content),
            brick_id_prefix=self.CONTACT_BRICKID,
        )
        self.assertInstanceLinkNoLabel(brick_node, entity=self.linus)
        self.assertNoInstanceLink(brick_node, entity=self.linus2)
        self.assertNoInstanceLink(brick_node, entity=self.alan)
        self.assertNoInstanceLink(brick_node, entity=self.andrew)

    def test_search_words02(self):
        "Grouped words."
        user = self.login_as_root_and_get()

        SearchConfigItem.objects.builder(
            model=FakeOrganisation, fields=['name'],
        ).get_or_create()

        create_orga = partial(FakeOrganisation.objects.create, user=user)
        orga1 = create_orga(name='Foobar Foundation')
        orga2 = create_orga(name='Foobar Mega Foundation')
        orga3 = create_orga(name='Mega Foobar Foundation')

        response = self._search(
            '"Foobar Foundation"',
            ct_id=ContentType.objects.get_for_model(FakeOrganisation).id,
        )
        self.assertEqual(200, response.status_code)

        brick_node = self.get_search_brick_node(
            self.get_html_tree(response.content),
            brick_id_prefix=self.ORGA_BRICKID,
        )
        self.assertInstanceLinkNoLabel(brick_node, entity=orga1)
        self.assertInstanceLinkNoLabel(brick_node, entity=orga3)
        self.assertNoInstanceLink(brick_node, entity=orga2)

    def test_search_custom_field01(self):
        "Type <CustomField.STR>."
        user = self.login_as_root_and_get()

        ct = ContentType.objects.get_for_model(FakeOrganisation)
        cfield = CustomField.objects.create(
            name='ID number', content_type=ct, field_type=CustomField.STR,
        )

        SearchConfigItem.objects.create(
            content_type=ct, cells=[EntityCellCustomField(cfield)],
        )

        create_orga = partial(FakeOrganisation.objects.create, user=user)
        orga1 = create_orga(name='Foobar Foundation')
        orga2 = create_orga(name='Foobar Mega Foundation')
        orga3 = create_orga(name='Mega Foobar Foundation')

        cfield.value_class(custom_field=cfield, entity=orga1).set_value_n_save('ABCD123')
        cfield.value_class(custom_field=cfield, entity=orga2).set_value_n_save('HIJK789')

        response = self._search('BCD1', ct.id)
        self.assertEqual(200, response.status_code)

        brick_node = self.get_search_brick_node(
            self.get_html_tree(response.content),
            brick_id_prefix=self.ORGA_BRICKID,
        )
        self.assertInstanceLinkNoLabel(brick_node, entity=orga1)
        self.assertNoInstanceLink(brick_node, entity=orga2)
        self.assertNoInstanceLink(brick_node, entity=orga3)

    def test_search_custom_field02(self):
        "Type <CustomField.ENUM>."
        user = self.login_as_root_and_get()

        ct = ContentType.objects.get_for_model(FakeOrganisation)
        cfield = CustomField.objects.create(
            name='Type', content_type=ct, field_type=CustomField.ENUM,
        )

        create_evalue = partial(CustomFieldEnumValue.objects.create, custom_field=cfield)
        eval_small = create_evalue(value='Small')
        eval_medium = create_evalue(value='Medium')
        create_evalue(value='Big')

        create_orga = partial(FakeOrganisation.objects.create, user=user)
        orga1 = create_orga(name='Foobar Foundation')
        orga2 = create_orga(name='Foobar Mega Foundation')
        orga3 = create_orga(name='Mega Foobar Foundation')

        create_enum = partial(CustomFieldEnum.objects.create, custom_field=cfield)
        create_enum(entity=orga1, value=eval_small)
        create_enum(entity=orga2, value=eval_medium)

        SearchConfigItem.objects.create(
            content_type=ct, cells=[EntityCellCustomField(cfield)],
        )

        response = self._search('Smal', ct.id)
        self.assertEqual(200, response.status_code)

        brick_node = self.get_search_brick_node(
            self.get_html_tree(response.content),
            brick_id_prefix=self.ORGA_BRICKID,
        )
        self.assertInstanceLinkNoLabel(brick_node, entity=orga1)
        self.assertNoInstanceLink(brick_node, entity=orga2)
        self.assertNoInstanceLink(brick_node, entity=orga3)

    def test_search_custom_field03(self):
        "Type <CustomField.MULTI_ENUM>."
        user = self.login_as_root_and_get()

        ct = ContentType.objects.get_for_model(FakeOrganisation)
        cfield = CustomField.objects.create(
            name='Countries', content_type=ct, field_type=CustomField.MULTI_ENUM,
        )

        create_evalue = partial(CustomFieldEnumValue.objects.create, custom_field=cfield)
        eval_fr = create_evalue(value='France')
        eval_ger = create_evalue(value='Germany')
        create_evalue(value='Italy')

        create_orga = partial(FakeOrganisation.objects.create, user=user)
        orga1 = create_orga(name='Foobar Foundation')
        orga2 = create_orga(name='Foobar Mega Foundation')
        orga3 = create_orga(name='Mega Foobar Foundation')

        cf_memum = partial(CustomFieldMultiEnum, custom_field=cfield)
        cf_memum(entity=orga1).set_value_n_save([eval_fr])
        cf_memum(entity=orga2).set_value_n_save([eval_ger, eval_fr])

        SearchConfigItem.objects.create(
            content_type=ct, cells=[EntityCellCustomField(cfield)],
        )

        response = self._search('fran', ct.id)
        self.assertEqual(200, response.status_code)

        brick_node = self.get_search_brick_node(
            self.get_html_tree(response.content),
            brick_id_prefix=self.ORGA_BRICKID,
        )
        self.assertInstanceLinkNoLabel(brick_node, entity=orga1)
        self.assertInstanceLinkNoLabel(brick_node, entity=orga2)
        self.assertNoInstanceLink(brick_node, entity=orga3)

    def test_search_invalid_cell_type(self):
        "No error."
        self.login_as_root()

        ct = ContentType.objects.get_for_model(FakeOrganisation)
        cell = EntityCellFunctionField.build(FakeOrganisation, 'get_pretty_properties')
        self.assertIsNotNone(cell)

        SearchConfigItem.objects.create(content_type=ct, cells=[cell])

        response = self._search('cool', ct.id)
        self.assertEqual(200, response.status_code)

    def test_reload_brick(self):
        user = self.login_as_root_and_get()
        self._setup_contacts(user=user)

        url = reverse('creme_core__reload_search_brick')
        brick_id = self.CONTACT_BRICKID + '32132154'
        response = self.assertGET200(url, data={'brick_id': brick_id, 'search': 'linu'})

        results = response.json()
        self.assertIsList(results, length=1)

        result = results[0]
        self.assertIsList(result, length=2)

        self.assertEqual(brick_id, result[0])

        doc = self.get_html_tree(result[1])
        self.get_brick_node(doc, brick_id)

        # ---
        self.assertGET404(url, data={'brick_id': brick_id, 'search': 'da'})

        def assertBadID(brick_id):
            self.assertGET404(url, data={'brick_id': brick_id, 'search': 'linu'})

        assertBadID('invalid_prefix-creme_core-fakecontact-')
        assertBadID('found-creme_core-fakecontact-123-extra')
        assertBadID('found-creme_core-invalid-123')
        assertBadID('found-creme_core-fakesector-123')

    def test_light_search01(self):
        user = self.login_as_root_and_get()
        self._setup_contacts(user=user)
        coxi = FakeContact.objects.create(user=user, first_name='Coxi', last_name='Nail')

        self._setup_orgas(user=user)

        response = self.assertGET200(self.LIGHT_URL, data={'value': 'cox'})

        results = response.json()

        alan = self.alan
        coxco = self.coxco

        self.maxDiff = None
        self.assertDictEqual(
            {
                'best': {
                    'label': str(coxco),
                    # 'score': 102,
                    'url':   coxco.get_absolute_url(),
                },
                # 'query':   {'content': 'cox',
                #             'limit': 5,
                #             'ctype': None,
                #            },
                'results': [
                    {
                        'count':   2,
                        'id':      alan.entity_type_id,
                        'label':   'Test Contact',
                        'results': [
                            {
                                'label': str(alan),
                                # 'score': 101,
                                'url':   alan.get_absolute_url(),
                            }, {
                                'label': str(coxi),
                                # 'score': 101,
                                'url':   coxi.get_absolute_url(),
                            },
                        ],
                    }, {
                        'count':   1,
                        'id':      coxco.entity_type_id,
                        'label':   'Test Organisation',
                        'results': [
                            {
                                'label': str(coxco),
                                # 'score': 102,
                                'url':   coxco.get_absolute_url(),
                            },
                        ],
                    },
                ],
            },
            results,
        )

    def test_light_search02(self):
        "Credentials."
        user = self.login_as_standard(allowed_apps=['creme_core'])
        self.add_credentials(user.role, own=['VIEW'])

        self._setup_contacts(user=self.get_root_user())
        coxi = FakeContact.objects.create(user=user, first_name='Coxi', last_name='Nail')

        response = self.assertGET200(self.LIGHT_URL, data={'value': 'cox'})

        self.maxDiff = None
        self.assertDictEqual(
            {
                'best': {
                    'label': str(coxi),
                    # 'score': 101,
                    'url':   coxi.get_absolute_url(),
                },
                # 'query':   {'content': 'cox',
                #             'limit': 5,
                #             'ctype': None,
                #            },
                'results': [
                    {
                        'count':   1,
                        'id':      coxi.entity_type_id,
                        'label':   'Test Contact',
                        'results': [
                            {
                                'label': str(coxi),
                                # 'score': 101,
                                'url':   coxi.get_absolute_url(),
                            },
                        ],
                    },
                ],
            },
            response.json(),
        )

    def test_light_search03(self):
        "Errors."
        self.login_as_root()

        url = self.LIGHT_URL
        response = self.assertGET200(url)
        self.assertDictEqual(
            {
                # 'query': {'content': '',
                #           'limit': 5,
                #           'ctype': None,
                #          },
                'error': _('Empty search…'),
            },
            response.json(),
        )

        response = self.assertGET200(url, data={'value': 'co'})
        self.assertDictEqual(
            {
                # 'query': {'content': 'co',
                #           'limit': 5,
                #           'ctype': None,
                #          },
                'error': _('Please enter at least {count} characters').format(count=3),
            },
            response.json(),
        )

    def test_light_search04(self):
        "Deleted entities are ignored."
        user = self.login_as_root_and_get()
        self._setup_contacts(user=user)
        response = self.assertGET200(self.LIGHT_URL, data={'value': 'Linu'})

        linus = self.linus
        linus2 = self.linus2
        andrew = self.andrew
        self.maxDiff = None
        self.assertDictEqual(
            {
                'best': {
                    'label': str(andrew),
                    'url':   andrew.get_absolute_url(),
                },
                'results': [
                    {
                        'count':   3,
                        'id':      linus.entity_type_id,
                        'label':   'Test Contact',
                        'results': [
                            {
                                'label':   str(linus2),
                                'url':     linus2.get_absolute_url(),
                                'deleted': True,
                            }, {
                                'label': str(andrew),
                                'url':   andrew.get_absolute_url(),
                            }, {
                                'label': str(linus),
                                'url':   linus.get_absolute_url(),
                            },
                        ],
                    },
                ],
            },
            response.json(),
        )

    def test_search_app_credentials(self):
        from creme.documents import get_document_model

        user = self.login_as_standard(allowed_apps=['documents'])  # Not 'creme_core'
        self.add_credentials(user.role, own='*')
        self._setup_contacts(user=user)

        Document = get_document_model()
        SearchConfigItem.objects.builder(model=Document, fields=['title']).get_or_create()

        searched = 'linu'
        response1 = self._search(searched)
        self.assertEqual(200, response1.status_code)

        tree1 = self.get_html_tree(response1.content)
        self.assertNoSearchBrick(tree1, brick_id_prefix=self.ORGA_BRICKID)
        self.assertNoSearchBrick(tree1, brick_id_prefix=self.CONTACT_BRICKID)

        context1 = response1.context
        models = context1['models']
        self.assertNotIn(FakeContact, models)
        self.assertNotIn(FakeOrganisation, models)

        vnames = {str(vname) for vname in context1['verbose_names']}
        self.assertNotIn('Test Contact', vnames)
        self.assertNotIn('Test Organisation', vnames)
        self.assertIn(str(Document._meta.verbose_name), vnames)

        # ---
        response2 = self._search(searched, self.contact_ct_id)
        self.assertEqual(403, response2.status_code)

        # ---
        reload_url = reverse('creme_core__reload_search_brick')
        self.assertGET200(
            reload_url,
            data={'brick_id': 'found-documents-document-', 'search': searched},
        )
        self.assertGET403(
            reload_url,
            data={'brick_id': self.CONTACT_BRICKID + '456132', 'search': searched},
        )

        # ---
        response3 = self.assertGET200(self.LIGHT_URL, data={'value': searched})
        self.assertDictEqual(
            {'best': None, 'results': []},
            response3.json(),
        )
