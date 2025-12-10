import re
from datetime import date, timedelta
from decimal import Decimal
from functools import partial
from json import dumps as json_dump
from random import shuffle
from urllib.parse import quote, urlencode
from xml.etree.ElementTree import tostring as html_tostring

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q
from django.test.utils import override_settings
from django.urls import reverse
from django.utils.formats import number_format
from django.utils.timezone import now
from django.utils.translation import gettext as _
from django.utils.translation import pgettext

from creme.creme_core.auth.entity_credentials import EntityCredentials
from creme.creme_core.core.entity_cell import (
    EntityCellCustomField,
    EntityCellFunctionField,
    EntityCellRegularField,
    EntityCellRelation,
)
from creme.creme_core.core.entity_filter import (
    EF_CREDENTIALS,
    condition_handler,
    operators,
)
from creme.creme_core.core.function_field import function_field_registry
from creme.creme_core.gui.listview import ListViewState
from creme.creme_core.gui.view_tag import ViewTag
from creme.creme_core.models import (
    CremeProperty,
    CremePropertyType,
    CustomField,
    CustomFieldEnumValue,
    EntityFilter,
    FakeActivity,
    FakeActivityType,
    FakeAddress,
    FakeCivility,
    FakeContact,
    FakeDocument,
    FakeEmailCampaign,
    FakeFolder,
    FakeFolderCategory,
    FakeImage,
    FakeImageCategory,
    FakeInvoice,
    FakeInvoiceLine,
    FakeMailingList,
    FakeOrganisation,
    FakeSector,
    FieldsConfig,
    HeaderFilter,
    Relation,
    RelationType,
    SetCredentials,
)
from creme.creme_core.models.entity_filter import EntityFilterList
from creme.creme_core.models.header_filter import HeaderFilterList
from creme.creme_core.utils.profiling import CaptureQueriesContext
from creme.creme_core.utils.queries import QSerializer

from .. import fake_constants
from ..base import CremeTestCase


