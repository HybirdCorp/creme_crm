import json
from functools import partial
from urllib.parse import parse_qs, urlencode, urlparse

from django.contrib.contenttypes.models import ContentType
from django.db.models import Q
from django.urls import reverse
from django.utils.translation import gettext as _

from creme.creme_core.core import entity_filter
from creme.creme_core.core.entity_cell import EntityCellRegularField
from creme.creme_core.models import (
    EntityFilter,
    FakeContact,
    FakeOrganisation,
    HeaderFilter,
    Relation,
    RelationType,
)
from creme.creme_core.tests.base import CremeTestCase
from creme.creme_core.utils.queries import QSerializer
from creme.creme_core.views.generic.detailview import EntityVisitor


class VisitTestCase(CremeTestCase):
    def assertVisitRedirects(self, response, *,
                             entity, sort, index, hfilter,
                             lv_url='', page=None, efilter=None, search=None,
                             requested_q='', internal_q='',
                             ):
        try:
            chain = response.redirect_chain
        except AttributeError:
            self.fail('Not a redirection')

        if not chain:
            self.fail('The redirection chain is empty')

        if len(chain) != 1:
            self.fail(f'The redirection chain is too long: {chain}')

        parsed_uri = urlparse(chain[0][0])
        self.assertEqual(entity.get_absolute_url(), parsed_uri.path)

        visitor_data = {
            'hfilter': hfilter.pk,
            'sort': sort if isinstance(sort, str) else sort.key,
            'page': page or {'type': 'first'},
            'index': index,
            'callback': lv_url or entity.get_lv_absolute_url(),
        }
        if efilter:
            visitor_data['efilter'] = efilter.pk
        if internal_q:
            visitor_data['internal_q'] = internal_q
        if requested_q:
            visitor_data['requested_q'] = requested_q
        if search:
            visitor_data['search'] = search

        params = parse_qs(parsed_uri.query, keep_blank_values=True, strict_parsing=True)
        self.assertIsDict(params, length=1)

        param = params.get('visitor')
        self.assertIsList(param, length=1)

        try:
            deserialized_data = json.loads(param[0])
        except json.JSONDecodeError:
            self.fail('GET parameter "visitor" is not valid JSON.')

        self.assertDictEqual(visitor_data, deserialized_data)

    def assertVisitEnds(self, response, *,
                        lv_url='',
                        sort_key,
                        sort_order='ASC',
                        hfilter,
                        efilter=None,
                        extra_q='',
                        **search,
                        ):
        self.assertTemplateUsed(response, 'creme_core/visit-end.html')

        html = self.get_html_tree(response.content)
        title_node = self.get_html_node_or_fail(html, './/div[@class="bar-title"]//h1')
        self.assertEqual(_('The exploration is over'), title_node.text)

        content_node = self.get_html_node_or_fail(html, './/div[@class="buttons-list"]')
        button_node = self.get_html_node_or_fail(content_node, './/a')
        self.assertIn(
            _('Back to the list'),
            (txt.strip() for txt in button_node.itertext()),
        )

        parsed_uri = urlparse(button_node.attrib.get('href'))
        self.assertEqual(
            lv_url or FakeOrganisation.get_lv_absolute_url(),
            parsed_uri.path,
        )

        lv_data = {
            'hfilter': [hfilter.pk],
            'sort_key': [sort_key if isinstance(sort_key, str) else sort_key.key],
            'sort_order': [sort_order],
            **{k: [v] for k, v in search.items()},
        }
        if efilter:
            lv_data['filter'] = [efilter.pk]
        if extra_q:
            lv_data['q_filter'] = [extra_q]

        self.assertTrue(parsed_uri.query)
        self.assertDictEqual(
            lv_data,
            parse_qs(parsed_uri.query, keep_blank_values=True, strict_parsing=True),
        )

    @staticmethod
    def _build_visit_uri(model, page=None, lv_url=None, **kwargs):
        kwargs['callback'] = lv_url if lv_url is not None else model.get_lv_absolute_url()

        if page:
            kwargs['page'] = page if isinstance(page, str) else json.dumps(page)

        url = reverse(
            'creme_core__visit_next_entity',
            args=(ContentType.objects.get_for_model(model).id,),
        )

        return f'{url}?{urlencode(kwargs)}'

    def _create_orga_hfilter(self, *fields):
        return HeaderFilter.objects.proxy(
            id='creme_core-visit',
            model=FakeOrganisation,
            name='Simple view',
            cells=[
                (EntityCellRegularField, 'name'),
                (EntityCellRegularField, 'phone'),
                *((EntityCellRegularField, field_name) for field_name in fields),
            ],
        ).get_or_create()[0]

    def test_empty(self):
        self.login_as_root()
        self.assertFalse(FakeOrganisation.objects.all())
        self.assertGET404(self._build_visit_uri(FakeOrganisation))

        # ---
        cell = EntityCellRegularField.build(model=FakeOrganisation, name='name')
        hfilter = self._create_orga_hfilter()
        response2 = self.assertGET200(self._build_visit_uri(
            FakeOrganisation, sort=cell.key, hfilter=hfilter.pk,
        ))
        self.assertVisitEnds(response2, sort_key=cell, hfilter=hfilter)

    def test_simple(self):
        "No filter, search..."
        user = self.login_as_root_and_get()

        create_orga = partial(FakeOrganisation.objects.create, user=user)
        orgas = [
            create_orga(name='A1'),
            create_orga(name='A2'),

            # second page
            create_orga(name='A3'),
            create_orga(name='A4'),

            # third page
            create_orga(name='A5'),
        ]
        self.assertListEqual(
            orgas,
            [*FakeOrganisation.objects.order_by('name')[:len(orgas)]],
        )

        cell = EntityCellRegularField.build(model=FakeOrganisation, name='name')
        hfilter = self._create_orga_hfilter()
        response1 = self.assertGET200(
            self._build_visit_uri(FakeOrganisation, hfilter=hfilter.pk, sort=cell.key),
            follow=True,
        )
        page1 = {'type': 'first'}
        self.assertVisitRedirects(
            response1,
            entity=orgas[0], hfilter=hfilter, sort=cell, page=page1, index=0,
        )
        visitor1 = response1.context.get('visitor')

        self.assertIsInstance(visitor1, EntityVisitor)
        self.assertEqual(FakeOrganisation,  visitor1.model)
        self.assertEqual(hfilter.id,        visitor1.hfilter_id)
        self.assertEqual(cell.key,          visitor1.sort)
        self.assertEqual({'type': 'first'}, visitor1.page_info)
        self.assertEqual(0,                 visitor1.index)
        self.assertIsNone(visitor1.efilter_id)

        url2 = self._build_visit_uri(
            FakeOrganisation,
            hfilter=hfilter.pk, sort=cell.key, page=page1, index=0,
        )
        self.assertURLEqual(url2, visitor1.uri)

        # Second entity ---
        response2 = self.assertGET200(url2, follow=True)
        self.assertVisitRedirects(
            response2,
            entity=orgas[1], hfilter=hfilter, sort=cell, page=page1, index=1,
        )
        visitor2 = response2.context.get('visitor')
        self.assertEqual(cell.key, visitor2.sort)
        self.assertEqual(1,        visitor2.index)
        self.assertURLEqual(
            self._build_visit_uri(
                FakeOrganisation,
                hfilter=hfilter.pk, sort=cell.key, page=page1, index=1,
            ),
            visitor2.uri,
        )

        # Third entity (page 2) ---
        page2 = {'type': 'forward', 'key': 'name', 'value': orgas[2].name}
        response3 = self.assertGET200(visitor2.uri, follow=True)
        self.assertVisitRedirects(
            response3,
            entity=orgas[2], hfilter=hfilter, sort=cell,
            page=page2, index=0,
        )
        visitor3 = response3.context.get('visitor')
        self.assertURLEqual(
            self._build_visit_uri(
                FakeOrganisation,
                hfilter=hfilter.pk, sort=cell.key,
                page=page2, index=0,
            ),
            visitor3.uri,
        )

    def test_is_deleted(self):
        user = self.login_as_root_and_get()

        create_orga = partial(FakeOrganisation.objects.create, user=user)
        create_orga(name='AAA', is_deleted=True)
        not_deleted = create_orga(name='AAAA')

        cell = EntityCellRegularField.build(model=FakeOrganisation, name='name')
        hfilter = self._create_orga_hfilter()
        response = self.assertGET200(
            self._build_visit_uri(FakeOrganisation, sort=cell.key, hfilter=hfilter.pk),
            follow=True,
        )
        self.assertVisitRedirects(
            response, entity=not_deleted, hfilter=hfilter, sort=cell, index=0,
        )

    def test_view_credentials(self):
        user = self.login_as_standard()
        self.add_credentials(user.role, own=['VIEW'])

        create_orga = FakeOrganisation.objects.create
        create_orga(user=self.get_root_user(), name='AAA')
        allowed = create_orga(user=user, name='AAAA')

        cell = EntityCellRegularField.build(model=FakeOrganisation, name='name')
        hfilter = self._create_orga_hfilter()
        response = self.assertGET200(
            self._build_visit_uri(FakeOrganisation, sort=cell.key, hfilter=hfilter.pk),
            follow=True,
        )
        self.assertVisitRedirects(
            response, entity=allowed, hfilter=hfilter, sort=cell, index=0,
        )

    def test_other_sort_field(self):
        user = self.login_as_root_and_get()

        create_orga = partial(FakeOrganisation.objects.create, user=user)
        second = create_orga(name='Acme',  phone='2222')
        first  = create_orga(name='Seele', phone='11111')
        third  = create_orga(name='Nerv',  phone='3333')
        self.assertListEqual(
            [first, second, third],
            [*FakeOrganisation.objects.order_by('phone')],
        )

        cell = EntityCellRegularField.build(model=FakeOrganisation, name='phone')
        hfilter = self._create_orga_hfilter()
        response_asc = self.assertGET200(
            self._build_visit_uri(FakeOrganisation, sort=cell.key, hfilter=hfilter.pk),
            follow=True,
        )
        self.assertVisitRedirects(
            response_asc, entity=first, hfilter=hfilter, sort=cell, index=0,
        )

        # DESC -----------------------------------------------------------------
        sort = f'-{cell.key}'
        response_desc1 = self.assertGET200(
            self._build_visit_uri(FakeOrganisation, sort=sort, hfilter=hfilter.pk),
            follow=True,
        )
        self.assertVisitRedirects(
            response_desc1, entity=third, hfilter=hfilter, sort=sort, index=0,
        )

        # ---
        with self.assertNoException():
            visitor_desc1 = response_desc1.context['visitor']
        response_desc2 = self.assertGET200(visitor_desc1.uri, follow=True)

        # ---
        with self.assertNoException():
            visitor_desc2 = response_desc2.context['visitor']
        response_desc3 = self.assertGET200(visitor_desc2.uri, follow=True)

        # ---
        with self.assertNoException():
            visitor_desc3 = response_desc3.context['visitor']

        response_desc4 = self.assertGET200(visitor_desc3.uri)
        self.assertVisitEnds(response_desc4, hfilter=hfilter, sort_key=cell, sort_order='DESC')

    def test_no_sort(self):
        user = self.login_as_root_and_get()

        create_orga = partial(FakeContact.objects.create, user=user)
        first  = create_orga(first_name='Spike', last_name='Spiegel')
        second = create_orga(first_name='Jet',   last_name='Black')

        hfilter = HeaderFilter.objects.proxy(
            id='creme_core-visit_no_order',
            model=FakeContact,
            name='No order view',
            cells=[(EntityCellRegularField, 'languages')],
        ).get_or_create()[0]
        response1 = self.client.get(
            self._build_visit_uri(FakeContact, sort='', hfilter=hfilter.pk),
            follow=True,
        )
        self.assertVisitRedirects(
            response1, entity=first, hfilter=hfilter, sort='', index=0,
        )

        response2 = self.assertGET200(response1.context['visitor'].uri, follow=True)
        self.assertVisitRedirects(
            response2, entity=second, hfilter=hfilter, sort='', index=1,
        )

        response3 = self.assertGET200(response2.context['visitor'].uri)
        self.assertVisitEnds(
            response3, lv_url=FakeContact.get_lv_absolute_url(), hfilter=hfilter, sort_key='',
        )

    def test_callback_url(self):
        user = self.login_as_root_and_get()

        lv_url = reverse('creme_core__list_fake_organisations_with_email')
        first  = FakeOrganisation.objects.create(
            user=user, name='Seele', email='contact@seele.jp',
        )
        cell = EntityCellRegularField.build(model=FakeOrganisation, name='phone')
        hfilter = self._create_orga_hfilter()
        response1 = self.assertGET200(
            self._build_visit_uri(
                FakeOrganisation, sort=cell.key, hfilter=hfilter.pk, lv_url=lv_url,
            ),
            follow=True,
        )
        self.assertVisitRedirects(
            response1, entity=first, hfilter=hfilter, sort=cell, index=0, lv_url=lv_url,
        )

        # ---
        with self.assertNoException():
            visitor1 = response1.context['visitor']

        response2 = self.assertGET200(visitor1.uri)
        self.assertVisitEnds(response2, lv_url=lv_url, hfilter=hfilter, sort_key=cell)

    def test_callback_url_error(self):
        self.login_as_root()

        cb_url = 'www.not-my-creme-instance.com'
        cell = EntityCellRegularField.build(model=FakeOrganisation, name='name')
        hfilter = self._create_orga_hfilter()
        self.assertGET404(self._build_visit_uri(
            FakeOrganisation, sort=cell.key, hfilter=hfilter.pk, lv_url='',
        ))
        self.assertGET409(self._build_visit_uri(
            FakeOrganisation, sort=cell.key, hfilter=hfilter.pk, lv_url=cb_url,
        ))

    def test_efilter(self):
        user = self.login_as_root_and_get()

        efilter = EntityFilter.objects.smart_update_or_create(
            pk='test-visit', name='Acme', model=FakeOrganisation, is_custom=True,
            conditions=[
                entity_filter.condition_handler.RegularFieldConditionHandler.build_condition(
                    model=FakeOrganisation,
                    operator=entity_filter.operators.ICONTAINS,
                    field_name='name', values=['inc.'],
                ),
            ],
        )

        create_orga = partial(FakeOrganisation.objects.create, user=user)
        orgas  = [
            create_orga(name='AAA'),
            create_orga(name='AAA inc.'),
            create_orga(name='AAB inc.'),
        ]

        cell = EntityCellRegularField.build(model=FakeOrganisation, name='name')
        hfilter = self._create_orga_hfilter()
        response1 = self.assertGET200(
            self._build_visit_uri(
                FakeOrganisation, sort=cell.key, hfilter=hfilter.pk, efilter=efilter.pk,
            ),
            follow=True,
        )
        self.assertVisitRedirects(
            response1,
            entity=orgas[1], hfilter=hfilter, sort=cell, efilter=efilter, index=0,
        )

        visitor1 = response1.context.get('visitor')
        page1 = {'type': 'first'}
        self.assertEqual(hfilter.id, visitor1.hfilter_id)
        self.assertEqual(cell.key,   visitor1.sort)
        self.assertEqual(efilter.id, visitor1.efilter_id)
        self.assertEqual(0,          visitor1.index)
        self.assertEqual(page1,      visitor1.page_info)

        url2 = self._build_visit_uri(
            FakeOrganisation,
            hfilter=hfilter.pk, sort=cell.key, efilter=efilter.id,
            page=page1, index=0,
        )
        self.assertURLEqual(url2, visitor1.uri)

        # ---
        response2 = self.assertGET200(url2, follow=True)
        self.assertVisitRedirects(
            response2,
            entity=orgas[2], hfilter=hfilter, sort=cell, efilter=efilter, index=1,
        )

        # ---
        with self.assertNoException():
            visitor2 = response2.context['visitor']

        response3 = self.assertGET200(visitor2.uri)
        self.assertVisitEnds(response3, hfilter=hfilter, sort_key=cell, efilter=efilter)

    def test_efilter_distinct(self):
        user = self.login_as_root_and_get()

        create_orga = partial(FakeOrganisation.objects.create, user=user)
        orgas  = [
            create_orga(name='AABebop'),  # No Relation => avoided by our filter
            create_orga(name='ABebop'),   # 2 Relations => should be visited only once
            create_orga(name='ABebop inc.'),
        ]

        piloted = RelationType.objects.builder(
            id='test-subject_pilots', predicate='is piloted by',
        ).symmetric(
            id='test-object_pilots', predicate='pilots',
        ).get_or_create()[0]

        create_contact = partial(FakeContact.objects.create, user=self.create_user())
        spike = create_contact(first_name='Spike',  last_name='Spiegel')
        jet   = create_contact(first_name='Jet',    last_name='Black')

        create_rel = partial(Relation.objects.create, user=user, type=piloted)
        create_rel(subject_entity=orgas[1], object_entity=spike)
        create_rel(subject_entity=orgas[1], object_entity=jet)
        create_rel(subject_entity=orgas[2], object_entity=jet)

        efilter = EntityFilter.objects.smart_update_or_create(
            pk='test-visit', name='Acme', model=FakeOrganisation, is_custom=True,
            conditions=[
                entity_filter.condition_handler.RelationConditionHandler.build_condition(
                    model=FakeOrganisation,
                    rtype=piloted,
                ),
            ],
        )

        cell = EntityCellRegularField.build(model=FakeOrganisation, name='name')
        hfilter = self._create_orga_hfilter()
        response1 = self.assertGET200(
            self._build_visit_uri(
                FakeOrganisation, sort=cell.key, hfilter=hfilter.pk, efilter=efilter.pk,
            ),
            follow=True,
        )
        self.assertVisitRedirects(
            response1,
            entity=orgas[1], hfilter=hfilter, sort=cell, efilter=efilter, index=0,
        )

        visitor1 = response1.context.get('visitor')
        response2 = self.assertGET200(
            visitor1.uri,
            follow=True,
        )
        self.assertVisitRedirects(
            response2,
            entity=orgas[2], hfilter=hfilter, sort=cell, efilter=efilter, index=1,
        )

    def test_requested_q(self):
        user = self.login_as_root_and_get()

        create_orga = partial(FakeOrganisation.objects.create, user=user)
        orgas  = [
            create_orga(name='AAA'),
            create_orga(name='AAA inc.'),
            create_orga(name='AAB inc.'),
        ]

        cell = EntityCellRegularField.build(model=FakeOrganisation, name='name')
        hfilter = self._create_orga_hfilter()
        serialized_q = QSerializer().dumps(Q(name__contains='inc.'))
        response1 = self.assertGET200(
            self._build_visit_uri(
                FakeOrganisation, sort=cell.key, hfilter=hfilter.pk, requested_q=serialized_q,
            ),
            follow=True,
        )
        self.assertVisitRedirects(
            response1,
            entity=orgas[1], hfilter=hfilter, sort=cell, requested_q=serialized_q, index=0,
        )

        visitor1 = response1.context.get('visitor')
        self.assertEqual(serialized_q, visitor1.serialized_requested_q)

        url2 = self._build_visit_uri(
            FakeOrganisation,
            hfilter=hfilter.pk, sort=cell.key, requested_q=serialized_q,
            page={'type': 'first'}, index=0,
        )
        self.assertURLEqual(url2, visitor1.uri)

        # ---
        response2 = self.assertGET200(url2, follow=True)
        self.assertVisitRedirects(
            response2,
            entity=orgas[2], hfilter=hfilter, sort=cell, requested_q=serialized_q, index=1,
        )

        # ---
        with self.assertNoException():
            visitor2 = response2.context['visitor']

        response3 = self.assertGET200(visitor2.uri)
        self.assertVisitEnds(
            response3, hfilter=hfilter, sort_key=cell, q_filter=serialized_q,
        )

    def test_requested_q_distinct(self):
        user = self.login_as_root_and_get()

        create_orga = partial(FakeOrganisation.objects.create, user=user)
        orgas  = [
            create_orga(name='AABebop'),  # No Relation => avoided by our filter
            create_orga(name='ABebop'),   # 2 Relations => should be visited only once
            create_orga(name='ABebop inc.'),
        ]

        piloted = RelationType.objects.builder(
            id='test-subject_pilots', predicate='is piloted by',
        ).symmetric(
            id='test-object_pilots', predicate='pilots',
        ).get_or_create()[0]

        create_contact = partial(FakeContact.objects.create, user=self.create_user())
        spike = create_contact(first_name='Spike',  last_name='Spiegel')
        jet   = create_contact(first_name='Jet',    last_name='Black')

        create_rel = partial(Relation.objects.create, user=user, type=piloted)
        create_rel(subject_entity=orgas[1], object_entity=spike)
        create_rel(subject_entity=orgas[1], object_entity=jet)
        create_rel(subject_entity=orgas[2], object_entity=jet)

        cell = EntityCellRegularField.build(model=FakeOrganisation, name='name')
        serialized_q = QSerializer().dumps(Q(relations__type=piloted.id))
        hfilter = self._create_orga_hfilter()
        response1 = self.assertGET200(
            self._build_visit_uri(
                FakeOrganisation, sort=cell.key, hfilter=hfilter.pk, requested_q=serialized_q,
            ),
            follow=True,
        )
        self.assertVisitRedirects(
            response1,
            entity=orgas[1], hfilter=hfilter, sort=cell, requested_q=serialized_q, index=0,
        )

        visitor1 = response1.context.get('visitor')
        response2 = self.assertGET200(
            visitor1.uri,
            follow=True,
        )
        self.assertVisitRedirects(
            response2,
            entity=orgas[2], hfilter=hfilter, sort=cell, requested_q=serialized_q, index=1,
        )

    def test_internal_q(self):
        user = self.login_as_root_and_get()

        create_orga = partial(FakeOrganisation.objects.create, user=user)
        orgas  = [
            create_orga(name='AAA', email='aaa@exemple.com'),
            create_orga(name='AAB'),
            create_orga(name='AAC', email='aac@exemple.com'),
        ]

        cell = EntityCellRegularField.build(model=FakeOrganisation, name='name')
        hfilter = self._create_orga_hfilter()
        serialized_q = QSerializer().dumps(~Q(email=''))
        response1 = self.assertGET200(
            self._build_visit_uri(
                FakeOrganisation,
                sort=cell.key, hfilter=hfilter.pk, internal_q=serialized_q,
            ),
            follow=True,
        )
        self.assertVisitRedirects(
            response1,
            entity=orgas[0], hfilter=hfilter, sort=cell, internal_q=serialized_q, index=0,
        )

        visitor1 = response1.context.get('visitor')
        self.assertEqual(serialized_q, visitor1.serialized_internal_q)

        url2 = self._build_visit_uri(
            FakeOrganisation,
            hfilter=hfilter.pk, sort=cell.key, internal_q=serialized_q,
            page={'type': 'first'}, index=0,
        )
        self.assertURLEqual(url2, visitor1.uri)

        # ---
        response2 = self.assertGET200(url2, follow=True)
        self.assertVisitRedirects(
            response2,
            entity=orgas[2], hfilter=hfilter, sort=cell, internal_q=serialized_q, index=1,
        )

        # ---
        with self.assertNoException():
            visitor2 = response2.context['visitor']

        response3 = self.assertGET200(visitor2.uri)
        self.assertVisitEnds(response3, hfilter=hfilter, sort_key=cell)  # not q_filter

    def test_quick_search(self):
        user = self.login_as_root_and_get()

        create_orga = partial(FakeOrganisation.objects.create, user=user)
        orgas  = [
            create_orga(name='AAA'),
            create_orga(name='AAA inc.'),
            create_orga(name='AAB inc.'),
        ]

        cell = EntityCellRegularField.build(model=FakeOrganisation, name='name')
        hfilter = self._create_orga_hfilter()
        search = {f'search-{cell.key}': 'inc.'}
        response1 = self.assertGET200(
            self._build_visit_uri(FakeOrganisation, sort=cell.key, hfilter=hfilter.pk, **search),
            follow=True,
        )
        self.assertVisitRedirects(
            response1,
            entity=orgas[1], sort=cell, hfilter=hfilter, index=0, search=search,
        )

        visitor1 = response1.context.get('visitor')
        self.assertEqual(search, visitor1.search_dict)

        url2 = self._build_visit_uri(
            FakeOrganisation,
            hfilter=hfilter.pk, sort=cell.key,
            page={'type': 'first'}, index=0,
            **search
        )
        self.assertURLEqual(url2, visitor1.uri)

        # ---
        response2 = self.assertGET200(url2, follow=True)
        self.assertVisitRedirects(
            response2,
            entity=orgas[2], hfilter=hfilter, sort=cell, index=1, search=search,
        )

        # ---
        with self.assertNoException():
            visitor2 = response2.context['visitor']

        response3 = self.assertGET200(visitor2.uri)
        self.assertVisitEnds(response3, hfilter=hfilter, sort_key=cell, **search)

    def test_complete_visit01(self):
        "Even number of entities."
        user = self.login_as_root_and_get()

        create_orga = partial(FakeOrganisation.objects.create, user=user)
        orgas = [
            create_orga(name='Acme1', phone='1123'),
            create_orga(name='Acme2', phone='1134'),
            create_orga(name='Acme3', phone='1145'),
            create_orga(name='Acme4', phone='1156'),
        ]

        cell = EntityCellRegularField.build(model=FakeOrganisation, name='name')
        hfilter = self._create_orga_hfilter()
        serialized_q = QSerializer().dumps(Q(phone__startswith='11'))

        ctxt1 = self.assertGET200(
            self._build_visit_uri(
                FakeOrganisation,
                hfilter=hfilter.pk, sort=cell.key, requested_q=serialized_q,
            ),
            follow=True,
        ).context
        self.assertEqual(orgas[0], ctxt1['object'])
        with self.assertNoException():
            visitor1 = ctxt1['visitor']

        # ---
        ctxt2 = self.assertGET200(visitor1.uri, follow=True).context
        self.assertEqual(orgas[1], ctxt2['object'])
        with self.assertNoException():
            visitor2 = ctxt2['visitor']

        # ---
        ctxt3 = self.assertGET200(visitor2.uri, follow=True).context
        self.assertEqual(orgas[2], ctxt3['object'])
        with self.assertNoException():
            visitor3 = ctxt3['visitor']

        # ---
        ctxt4 = self.assertGET200(visitor3.uri, follow=True).context
        self.assertEqual(orgas[3], ctxt4['object'])
        with self.assertNoException():
            visitor4 = ctxt4['visitor']

        # Next => end of visit
        response5 = self.assertGET200(visitor4.uri)
        self.assertVisitEnds(
            response5, hfilter=hfilter, sort_key=cell, q_filter=serialized_q,
        )

    def test_complete_visit02(self):
        "Odd number of entities."
        user = self.login_as_root_and_get()

        create_orga = partial(FakeOrganisation.objects.create, user=user)
        orgas = [
            create_orga(name='Acme1', phone='1123'),
            create_orga(name='Acme2', phone='1134'),
            create_orga(name='Acme3', phone='1145'),
            create_orga(name='Acme4', phone='1156'),
            create_orga(name='Acme5', phone='1156'),
        ]

        cell = EntityCellRegularField.build(model=FakeOrganisation, name='name')
        hfilter = self._create_orga_hfilter()
        serialized_q = QSerializer().dumps(Q(phone__startswith='11'))

        ctxt1 = self.assertGET200(
            self._build_visit_uri(
                FakeOrganisation, hfilter=hfilter.pk, sort=cell.key, requested_q=serialized_q,
            ),
            follow=True,
        ).context
        self.assertEqual(orgas[0], ctxt1['object'])
        with self.assertNoException():
            visitor1 = ctxt1['visitor']

        # ---
        ctxt2 = self.assertGET200(visitor1.uri, follow=True).context
        self.assertEqual(orgas[1], ctxt2['object'])
        with self.assertNoException():
            visitor2 = ctxt2['visitor']

        # ---
        ctxt3 = self.assertGET200(visitor2.uri, follow=True).context
        self.assertEqual(orgas[2], ctxt3['object'])
        with self.assertNoException():
            visitor3 = ctxt3['visitor']

        # ---
        ctxt4 = self.assertGET200(visitor3.uri, follow=True).context
        self.assertEqual(orgas[3], ctxt4['object'])
        with self.assertNoException():
            visitor4 = ctxt4['visitor']

        # ---
        ctxt5 = self.assertGET200(visitor4.uri, follow=True).context
        self.assertEqual(orgas[4], ctxt5['object'])
        with self.assertNoException():
            visitor5 = ctxt5['visitor']

        # Next => end of visit
        response6 = self.assertGET200(visitor5.uri)
        self.assertVisitEnds(
            response6, hfilter=hfilter, sort_key=cell, q_filter=serialized_q,
        )

    def test_visit_duplicates(self):
        user = self.login_as_root_and_get()

        create_orga = partial(FakeOrganisation.objects.create, user=user)
        orgas = [
            create_orga(name='Acme', phone='1123'),
            create_orga(name='Acme', phone='1134'),
            create_orga(name='Acme inc.', phone='1145'),
        ]

        cell = EntityCellRegularField.build(model=FakeOrganisation, name='name')
        hfilter = self._create_orga_hfilter()
        serialized_extra_q = QSerializer().dumps(Q(phone__startswith='11'))

        ctxt1 = self.assertGET200(
            self._build_visit_uri(
                FakeOrganisation,
                hfilter=hfilter.pk, sort=cell.key, extra_q=serialized_extra_q,
            ),
            follow=True,
        ).context
        self.assertEqual(orgas[0], ctxt1['object'])
        with self.assertNoException():
            visitor1 = ctxt1['visitor']

        # ---
        ctxt2 = self.assertGET200(visitor1.uri, follow=True).context
        self.assertEqual(orgas[1], ctxt2['object'])
        with self.assertNoException():
            visitor2 = ctxt2['visitor']

        # ---
        ctxt3 = self.assertGET200(visitor2.uri, follow=True).context
        self.assertEqual(orgas[2], ctxt3['object'])

    def test_page_errors(self):
        self.login_as_root()

        build_uri = partial(
            self._build_visit_uri,
            model=FakeOrganisation,
            hfilter=self._create_orga_hfilter().pk,
            sort=EntityCellRegularField.build(model=FakeOrganisation, name='name').key,
            page={'type': 'first'},
            index=0,
        )
        self.assertGET(400, build_uri(index='NaN'))
        self.assertGET(400, build_uri(index=-1))
        self.assertGET(400, build_uri(index=2))
        self.assertGET(400, build_uri(index=0, page='not_json'))
        self.assertGET(400, build_uri(index=0, page=['bad type']))
        self.assertGET200(build_uri(index=0, page={'type': 'unknown'}))  # Only log

    def test_hfilter_errors(self):
        self.login_as_root()

        build_uri = partial(
            self._build_visit_uri,
            model=FakeOrganisation,
            # hfilter=...,
            sort=EntityCellRegularField.build(model=FakeOrganisation, name='name').key,
            page={'type': 'first'},
            index=0,
        )
        # Invalid ID
        self.assertGET404(build_uri(hfilter='unknown'))

        # HeaderFilter with bad ContentType
        hfilter = HeaderFilter.objects.proxy(
            id='creme_core-visit_contact',
            model=FakeContact,
            name='Simple contact view',
            cells=[(EntityCellRegularField, 'last_name')],
        ).get_or_create()[0]
        self.assertGET404(build_uri(hfilter=hfilter.id))

        # HeaderFilter is not allowed
        private_hf = HeaderFilter.objects.proxy(
            id='creme_core-visit_orga_private',
            model=FakeOrganisation,
            name='Simple contact view',
            is_custom=True, user=self.create_user(), is_private=True,
            cells=[(EntityCellRegularField, 'email')],
        ).get_or_create()[0]
        self.assertGET404(build_uri(hfilter=private_hf.id))

    def test_efilter_errors(self):
        user = self.login_as_root_and_get()

        build_uri = partial(
            self._build_visit_uri,
            model=FakeOrganisation,
            hfilter=self._create_orga_hfilter().id,
            sort=EntityCellRegularField.build(model=FakeOrganisation, name='name').key,
            # page={'type': 'first'},
            # index=0,
        )
        # Invalid ID
        self.assertGET404(build_uri(efilter='unknown'))

        # EntityFilter with bad ContentType
        efilter = EntityFilter.objects.smart_update_or_create(
            'test-hf_contact_test_invalid_efilter',
            name='Cowboys',
            model=FakeContact,  # <===
            user=user,
            conditions=[
                entity_filter.condition_handler.RegularFieldConditionHandler.build_condition(
                    model=FakeContact, field_name='last_name',
                    operator=entity_filter.operators.ISTARTSWITH,
                    values=['Cowboy'],
                )
            ],
        )
        response2 = self.assertGET404(build_uri(efilter=efilter.id))
        self.assertIn(
            b'No EntityFilter matches the given query.',
            response2.content,
        )

        # EntityFilter is not allowed
        private_efilter = EntityFilter.objects.smart_update_or_create(
            'test-hf_orga_test_private_efilter',
            name='With Contact mail',
            model=FakeOrganisation,
            is_custom=True, user=self.create_user(), is_private=True,  # <===
            conditions=[
                entity_filter.condition_handler.RegularFieldConditionHandler.build_condition(
                    model=FakeOrganisation, field_name='email',
                    operator=entity_filter.operators.ISTARTSWITH,
                    values=['contact'],
                )
            ],
        )
        response3 = self.assertGET404(build_uri(efilter=private_efilter.id))
        self.assertIn(
            b'No EntityFilter matches the given query.',
            response3.content,
        )

    def test_extra_q_errors(self):
        self.login_as_root()

        kwargs = {
            'model':   FakeOrganisation,
            'hfilter': self._create_orga_hfilter().id,
            'sort':    EntityCellRegularField.build(model=FakeOrganisation, name='name').key,
        }
        self.assertGET(400, self._build_visit_uri(requested_q='[]', **kwargs))
        self.assertGET(400, self._build_visit_uri(internal_q='[]', **kwargs))

    def test_quick_search_errors(self):
        user = self.login_as_root_and_get()
        orga = FakeOrganisation.objects.create(user=user, name='A1')

        field_name = 'capital'
        cell = EntityCellRegularField.build(model=FakeOrganisation, name=field_name)
        search = {f'search-{cell.key}': 'not an int'}

        hfilter = self._create_orga_hfilter(field_name)
        cell = EntityCellRegularField.build(model=FakeOrganisation, name='name')

        # TODO error 400?
        response = self.assertGET200(
            self._build_visit_uri(
                model=FakeOrganisation,
                hfilter=hfilter.id,
                sort=cell.key,
                **search
            ),
            follow=True,
        )
        self.assertVisitRedirects(
            response,
            entity=orga, hfilter=hfilter, sort=cell, page={'type': 'first'}, index=0,
        )

        visitor = response.context.get('visitor')
        self.assertIsNone(visitor.search_dict)