@override_settings(LISTVIEW_ENUMERABLE_LIMIT=50)
class ListViewTestCase(CremeTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.url = FakeOrganisation.get_lv_absolute_url()
        cls.ctype = ContentType.objects.get_for_model(FakeOrganisation)

        cls._civ_backup = [*FakeCivility.objects.all()]
        FakeCivility.objects.all().delete()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        FakeCivility.objects.all().delete()
        FakeCivility.objects.bulk_create(cls._civ_backup)

    def _assertFastCount(self, captured_sql):
        db_engine = settings.DATABASES['default']['ENGINE']
        if db_engine == 'django.db.backends.mysql':
            trash_sql = (
                'SELECT COUNT(*) AS `__count` FROM `creme_core_cremeentity` '
                'WHERE `creme_core_cremeentity`.`is_deleted` = 1'
            )
        elif db_engine == 'django.db.backends.sqlite3':
            trash_sql = (
                'SELECT COUNT(*) AS "__count" FROM "creme_core_cremeentity" '
                'WHERE "creme_core_cremeentity"."is_deleted"'
            )
        elif db_engine.startswith('django.db.backends.postgresql'):
            trash_sql = (
                'SELECT COUNT(*) AS "__count" FROM "creme_core_cremeentity" '
                'WHERE "creme_core_cremeentity"."is_deleted"'
            )
        else:
            self.fail('This RDBMS is not managed by this test case.')

        entities_q_re = re.compile(
            r'^SELECT COUNT\(\*\) AS (.)__count(.) FROM (.)creme_core_cremeentity(.)'
        )

        optimized_counts = []
        for sql in captured_sql:
            if entities_q_re.match(sql) is not None and sql != trash_sql:
                if 'INNER JOIN' in sql:
                    self.fail(f'slow COUNT query found: {sql}')

                optimized_counts.append(sql)

        if len(optimized_counts) != 1:
            self.fail('{} fast queries found (one was expected):\n{}'.format(
                len(optimized_counts),
                '\n'.join(f' - {sql}' for sql in optimized_counts),
            ))

    def _assertNoDistinct(self, captured_sql):
        entities_q_re = re.compile(
            r'^SELECT (?P<distinct>DISTINCT )?(.)creme_core_cremeentity(.)\.(.)id(.)'
        )

        count_q_found = False
        entities_q_found = False

        for sql in captured_sql:
            if sql.startswith('SELECT COUNT(*)'):
                self.assertNotIn('DISTINCT', sql)
                count_q_found = True

            match = entities_q_re.match(sql)
            if match is not None:
                self.assertFalse(match.groupdict().get('distinct'))
                entities_q_found = True

        joined_sql = '\n'.join(captured_sql)
        self.assertTrue(count_q_found, f'Not COUNT query found in {joined_sql}')
        self.assertTrue(
            entities_q_found,
            f'Not query (which retrieve entities) found in {joined_sql}'
        )

    def _create_rtype(self, index=0):
        match index:
            case 0:
                return RelationType.objects.builder(
                    id='test-subject_piloted', predicate='is piloted by',
                ).symmetric(
                    id='test-object_piloted', predicate='pilots'
                ).get_or_create()[0]
            case 1:
                return RelationType.objects.builder(
                    id='test-subject_repaired', predicate='is repaired by',
                ).symmetric(
                    id='test-object_repaired', predicate='repairs',
                ).get_or_create()[0]
            case _:
                raise ValueError('Bad index')

    def _get_lv_node(self, response):
        page_tree = self.get_html_tree(response.content)

        node = page_tree.find(".//form[@widget='ui-creme-listview']")
        self.assertIsNotNone(node, 'The listview is not found.')

        return node

    def _get_lv_table_node(self, lv_node):
        node = lv_node.find(".//table[@data-total-count]")
        self.assertIsNotNone(node, "The listview's table is not found.")

        return node

    def _get_lv_header_buttons(self, lv_node):
        buttons_node = self.get_html_node_or_fail(
            lv_node, './/div[@class="list-header-buttons clearfix"]',
        )

        for a_node in buttons_node.findall('.//a'):
            yield {
                'url': a_node.attrib.get('href'),
                'label': next(
                    (label for txt in a_node.itertext() if (label := txt.strip())),
                    None
                ),
            }

    def _get_lv_header_titles(self, lv_table_node):
        thead_node = self.get_html_node_or_fail(lv_table_node, './/thead')
        tr_node = self.get_html_node_or_fail(thead_node, ".//tr[@class='lv-columns-header']")

        return [
            span_node.text
            for span_node in tr_node.findall(
                ".//th/button/div/span[@class='lv-sort-toggle-title']"
            )
        ]

    def _get_lv_header_widget_nodes(self, lv_table_node, cell_key, input_type='input', count=1):
        thead_node = self.get_html_node_or_fail(lv_table_node, './/thead')
        tr_node = self.get_html_node_or_fail(thead_node, ".//tr[@class='lv-search-header']")

        widget_nodes = tr_node.findall(f".//{input_type}[@name='search-{cell_key}']")
        self.assertEqual(count, len(widget_nodes))

        return widget_nodes

    def _assert_no_lv_header_widget_node(self, lv_table_node, cell_key):
        tr_node = self.get_html_node_or_fail(
            lv_table_node, ".//thead//tr[@class='lv-search-header']",
        )

        input_node = tr_node.find(f".//*[@name='{cell_key}']")
        self.assertIsNone(input_node)

    def _get_lv_inputs_content(self, lv_table_node):
        thead_node = self.get_html_node_or_fail(lv_table_node, './/thead')
        th_node = self.get_html_node_or_fail(thead_node, './/tr/th')

        return [
            (input_node.attrib.get('name'), input_node.attrib.get('value'))
            for input_node in th_node.findall('input')
        ]

    def _get_lv_cell_contents(self, lv_table_node):
        tbody_node = self.get_html_node_or_fail(lv_table_node, './/tbody')
        content = []

        for tr_node in tbody_node.findall('tr'):
            for td_node in tr_node.findall('td'):
                class_attr = td_node.attrib.get('class')

                if class_attr:
                    classes = class_attr.split()

                    if 'lv-cell-content' in classes:
                        div_node = td_node.find('.//div')

                        if div_node is not None:
                            content.append([*div_node] or div_node.text.strip())

        return content

    def _get_entities_set(self, response):
        with self.assertNoException():
            entities_page = response.context['page_obj']

        return {*entities_page.object_list}

    @staticmethod
    def _get_options_for_select_node(select_node):
        return {
            (option_node.attrib.get('value'), option_node.text)
            for option_node in select_node.findall('option')
        }

    @staticmethod
    def _get_sql(response):
        page = response.context['page_obj']
        return page.paginator.object_list.query.get_compiler('default').as_sql()[0]

    @staticmethod
    def _build_hf(*cells):
        return HeaderFilter.objects.proxy(
            id='test-hf_orga', name='Orga view',
            model=FakeOrganisation,
            cells=[
                EntityCellRegularField.build(model=FakeOrganisation, name='name'),
                *cells,
            ],
        ).get_or_create()[0]

    def test_not_logged(self):
        url = self.url
        response = self.assertGET(302, url)
        self.assertRedirects(
            response, '{}?next={}'.format(reverse('creme_login'), url),
        )

    def test_not_allowed(self):
        self.login_as_standard()  # listable_models=...
        self.assertContains(
            self.client.get(self.url),
            status_code=403,
            text=_('You are not allowed to list: {}').format('Test Organisation'),
            html=True,
        )

    def test_content(self):
        user = self.login_as_standard(listable_models=[FakeOrganisation])
        self.add_credentials(user.role, own=['VIEW'])

        create_orga = partial(FakeOrganisation.objects.create, user=user)
        bebop     = create_orga(name='Bebop')
        swordfish = create_orga(name='Swordfish')

        create_contact = partial(FakeContact.objects.create, user=user)
        spike = create_contact(first_name='Spike', last_name='Spiegel')
        faye  = create_contact(first_name='Faye',  last_name='Valentine')

        # Relation
        rtype = self._create_rtype()
        Relation.objects.create(
            user=user, subject_entity=swordfish, type=rtype, object_entity=spike,
        )

        # Property
        create_ptype = CremePropertyType.objects.create
        ptype1 = create_ptype(text='is red')
        ptype2 = create_ptype(text='is fast')
        CremeProperty.objects.create(type=ptype1, creme_entity=swordfish)

        # CustomField
        cfield = CustomField.objects.create(
            name='size (m)', content_type=self.ctype, field_type=CustomField.INT,
        )
        cfield_value = 42
        cfield.value_class(custom_field=cfield, entity=bebop).set_value_n_save(cfield_value)

        hf = self._build_hf(
            EntityCellRelation(model=FakeOrganisation, rtype=rtype),
            EntityCellFunctionField.build(FakeOrganisation, 'get_pretty_properties'),
            EntityCellCustomField(cfield),
        )

        queries_context = CaptureQueriesContext()

        with queries_context:
            response = self.assertPOST200(self.url, data={'hfilter': hf.id})

        ctxt = response.context
        self.assertEqual(ViewTag.HTML_LIST, ctxt.get('view_tag'))

        with self.assertNoException():
            hfilters = ctxt['header_filters']
            efilters = ctxt['entity_filters']
            orgas_page = ctxt['page_obj']

        self.assertIsInstance(hfilters, HeaderFilterList)
        self.assertIn(hf, hfilters)

        self.assertIsInstance(efilters, EntityFilterList)

        with self.assertNoException():
            sel_hf = hfilters.selected

        self.assertIsInstance(sel_hf, HeaderFilter)
        self.assertEqual(sel_hf.id, hf.id)

        orgas_set = {*orgas_page.object_list}
        self.assertIn(bebop,     orgas_set)
        self.assertIn(swordfish, orgas_set)

        table_node = self._get_lv_table_node(self._get_lv_node(response))
        content = self._get_lv_cell_contents(table_node)
        bebop_idx = self.assertIndex(bebop.name, content)
        swordfish_idx = self.assertIndex(swordfish.name, content)
        self.assertGreater(swordfish_idx, bebop_idx)  # Order

        titles = self._get_lv_header_titles(table_node)

        self.assertIn(rtype.predicate, titles)
        rtype_cell_content = content[5]
        self.assertIsList(rtype_cell_content, length=1)
        self.assertHTMLEqual(
            f'<a href="/tests/contact/{spike.id}" target="_self">{spike}</a>',
            html_tostring(rtype_cell_content[0], encoding='unicode'),
        )

        self.assertNotIn(faye.last_name, content)

        ptype_cell_content = content[6]
        self.assertIsList(ptype_cell_content, length=1)
        self.assertHTMLEqual(
            f'<a href="{ptype1.get_absolute_url()}">{ptype1.text}</a>',
            html_tostring(ptype_cell_content[0], encoding='unicode'),
        )
        self.assertNotIn(ptype2.text, content)  # NB: not really useful...

        self.assertIn(cfield.name, titles)
        self.assertIn(str(cfield_value), content)

        self.assertEqual(2, orgas_page.paginator.count)
        self._assertFastCount(queries_context.captured_sql)

    def test_content__fields_config(self):
        user = self.login_as_root_and_get()

        valid_fname = 'name'
        hidden_fname = 'url_site'

        build_cell = partial(EntityCellRegularField.build, model=FakeOrganisation)
        hf = self._build_hf(build_cell(name=valid_fname), build_cell(name=hidden_fname))

        FieldsConfig.objects.create(
            content_type=FakeOrganisation,
            descriptions=[(hidden_fname, {FieldsConfig.HIDDEN: True})],
        )

        bebop = FakeOrganisation.objects.create(user=user, name='Bebop', url_site='sww.bebop.mrs')

        response = self.assertPOST200(self.url, data={'hfilter': hf.id})

        content = self._get_lv_cell_contents(self._get_lv_table_node(self._get_lv_node(response)))
        self.assertIn(bebop.name, content)
        self.assertNotIn(bebop.url_site, content, '"url_site" not hidden')

    def test_content__template(self):
        "Use reload template (content=1)."
        self.login_as_root()
        url = self.url

        response = self.assertPOST200(url)
        self.assertTemplateUsed(response, 'creme_core/generics/entities.html')

        response = self.assertPOST200(url, headers={'X-Requested-With': 'XMLHttpRequest'})
        self.assertTemplateUsed(response, 'creme_core/generics/entities.html')

        response = self.assertPOST200(url, data={'content': 1})
        self.assertTemplateUsed(response, 'creme_core/listview/content.html')

        response = self.assertPOST200(
            url, data={'content': 1}, headers={'X-Requested-With': 'XMLHttpRequest'},
        )
        self.assertTemplateUsed(response, 'creme_core/listview/content.html')

    def test_content__popup__template(self):
        self.login_as_root()
        ct_id = self.ctype.id

        response1 = self.assertPOST200(
            reverse('creme_core__listview_popup'),
            data={'ct_id': ct_id},
        )
        self.assertTemplateUsed(response1, 'creme_core/generics/entities-popup.html')

        response2 = self.assertPOST200(
            reverse('creme_core__listview_popup'),
            data={'ct_id': ct_id},
            headers={'X-Requested-With': 'XMLHttpRequest'},
        )
        self.assertTemplateUsed(response2, 'creme_core/generics/entities-popup.html')

        response3 = self.assertPOST200(
            reverse('creme_core__listview_popup'),
            data={'ct_id': ct_id, 'content': 1},
        )
        self.assertTemplateUsed(response3, 'creme_core/listview/content.html')

        response4 = self.assertPOST200(
            reverse('creme_core__listview_popup'),
            data={'ct_id': ct_id, 'content': 1},
            headers={'X-Requested-With': 'XMLHttpRequest'},
        )
        self.assertTemplateUsed(response4, 'creme_core/listview/content.html')

    def test_content__popup__viewtag(self):
        user = self.login_as_root_and_get()
        ct_id = self.ctype.id

        create_orga = partial(FakeOrganisation.objects.create, user=user)
        create_orga(name='Bebop')
        swordfish = create_orga(name='Swordfish')

        spike = FakeContact.objects.create(user=user, first_name='Spike', last_name='Spiegel')

        # Relation
        rtype = self._create_rtype()
        Relation.objects.create(
            user=user, subject_entity=swordfish, type=rtype, object_entity=spike,
        )

        hf = self._build_hf(
            EntityCellRelation(model=FakeOrganisation, rtype=rtype),
        )

        response = self.assertPOST200(
            reverse('creme_core__listview_popup'),
            data={'ct_id': ct_id, 'hfilter': hf.id},
        )
        self.assertEqual(ViewTag.HTML_FORM, response.context.get('view_tag'))

        content = self._get_lv_cell_contents(self._get_lv_table_node(self._get_lv_node(response)))
        rtype_cell_content = content[3]
        self.assertIsList(rtype_cell_content, length=1)
        self.assertHTMLEqual(
            f'<a href="/tests/contact/{spike.id}" target="_blank">{spike}</a>',
            html_tostring(rtype_cell_content[0], encoding='unicode'),
        )

    def test_no_headerfilter(self):
        self.login_as_root()
        ct = ContentType.objects.get_for_model(FakeMailingList)
        self.assertFalse(HeaderFilter.objects.filter(entity_type=ct))

        url = FakeMailingList.get_lv_absolute_url()
        response1 = self.assertGET200(url)
        self.assertTemplateUsed(response1, 'creme_core/forms/header-filter.html')

        # ---
        name = 'ML view'
        response2 = self.client.post(
            url,
            data={
                'name':  name,
                'cells': 'regular_field-name',
            },
        )
        self.assertNoFormError(response2, status=302)

        hfilter = self.get_object_or_fail(HeaderFilter, entity_type=ct, name=name)
        self.assertEqual(1, len(hfilter.cells))

        self.assertRedirects(response2, url)

        # ---
        response3 = self.assertGET200(url)
        self._get_lv_node(response3)

    def test_selection_single(self):
        user = self.login_as_root_and_get()

        create_contact = partial(FakeContact.objects.create, user=user)
        create_contact(first_name='Spike', last_name='Spiegel')
        create_contact(first_name='Faye',  last_name='Valentine')

        def post(selection):
            response = self.assertPOST200(self.url, data={'selection': selection})
            self.assertInHTML(
                f'<input class="lv-state-field" value="{selection}" '
                f'name="selection" type="hidden" />',
                response.text,
            )

        post('none')
        post('single')
        post('multiple')

        self.assertPOST404(self.url, data={'selection': 'unknown'})

    def test_selection_single_GET(self):
        user = self.login_as_root_and_get()

        create_contact = partial(FakeContact.objects.create, user=user)
        create_contact(first_name='Spike', last_name='Spiegel')
        create_contact(first_name='Faye',  last_name='Valentine')

        def get(selection):
            response = self.assertGET200(self.url, data={'selection': selection})
            self.assertInHTML(
                f'<input class="lv-state-field" value="{selection}" '
                f'name="selection" type="hidden" />',
                response.text,
            )

        get('none')
        get('single')
        get('multiple')

        self.assertGET404(self.url, data={'selection': 'unknown'})

    def test_ordering__regular_field(self):
        user = self.login_as_root_and_get()

        create_orga = partial(FakeOrganisation.objects.create, user=user)
        bebop     = create_orga(name='Bebop')
        swordfish = create_orga(name='Swordfish')

        self._build_hf()

        def post(first, second, sort_order='', sort_key='regular_field-name', **kwargs):
            response = self.assertPOST200(
                self.url,
                data={
                    'sort_key': sort_key,
                    'sort_order': sort_order,
                },
                **kwargs
            )

            content = self._get_lv_cell_contents(
                self._get_lv_table_node(self._get_lv_node(response))
            )
            first_idx = self.assertIndex(first.name, content)
            second_idx = self.assertIndex(second.name, content)
            self.assertLess(first_idx, second_idx)

        post(bebop, swordfish)
        post(swordfish, bebop, 'DESC')
        post(bebop, swordfish, sort_key='unknown')  # Invalid value

        # ajax POST request
        post(bebop, swordfish, headers={'X-Requested-With': 'XMLHttpRequest'})
        post(swordfish, bebop, 'DESC', headers={'X-Requested-With': 'XMLHttpRequest'})

        state = ListViewState.get_state(self.client, url=self.url)
        self.assertIsNotNone(state)
        self.assertEqual('regular_field-name', state.sort_cell_key)
        self.assertEqual('DESC', state.sort_order)

    def test_ordering__regular_field__invalid_order(self):
        self.login_as_root()
        self._build_hf()

        with self.assertRaises(ValueError):
            self.client.post(
                self.url,
                data={
                    'sort_key':   'regular_field-name',
                    'sort_order': 'invalid',
                },
            )

    def test_ordering__regular_field__GET(self):
        user = self.login_as_root_and_get()

        create_orga = partial(FakeOrganisation.objects.create, user=user)
        bebop     = create_orga(name='Bebop')
        swordfish = create_orga(name='Swordfish')

        self._build_hf()

        def get(first, second, sort_order='ASC', sort_key='regular_field-name', **kwargs):
            response = self.assertGET200(
                self.url,
                data={
                    'sort_key': sort_key,
                    'sort_order': sort_order,
                },
                **kwargs
            )
            content = self._get_lv_cell_contents(
                self._get_lv_table_node(self._get_lv_node(response))
            )
            first_idx = self.assertIndex(first.name, content)
            second_idx = self.assertIndex(second.name, content)
            self.assertLess(first_idx, second_idx)

        get(bebop, swordfish)
        get(swordfish, bebop, 'DESC')
        get(bebop, swordfish, sort_key='unknown')  # Invalid value

        state = ListViewState.get_state(self.client, url=self.url)
        self.assertIsNone(state)

        # ajax GET request
        get(bebop, swordfish, headers={'X-Requested-With': 'XMLHttpRequest'})
        get(swordfish, bebop, 'DESC', headers={'X-Requested-With': 'XMLHttpRequest'})

        # state is not saved or update by GET requests.
        state = ListViewState.get_state(self.client, url=self.url)
        self.assertIsNone(state)

    def test_ordering__regular_field__transient(self):
        user = self.login_as_root_and_get()

        create_orga = partial(FakeOrganisation.objects.create, user=user)
        bebop     = create_orga(name='Bebop')
        swordfish = create_orga(name='Swordfish')

        self._build_hf()

        def post(first, second, sort_order='ASC', sort_key='regular_field-name', **kwargs):
            response = self.assertPOST200(
                self.url,
                data={
                    'sort_key': sort_key,
                    'sort_order': sort_order,
                    'transient': '1',
                },
                **kwargs
            )
            content = self._get_lv_cell_contents(
                self._get_lv_table_node(self._get_lv_node(response))
            )
            first_idx = self.assertIndex(first.name, content)
            second_idx = self.assertIndex(second.name, content)
            self.assertLess(first_idx, second_idx)

        post(bebop, swordfish)
        post(swordfish, bebop, 'DESC')
        post(bebop, swordfish, sort_key='unknown')  # Invalid value

        state = ListViewState.get_state(self.client, url=self.url)
        self.assertIsNone(state)

        # ajax GET request
        post(bebop, swordfish, headers={'X-Requested-With': 'XMLHttpRequest'})
        post(swordfish, bebop, 'DESC', headers={'X-Requested-With': 'XMLHttpRequest'})

        # state is not saved or update by GET requests.
        state = ListViewState.get_state(self.client, url=self.url)
        self.assertIsNone(state)

    # TODO: for now there should not be CremeEntity with 'id' as ordering
    # def test_order02_prelude(self):
    #     "Sort by ForeignKey"
    #     #NB: the DatabaseError cannot be rollbacked here in the test context,
    #     #    so we cannot do this test in test_order02, because it cause an error.
    #     try:
    #         bool(Contact.objects.order_by('image'))
    #     except:
    #         pass
    #     else:
    #         self.fail('ORM bug has been fixed ?! => reactivate FK on CremeEntity sorting')

    def assertListViewContentOrder(self, response, key, entries):
        content = self._get_lv_cell_contents(
            self._get_lv_table_node(self._get_lv_node(response))
        )
        lines = [
            (self.assertIndex(str(getattr(e, key)), content), e)
            for e in entries
        ]
        self.assertListEqual(
            [*entries],
            [line[1] for line in sorted(lines, key=lambda e: e[0])],
        )

    def test_ordering__regular_field__fk(self):
        "Sort by ForeignKey."
        user = self.login_as_root_and_get()

        create_civ = FakeCivility.objects.create
        mister = create_civ(title='Mister')
        miss   = create_civ(title='Miss')
        self.assertLess(mister.id, miss.id)

        create_contact = partial(FakeContact.objects.create, user=user)
        spike = create_contact(first_name='Spike',  last_name='Spiegel',   civility=mister)
        faye  = create_contact(first_name='Faye',   last_name='Valentine', civility=miss)
        ed    = create_contact(first_name='Edward', last_name='Wong')

        hf = HeaderFilter.objects.proxy(
            id='test-hf_contact', name='Order02 view', model=FakeContact,
            cells=[
                (EntityCellRegularField, 'last_name'),
                (EntityCellRegularField, 'image'),
                (EntityCellRegularField, 'image__name'),
                (EntityCellRegularField, 'civility'),
                (EntityCellRegularField, 'civility__title'),
            ],
        ).get_or_create()[0]

        url = FakeContact.get_lv_absolute_url()

        # ---------------------------------------------------------------------
        response = self.assertPOST200(url, data={'hfilter': hf.id})

        with self.assertNoException():
            selected_hf = response.context['header_filters'].selected

        self.assertEqual(hf, selected_hf)

        # ---------------------------------------------------------------------
        # FK on CremeEntity we just check that it does not crash
        self.assertPOST200(url, data={'sort_key': 'regular_field-image'})

        # ---------------------------------------------------------------------
        def post(sort_key, reverse, *contacts):
            response = self.assertPOST200(
                url,
                data={
                    'sort_key': sort_key,
                    'sort_order': 'DESC' if reverse else 'ASC',
                },
            )
            content = self._get_lv_cell_contents(
                self._get_lv_table_node(self._get_lv_node(response))
            )
            indices = [self.assertIndex(c.last_name, content) for c in contacts]
            self.assertEqual(indices, sorted(indices))

            return content

        # NB: it seems that NULL are not ordered in the same way on different DB engines
        content = post('regular_field-civility', False, faye, spike)  # Sorting is done by 'title'
        self.assertCountOccurrences(ed.last_name, content, count=1)

        post('regular_field-civility', True, spike, faye)
        post('regular_field-civility__title', False, faye, spike)
        post('regular_field-civility__title', True, spike, faye)

    @override_settings(FAST_QUERY_MODE_THRESHOLD=100000)
    def test_ordering__regular_field__fast_mode(self):
        "Ordering = '-fieldname'."
        user = self.login_as_root_and_get()
        self.assertTrue('-start', FakeActivity._meta.ordering[0])

        act_type = FakeActivityType.objects.all()[0]
        create_act = partial(FakeActivity.objects.create, user=user, type=act_type)
        act1 = create_act(title='Act#1', start=now())
        act2 = create_act(title='Act#2', start=act1.start + timedelta(hours=1))

        # See fake populate
        hf = self.get_object_or_fail(
            HeaderFilter, pk=fake_constants.DEFAULT_HFILTER_FAKE_ACTIVITY,
        )

        response = self.assertPOST200(
            FakeActivity.get_lv_absolute_url(), data={'hfilter': hf.pk},
        )
        content = self._get_lv_cell_contents(
            self._get_lv_table_node(self._get_lv_node(response))
        )
        first_idx  = self.assertIndex(act2.title, content)
        second_idx = self.assertIndex(act1.title, content)
        self.assertLess(first_idx, second_idx)

        with self.assertNoException():
            lvs = response.context['list_view_state']
            sort_cell_key = lvs.sort_cell_key
            sort_order = lvs.sort_order

        self.assertEqual('regular_field-start', sort_cell_key)
        self.assertEqual('DESC',  sort_order)

        self.assertRegex(
            self._get_sql(response),
            r'ORDER BY '
            r'.creme_core_fakeactivity.\..start. DESC( NULLS LAST)?\, '
            r'.creme_core_fakeactivity.\..cremeentity_ptr_id. DESC( NULLS LAST)?$'
        )

    def test_ordering__unsortable_fields(self):
        "Un-sortable fields: ManyToMany, FunctionFields."
        user = self.login_as_root_and_get()

        # Bug on ORM with M2M happens only if there is at least one entity
        FakeEmailCampaign.objects.create(user=user, name='Camp01')

        fname = 'mailing_lists'
        func_field_name = 'get_pretty_properties'
        HeaderFilter.objects.proxy(
            id='test-hf_camp', name='Campaign view', model=FakeEmailCampaign,
            cells=[
                (EntityCellRegularField, 'name'),
                (EntityCellRegularField, fname),
                (EntityCellFunctionField, func_field_name),
            ],
        ).get_or_create()

        url = FakeEmailCampaign.get_lv_absolute_url()
        # We just check that it does not crash
        self.assertPOST200(url, data={'sort_key': f'regular_field-{fname}'})
        self.assertPOST200(url, data={'sort_key': f'function_field-{func_field_name}'})

    @override_settings(FAST_QUERY_MODE_THRESHOLD=100000)
    def test_ordering__default(self):
        user = self.login_as_root_and_get()
        self.assertEqual(('last_name', 'first_name'), FakeContact._meta.ordering)

        create_contact = partial(FakeContact.objects.create, user=user)
        create_contact(first_name='Spike',  last_name='Spiegel')
        create_contact(first_name='Faye',   last_name='Valentine')
        create_contact(first_name='Edward', last_name='Wong')

        url = FakeContact.get_lv_absolute_url()
        # For the filter to prevent an issue when HeaderFiltersTestCase is run before this test
        # See fake populate
        hf = self.get_object_or_fail(HeaderFilter, pk=fake_constants.DEFAULT_HFILTER_FAKE_CONTACT)
        response = self.assertPOST200(url, {'hfilter': hf.pk})

        entries = FakeContact.objects.all()
        self.assertListViewContentOrder(response, 'last_name', entries)

        listview_state = response.context['list_view_state']
        self.assertEqual('regular_field-last_name', listview_state.sort_cell_key)
        self.assertEqual('ASC', listview_state.sort_order)

        self.assertRegex(
            self._get_sql(response),
            r'ORDER BY '
            r'.creme_core_fakecontact.\..last_name. ASC( NULLS FIRST)?\, '
            r'.creme_core_fakecontact.\..first_name. ASC( NULLS FIRST)?\, '
            r'.creme_core_fakecontact.\..cremeentity_ptr_id. ASC( NULLS FIRST)?$'
        )

    def test_ordering__merge_column_and_default(self):
        self.assertEqual(('last_name', 'first_name'), FakeContact._meta.ordering)
        user = self.login_as_root_and_get()

        create_civ = FakeCivility.objects.create
        mister = create_civ(title='Mister')
        miss   = create_civ(title='Miss')
        self.assertLess(mister.id, miss.id)

        create_contact = partial(FakeContact.objects.create, user=user)
        spike = create_contact(first_name='Spike', last_name='Spiegel', civility=mister)
        faye = create_contact(first_name='Faye', last_name='Valentine', civility=miss)
        ed = create_contact(first_name='Edward', last_name='Wong')

        build_cell = partial(EntityCellRegularField.build, model=FakeContact)
        cell_civ   = build_cell(name='civility')
        cell_fname = build_cell(name='first_name')
        hf = HeaderFilter.objects.proxy(
            id='test-hf_contact', name='Order02 view', model=FakeContact,
            cells=[cell_civ, (EntityCellRegularField, 'last_name'), cell_fname],
        ).get_or_create()[0]

        contacts = FakeContact.objects.filter(pk__in=(spike, faye, ed))
        url = FakeContact.get_lv_absolute_url()
        response1 = self.assertPOST200(
            url,
            data={
                'hfilter': hf.id,
                'sort_key': cell_civ.key,
                'sort_order': '',
            },
        )
        self.assertListViewContentOrder(
            response1,
            key='last_name',
            entries=contacts.order_by('civility', 'last_name', 'first_name'),
        )

        # ---
        response2 = self.assertPOST200(
            url,
            data={
                'hfilter': hf.id,
                'sort_key': cell_civ.key,
                'sort_order': 'DESC',
            },
        )
        self.assertListViewContentOrder(
            response2,
            'last_name',
            entries=contacts.order_by('-civility', 'last_name', 'first_name'),
        )

        # ---
        response3 = self.assertPOST200(
            url,
            data={
                'hfilter': hf.id,
                'sort_key': cell_fname.key,
                'sort_order': 'ASC',
            },
        )
        self.assertListViewContentOrder(
            response3,
            key='last_name',
            entries=contacts.order_by('first_name', 'last_name'),
        )

        # ---
        response4 = self.assertPOST200(
            url,
            data={
                'hfilter': hf.id,
                'sort_key': cell_fname.key,
                'sort_order': 'DESC',
            },
        )
        self.assertListViewContentOrder(
            response4,
            key='last_name',
            entries=contacts.order_by('-first_name', 'last_name'),
        )

    def test_ordering__related_column(self):
        user = self.login_as_root_and_get()

        self.assertEqual(('last_name', 'first_name'), FakeContact._meta.ordering)
        self.assertFalse(bool(FakeAddress._meta.ordering))

        def create_contact(first_name, last_name, address):
            contact = FakeContact.objects.create(
                user=user, first_name=first_name, last_name=last_name,
            )
            contact.address = FakeAddress.objects.create(entity=contact, value=address)
            contact.save()
            return contact

        create_contact(first_name='Spike',  last_name='Spiegel',   address='C')
        create_contact(first_name='Faye',   last_name='Valentine', address='B')
        create_contact(first_name='Edward', last_name='Wong',      address='A')

        cell = EntityCellRegularField.build(model=FakeContact, name='address')
        hf = HeaderFilter.objects.proxy(
            id='test-hf_contact', name='Order02 view', model=FakeContact,
            cells=[
                (EntityCellRegularField, 'civility'),
                (EntityCellRegularField, 'last_name'),
                (EntityCellRegularField, 'first_name'),
                cell,
            ],
        ).get_or_create()[0]

        url = FakeContact.get_lv_absolute_url()
        # For the filter to prevent an issue when HeaderFiltersTestCase is run before this test
        response = self.assertPOST200(
            url,
            data={
                'hfilter':    hf.id,
                'sort_key': cell.key,
                # 'sort_order': '',
            },
        )

        entries = FakeContact.objects.order_by('address_id', 'last_name', 'first_name')
        self.assertListViewContentOrder(response, 'last_name', entries)

        listview_state = response.context['list_view_state']
        self.assertEqual(cell.key, listview_state.sort_cell_key)
        self.assertEqual('ASC', listview_state.sort_order)
        self.assertRegex(
            self._get_sql(response),
            r'ORDER BY '
            r'.creme_core_fakecontact.\..address_id. ASC( NULLS FIRST)?\, '
            r'.creme_core_fakecontact.\..last_name. ASC( NULLS FIRST)?\, '
            r'.creme_core_fakecontact.\..first_name. ASC( NULLS FIRST)?\, '
            r'.creme_core_fakecontact.\..cremeentity_ptr_id. ASC( NULLS FIRST)?$'
        )

    def test_ordering__customfield_column(self):
        "Custom field ordering is ignored in current implementation."
        user = self.login_as_root_and_get()

        create_orga = partial(FakeOrganisation.objects.create, user=user)
        bebop     = create_orga(name='Bebop')
        swordfish = create_orga(name='Swordfish')
        redtail   = create_orga(name='Redtail')

        cfield = CustomField.objects.create(
            name='size (m)', content_type=self.ctype, field_type=CustomField.INT,
        )
        klass = cfield.value_class

        def set_cfvalue(entity, value):
            klass(custom_field=cfield, entity=entity).set_value_n_save(value)

        set_cfvalue(bebop,     42)
        set_cfvalue(swordfish, 12)
        set_cfvalue(redtail,   4)

        cfield_cell = EntityCellCustomField(cfield)
        hf = self._build_hf(cfield_cell)

        response = self.assertPOST200(
            FakeOrganisation.get_lv_absolute_url(),
            data={
                'hfilter': hf.pk,
                'sort_key': cfield_cell.key,
                'sort_order': '',
            },
        )
        self.assertListViewContentOrder(
            response,
            key='name',
            entries=FakeOrganisation.objects.order_by('name'),
        )

    def _aux_test_ordering_fast_mode(self):
        user = self.login_as_root_and_get()

        create_contact = partial(FakeContact.objects.create, user=user)
        create_contact(first_name='Spike',  last_name='Spiegel')
        create_contact(first_name='Faye',   last_name='Valentine')
        create_contact(first_name='Edward', last_name='Wong')

        build_cell = partial(EntityCellRegularField.build, model=FakeContact)
        cell1 = build_cell(name='birthday')
        hf = HeaderFilter.objects.proxy(
            id='test-hf_contact', name='Contact view', model=FakeContact,
            cells=[
                cell1,
                build_cell(name='last_name'),
                build_cell(name='first_name'),
            ],
        ).get_or_create()[0]

        # context = CaptureQueriesContext()
        # with context:
        with CaptureQueriesContext() as context:
            self.assertPOST200(
                FakeContact.get_lv_absolute_url(),
                data={
                    'hfilter': hf.pk,
                    'sort_key': cell1.key,
                    'sort_order': '',
                },
            )

        db_engine = settings.DATABASES['default']['ENGINE']
        if db_engine == 'django.db.backends.mysql':
            main_sql_match = re.compile(
                r'SELECT .creme_core_cremeentity.\..id., .*'
                r'.creme_core_fakecontact.\..last_name., .*'
                r'WHERE .creme_core_cremeentity.\..is_deleted. = 0'
            ).match
        else:
            main_sql_match = re.compile(
                r'SELECT .creme_core_cremeentity.\..id., .*'
                r'.creme_core_fakecontact.\..last_name., .*'
                r'WHERE NOT .creme_core_cremeentity.\..is_deleted'
            ).match

        main_sql = [sql for sql in context.captured_sql if main_sql_match(sql)]

        if not main_sql:
            self.fail(
                'No main List-view query in:\n{}'.format('\n'.join(context.captured_sql))
            )
        elif len(main_sql) >= 2:
            self.fail(f'There should be one SQL query: {main_sql}')

        return main_sql[0]

    @override_settings(FAST_QUERY_MODE_THRESHOLD=100000)
    def test_ordering__fast_mode__off(self):
        sql = self._aux_test_ordering_fast_mode()
        self.assertRegex(
            sql,
            r'ORDER BY '
            r'.creme_core_fakecontact.\..birthday. ASC( NULLS FIRST)?, '
            r'.creme_core_fakecontact.\..last_name. ASC( NULLS FIRST)?, '
            r'.creme_core_fakecontact.\..first_name. ASC( NULLS FIRST)?, '
            r'.creme_core_fakecontact.\..cremeentity_ptr_id. ASC( NULLS FIRST)? LIMIT'
        )

    @override_settings(FAST_QUERY_MODE_THRESHOLD=2)
    def test_ordering__fast_mode__on(self):
        sql = self._aux_test_ordering_fast_mode()
        self.assertRegex(
            sql,
            r'ORDER BY'
            r' .creme_core_fakecontact.\..birthday. ASC( NULLS FIRST)?,'
            r' .creme_core_fakecontact.\..cremeentity_ptr_id. ASC( NULLS FIRST)? LIMIT'
        )

    def test_efilter__regular(self):
        user = self.login_as_root_and_get()

        create_orga = partial(FakeOrganisation.objects.create, user=user)
        bebop   = create_orga(name='Bebop')
        redtail = create_orga(name='Redtail')
        dragons = create_orga(name='Red Dragons')

        self._build_hf()

        efilter = EntityFilter.objects.smart_update_or_create(
            'test-filter01', 'Red', FakeOrganisation,
            user=user, is_custom=False,
            conditions=[
                condition_handler.RegularFieldConditionHandler.build_condition(
                    model=FakeOrganisation, field_name='name',
                    operator=operators.ISTARTSWITH, values=['Red'],
                ),
            ],
        )

        # context = CaptureQueriesContext()
        # with context:
        with CaptureQueriesContext() as context:
            response1 = self.assertPOST200(self.url, data={'filter': efilter.id})

        content1 = self._get_lv_cell_contents(
            self._get_lv_table_node(self._get_lv_node(response1))
        )
        self.assertNotIn(bebop.name, content1)
        self.assertCountOccurrences(redtail.name, content1, count=1)
        self.assertCountOccurrences(dragons.name, content1, count=1)

        self.assertEqual(2, response1.context['page_obj'].paginator.count)

        self._assertNoDistinct(context.captured_sql)

        # Reset the "All" filter ---
        response2 = self.assertPOST200(self.url, data={'filter': ''})
        content2 = self._get_lv_cell_contents(
            self._get_lv_table_node(self._get_lv_node(response2))
        )
        self.assertCountOccurrences(bebop.name,   content2, count=1)
        self.assertCountOccurrences(redtail.name, content2, count=1)
        self.assertCountOccurrences(dragons.name, content2, count=1)

    def test_efilter__other_type(self):
        "Pass a filter which is not EF_REGULAR."
        user = self.login_as_root_and_get()

        create_orga = partial(FakeOrganisation.objects.create, user=user)
        bebop   = create_orga(name='Bebop')
        redtail = create_orga(name='Redtail')
        dragons = create_orga(name='Red Dragons')

        self._build_hf()

        efilter = EntityFilter.objects.create(
            id='creme_core-filter01', name='Red', entity_type=FakeOrganisation,
            user=user,
            filter_type=EF_CREDENTIALS,
        ).set_conditions([
            condition_handler.RegularFieldConditionHandler.build_condition(
                model=FakeOrganisation, field_name='name',
                operator=operators.ISTARTSWITH, values=['Red'],
                filter_type=EF_CREDENTIALS,
            ),
        ])

        response1 = self.assertPOST200(self.url, data={'filter': efilter.id})

        content1 = self._get_lv_cell_contents(
            self._get_lv_table_node(self._get_lv_node(response1))
        )
        self.assertCountOccurrences(redtail.name, content1, count=1)
        self.assertCountOccurrences(dragons.name, content1, count=1)
        self.assertNotIn(bebop.name, content1)

        self.assertEqual(2, response1.context['page_obj'].paginator.count)

        # Private filter belonging to another user => filter is ignored ---
        forbidden_efilter = EntityFilter.objects.create(
            id='reports-filter02', name='Dragons', entity_type=FakeOrganisation,
            user=self.create_user(), is_private=True,
        ).set_conditions([
            condition_handler.RegularFieldConditionHandler.build_condition(
                model=FakeOrganisation, field_name='name',
                operator=operators.ICONTAINS, values=['Dragons'],
            ),
        ])
        self.assertFalse(forbidden_efilter.can_view(user)[0])

        response2 = self.assertPOST200(self.url, data={'filter': forbidden_efilter.id})

        content2 = self._get_lv_cell_contents(
            self._get_lv_table_node(self._get_lv_node(response2))
        )
        self.assertCountOccurrences(redtail.name, content2, count=1)
        self.assertCountOccurrences(dragons.name, content2, count=1)
        self.assertCountOccurrences(bebop.name,   content2, count=1)

    def test_internal_q(self):
        user = self.login_as_root_and_get()

        create_orga = partial(FakeOrganisation.objects.create, user=user)
        bebop   = create_orga(name='Bebop', email='bebop@bigshot.mrs')
        redtail = create_orga(name='Redtail')
        dragons = create_orga(name='Red Dragons', email='contact@reddragons.mrs')

        self._build_hf()

        response = self.assertGET200(reverse('creme_core__list_fake_organisations_with_email'))

        table_node = self._get_lv_table_node(self._get_lv_node(response))
        content = self._get_lv_cell_contents(table_node)
        self.assertCountOccurrences(bebop.name, content, count=1)
        self.assertNotIn(redtail.name, content)
        self.assertCountOccurrences(dragons.name, content, count=1)

        self.assertEqual(2, response.context['page_obj'].paginator.count)

    def test_qfilter__GET(self):
        user = self.login_as_root_and_get()

        create_orga = partial(FakeOrganisation.objects.create, user=user)
        bebop   = create_orga(name='Bebop')
        redtail = create_orga(name='Redtail')
        dragons = create_orga(name='Red Dragons')

        self._build_hf()

        # context = CaptureQueriesContext()
        qfilter_json = QSerializer().dumps(Q(name='Bebop'))

        # with context:
        response = self.assertGET200(self.url, data={'q_filter': qfilter_json})

        table_node = self._get_lv_table_node(self._get_lv_node(response))
        inputs_content = self._get_lv_inputs_content(table_node)
        self.assertIn(('q_filter', qfilter_json), inputs_content)

        content = self._get_lv_cell_contents(table_node)
        self.assertCountOccurrences(bebop.name, content, count=1)
        self.assertNotIn(redtail.name, content)
        self.assertNotIn(dragons.name, content)

        self.assertEqual(1, response.context['page_obj'].paginator.count)

        # TODO
        # self._assertNoDistinct(context.captured_sql)

    def test_qfilter__GET__invalid(self):
        user = self.login_as_root_and_get()
        bebop = FakeOrganisation.objects.create(user=user, name='Bebop')

        self._build_hf()
        response = self.assertGET200(self.url, data={'q_filter': 'invalid_serialized_q'})

        content = self._get_lv_cell_contents(
            self._get_lv_table_node(self._get_lv_node(response))
        )
        self.assertCountOccurrences(bebop.name, content, count=1)

    def test_qfilter__POST(self):
        user = self.login_as_root_and_get()

        create_orga = partial(FakeOrganisation.objects.create, user=user)
        bebop   = create_orga(name='Bebop')
        redtail = create_orga(name='Redtail')
        dragons = create_orga(name='Red Dragons')

        self._build_hf()

        qfilter_json = QSerializer().dumps(Q(name='Bebop'))
        response = self.assertPOST200(self.url, data={'q_filter': qfilter_json})

        table_node = self._get_lv_table_node(self._get_lv_node(response))
        inputs_content = self._get_lv_inputs_content(table_node)
        self.assertIn(('q_filter', qfilter_json), inputs_content)

        content = self._get_lv_cell_contents(table_node)
        self.assertCountOccurrences(bebop.name, content, count=1)
        self.assertNotIn(redtail.name, content)
        self.assertNotIn(dragons.name, content)

        self.assertEqual(1, response.context['page_obj'].paginator.count)

    # TODO: with new QSerializer format ?
    # def test_qfilter_invalid_Q(self):
    #     user = self.login()
    #
    #     create_orga = partial(FakeOrganisation.objects.create, user=user)
    #     bebop   = create_orga(name='Bebop')
    #     redtail = create_orga(name='Redtail')
    #     dragons = create_orga(name='Red Dragons')
    #
    #     self._build_hf()
    #
    #     # Invalid field : ignore filter
    #     response = self.assertGET200(
    #          self.url, data={'q_filter': '{"unknown_model_field":"Bebop"}'}
    #     )
    #
    #     content = self._get_lv_cell_contents(
    #         self._get_lv_table_node(self._get_lv_node(response))
    #     )
    #     self.assertIn(bebop.name, content)
    #     self.assertIn(redtail.name, content)
    #     self.assertIn(dragons.name, content)

    def test_header_buttons(self):
        self.login_as_root()
        hf = self._build_hf()
        ct_id = self.ctype.id

        q_filter = QSerializer().dumps(Q(name='Bebop'))
        searched_phone = '#123'
        response = self.assertGET200(
            self.url,
            data={
                'hfilter': hf.id,
                'q_filter': q_filter,
                'search-regular_field-phone': searched_phone,
            },
        )

        page_tree = self.get_html_tree(response.content)
        buttons_node = self.get_html_node_or_fail(
            page_tree, ".//div[@class='list-header-buttons clearfix']",
        )

        hrefs = [
            button_node.attrib.get('href')
            for button_node in buttons_node.findall('a')
        ]
        self.assertEqual(FakeOrganisation.get_create_absolute_url(), hrefs[0])

        data_hrefs = [
            button_node.attrib.get('data-action-url')
            for button_node in buttons_node.findall('a')
        ]
        dl_url = reverse('creme_core__mass_export', query={'ct_id': ct_id})
        dl_uri = data_hrefs[1]
        self.assertStartsWith(dl_uri, dl_url)
        self.assertIn(f'hfilter={hf.id}', dl_uri)
        self.assertIn(f'&extra_q={quote(q_filter)}', dl_uri)
        self.assertIn(f'&search-regular_field-phone={quote(searched_phone)}', dl_uri)

        dl_header_uri = data_hrefs[2]
        self.assertStartsWith(dl_header_uri, dl_url)
        self.assertIn('&header=true', dl_header_uri)

        self.assertEqual(reverse('creme_core__mass_import',   args=(ct_id,)), hrefs[3])
        self.assertEqual(reverse('creme_core__batch_process', args=(ct_id,)), hrefs[4])

    @override_settings(
        FAST_QUERY_MODE_THRESHOLD=1_000_000,
        PAGE_SIZES=[10, 25],
        DEFAULT_PAGE_SIZE_IDX=1,
    )
    def test_search__regular_fields__str(self):
        user = self.login_as_root_and_get()

        create_orga = partial(FakeOrganisation.objects.create, user=user)
        bebop     = create_orga(name='Bebop')
        swordfish = create_orga(name='Swordfish',   phone='668899')
        redtail   = create_orga(name='Redtail',     phone='889977')
        dragons   = create_orga(name='Red Dragons', phone='123')

        phone_cell = EntityCellRegularField.build(model=FakeOrganisation, name='phone')
        self._build_hf(phone_cell)

        url = self.url

        def build_data(name='', phone='', clear=False):
            return {
                'search': 'clear' if clear else '',
                'search-regular_field-name': name,
                'search-' + phone_cell.key: phone,
            }

        response1 = self.assertPOST200(url, data=build_data('Red'))
        table_node1 = self._get_lv_table_node(self._get_lv_node(response1))
        widget_node1 = self._get_lv_header_widget_nodes(
            table_node1, phone_cell.key, input_type='input',
        )[0]
        self.assertEqual('text', widget_node1.attrib.get('data-lv-search-widget'))
        self.assertNotIn('value', widget_node1.attrib)
        # self.assertEqual(_('Phone number'), widget_node.attrib.get('title')) TODO ?

        content1 = self._get_lv_cell_contents(table_node1)
        self.assertNotIn(bebop.name,     content1)
        self.assertNotIn(swordfish.name, content1)
        self.assertCountOccurrences(redtail.name, content1, count=1)
        self.assertCountOccurrences(dragons.name, content1, count=1)
        self.assertEqual(2, response1.context['page_obj'].paginator.count)

        # ---
        response2 = self.assertPOST200(url, data=build_data('', '88'))
        table_node2 = self._get_lv_table_node(self._get_lv_node(response2))
        content2 = self._get_lv_cell_contents(table_node2)
        self.assertNotIn(bebop.name,   content2)
        self.assertIn(swordfish.name,  content2)
        self.assertIn(redtail.name,    content2)
        self.assertNotIn(dragons.name, content2)
        widget_node2 = self._get_lv_header_widget_nodes(
            table_node2, phone_cell.key, input_type='input',
        )[0]
        self.assertEqual('88', widget_node2.attrib.get('value'))

        # ---
        response3 = self.assertPOST200(url, data=build_data('Red', '88'))
        content3 = self._get_lv_cell_contents(
            self._get_lv_table_node(self._get_lv_node(response3))
        )
        self.assertNotIn(bebop.name,     content3)
        self.assertNotIn(swordfish.name, content3)
        self.assertIn(redtail.name,      content3)
        self.assertNotIn(dragons.name,   content3)

        # ---
        context = CaptureQueriesContext()

        with context:
            response4 = self.assertPOST200(url, data=build_data(clear=True))

        content4 = self._get_lv_cell_contents(
            self._get_lv_table_node(self._get_lv_node(response4))
        )
        self.assertIn(bebop.name,     content4)
        self.assertIn(swordfish.name, content4)
        self.assertIn(redtail.name,   content4)
        self.assertIn(dragons.name,   content4)
        self.assertEqual(4, response4.context['page_obj'].paginator.count)

        self._assertFastCount(context.captured_sql)

    def test_search__regular_fields__bool(self):
        user = self.login_as_root_and_get()

        create_orga = partial(FakeOrganisation.objects.create, user=user)
        bebop = create_orga(name='Bebop inc', subject_to_vat=False)
        nerv  = create_orga(name='NERV',      subject_to_vat=True)
        seele = create_orga(name='Seele',     subject_to_vat=True)

        cell = EntityCellRegularField.build(model=FakeOrganisation, name='subject_to_vat')
        hf = self._build_hf(cell)
        url = self.url
        data = {'hfilter': hf.id}
        response1 = self.assertPOST200(url, data={**data, f'search-{cell.key}': '1'})
        orgas_set1 = self._get_entities_set(response1)
        self.assertNotIn(bebop, orgas_set1)
        self.assertIn(nerv,     orgas_set1)
        self.assertIn(seele,    orgas_set1)

        # -------------------------------
        # with CaptureQueriesContext() as context:  TODO
        response2 = self.assertPOST200(url, data={**data, f'search-{cell.key}': '0'})

        orgas_set2 = self._get_entities_set(response2)
        self.assertIn(bebop,    orgas_set2)
        self.assertNotIn(nerv,  orgas_set2)
        self.assertNotIn(seele, orgas_set2)

        # Empty search => stored search used ---
        response3 = self.assertPOST200(url, data=data)

        orgas_set3 = self._get_entities_set(response3)
        self.assertIn(bebop,    orgas_set3)
        self.assertNotIn(nerv,  orgas_set3)
        self.assertNotIn(seele, orgas_set3)

        # TODO
        # self._assertNoDistinct(context.captured_sql)

    def test_search__regular_fields__fk(self):
        "ForeignKey (NULL or not)."
        user = self.login_as_root_and_get()

        create_sector = FakeSector.objects.create
        mercenary = create_sector(title='Mercenary')
        robotics  = create_sector(title='Robotics')

        create_orga = partial(FakeOrganisation.objects.create, user=user)
        bebop = create_orga(name='Bebop inc', sector=mercenary)
        nerv  = create_orga(name='NERV',      sector=robotics)
        seele = create_orga(name='Seele')

        cell = EntityCellRegularField.build(model=FakeOrganisation, name='sector')
        hf = self._build_hf(cell)

        url = self.url
        data = {'hfilter': hf.id}
        # ----------------------------------------------------------------------
        response = self.assertGET200(url, data=data)
        widget_node = self._get_lv_header_widget_nodes(
            self._get_lv_table_node(self._get_lv_node(response)), cell.key, input_type='select',
        )[0]
        # self.assertEqual(_('Sector'), widget_node.attrib.get('title'))  TODO

        options = self._get_options_for_select_node(widget_node)
        self.assertInChoices(
            value='', label=pgettext('creme_core-filter', 'All'), choices=options,
        )
        self.assertInChoices(value=str(mercenary.id), label=mercenary.title, choices=options)
        self.assertInChoices(value=str(robotics.id),  label=robotics.title,  choices=options)

        # ----------------------------------------------------------------------
        response = self.assertPOST200(url, data={**data, 'search-' + cell.key: str(mercenary.id)})
        orgas_set = self._get_entities_set(response)
        self.assertIn(bebop,    orgas_set)
        self.assertNotIn(nerv,  orgas_set)
        self.assertNotIn(seele, orgas_set)

        # ----------------------------------------------------------------------
        response = self.assertPOST200(url, data={**data, 'search-' + cell.key: 'NULL'})
        orgas_set = self._get_entities_set(response)
        self.assertNotIn(bebop, orgas_set)
        self.assertNotIn(nerv,  orgas_set)
        self.assertIn(seele,    orgas_set)

    def test_search__regular_fields__boolean(self):
        "BooleanField (NULL or not)."
        user = self.login_as_root_and_get()

        create_orga = partial(FakeOrganisation.objects.create, user=user)
        bebop = create_orga(name='Bebop inc', subject_to_vat=True)
        nerv  = create_orga(name='NERV',      subject_to_vat=False)
        seele = create_orga(name='Seele',     subject_to_vat=True)

        cell = EntityCellRegularField.build(model=FakeOrganisation, name='subject_to_vat')
        hf = self._build_hf(cell)

        url = self.url
        data = {'hfilter': hf.id}

        # ----------------------------------------------------------------------
        response1 = self.assertGET200(url, data=data)
        widget_node = self._get_lv_header_widget_nodes(
            self._get_lv_table_node(self._get_lv_node(response1)), cell.key,
            input_type='select',
        )[0]

        options = self._get_options_for_select_node(widget_node)
        self.assertInChoices(
            value='',  label=pgettext('creme_core-filter', 'All'), choices=options,
        )
        self.assertInChoices(value='1', label=_('Yes'), choices=options)
        self.assertInChoices(value='0', label=_('No'),  choices=options)
        self.assertEqual(3, len(options))

        # ----------------------------------------------------------------------
        response2 = self.assertPOST200(url, data={**data, f'search-{cell.key}': '1'})
        orgas_set = self._get_entities_set(response2)
        self.assertIn(bebop, orgas_set)
        self.assertIn(seele, orgas_set)
        self.assertNotIn(nerv, orgas_set)

        # ----------------------------------------------------------------------
        response3 = self.assertPOST200(url, data={**data, f'search-{cell.key}': '0'})
        orgas_set = self._get_entities_set(response3)
        self.assertIn(nerv, orgas_set)
        self.assertNotIn(bebop, orgas_set)
        self.assertNotIn(seele, orgas_set)

    def test_search__date_fields(self):
        user = self.login_as_root_and_get()

        create_orga = partial(FakeOrganisation.objects.create, user=user)
        bebop     = create_orga(name='Bebop',     creation_date=date(year=2075, month=3, day=26))
        swordfish = create_orga(name='Swordfish', creation_date=date(year=2074, month=6, day=5))
        redtail   = create_orga(name='Redtail',   creation_date=date(year=2076, month=7, day=25))
        dragons   = create_orga(name='Red Dragons')

        cell = EntityCellRegularField.build(model=FakeOrganisation, name='creation_date')
        hf = self._build_hf(cell)
        url = self.url

        # ----------------------------------------------------------------------
        date_value = self.formfield_value_date

        def post(start, end=''):
            ckey = cell.key
            return self.assertPOST200(
                url,
                data={
                    'hfilter': hf.id,
                    f'search-{ckey}-start': start,
                    f'search-{ckey}-end': end,
                },
            )

        content1 = self._get_lv_cell_contents(self._get_lv_table_node(self._get_lv_node(
            post(date_value(2075, 1, 1))
        )))
        self.assertIn(bebop.name,        content1)
        self.assertNotIn(swordfish.name, content1)
        self.assertIn(redtail.name,      content1)
        self.assertNotIn(dragons.name,   content1)

        # ---
        content2 = self._get_lv_cell_contents(self._get_lv_table_node(self._get_lv_node(
            post('', date_value(2075, 1, 1))
        )))
        self.assertNotIn(bebop.name,   content2)
        self.assertIn(swordfish.name,  content2)
        self.assertNotIn(redtail.name, content2)
        self.assertNotIn(dragons.name, content2)

        # ---
        content3 = self._get_lv_cell_contents(self._get_lv_table_node(self._get_lv_node(
            post(date_value(2074, 1, 1), date_value(2074, 12, 31))
        )))
        self.assertNotIn(bebop.name,   content3)
        self.assertIn(swordfish.name,  content3)
        self.assertNotIn(redtail.name, content3)
        self.assertNotIn(dragons.name, content3)

        # ---
        content4 = self._get_lv_cell_contents(self._get_lv_table_node(self._get_lv_node(
            post('notadate')
        )))
        self.assertIn(bebop.name,     content4)
        self.assertIn(swordfish.name, content4)
        self.assertIn(redtail.name,   content4)
        self.assertIn(dragons.name,   content4)

    def test_search__datetime_fields(self):
        user = self.login_as_root_and_get()

        create_orga = partial(FakeOrganisation.objects.create, user=user)
        bebop      = create_orga(name='Bebop')
        swordfish  = create_orga(name='Swordfish')
        swordfish2 = create_orga(name='Swordfish II')
        sf_alpha   = create_orga(name='Swordfish Alpha')
        redtail    = create_orga(name='Redtail')

        def set_created(orga, dt):
            FakeOrganisation.objects.filter(pk=orga.id).update(created=dt)

        create_dt = self.create_datetime
        set_created(bebop,      create_dt(year=2075, month=3, day=26))
        set_created(swordfish,  create_dt(year=2074, month=6, day=5, hour=12))
        set_created(swordfish2, create_dt(year=2074, month=6, day=6, hour=0))  # Next day
        # Previous day
        set_created(sf_alpha,   create_dt(year=2074, month=6, day=4, hour=23, minute=59))
        set_created(redtail,    create_dt(year=2076, month=7, day=25))

        cell = EntityCellRegularField.build(model=FakeOrganisation, name='created')
        hf = self._build_hf(cell)
        url = self.url

        def post(start='', end=''):
            response = self.assertPOST200(
                url,
                data={
                    'hfilter': hf.id,
                    f'search-{cell.key}-start': start,
                    f'search-{cell.key}-end': end,
                },
            )
            return self._get_lv_cell_contents(
                self._get_lv_table_node(self._get_lv_node(response))
            )

        date_value = self.formfield_value_date
        content = post(date_value(2075, 1, 1))
        self.assertIn(bebop.name,        content)
        self.assertNotIn(swordfish.name, content)
        self.assertIn(redtail.name,      content)

        content = post('', date_value(2075, 1, 1))
        self.assertNotIn(bebop.name,   content)
        self.assertIn(swordfish.name,  content)
        self.assertNotIn(redtail.name, content)

        content = post(date_value(2074, 1, 1), date_value(2074, 12, 31))
        self.assertNotIn(bebop.name,   content)
        self.assertIn(swordfish.name,  content)
        self.assertNotIn(redtail.name, content)

        content = post(date_value(2074, 6, 5), date_value(2074, 6, 5))
        self.assertNotIn(bebop.name,      content)
        self.assertIn(swordfish.name,     content)
        self.assertNotIn(swordfish2.name, content)
        self.assertNotIn(sf_alpha.name,   content)
        self.assertNotIn(redtail.name,    content)

    def test_search__field_with_choices(self):
        user = self.login_as_root_and_get()

        invoice = FakeInvoice.objects.create(user=user, name='Invoice #1')
        create_line = partial(FakeInvoiceLine.objects.create, user=user, linked_invoice=invoice)
        line1 = create_line(item='Item #1', discount_unit=FakeInvoiceLine.Discount.PERCENT)
        line2 = create_line(item='Item #2', discount_unit=FakeInvoiceLine.Discount.AMOUNT)
        line3 = create_line(item='Item #3', discount_unit=FakeInvoiceLine.Discount.PERCENT)

        build_cell = partial(EntityCellRegularField.build, model=FakeInvoiceLine)
        du_cell = build_cell(name='discount_unit')
        hf = HeaderFilter.objects.proxy(
            id='test-hf_invoiceline', name='Line view', model=FakeInvoiceLine,
            cells=[
                build_cell(name='item'),
                build_cell(name='discount'),
                du_cell,
            ],
        ).get_or_create()[0]

        url = FakeInvoiceLine.get_lv_absolute_url()
        response1 = self.assertGET200(url, data={'hfilter': hf.id})
        widget_node = self._get_lv_header_widget_nodes(
            self._get_lv_table_node(self._get_lv_node(response1)),
            du_cell.key, input_type='select',
        )[0]

        options = self._get_options_for_select_node(widget_node)
        self.assertInChoices(
            value='', label=pgettext('creme_core-filter', 'All'), choices=options,
        )

        # ---------------------------------------------------------------------
        response2 = self.assertPOST200(
            url,
            data={
                'hfilter': hf.id,
                f'search-{du_cell.key}': FakeInvoiceLine.Discount.PERCENT.value,
            },
        )
        content2 = self._get_lv_cell_contents(
            self._get_lv_table_node(self._get_lv_node(response2))
        )
        self.assertCountOccurrences(line1.item, content2, count=1)
        self.assertCountOccurrences(line3.item, content2, count=1)
        self.assertNotIn(line2.item, content2)

    def test_search__fk(self):
        user = self.login_as_root_and_get()

        create_civ = FakeCivility.objects.create
        mister = create_civ(title='Mister')
        miss   = create_civ(title='Miss')
        self.assertLess(mister.id, miss.id)

        create_img = partial(FakeImage.objects.create, user=user)
        img_faye = create_img(name='Faye selfie')
        img_ed   = create_img(name='Ed selfie')

        create_contact = partial(FakeContact.objects.create, user=user)
        spike = create_contact(
            first_name='Spike', last_name='Spiegel', civility=mister,
        )
        faye = create_contact(
            first_name='Faye', last_name='Valentine', civility=miss, image=img_faye,
        )
        ed = create_contact(
            first_name='Edward', last_name='Wong', image=img_ed,
        )

        build_cell = partial(EntityCellRegularField.build, model=FakeContact)
        cell_image    = build_cell(name='image')
        cell_img_name = build_cell(name='image__name')
        cell_civ      = build_cell(name='civility')
        cell_civ_name = build_cell(name='civility__title')
        hf = HeaderFilter.objects.proxy(
            id='test-hf_contact', name='Order02 view', model=FakeContact,
            cells=[
                build_cell(name='last_name'),
                cell_image, cell_img_name, cell_civ, cell_civ_name,
            ],
        ).get_or_create()[0]

        url = FakeContact.get_lv_absolute_url()

        # ---------------------------------------------------------------------
        response = self.assertGET200(url, data={'hfilter': hf.id})
        get_widget_node = partial(
            self._get_lv_header_widget_nodes,
            lv_table_node=self._get_lv_table_node(self._get_lv_node(response)),
        )
        get_widget_node(cell_key=cell_image.key,    input_type='input')
        get_widget_node(cell_key=cell_img_name.key, input_type='input')
        get_widget_node(cell_key=cell_civ_name.key, input_type='input')

        civ_widget_node = get_widget_node(cell_key=cell_civ.key, input_type='select')[0]
        options = self._get_options_for_select_node(civ_widget_node)
        self.assertInChoices(value=str(mister.id), label=mister.title, choices=options)
        self.assertInChoices(value=str(miss.id),   label=miss.title,   choices=options)

        # ---------------------------------------------------------------------
        response = self.assertPOST200(url, data={'hfilter': hf.id})

        with self.assertNoException():
            selected_hf = response.context['header_filters'].selected

        self.assertEqual(hf, selected_hf)

        # ---------------------------------------------------------------------
        response = self.assertPOST200(url, data={f'search-{cell_civ.key}': mister.id})
        content = self._get_lv_cell_contents(self._get_lv_table_node(self._get_lv_node(response)))
        self.assertCountOccurrences(spike.last_name, content, count=1)
        self.assertNotIn(faye.last_name, content)
        self.assertNotIn(ed.last_name,   content)

        # ---------------------------------------------------------------------
        response = self.assertPOST200(url, data={f'search-{cell_civ_name.key}': 'iss'})
        content = self._get_lv_cell_contents(self._get_lv_table_node(self._get_lv_node(response)))
        self.assertNotIn(spike.last_name, content)
        self.assertIn(faye.last_name,     content)
        self.assertNotIn(ed.last_name,    content)

        # ---------------------------------------------------------------------
        response = self.assertPOST200(url, data={f'search-{cell_img_name.key}': img_ed.name})
        content = self._get_lv_cell_contents(self._get_lv_table_node(self._get_lv_node(response)))
        self.assertNotIn(spike.last_name, content)
        self.assertNotIn(faye.last_name,  content)
        self.assertIn(ed.last_name,       content)

        # ---------------------------------------------------------------------
        response = self.assertPOST200(url, data={f'search-{cell_image.key}': img_ed.name})
        content = self._get_lv_cell_contents(self._get_lv_table_node(self._get_lv_node(response)))
        self.assertNotIn(spike.last_name, content)
        self.assertNotIn(faye.last_name,  content)
        self.assertIn(ed.last_name,       content)

    def test_search__fk__sub_fk(self):
        "Search on a subfield which is a FK too."
        user = self.login_as_root_and_get()

        create_cat = FakeFolderCategory.objects.create
        cat1 = create_cat(name='Maps')
        cat2 = create_cat(name='Blue prints')

        create_folder = partial(FakeFolder.objects.create, user=user)
        folder1 = create_folder(title='Earth maps', category=cat1)
        folder2 = create_folder(title='Mars maps',  category=cat1)
        folder3 = create_folder(title='Ships',      category=cat2)
        folder4 = create_folder(title="Faye's pix")

        create_doc = partial(FakeDocument.objects.create, user=user)
        doc1 = create_doc(title='Japan map',   linked_folder=folder1)
        doc2 = create_doc(title='Mars city 1', linked_folder=folder2)
        doc3 = create_doc(title='Swordfish',   linked_folder=folder3)
        doc4 = create_doc(title='Money!!.jpg', linked_folder=folder4)

        build_cell = partial(EntityCellRegularField.build, model=FakeDocument)
        cell = build_cell(name='linked_folder__category')
        hf = HeaderFilter.objects.proxy(
            id='test-hf_doc', name='Doc view', model=FakeDocument,
            cells=[build_cell(name='title'), cell],
        ).get_or_create()[0]

        response = self.assertPOST200(
            FakeDocument.get_lv_absolute_url(),
            data={
                'hfilter': hf.id,
                f'search-{cell.key}': cat1.id,
            },
        )
        content = self._get_lv_cell_contents(self._get_lv_table_node(self._get_lv_node(response)))
        self.assertIn(doc1.title, content)
        self.assertIn(doc2.title, content)
        self.assertNotIn(doc3.title, content)
        self.assertNotIn(doc4.title, content)

        # '*is empty*'
        response = self.assertPOST200(
            FakeDocument.get_lv_absolute_url(),
            data={
                'hfilter': hf.id,
                f'search-{cell.key}': 'NULL',
            },
        )
        content = self._get_lv_cell_contents(self._get_lv_table_node(self._get_lv_node(response)))
        self.assertNotIn(doc1.title, content)
        self.assertNotIn(doc2.title, content)
        self.assertNotIn(doc3.title, content)
        self.assertIn(doc4.title, content)

    def test_search__fk__sub_fk_on_entity(self):
        "Search on a subfield which is a FK on CremeEntity."
        user = self.login_as_root_and_get()

        create_folder = partial(FakeFolder.objects.create, user=user)
        p_folder1 = create_folder(title='Maps')
        p_folder2 = create_folder(title='Pix')

        folder1 = create_folder(title='Earth', parent=p_folder1)
        folder2 = create_folder(title='Mars',  parent=p_folder1)
        folder3 = create_folder(title='Ships')
        folder4 = create_folder(title="Faye's pix", parent=p_folder2)

        create_doc = partial(FakeDocument.objects.create, user=user)
        doc1 = create_doc(title='Japan',       linked_folder=folder1)
        doc2 = create_doc(title='Mars city 1', linked_folder=folder2)
        doc3 = create_doc(title='Swordfish',   linked_folder=folder3)
        doc4 = create_doc(title='Money!!.jpg', linked_folder=folder4)

        build_cell = partial(EntityCellRegularField.build, model=FakeDocument)
        cell = build_cell(name='linked_folder__parent')
        hf = HeaderFilter.objects.proxy(
            id='test-hf_doc', name='Doc view', model=FakeDocument,
            cells=[build_cell(name='title'), cell],
        ).get_or_create()[0]

        response = self.assertPOST200(
            FakeDocument.get_lv_absolute_url(),
            data={
                'hfilter': hf.id,
                f'search-{cell.key}': p_folder1.title,
            },
        )
        content = self._get_lv_cell_contents(self._get_lv_table_node(self._get_lv_node(response)))
        self.assertIn(doc1.title, content)
        self.assertIn(doc2.title, content)
        self.assertNotIn(doc3.title, content)
        self.assertNotIn(doc4.title, content)

    def test_search__m2m__entity(self):
        "M2M to CremeEntity model."
        user = self.login_as_root_and_get()
        build_cell = partial(EntityCellRegularField.build, model=FakeEmailCampaign)

        cell_m2m = build_cell(name='mailing_lists')
        hf = HeaderFilter.objects.proxy(
            id='test-hf_camp', name='Campaign view',
            model=FakeEmailCampaign,
            cells=[build_cell(name='name'), cell_m2m],
        ).get_or_create()[0]

        create_mlist = partial(FakeMailingList.objects.create, user=user)
        ml1 = create_mlist(name='Bebop staff')
        ml2 = create_mlist(name='Mafia staff')

        create_camp = partial(FakeEmailCampaign.objects.create, user=user)
        camp1 = create_camp(name='Ships')
        camp2 = create_camp(name='Bonzais')
        camp3 = create_camp(name='Mushrooms')

        camp1.mailing_lists.set([ml1, ml2])
        camp2.mailing_lists.set([ml1])

        url = FakeEmailCampaign.get_lv_absolute_url()
        # ----------------------------------------------------------------------
        response = self.assertGET200(url, data={'hfilter': hf.id})
        self._get_lv_header_widget_nodes(
            self._get_lv_table_node(self._get_lv_node(response)),
            cell_m2m.key, input_type='input',
        )

        # ----------------------------------------------------------------------
        def search(term):
            response = self.assertPOST200(
                url,
                data={
                    'hfilter': hf.id,
                    f'search-{cell_m2m.key}': term,
                },
            )
            return self._get_lv_cell_contents(
                self._get_lv_table_node(self._get_lv_node(response))
            )

        content = search('Bebo')
        self.assertCountOccurrences(camp1.name, content, count=1)
        self.assertCountOccurrences(camp2.name, content, count=1)
        self.assertNotIn(camp3.name, content)

        content = search('afia')
        self.assertCountOccurrences(camp1.name, content, count=1)
        self.assertNotIn(camp2.name, content)
        self.assertNotIn(camp3.name, content)

        content = search('staff')
        self.assertCountOccurrences(camp1.name, content, count=1)  # Not 2 !!

    def test_search__m2m__minion(self):
        "M2M to basic model."
        user = self.login_as_root_and_get()
        build_cell = partial(EntityCellRegularField.build, model=FakeImage)
        cell_m2m = build_cell(name='categories')
        hf = HeaderFilter.objects.proxy(
            id='test-hf_img', name='Image view', model=FakeImage,
            cells=[build_cell(name='name'), cell_m2m],
        ).get_or_create()[0]

        cat1, cat2 = FakeImageCategory.objects.all()[:2]

        create_img = partial(FakeImage.objects.create, user=user)
        img1 = create_img(name='Bebop image')
        img2 = create_img(name='Dragon logo')
        img3 = create_img(name='Mushrooms image')

        img1.categories.set([cat1, cat2])
        img2.categories.set([cat1])

        def search(searched):
            response = self.assertPOST200(
                FakeImage.get_lv_absolute_url(),
                data={
                    'hfilter': hf.id,
                    f'search-{cell_m2m.key}': searched,
                },
            )
            return self._get_lv_cell_contents(
                self._get_lv_table_node(self._get_lv_node(response))
            )

        content = search(self.UNUSED_PK)  # Invalid we need an ID => no filter
        self.assertIn(img1.name, content)
        self.assertIn(img3.name, content)

        content = search(cat1.id)
        self.assertIn(img1.name,    content)
        self.assertIn(img2.name,    content)
        self.assertNotIn(img3.name, content)

        content = search(cat2.id)
        self.assertIn(img1.name,    content)
        self.assertNotIn(img2.name, content)
        self.assertNotIn(img3.name, content)

        content = search('NULL')
        self.assertNotIn(img1.name, content)
        self.assertNotIn(img2.name, content)
        self.assertIn(img3.name,    content)

    def test_search__m2m__sub_field(self):
        "M2M to basic model + sub-field."
        user = self.login_as_root_and_get()
        build_cell = partial(EntityCellRegularField.build, model=FakeImage)
        cell_m2m = build_cell(name='categories__name')
        hf = HeaderFilter.objects.proxy(
            id='test-hf_img', name='Image view', model=FakeImage,
            cells=[build_cell(name='name'), cell_m2m],
        ).get_or_create()[0]

        cat1, cat2 = FakeImageCategory.objects.all()[:2]

        create_img = partial(FakeImage.objects.create, user=user)
        img1 = create_img(name='Bebop image')
        img2 = create_img(name='Dragon logo')
        img3 = create_img(name='Mushrooms image')

        img1.categories.set([cat1, cat2])
        img2.categories.set([cat1])

        def search(searched):
            response = self.assertPOST200(
                FakeImage.get_lv_absolute_url(),
                data={
                    'hfilter': hf.id,
                    f'search-{cell_m2m.key}': searched,
                },
            )
            return self._get_lv_cell_contents(
                self._get_lv_table_node(self._get_lv_node(response))
            )

        content = search(cat1.name[:5])
        self.assertIn(img1.name,    content)
        self.assertIn(img2.name,    content)
        self.assertNotIn(img3.name, content)

    def test_search__relations(self):
        user = self.login_as_root_and_get()

        create_orga = partial(FakeOrganisation.objects.create, user=user)
        bebop     = create_orga(name='Bebop')
        swordfish = create_orga(name='Swordfish')
        redtail   = create_orga(name='Redtail')
        dragons   = create_orga(name='Red Dragons')

        create_contact = partial(FakeContact.objects.create, user=user)
        spike = create_contact(first_name='Spike', last_name='Spiegel')
        faye  = create_contact(first_name='Faye',  last_name='Spiegel')
        jet   = create_contact(first_name='Jet',   last_name='Black')

        rtype = self._create_rtype()
        create_rel = partial(Relation.objects.create, user=user, type=rtype)
        create_rel(subject_entity=swordfish, object_entity=spike)
        create_rel(subject_entity=redtail,   object_entity=faye)
        create_rel(subject_entity=bebop,     object_entity=jet)

        cell = EntityCellRelation(model=FakeOrganisation, rtype=rtype)
        hf = self._build_hf(cell)

        url = self.url
        # ----------------------------------------------------------------------
        response = self.assertGET200(url, data={'hfilter': hf.id})
        self._get_lv_header_widget_nodes(
            self._get_lv_table_node(self._get_lv_node(response)),
            cell.key, input_type='input',
        )

        # ----------------------------------------------------------------------
        data = {
            'hfilter': hf.id,
            'search-regular_field-name': '',
            'search-' + cell.key: 'Spiege',
        }
        response = self.assertPOST200(url, data=data)
        content = self._get_lv_cell_contents(
            self._get_lv_table_node(self._get_lv_node(response))
        )
        self.assertNotIn(bebop.name,   content)
        self.assertIn(swordfish.name,  content)
        self.assertIn(redtail.name,    content)
        self.assertNotIn(dragons.name, content)

        data['search-regular_field-name'] = 'Swo'
        content = self._get_lv_cell_contents(self._get_lv_table_node(self._get_lv_node(
            self.assertPOST200(url, data=data)
        )))
        self.assertNotIn(bebop.name,   content)
        self.assertIn(swordfish.name,  content)
        self.assertNotIn(redtail.name, content)
        self.assertNotIn(dragons.name, content)

    def test_search__relations__2_searches(self):
        "2 searches at the same time."
        user = self.login_as_root_and_get()

        create_orga = partial(FakeOrganisation.objects.create, user=user)
        bebop     = create_orga(name='Bebop')
        swordfish = create_orga(name='Swordfish')
        redtail   = create_orga(name='Redtail')

        create_contact = partial(FakeContact.objects.create, user=user)
        spike = create_contact(first_name='Spike', last_name='Spiegel')
        faye  = create_contact(first_name='Faye',  last_name='Spiegel')
        jet   = create_contact(first_name='Jet',   last_name='Black')

        rtype1 = self._create_rtype(index=0)
        rtype2 = self._create_rtype(index=1)

        create_rel = partial(Relation.objects.create, user=user)
        create_rel(subject_entity=swordfish, object_entity=spike, type=rtype1)
        create_rel(subject_entity=redtail,   object_entity=faye,  type=rtype1)
        create_rel(subject_entity=bebop,     object_entity=jet,   type=rtype1)

        create_rel(subject_entity=swordfish, object_entity=jet, type=rtype2)
        create_rel(subject_entity=bebop,     object_entity=jet, type=rtype2)

        cell1 = EntityCellRelation(model=FakeOrganisation, rtype=rtype1)
        cell2 = EntityCellRelation(model=FakeOrganisation, rtype=rtype2)
        hf = self._build_hf(cell1, cell2)

        response = self.assertPOST200(
            self.url,
            data={
                'hfilter': hf.id,
                f'search-{cell1.key}': 'Jet',
                f'search-{cell2.key}': 'Jet',
            },
        )
        content = self._get_lv_cell_contents(
            self._get_lv_table_node(self._get_lv_node(response))
        )
        self.assertIn(bebop.name, content)
        self.assertNotIn(swordfish.name, content)
        self.assertNotIn(redtail.name,   content)

    def test_search__custom_field__int(self):
        user = self.login_as_root_and_get()

        create_orga = partial(FakeOrganisation.objects.create, user=user)
        bebop     = create_orga(name='Bebop')
        swordfish = create_orga(name='Swordfish')
        redtail   = create_orga(name='Redtail')
        dragons   = create_orga(name='Red Dragons')

        cfield = CustomField.objects.create(
            name='size (m)', content_type=self.ctype, field_type=CustomField.INT,
        )
        klass = cfield.value_class

        def set_cfvalue(entity, value):
            klass(custom_field=cfield, entity=entity).set_value_n_save(value)

        set_cfvalue(bebop,     42)
        set_cfvalue(swordfish, 12)
        set_cfvalue(redtail,   4)

        cell = EntityCellCustomField(cfield)
        hf = self._build_hf(cell)

        # ----------------------------------------------------------------------
        response1 = self.assertGET200(self.url, data={'hfilter': hf.id})
        self._get_lv_header_widget_nodes(
            self._get_lv_table_node(self._get_lv_node(response1)),
            cell.key, input_type='input',
        )

        # ----------------------------------------------------------------------
        response2 = self.assertPOST200(
            self.url,
            data={
                'hfilter': hf.id,
                'search-regular_field-name': '',
                f'search-{cell.key}': '>10',
            },
        )
        content2 = self._get_lv_cell_contents(
            self._get_lv_table_node(self._get_lv_node(response2))
        )
        self.assertIn(bebop.name,     content2)
        self.assertIn(swordfish.name, content2)
        self.assertNotIn(redtail.name, content2)
        self.assertNotIn(dragons.name, content2)

    def test_search__custom_field__int_n_str(self):
        user = self.login_as_root_and_get()

        create_orga = partial(FakeOrganisation.objects.create, user=user)
        bebop     = create_orga(name='Bebop')
        swordfish = create_orga(name='Swordfish')
        redtail   = create_orga(name='Redtail')
        dragons   = create_orga(name='Red Dragons')

        create_cfield = partial(CustomField.objects.create, content_type=self.ctype)
        cfield1 = create_cfield(name='size (m)',   field_type=CustomField.INT)
        cfield2 = create_cfield(name='color code', field_type=CustomField.STR)

        def set_cfvalue(cfield, entity, value):
            cfield.value_class(custom_field=cfield, entity=entity).set_value_n_save(value)

        set_cfvalue(cfield1, bebop,     42)
        set_cfvalue(cfield1, swordfish, 12)
        set_cfvalue(cfield1, redtail,   4)

        set_cfvalue(cfield2, swordfish, '#ff0000')
        set_cfvalue(cfield2, redtail,   '#050508')

        cell1 = EntityCellCustomField(cfield1)
        cell2 = EntityCellCustomField(cfield2)
        hf = self._build_hf(cell1, cell2)

        response = self.assertPOST200(
            self.url,
            data={
                'hfilter': hf.id,
                'search-regular_field-name': '',
                f'search-{cell1.key}': '4',
                f'search-{cell2.key}': '#05',
            },
        )
        orgas_set = self._get_entities_set(response)
        self.assertNotIn(bebop,     orgas_set)
        self.assertNotIn(swordfish, orgas_set)
        self.assertIn(redtail,      orgas_set)
        self.assertNotIn(dragons,   orgas_set)

    def test_search__custom_field__int_x2(self):
        user = self.login_as_root_and_get()

        create_orga = partial(FakeOrganisation.objects.create, user=user)
        bebop     = create_orga(name='Bebop')
        swordfish = create_orga(name='Swordfish')
        redtail   = create_orga(name='Redtail')
        dragons   = create_orga(name='Red Dragons')

        create_cfield = partial(
            CustomField.objects.create,
            content_type=self.ctype,
            field_type=CustomField.INT,
        )
        cfield1 = create_cfield(name='size (m)')
        cfield2 = create_cfield(name='weight')

        def set_cfvalue(cfield, entity, value):
            cfield.value_class(custom_field=cfield, entity=entity).set_value_n_save(value)

        set_cfvalue(cfield1, bebop,     42)
        set_cfvalue(cfield1, swordfish, 12)
        set_cfvalue(cfield1, redtail,   4)

        set_cfvalue(cfield2, swordfish, 1000)
        set_cfvalue(cfield2, redtail,   2000)

        cell1 = EntityCellCustomField(cfield1)
        cell2 = EntityCellCustomField(cfield2)
        hf = self._build_hf(cell1, cell2)
        response = self.assertPOST200(
            self.url,
            data={
                'hfilter': hf.id,
                'search-regular_field-name': '',
                f'search-{cell1.key}': '4',
                f'search-{cell2.key}': '2000',
            },
        )
        orgas_set = self._get_entities_set(response)
        self.assertNotIn(bebop,     orgas_set)
        self.assertNotIn(swordfish, orgas_set)
        self.assertIn(redtail,      orgas_set)
        self.assertNotIn(dragons,   orgas_set)

    def test_search__custom_field__enum(self):
        user = self.login_as_root_and_get()

        create_orga = partial(FakeOrganisation.objects.create, user=user)
        bebop     = create_orga(name='Bebop')
        swordfish = create_orga(name='Swordfish')
        redtail   = create_orga(name='Redtail')
        dragons   = create_orga(name='Red Dragons')

        cfield = CustomField.objects.create(
            name='Type', content_type=self.ctype, field_type=CustomField.ENUM,
        )

        create_evalue = CustomFieldEnumValue.objects.create
        type1 = create_evalue(custom_field=cfield, value='Light')
        type2 = create_evalue(custom_field=cfield, value='Heavy')

        klass = cfield.value_class

        def set_cfvalue(entity, value):
            klass(custom_field=cfield, entity=entity).set_value_n_save(value)

        set_cfvalue(bebop,     type2.id)
        set_cfvalue(swordfish, type1.id)
        set_cfvalue(redtail,   type1.id)

        cell = EntityCellCustomField(cfield)
        hf = self._build_hf(cell)
        # ----------------------------------------------------------------------
        response = self.assertGET200(self.url, data={'hfilter': hf.id})
        widget_node = self._get_lv_header_widget_nodes(
            self._get_lv_table_node(self._get_lv_node(response)),
            cell.key, input_type='select',
        )[0]

        options = self._get_options_for_select_node(widget_node)
        self.assertInChoices(value='NULL',        label=_('* is empty *'), choices=options)
        self.assertInChoices(value=str(type1.id), label=type1.value,       choices=options)
        self.assertInChoices(value=str(type2.id), label=type2.value,       choices=options)

        # ----------------------------------------------------------------------
        response = self.assertPOST200(
            self.url,
            data={
                'hfilter': hf.id,
                'search-regular_field-name': '',
                f'search-{cell.key}': type1.id,
            },
        )
        orgas_set = self._get_entities_set(response)
        self.assertNotIn(bebop,   orgas_set)
        self.assertIn(swordfish,  orgas_set)
        self.assertIn(redtail,    orgas_set)
        self.assertNotIn(dragons, orgas_set)

        response = self.assertPOST200(
            self.url,
            data={
                'hfilter': hf.id,
                f'search-{cell.key}': 'NULL',
            },
        )
        orgas_set = self._get_entities_set(response)
        self.assertNotIn(bebop,     orgas_set)
        self.assertNotIn(swordfish, orgas_set)
        self.assertNotIn(redtail,   orgas_set)
        self.assertIn(dragons,      orgas_set)

    def test_search__custom_field__multi_enum(self):
        user = self.login_as_root_and_get()

        create_orga = partial(FakeOrganisation.objects.create, user=user)
        bebop    = create_orga(name='Bebop')
        dragons  = create_orga(name='Red Dragons')
        eva01    = create_orga(name='Eva01')
        valkyrie = create_orga(name='Valkyrie')

        cfield = CustomField.objects.create(
            name='Capabilities', content_type=self.ctype, field_type=CustomField.MULTI_ENUM,
        )

        create_evalue = CustomFieldEnumValue.objects.create
        can_walk = create_evalue(custom_field=cfield, value='Walk')
        can_fly  = create_evalue(custom_field=cfield, value='Fly')

        klass = cfield.value_class

        def set_cfvalue(entity, value):
            klass(custom_field=cfield, entity=entity).set_value_n_save(value)

        set_cfvalue(bebop,     [can_fly.id])
        set_cfvalue(eva01,     [can_walk.id])
        set_cfvalue(valkyrie,  [can_fly.id, can_walk.id])

        cell = EntityCellCustomField(cfield)
        hf = self._build_hf(cell)
        # ----------------------------------------------------------------------
        response = self.assertGET200(self.url, data={'hfilter': hf.id})
        widget_node = self._get_lv_header_widget_nodes(
            self._get_lv_table_node(self._get_lv_node(response)),
            cell.key, input_type='select',
        )[0]

        options = self._get_options_for_select_node(widget_node)
        self.assertInChoices(value='NULL',           label=_('* is empty *'), choices=options)
        self.assertInChoices(value=str(can_walk.id), label=can_walk.value,    choices=options)

        # ----------------------------------------------------------------------
        response = self.assertPOST200(
            self.url,
            data={
                'hfilter': hf.id,
                'search-regular_field-name': '',
                f'search-{cell.key}': can_walk.id,
            },
        )
        orgas_set = self._get_entities_set(response)
        self.assertNotIn(bebop,   orgas_set)
        self.assertNotIn(dragons, orgas_set)
        self.assertIn(eva01,      orgas_set)
        self.assertIn(valkyrie,   orgas_set)

        response = self.assertPOST200(
            self.url,
            data={
                'hfilter': hf.id,
                'search-regular_field-name': '',
                f'search-{cell.key}': 'NULL',
            },
        )
        orgas_set = self._get_entities_set(response)
        self.assertNotIn(bebop,    orgas_set)
        self.assertNotIn(eva01,    orgas_set)
        self.assertNotIn(valkyrie, orgas_set)
        self.assertIn(dragons,     orgas_set)

    def test_search__custom_field__enum_x2(self):
        user = self.login_as_root_and_get()

        create_orga = partial(FakeOrganisation.objects.create, user=user)
        bebop     = create_orga(name='Bebop')
        swordfish = create_orga(name='Swordfish')
        redtail   = create_orga(name='Redtail')
        dragons   = create_orga(name='Red Dragons')

        create_cfield = partial(
            CustomField.objects.create,
            content_type=self.ctype, field_type=CustomField.ENUM,
        )
        cfield_type  = create_cfield(name='Type')
        cfield_color = create_cfield(name='Color')

        create_evalue = CustomFieldEnumValue.objects.create
        type1 = create_evalue(custom_field=cfield_type, value='Light')
        type2 = create_evalue(custom_field=cfield_type, value='Heavy')

        color1 = create_evalue(custom_field=cfield_color, value='Red')
        color2 = create_evalue(custom_field=cfield_color, value='Grey')

        def set_cfvalue(cfield, entity, value):
            cfield.value_class(custom_field=cfield, entity=entity).set_value_n_save(value)

        set_cfvalue(cfield_type,  bebop,     type2.id)
        set_cfvalue(cfield_color, bebop,     color2.id)

        set_cfvalue(cfield_type,  swordfish, type1.id)
        set_cfvalue(cfield_color, swordfish, color1.id)

        set_cfvalue(cfield_type,  redtail,   type1.id)
        set_cfvalue(cfield_color, redtail,   color2.id)

        cell_type  = EntityCellCustomField(cfield_type)
        cell_color = EntityCellCustomField(cfield_color)
        hf = self._build_hf(cell_type, cell_color)
        response1 = self.assertPOST200(
            self.url,
            data={
                'hfilter': hf.id,
                'search-regular_field-name': '',
                f'search-{cell_type.key}':   type1.id,
                f'search-{cell_color.key}':  color2.id,
            },
        )
        orgas_set = self._get_entities_set(response1)
        self.assertNotIn(bebop,     orgas_set)
        self.assertNotIn(swordfish, orgas_set)
        self.assertIn(redtail,      orgas_set)
        self.assertNotIn(dragons,   orgas_set)

        # ---
        set_cfvalue(cfield_color, dragons, color1.id)  # Type is NULL

        response2 = self.assertPOST200(
            self.url,
            data={
                'hfilter': hf.id,
                'search-regular_field-name': '',
                f'search-{cell_type.key}':   'NULL',
                f'search-{cell_color.key}':  color1.id,
            },
        )
        orgas_set = self._get_entities_set(response2)
        self.assertNotIn(bebop,     orgas_set)
        self.assertNotIn(swordfish, orgas_set)
        self.assertNotIn(redtail,   orgas_set)
        self.assertIn(dragons,      orgas_set)

    def test_search__custom_field__multi_enum_x2(self):
        user = self.login_as_root_and_get()

        create_orga = partial(FakeOrganisation.objects.create, user=user)
        bebop     = create_orga(name='Bebop')
        swordfish = create_orga(name='Swordfish')
        eva02     = create_orga(name='Eva02')
        valkyrie  = create_orga(name='Valkyrie')

        create_cfield = partial(
            CustomField.objects.create,
            content_type=self.ctype, field_type=CustomField.MULTI_ENUM,
        )
        cfield_cap   = create_cfield(name='Capabilities')
        cfield_color = create_cfield(name='Color')

        create_evalue = CustomFieldEnumValue.objects.create
        can_fly  = create_evalue(custom_field=cfield_cap, value='Walk')
        can_walk = create_evalue(custom_field=cfield_cap, value='Fly')

        red    = create_evalue(custom_field=cfield_color, value='Red')
        grey   = create_evalue(custom_field=cfield_color, value='Grey')
        orange = create_evalue(custom_field=cfield_color, value='Orange')

        def set_cfvalue(cfield, entity, value):
            cfield.value_class(custom_field=cfield, entity=entity).set_value_n_save(value)

        set_cfvalue(cfield_cap,   bebop,     [can_fly.id])
        set_cfvalue(cfield_color, bebop,     [grey.id])

        set_cfvalue(cfield_cap,   swordfish, [can_fly.id])
        set_cfvalue(cfield_color, swordfish, [red.id])

        set_cfvalue(cfield_cap,   eva02,     [can_walk.id])
        set_cfvalue(cfield_color, eva02,     [red.id, orange.id])

        set_cfvalue(cfield_cap,   valkyrie,  [can_fly.id, can_walk.id])

        cell_cap   = EntityCellCustomField(cfield_cap)
        cell_color = EntityCellCustomField(cfield_color)
        hf = self._build_hf(cell_cap, cell_color)
        response1 = self.assertPOST200(
            self.url,
            data={
                'hfilter': hf.id,
                'search-regular_field-name': '',
                f'search-{cell_cap.key}':   can_walk.id,
                f'search-{cell_color.key}': red.id,
            },
        )
        orgas_set = self._get_entities_set(response1)
        self.assertNotIn(bebop,     orgas_set)
        self.assertNotIn(swordfish, orgas_set)
        self.assertIn(eva02,        orgas_set)
        self.assertNotIn(valkyrie,  orgas_set)

        # ---
        response2 = self.assertPOST200(
            self.url,
            data={
                'search-regular_field-name': '',
                f'search-{cell_cap.key}':    can_walk.id,
                f'search-{cell_color.key}':  'NULL',
            },
        )
        orgas_set = self._get_entities_set(response2)
        self.assertNotIn(bebop,     orgas_set)
        self.assertNotIn(swordfish, orgas_set)
        self.assertNotIn(eva02,     orgas_set)
        self.assertIn(valkyrie,     orgas_set)

    def test_search__custom_field__datetime(self):
        user = self.login_as_root_and_get()

        create_orga = partial(FakeOrganisation.objects.create, user=user)
        bebop     = create_orga(name='Bebop')
        swordfish = create_orga(name='Swordfish')
        redtail   = create_orga(name='Redtail')
        dragons   = create_orga(name='Red Dragons')

        cfield = CustomField.objects.create(
            name='First flight', content_type=self.ctype, field_type=CustomField.DATETIME,
        )
        create_cf_value = partial(cfield.value_class.objects.create, custom_field=cfield)
        create_dt = partial(self.create_datetime, utc=True)
        create_cf_value(entity=bebop,     value=create_dt(year=2075, month=3, day=26))
        create_cf_value(entity=swordfish, value=create_dt(year=2074, month=6, day=5))
        create_cf_value(entity=redtail,   value=create_dt(year=2076, month=7, day=25))

        cell = EntityCellCustomField(cfield)
        hf = self._build_hf(cell)

        # ----------------------------------------------------------------------
        date_value = self.formfield_value_date

        def post(start=None, end=None):
            ckey = cell.key
            response = self.assertPOST200(
                self.url,
                data={
                    'hfilter': hf.id,
                    f'search-{ckey}-start': date_value(start) if start else '',
                    f'search-{ckey}-end':   date_value(end)   if end   else '',
                },
            )

            return self._get_lv_cell_contents(
                self._get_lv_table_node(self._get_lv_node(response))
            )

        content = post(start=date(2075, 1, 1))
        self.assertIn(bebop.name,        content)
        self.assertNotIn(swordfish.name, content)
        self.assertIn(redtail.name,      content)
        self.assertNotIn(dragons.name,   content)

        content = post(end=date(2075, 1, 1))
        self.assertNotIn(bebop.name,   content)
        self.assertIn(swordfish.name,  content)
        self.assertNotIn(redtail.name, content)
        self.assertNotIn(dragons.name, content)

        content = post(date(2074, 1, 1), date(2074, 12, 31))
        self.assertNotIn(bebop.name,   content)
        self.assertIn(swordfish.name,  content)
        self.assertNotIn(redtail.name, content)
        self.assertNotIn(dragons.name, content)

        content = post(date(2074, 6, 5), date(2074, 6, 5))
        self.assertNotIn(bebop.name,   content)
        self.assertIn(swordfish.name,  content)
        self.assertNotIn(redtail.name, content)
        self.assertNotIn(dragons.name, content)

    def test_search__custom_field__datetime_x2(self):
        user = self.login_as_root_and_get()

        create_orga = partial(FakeOrganisation.objects.create, user=user)
        bebop      = create_orga(name='Bebop')
        swordfish  = create_orga(name='Swordfish')
        redtail    = create_orga(name='Redtail')
        hammerhead = create_orga(name='HammerHead')
        dragons    = create_orga(name='Red Dragons')

        create_cfield = partial(
            CustomField.objects.create,
            content_type=self.ctype,
            field_type=CustomField.DATETIME,
        )
        cfield_flight = create_cfield(name='First flight')
        cfield_blood  = create_cfield(name='First blood')

        create_cf_value = partial(cfield_flight.value_class.objects.create)
        create_dt = partial(self.create_datetime, utc=True)
        create_cf_value(
            entity=bebop,
            custom_field=cfield_flight,
            value=create_dt(year=2075, month=3, day=26),
        )
        create_cf_value(
            entity=swordfish,
            custom_field=cfield_flight,
            value=create_dt(year=2074, month=6, day=5),
        )
        create_cf_value(
            entity=redtail,
            custom_field=cfield_flight,
            value=create_dt(year=2076, month=7, day=25),
        )
        create_cf_value(
            entity=hammerhead,
            custom_field=cfield_flight,
            value=create_dt(year=2074, month=7, day=6),
        )

        create_cf_value(
            entity=swordfish,
            custom_field=cfield_blood,
            value=create_dt(year=2074, month=6, day=8),
        )
        create_cf_value(
            entity=hammerhead,
            custom_field=cfield_blood,
            value=create_dt(year=2075, month=7, day=6),
        )

        cell_flight = EntityCellCustomField(cfield_flight)
        cell_blood  = EntityCellCustomField(cfield_blood)
        hf = self._build_hf(cell_flight, cell_blood)
        date_value = self.formfield_value_date
        response = self.assertPOST200(
            self.url,
            data={
                'hfilter': hf.id,
                f'search-{cell_flight.key}-start': date_value(2074, 1, 1),
                f'search-{cell_flight.key}-end':   date_value(2074, 12, 31),

                f'search-{cell_blood.key}-start': '',
                f'search-{cell_blood.key}-end':   date_value(2075, 1, 1),
            },
        )
        content = self._get_lv_cell_contents(
            self._get_lv_table_node(self._get_lv_node(response))
        )
        self.assertNotIn(bebop.name,      content)
        self.assertIn(swordfish.name,     content)
        self.assertNotIn(redtail.name,    content)
        self.assertNotIn(hammerhead.name, content)
        self.assertNotIn(dragons.name,    content)

    def test_search__custom_field__bool(self):
        user = self.login_as_root_and_get()

        create_orga = partial(FakeOrganisation.objects.create, user=user)
        bebop     = create_orga(name='Bebop')
        swordfish = create_orga(name='Swordfish')
        dragons   = create_orga(name='Red Dragons')

        cfield = CustomField.objects.create(
            name='Is hunting?', content_type=self.ctype, field_type=CustomField.BOOL,
        )
        klass = cfield.value_class

        def set_cfvalue(entity, value):
            klass(custom_field=cfield, entity=entity).set_value_n_save(value)

        set_cfvalue(bebop,   True)
        set_cfvalue(dragons, False)

        cell = EntityCellCustomField(cfield)
        hf = self._build_hf(cell)

        # ----------------------------------------------------------------------
        response1 = self.assertGET200(self.url, data={'hfilter': hf.id})
        widget_node = self._get_lv_header_widget_nodes(
            self._get_lv_table_node(self._get_lv_node(response1)),
            cell.key, input_type='select',
        )[0]

        options = self._get_options_for_select_node(widget_node)
        self.assertInChoices(
            value='', label=pgettext('creme_core-filter', 'All'), choices=options,
        )
        self.assertInChoices(value='1', label=_('Yes'), choices=options)
        self.assertInChoices(value='0', label=_('No'),  choices=options)
        self.assertEqual(3, len(options))

        # ----------------------------------------------------------------------
        response2 = self.assertPOST200(
            self.url,
            data={
                'hfilter': hf.id,
                f'search-{cell.key}': '1',
            },
        )
        content1 = self._get_lv_cell_contents(self._get_lv_table_node(
            self._get_lv_node(response2)
        ))
        self.assertIn(bebop.name,        content1)
        self.assertNotIn(swordfish.name, content1)
        self.assertNotIn(dragons.name,   content1)

        # ----------------------------------------------------------------------
        response3 = self.assertPOST200(
            self.url,
            data={
                'hfilter': hf.id,
                f'search-{cell.key}': '0',
            },
        )
        content2 = self._get_lv_cell_contents(
            self._get_lv_table_node(self._get_lv_node(response3))
        )
        self.assertIn(dragons.name, content2)
        self.assertNotIn(bebop.name,     content2)
        self.assertNotIn(swordfish.name, content2)

    def test_search__function_field(self):
        "PropertiesField."
        user = self.login_as_root_and_get()

        create_orga = partial(FakeOrganisation.objects.create, user=user)
        bebop     = create_orga(name='Bebop')
        swordfish = create_orga(name='Swordfish')
        eva01     = create_orga(name='Eva01')
        eva02     = create_orga(name='Eva02')

        create_ptype = CremePropertyType.objects.create
        is_red  = create_ptype(text='is red')
        is_fast = create_ptype(text='is fast')

        create_prop = CremeProperty.objects.create
        create_prop(type=is_red, creme_entity=swordfish)
        create_prop(type=is_red, creme_entity=eva02)

        create_prop(type=is_fast, creme_entity=swordfish)
        create_prop(type=is_fast, creme_entity=bebop)

        ff_name = 'get_pretty_properties'
        cell = EntityCellFunctionField.build(FakeOrganisation, ff_name)
        hf = self._build_hf(cell)

        # ----------------------------------------------------------------------
        response1 = self.assertGET200(self.url, data={'hfilter': hf.id})
        self._get_lv_header_widget_nodes(
            self._get_lv_table_node(self._get_lv_node(response1)),
            cell.key, input_type='select',
        )

        # ----------------------------------------------------------------------
        response2 = self.assertPOST200(
            self.url,
            data={
                'hfilter': hf.id,
                f'search-{cell.key}': is_red.id,
            },
        )
        orgas_set = self._get_entities_set(response2)
        self.assertIn(swordfish, orgas_set)
        self.assertIn(eva02,     orgas_set)
        self.assertNotIn(bebop,  orgas_set)
        self.assertNotIn(eva01,  orgas_set)

    def test_search__function_field__no_search(self):
        "Can not search on this FunctionField."
        user = self.login_as_root_and_get()

        create_orga = partial(FakeOrganisation.objects.create, user=user)
        create_orga(name='Bebop')
        create_orga(name='Swordfish')

        func_field = function_field_registry.get(FakeOrganisation, 'tests-fake_todos')
        cell = EntityCellFunctionField(model=FakeOrganisation, func_field=func_field)
        hf = self._build_hf(cell)

        response = self.assertGET200(self.url, data={'hfilter': hf.id})
        self._assert_no_lv_header_widget_node(
            self._get_lv_table_node(self._get_lv_node(response)),
            cell.key
        )

    def test_aggregation(self):
        user = self.login_as_root_and_get()

        hf = HeaderFilter.objects.proxy(
            id='test-hf_invoice', name='Invoice view with aggregation',
            model=FakeInvoice,
            cells=[
                EntityCellRegularField.build(model=FakeInvoice, name='name'),
                EntityCellRegularField.build(model=FakeInvoice, name='total_vat'),
            ],
        ).get_or_create()[0]

        create_invoice = partial(FakeInvoice.objects.create, user=user)
        create_invoice(name='Invoice #1', total_vat=Decimal('1100.24')),
        create_invoice(name='Invoice #2', total_vat=Decimal('2200.30')),

        response = self.assertGET200(
            FakeInvoice.get_lv_absolute_url(), data={'hfilter': hf.id},
        )
        table_node = self._get_lv_table_node(self._get_lv_node(response))

        tbody_node = self.get_html_node_or_fail(table_node, './/tbody')
        first_tr_node = tbody_node.find('tr')
        self.assertIsNotNone(first_tr_node)
        self.assertIn('lv-row-aggregation', first_tr_node.attrib.get('class').split())

        name_td_node = self.get_html_node_or_fail(
            first_tr_node, './/td[@data-column-key="regular_field-name"]',
        )
        self.assertFalse([*name_td_node])

        total_td_node = self.get_html_node_or_fail(
            first_tr_node, './/td[@data-column-key="regular_field-total_vat"]',
        )
        # See code about aggregator_registry in fake_apps.py
        agg_ul_node = self.get_html_node_or_fail(total_td_node, './/ul')
        li_nodes = agg_ul_node.findall('.//li')
        self.assertEqual(2, len(li_nodes))

        msg_fmt = _('{aggregation_label}: {aggregation_value}').format
        self.assertEqual(
            msg_fmt(
                aggregation_label='Sum',
                aggregation_value=number_format(Decimal('3300.54'), force_grouping=True),
            ),
            li_nodes[0].text,
        )
        self.assertEqual(
            msg_fmt(
                aggregation_label='Average',
                aggregation_value=number_format(Decimal('1650.27'), force_grouping=True),
            ),
            li_nodes[1].text,
        )

    def test_aggregation__no_cell_to_aggregate(self):
        user = self.login_as_root_and_get()

        hf = HeaderFilter.objects.proxy(
            id='test-hf_invoice', name='Invoice view with aggregation',
            model=FakeInvoice,
            cells=[
                EntityCellRegularField.build(model=FakeInvoice, name='name'),
                # EntityCellRegularField.build(model=FakeInvoice, name='total_vat'),
            ],
        ).get_or_create()[0]

        FakeInvoice.objects.create(user=user, name='Invoice #1', total_vat=1100),

        response = self.assertGET200(
            FakeInvoice.get_lv_absolute_url(), data={'hfilter': hf.id},
        )
        table_node = self._get_lv_table_node(self._get_lv_node(response))

        tbody_node = self.get_html_node_or_fail(table_node, './/tbody')
        first_tr_node = tbody_node.find('tr')
        self.assertIsNotNone(first_tr_node)
        self.assertNotIn('lv-row-aggregation', first_tr_node.attrib.get('class').split())

    def _build_orgas(self, user=None):
        count = FakeOrganisation.objects.count()
        expected_count = 13  # 13 = 10 (our page size) + 3
        self.assertLessEqual(count, expected_count)

        create_orga = partial(FakeOrganisation.objects.create, user=user or self.user)
        for i in range(expected_count - count):
            create_orga(name=f'Mafia #{i:02}')

        organisations = [*FakeOrganisation.objects.all()]
        self.assertEqual(expected_count, len(organisations))

        return organisations

    @override_settings(
        FAST_QUERY_MODE_THRESHOLD=100000,
        PAGE_SIZES=[10, 25, 200],
        DEFAULT_PAGE_SIZE_IDX=0,
    )
    def test_pagination__slow(self):
        "Paginator with only OFFSET (small number of lines)."
        user = self.login_as_root_and_get()
        organisations = self._build_orgas(user=user)
        hf = self._build_hf()

        def post(page, rows=10):
            return self.assertPOST200(
                self.url,
                data={
                    'hfilter': hf.id,
                    'page':    page,
                    'rows':    rows,
                },
            )

        # Page 1 --------------------
        response = post(page=1)
        with self.assertNoException():
            entities_page = response.context['page_obj']

        self.assertEqual(10, len(entities_page))
        self.assertTrue(entities_page.has_next())
        self.assertFalse(entities_page.has_previous())
        self.assertEqual(2, entities_page.next_page_number())

        paginator = entities_page.paginator
        self.assertEqual(10, paginator.per_page)
        self.assertEqual(13, paginator.count)
        self.assertEqual(2,  paginator.num_pages)

        entities = [*entities_page.object_list]
        idx1 = self.assertIndex(organisations[0], entities)
        self.assertEqual(0, idx1)
        idx10 = self.assertIndex(organisations[9], entities)
        self.assertEqual(9, idx10)

        # Page 2 --------------------
        response = post(page=2)
        entities_page = response.context['page_obj']

        self.assertEqual(3, len(entities_page))

        entities = [*entities_page.object_list]
        idx11 = self.assertIndex(organisations[10], entities)
        self.assertEqual(0, idx11)

        # Change 'rows' parameter -------------
        rows = 25
        response = post(page=1, rows=rows)
        self.assertEqual(rows, response.context['page_obj'].paginator.per_page)

        # Check invalid page size
        response = post(page=1, rows=1000)
        self.assertEqual(10, response.context['page_obj'].paginator.per_page)

    @override_settings(
        FAST_QUERY_MODE_THRESHOLD=100000,
        PAGE_SIZES=[10],
        DEFAULT_PAGE_SIZE_IDX=0,
    )
    def test_pagination__slow__saved_page(self):
        "Page is saved."
        user = self.login_as_root_and_get()
        organisations = self._build_orgas(user=user)
        hf = self._build_hf()

        def post(page=None):
            data = {
                'hfilter': hf.id,
                'rows':    10,
            }

            if page:
                data['page'] = page

            return self.assertPOST200(self.url, data=data)

        post(page=1)

        # Go to page 2...
        response = post(page=2)
        entities_page = response.context['page_obj']
        self.assertEqual(2, entities_page.number)
        self.assertIndex(organisations[10], [*entities_page.object_list])

        # ... which should be kept in session
        response = post()
        entities_page = response.context['page_obj']
        self.assertEqual(2, entities_page.number)
        self.assertIndex(organisations[10], [*entities_page.object_list])

    @override_settings(
        FAST_QUERY_MODE_THRESHOLD=5,
        PAGE_SIZES=[10, 25],
        DEFAULT_PAGE_SIZE_IDX=0,
    )
    def test_pagination__fast__organisation(self):
        "Paginator with 'keyset' (big number of lines)."
        user = self.login_as_root_and_get()
        organisations = self._build_orgas(user=user)
        hf = self._build_hf()

        def post(page_info=None):
            return self.assertPOST200(
                self.url,
                data={
                    'hfilter': hf.id,
                    'page': json_dump(page_info) if page_info else '',
                },
            )

        # Page 1 --------------------
        response = post()
        with self.assertNoException():
            entities_page1 = response.context['page_obj']

        self.assertEqual(10, len(entities_page1))
        self.assertTrue(entities_page1.has_next())
        self.assertFalse(entities_page1.has_previous())
        self.assertHasNoAttr(entities_page1, 'next_page_number')
        self.assertHasAttr(entities_page1, 'next_page_info')
        self.assertHasNoAttr(entities_page1, 'start_index')

        paginator = entities_page1.paginator
        self.assertEqual(10, paginator.per_page)
        self.assertEqual(13, paginator.count)
        self.assertEqual(2, paginator.num_pages)

        entities = [*entities_page1.object_list]
        idx1 = self.assertIndex(organisations[0], entities)
        self.assertEqual(0, idx1)

        idx10 = self.assertIndex(organisations[9], entities)
        self.assertEqual(9, idx10)

        # Page 2 --------------------
        response = post(entities_page1.next_page_info())
        entities_page2 = response.context['page_obj']

        self.assertEqual(3, len(entities_page2))

        entities = [*entities_page2.object_list]
        idx11 = self.assertIndex(organisations[10], entities)
        self.assertEqual(0, idx11)

    @override_settings(
        FAST_QUERY_MODE_THRESHOLD=5,
        PAGE_SIZES=[10, 50],
        DEFAULT_PAGE_SIZE_IDX=0,
    )
    def test_pagination__fast__contact(self):
        "ContentType = Contact."
        user = self.login_as_root_and_get()
        rows = 10
        expected_count = rows + 3

        count = FakeContact.objects.count()
        self.assertLessEqual(count, expected_count)

        create_contact = partial(FakeContact.objects.create, user=user)
        for i in range(expected_count - count):
            create_contact(first_name='Gally', last_name=f'Tuned{i:02}')

        contacts = [*FakeContact.objects.all()]
        self.assertEqual(expected_count, len(contacts))

        hf = HeaderFilter.objects.proxy(
            id='test-hf_contact', name='Order02 view', model=FakeContact,
            cells=[
                (EntityCellRegularField, 'last_name'),
                (EntityCellRegularField, 'first_name'),
            ],
        ).get_or_create()[0]

        def post(page_info=None):
            return self.assertPOST200(
                FakeContact.get_lv_absolute_url(),
                data={
                    'hfilter': hf.id,
                    'page': json_dump(page_info) if page_info else '',
                    'rows': rows,
                },
            )

        # Page 1 --------------------
        response = post()
        with self.assertNoException():
            entities_page1 = response.context['page_obj']

        self.assertEqual(rows, len(entities_page1))
        self.assertTrue(entities_page1.has_next())
        self.assertFalse(entities_page1.has_previous())
        self.assertHasNoAttr(entities_page1, 'next_page_number')

        paginator = entities_page1.paginator
        self.assertEqual(rows, paginator.per_page)
        self.assertEqual(expected_count, paginator.count)

        entities = [*entities_page1.object_list]
        idx1 = self.assertIndex(contacts[0], entities)
        self.assertEqual(0, idx1)

        idx10 = self.assertIndex(contacts[9], entities)
        self.assertEqual(9, idx10)

        # Page 2 --------------------
        response = post(entities_page1.next_page_info())
        entities_page2 = response.context['page_obj']

        self.assertEqual(3, len(entities_page2))

        entities = [*entities_page2.object_list]
        idx11 = self.assertIndex(contacts[10], entities)
        self.assertEqual(0, idx11)

    @override_settings(
        FAST_QUERY_MODE_THRESHOLD=5,
        PAGE_SIZES=[10, 25],
        DEFAULT_PAGE_SIZE_IDX=1,
    )
    def test_pagination__fast__order(self):
        "Set an ORDER."
        user = self.login_as_root_and_get()
        rows = 10
        expected_count = rows + 3

        count = FakeContact.objects.count()
        self.assertLessEqual(count, expected_count)

        ids = [*range(expected_count - count)]
        shuffle(ids)

        create_contact = partial(FakeContact.objects.create, user=user)
        for i, id_ in enumerate(ids):
            # NB: we want the ordering by 'first_name' to be different from the 'last_name' one
            create_contact(first_name=f'Gally{id_:02}', last_name=f'Tuned{i:02}')

        ordering_fname = 'first_name'
        contacts = [*FakeContact.objects.order_by(ordering_fname)]
        self.assertEqual(expected_count, len(contacts))

        build_cell = partial(EntityCellRegularField.build, model=FakeContact)
        cell2 = build_cell(name=ordering_fname)
        hf = HeaderFilter.objects.proxy(
            id='test-hf_contact', name='Order02 view', model=FakeContact,
            cells=[build_cell(name='last_name'), cell2],
        ).get_or_create()[0]

        def post(page_info=None):
            return self.assertPOST200(
                FakeContact.get_lv_absolute_url(),
                data={
                    'hfilter': hf.id,
                    'sort_key': cell2.key,
                    'sort_order': '',  # TODO: 'DESC'
                    'page': json_dump(page_info) if page_info else '',
                    'rows': rows,
                },
            )

        # Page 1 --------------------
        response = post()
        entities_page1 = response.context['page_obj']
        entities = [*entities_page1.object_list]
        idx1 = self.assertIndex(contacts[0], entities)
        self.assertEqual(0, idx1)

        idx10 = self.assertIndex(contacts[9], entities)
        self.assertEqual(9, idx10)

        # Page 2 --------------------
        response = post(entities_page1.next_page_info())
        entities_page2 = response.context['page_obj']

        self.assertEqual(3, len(entities_page2))

        entities = [*entities_page2.object_list]
        idx11 = self.assertIndex(contacts[10], entities)
        self.assertEqual(0, idx11)

    @override_settings(
        FAST_QUERY_MODE_THRESHOLD=5,
        PAGE_SIZES=[10],
        DEFAULT_PAGE_SIZE_IDX=0,
    )
    def test_pagination__fast__offset(self):
        "Field key duplicates => use OFFSET too."
        user = self.login_as_root_and_get()
        rows = 10
        expected_count = rows + 3

        count = FakeContact.objects.count()
        self.assertLessEqual(count, expected_count)

        create_contact = partial(FakeContact.objects.create, user=user)
        for i in range(expected_count - count):
            # NB: same last_name
            create_contact(first_name='Gally', last_name='Tuned', phone=f'11 22 33 #{i:02}')

        contacts = [
            *FakeContact.objects.order_by('last_name', 'first_name', 'cremeentity_ptr_id'),
        ]
        self.assertEqual(expected_count, len(contacts))

        hf = HeaderFilter.objects.proxy(
            id='test-hf_contact', name='Order02 view', model=FakeContact,
            cells=[
                (EntityCellRegularField, 'last_name'),
                (EntityCellRegularField, 'first_name'),
            ],
        )

        def post(page_info=None):
            return self.assertPOST200(
                FakeContact.get_lv_absolute_url(),
                data={
                    'hfilter': hf.id,
                    'page': json_dump(page_info) if page_info else '',
                    'rows': rows,
                },
            )

        # Page 1 --------------------
        response = post()
        entities_page1 = response.context['page_obj']
        idx10 = self.assertIndex(contacts[9], [*entities_page1.object_list])
        self.assertEqual(9, idx10)

        # Page 2 --------------------
        response = post(entities_page1.next_page_info())
        entities_page2 = response.context['page_obj']

        self.assertEqual(3, len(entities_page2))

        idx11 = self.assertIndex(contacts[10], [*entities_page2.object_list])
        self.assertEqual(0, idx11)

    @override_settings(FAST_QUERY_MODE_THRESHOLD=5, PAGE_SIZES=[5, 10])
    def test_pagination__fast__errors(self):
        "Errors => page 1."
        user = self.login_as_root_and_get()
        rows = 5
        expected_count = rows + 3

        count = FakeContact.objects.count()
        self.assertLessEqual(count, expected_count)

        create_contact = partial(FakeContact.objects.create, user=user)
        for i in range(expected_count - count):
            create_contact(first_name='Gally', last_name=f'Tuned#{i:02}')

        hf = HeaderFilter.objects.proxy(
            id='test-hf_contact', name='Order02 view', model=FakeContact,
            cells=[
                (EntityCellRegularField, 'last_name'),
                (EntityCellRegularField, 'first_name'),
            ],
        )

        def post(page_info=''):
            response = self.assertPOST200(
                FakeContact.get_lv_absolute_url(),
                data={
                    'hfilter': hf.id,
                    'page': page_info,
                    'rows': rows,
                },
            )
            return response.context['page_obj']

        page1 = post()
        page2_info = page1.next_page_info()

        # Invalid Page => page 1
        page1_info = {**page2_info}
        del page1_info['type']

        page = post(json_dump(page1_info))
        self.assertFalse(page.has_previous())

        # Invalid JSON => page 1
        invalid_json = json_dump(page2_info)[:-1]
        page = post(invalid_json)
        self.assertFalse(page.has_previous())

        # FirstPage => page 1
        page1a_info = page1.paginator.page(page2_info).previous_page_info()
        page = post(json_dump(page1a_info))
        self.assertFalse(page.has_previous())

    @override_settings(FAST_QUERY_MODE_THRESHOLD=5, PAGE_SIZES=[5, 10])
    def test_pagination__fast__last_page(self):
        "LastPage => last page."
        user = self.login_as_root_and_get()
        rows = 5
        expected_count = 2 * rows + 3

        count = FakeContact.objects.count()
        self.assertLessEqual(count, expected_count)

        create_contact = partial(FakeContact.objects.create, user=user)
        for i in range(expected_count - count):
            create_contact(first_name='Gally', last_name=f'Tuned#{i:02}')

        hf = HeaderFilter.objects.proxy(
            id='test-hf_contact', name='Order02 view', model=FakeContact,
            cells=[
                (EntityCellRegularField, 'last_name'),
                (EntityCellRegularField, 'first_name'),
            ],
        )

        def post(page_info=''):
            response = self.assertPOST200(
                FakeContact.get_lv_absolute_url(),
                data={
                    'hfilter': hf.id,
                    'page': page_info,
                    'rows': rows,
                },
            )

            return response.context['page_obj']

        page1 = post()
        paginator = page1.paginator
        self.assertEqual(rows, paginator.per_page)

        page2 = paginator.page(page1.next_page_info())
        page3_info = page2.next_page_info()

        # We delete the content of the 2nd page
        for c in FakeContact.objects.reverse()[:4]:
            c.delete()

        last_page = post(json_dump(page3_info))
        self.assertTrue(last_page.has_previous())

    @override_settings(FAST_QUERY_MODE_THRESHOLD=5, PAGE_SIZES=[10])
    def test_pagination__fast__save_page(self):
        "Page is saved."
        user = self.login_as_root_and_get()
        organisations = self._build_orgas(user=user)
        hf = self._build_hf()
        url = FakeOrganisation.get_lv_absolute_url()

        def post(page_info=''):
            data = {
                'hfilter': hf.id,
                'page': page_info,
                'rows': 10,
            }

            response = self.assertPOST200(url, data=data)
            return response.context['page_obj']

        page1 = post()

        # Go to page 2...
        page2 = post(json_dump(page1.next_page_info()))
        self.assertIndex(organisations[10], page2.object_list)

        # ... which should be kept in session
        page2a = post()
        self.assertIndex(organisations[10], page2a.object_list)

    @override_settings(FAST_QUERY_MODE_THRESHOLD=14, PAGE_SIZES=[10])
    def test_pagination__fast__transition(self):
        "Change paginator class slow => fast (so saved page info are not compatible)."
        user = self.login_as_root_and_get()
        self._build_orgas(user=user)
        hf = self._build_hf()
        url = FakeOrganisation.get_lv_absolute_url()

        def post():
            response = self.assertPOST200(
                url,
                data={
                    'hfilter': hf.id,
                    'rows': 10,
                },
            )
            return response.context['page_obj']

        page1_slow = post()
        self.assertHasAttr(page1_slow, 'number')  # Means slow mode

        FakeOrganisation.objects.create(user=user, name='Zalem')  # We exceed the threshold
        page1_fast = post()
        self.assertHasAttr(page1_fast, 'next_page_info')  # Means fast mode

    def test_listview_popup__GET(self):
        # user = self.login_as_root_and_get()
        user = self.login_as_standard(listable_models=[FakeOrganisation])
        self.add_credentials(user.role, own=['VIEW'])

        create_orga = partial(FakeOrganisation.objects.create, user=user)
        bebop   = create_orga(name='Bebop')
        redtail = create_orga(name='Redtail')
        dragons = create_orga(name='Red Dragons')

        self._build_hf()

        # context = CaptureQueriesContext()
        qfilter_json = QSerializer().dumps(Q(name='Bebop'))

        # with context:
        response = self.assertGET200(
            reverse('creme_core__listview_popup'),
            data={
                'ct_id': self.ctype.id,
                'q_filter': qfilter_json,
            },
        )

        table_node = self._get_lv_table_node(self._get_lv_node(response))
        inputs_content = self._get_lv_inputs_content(table_node)
        self.assertIn(('q_filter', qfilter_json), inputs_content)

        content = self._get_lv_cell_contents(table_node)
        self.assertCountOccurrences(bebop.name, content, count=1)
        self.assertNotIn(redtail.name, content)
        self.assertNotIn(dragons.name, content)

        self.assertEqual(1, response.context['page_obj'].paginator.count)

    def test_listview_popup__POST(self):
        user = self.login_as_root_and_get()

        create_orga = partial(FakeOrganisation.objects.create, user=user)
        bebop   = create_orga(name='Bebop')
        redtail = create_orga(name='Redtail')
        dragons = create_orga(name='Red Dragons')

        self._build_hf()

        # context = CaptureQueriesContext()
        qfilter_json = QSerializer().dumps(Q(name='Bebop'))

        # with context:
        response = self.assertPOST200(
            reverse('creme_core__listview_popup'),
            data={
                'ct_id': self.ctype.id,
                'q_filter': qfilter_json,
            },
        )

        table_node = self._get_lv_table_node(self._get_lv_node(response))
        inputs_content = self._get_lv_inputs_content(table_node)
        self.assertIn(('q_filter', qfilter_json), inputs_content)

        content = self._get_lv_cell_contents(table_node)
        self.assertCountOccurrences(bebop.name, content, count=1)
        self.assertNotIn(redtail.name, content)
        self.assertNotIn(dragons.name, content)

        self.assertEqual(1, response.context['page_obj'].paginator.count)

    def test_listview_popup__not_allowed(self):
        self.login_as_standard()  # listable_models=[FakeOrganisation]

        response = self.client.get(
            reverse('creme_core__listview_popup'),
            data={'ct_id': self.ctype.id},
        )
        self.assertContains(
            response,
            status_code=403,
            text=_('You are not allowed to list: {}').format('Test Organisation'),
            html=True,
        )

    @override_settings(PAGE_SIZES=[10], DEFAULT_PAGE_SIZE_IDX=0)
    def test_credentials_with_filter__no_fast_count(self):
        "Fast count is not possible."
        user = self.login_as_standard(listable_models=[FakeOrganisation])
        self.add_credentials(user.role, own='*')

        efilter = EntityFilter.objects.create(
            id='creme_core-test_listview',
            entity_type=FakeOrganisation,
            filter_type=EF_CREDENTIALS,
        ).set_conditions(
            [
                condition_handler.RegularFieldConditionHandler.build_condition(
                    model=FakeOrganisation,
                    operator=operators.ICONTAINS,
                    field_name='name', values=['Corp'],
                    filter_type=EF_CREDENTIALS,
                ),
            ],
            check_cycles=False,  # There cannot be a cycle without sub-filter.
            check_privacy=False,  # No sense here.
        )

        SetCredentials.objects.create(
            # role=self.role,
            role=user.role,
            value=EntityCredentials.VIEW,
            set_type=SetCredentials.ESET_FILTER,
            ctype=FakeOrganisation,
            efilter=efilter,
        )

        create_orga = partial(FakeOrganisation.objects.create, user=user)
        orga1 = create_orga(name='Acme')  # OK (belongs to user)
        orga2 = create_orga(name='Foobar incorporated')  # OK: (name passes the Filter)
        orga3 = create_orga(name='Genius company', user=self.get_root_user())

        hf = self._build_hf()

        with self.assertLogs(level='DEBUG') as logs_manager:
            response = self.assertPOST200(self.url, data={'hfilter': hf.id})

        with self.assertNoException():
            orgas_page = response.context['page_obj']

        self.assertIn(orga1, orgas_page.object_list)
        self.assertIn(orga2, orgas_page.object_list)
        self.assertNotIn(orga3, orgas_page.object_list)

        self.assertEqual(2, orgas_page.paginator.count)

        for msg in logs_manager.output:
            if msg.startswith(
                'DEBUG:creme.creme_core.views.generic.listview:'
                'FakeOrganisationsList.get_unordered_queryset_n_count() : '
                'fast count is not possible'
            ):
                break
        else:
            self.fail(f'No slow count message found in {logs_manager.output}')

    @override_settings(PAGE_SIZES=[10], DEFAULT_PAGE_SIZE_IDX=0)
    def test_credentials_with_filter__distinct(self):
        "Beware of DISTINCT with filter on relationships."
        user = self.login_as_standard(listable_models=[FakeContact])

        rtype = self._create_rtype()

        cred_efilter = EntityFilter.objects.create(
            id='creme_core-test_listview01',
            entity_type=FakeContact,
            filter_type=EF_CREDENTIALS,
        ).set_conditions(
            [
                condition_handler.RelationConditionHandler.build_condition(
                    model=FakeContact,
                    rtype=rtype,
                    filter_type=EF_CREDENTIALS,
                ),
            ],
            check_cycles=False,  # There cannot be a cycle without sub-filter.
            check_privacy=False,  # No sense here.
        )

        SetCredentials.objects.create(
            role=user.role,
            value=EntityCredentials.VIEW,
            set_type=SetCredentials.ESET_FILTER,
            ctype=FakeContact,
            efilter=cred_efilter,
        )

        create_orga = partial(FakeOrganisation.objects.create, user=user)
        bebop      = create_orga(name='Bebop')
        swordfish  = create_orga(name='Swordfish')
        hammerhead = create_orga(name='Hammerhead')

        create_contact = partial(FakeContact.objects.create, user=user)
        spike = create_contact(first_name='Spike',  last_name='Spiegel')
        jet   = create_contact(first_name='Jet',    last_name='Black')
        ed    = create_contact(first_name='Edward', last_name='Wong')  # <== No Relation

        create_rel = partial(Relation.objects.create, user=user, type=rtype)
        create_rel(subject_entity=spike, object_entity=swordfish)
        create_rel(subject_entity=jet,   object_entity=bebop)
        create_rel(subject_entity=jet,   object_entity=hammerhead)  # <== 2 Relations !!

        response = self.assertPOST200(
            FakeContact.get_lv_absolute_url(),
            data={'hfilter': fake_constants.DEFAULT_HFILTER_FAKE_CONTACT},  # See fake_populate.py
        )

        with self.assertNoException():
            contacts_page = response.context['page_obj']

        contacts = [*contacts_page]
        self.assertCountOccurrences(member=spike, container=contacts, count=1)
        self.assertNotIn(ed, contacts)
        self.assertCountOccurrences(member=jet, container=contacts, count=1)  # Not 2

        self.assertEqual(2, contacts_page.paginator.count)

    def test_buttons(self):
        self.login_as_root()

        response = self.assertPOST200(
            FakeContact.get_lv_absolute_url(),
            data={'hfilter': fake_constants.DEFAULT_HFILTER_FAKE_CONTACT},
        )

        lv_node = self._get_lv_node(response)
        buttons_info = [*self._get_lv_header_buttons(lv_node)]

        creation_url = FakeContact.get_create_absolute_url()
        for button_info in buttons_info:
            if button_info['url'] == creation_url:
                self.assertEqual(
                    FakeContact.creation_label,
                    button_info['label'],
                )
                break
        else:
            self.fail('No creation button found.')

        # ---
        import_url = reverse(
            'creme_core__mass_import',
            args=[ContentType.objects.get_for_model(FakeContact).id],
        )
        for button_info in buttons_info:
            if button_info['url'] == import_url:
                self.assertEqual(_('Import'), button_info['label'])
                break
        else:
            self.fail('No mass-import button found.')

    def test_visitor_button(self):
        user = self.login_as_root_and_get()
        self.maxDiff = None

        lv_url = FakeContact.get_lv_absolute_url()
        hfilter_id = fake_constants.DEFAULT_HFILTER_FAKE_CONTACT
        data = {'hfilter': hfilter_id}
        label = _('Enter the exploration mode')

        # ---
        self.assertFalse(FakeContact.objects.all())
        response1 = self.assertPOST200(lv_url, data=data)
        lv_node1 = self._get_lv_node(response1)
        for button_info in self._get_lv_header_buttons(lv_node1):
            if button_info['label'] == label:
                self.fail('Exploration button found in empty list.')

        # ---
        visit_url = reverse(
            'creme_core__visit_next_entity',
            args=(ContentType.objects.get_for_model(FakeContact).id,),
        )

        def assert_button_url(response, parameters):
            lv_node = self._get_lv_node(response)

            for button_info in self._get_lv_header_buttons(lv_node):
                if button_info['label'] == label:
                    self.assertURLEqual(
                        f'{visit_url}?{urlencode(parameters)}',
                        button_info['url'],
                    )
                    break
            else:
                self.fail('No exploration button found.')

        contact = FakeContact.objects.create(user=user, first_name='Spike', last_name='Spiegel')
        response2 = self.assertPOST200(lv_url, data=data)
        assert_button_url(
            response2,
            {
                'hfilter': hfilter_id,
                'sort': 'regular_field-last_name',
                'callback': lv_url,
            },
        )

        # No order -------------------------------------------------------------
        hf2 = HeaderFilter.objects.proxy(
            id='test-hf_contact_no_order', name='Only details', model=FakeContact,
            cells=[
                (EntityCellRegularField, 'phone'),
                (EntityCellRegularField, 'mobile'),
            ],
        ).get_or_create()[0]
        response3 = self.assertPOST200(lv_url, data={'hfilter': hf2.id})
        assert_button_url(
            response3,
            {'hfilter': hf2.id, 'sort': '', 'callback': lv_url},
        )

        # Filter, search -------------------------------------------------------
        efilter = EntityFilter.objects.smart_update_or_create(
            'test-test_visitor_button01', 'Spiegels', FakeContact,
            user=user, is_custom=False,
            conditions=[
                condition_handler.RegularFieldConditionHandler.build_condition(
                    model=FakeContact, field_name='last_name',
                    operator=operators.ISTARTSWITH, values=[contact.last_name],
                ),
            ],
        )
        serialized_q = QSerializer().dumps(Q(first_name__startswith='Spik'))
        response4 = self.assertPOST200(
            lv_url, data={
                'hfilter': hfilter_id,
                'filter': efilter.id,
                'q_filter': serialized_q,
                'search-regular_field-first_name': contact.first_name,
            },
        )
        assert_button_url(
            response4,
            {
                'hfilter': hfilter_id,
                'sort': 'regular_field-last_name',
                'callback': lv_url,

                'efilter': efilter.id,
                'search-regular_field-first_name': contact.first_name,
                'requested_q': serialized_q,
            },
        )

    def test_visitor_button__custom_view(self):
        "Custom list-view."
        user = self.login_as_root_and_get()

        lv_url = reverse('creme_core__list_fake_organisations_with_email')
        hfilter_id = fake_constants.DEFAULT_HFILTER_FAKE_ORGA
        data = {'hfilter': hfilter_id}

        FakeOrganisation.objects.create(user=user, name='Bebop', email='contact@bebop.mrs')
        response = self.assertPOST200(lv_url, data=data)
        lv_node = self._get_lv_node(response)
        visit_url = reverse(
            'creme_core__visit_next_entity',
            args=(ContentType.objects.get_for_model(FakeOrganisation).id,),
        )
        label = _('Enter the exploration mode')
        for button_info in self._get_lv_header_buttons(lv_node):
            if button_info['label'] == label:
                parameters = {
                    'hfilter': hfilter_id,
                    'sort': 'regular_field-name',
                    'callback': lv_url,
                    'internal_q': QSerializer().dumps(~Q(email='')),
                }
                self.assertURLEqual(
                    f'{visit_url}?{urlencode(parameters)}', button_info['url'],
                )
                break
        else:
            self.fail('No exploration button found.')

    # TODO: test other buttons
