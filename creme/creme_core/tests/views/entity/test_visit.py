from functools import partial
from json import dumps as json_dump
from urllib.parse import parse_qs, urlencode, urlparse

from django.contrib.contenttypes.models import ContentType
from django.db.models import Q
from django.urls import reverse
from django.utils.translation import gettext as _

from creme.creme_core.auth import EntityCredentials
from creme.creme_core.core import entity_filter
from creme.creme_core.core.entity_cell import EntityCellRegularField
from creme.creme_core.models import (
    EntityFilter,
    FakeContact,
    FakeOrganisation,
    HeaderFilter,
    Relation,
    RelationType,
    SetCredentials,
)
from creme.creme_core.tests.views.base import ViewsTestCase
from creme.creme_core.utils.queries import QSerializer
from creme.creme_core.views.generic.detailview import EntityVisitor


class VisitTestCase(ViewsTestCase):
    def assertVisitRedirects(self, response, *,
                             entity, sort, index, hfilter,
                             page=None, efilter=None, extra_q='', search=None,
                             ):
        try:
            chain = response.redirect_chain
        except AttributeError:
            self.fail('Not a redirection')

        if len(chain) != 1:
            self.fail(f'The redirection chain is too long: {chain}')

        parsed_uri = urlparse(chain[0][0])
        self.assertEqual(entity.get_absolute_url(), parsed_uri.path)

        visitor_data = {
            'hfilter': hfilter.pk,
            'sort': sort if isinstance(sort, str) else sort.key,
            'page': page or {'type': 'first'},
            'index': index,
        }
        if efilter:
            visitor_data['efilter'] = efilter.pk
        if extra_q:
            visitor_data['extra_q'] = extra_q
        if search:
            visitor_data['search'] = search

        self.assertDictEqual(
            {'visitor': [json_dump(visitor_data)]},
            parse_qs(
                parsed_uri.query, keep_blank_values=True, strict_parsing=True,
            ),
        )

    @staticmethod
    def _build_visit_uri(model, page=None, **kwargs):
        if page:
            kwargs['page'] = page if isinstance(page, str) else json_dump(page)

        url = reverse(
            'creme_core__visit_next_entity',
            args=(ContentType.objects.get_for_model(model).id,),
        )

        return f'{url}?{urlencode(kwargs)}'

    def _create_orga_hfilter(self, *fields):
        return HeaderFilter.objects.create_if_needed(
            pk='creme_core-visit',
            model=FakeOrganisation,
            name='Simple view',
            cells_desc=[
                (EntityCellRegularField, {'name': 'name'}),
                (EntityCellRegularField, {'name': 'phone'}),
                *(
                    (EntityCellRegularField, {'name': field_name})
                    for field_name in fields
                )
            ],
        )

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
        self.assertTemplateUsed(response2, 'creme_core/visit-end.html')

        html = self.get_html_tree(response2.content)
        title_node = self.get_html_node_or_fail(html, './/div[@class="bar-title"]//h1')
        self.assertEqual(_('The exploration is over'), title_node.text)

        content_node = self.get_html_node_or_fail(html, './/div[@class="buttons-list"]')
        button_node = self.get_html_node_or_fail(content_node, './/a')
        self.assertIn(
            _('Back to the list'),
            (txt.strip() for txt in button_node.itertext()),
        )
        self.assertEqual(
            FakeOrganisation.get_lv_absolute_url(),
            button_node.attrib.get('href'),
        )

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
        # user = self.login(is_superuser=False)
        user = self.login_as_standard()
        SetCredentials.objects.create(
            role=user.role,
            value=EntityCredentials.VIEW,
            set_type=SetCredentials.ESET_OWN,
        )

        create_orga = FakeOrganisation.objects.create
        # create_orga(user=self.other_user, name='AAA')
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
            [*FakeOrganisation.objects.order_by('phone')[:3]],
        )

        cell = EntityCellRegularField.build(model=FakeOrganisation, name='phone')
        hfilter = self._create_orga_hfilter()
        response1 = self.assertGET200(
            self._build_visit_uri(FakeOrganisation, sort=cell.key, hfilter=hfilter.pk),
            follow=True,
        )
        self.assertVisitRedirects(
            response1, entity=first, hfilter=hfilter, sort=cell, index=0,
        )

        # DESC ---
        sort = f'-{cell.key}'
        response2 = self.assertGET200(
            self._build_visit_uri(FakeOrganisation, sort=sort, hfilter=hfilter.pk),
            follow=True,
        )
        self.assertVisitRedirects(
            response2, entity=third, hfilter=hfilter, sort=sort, index=0,
        )

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

    def test_efilter_distinct(self):
        user = self.login_as_root_and_get()

        create_orga = partial(FakeOrganisation.objects.create, user=user)
        orgas  = [
            create_orga(name='AABebop'),  # No Relation => avoided by our filter
            create_orga(name='ABebop'),   # 2 Relations => should be visited only once
            create_orga(name='ABebop inc.'),
        ]

        piloted = RelationType.objects.smart_update_or_create(
            ('test-subject_pilots', 'pilots'),
            ('test-object_pilots',  'is piloted by'),
        )[1]

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

    def test_extra_q(self):
        user = self.login_as_root_and_get()

        create_orga = partial(FakeOrganisation.objects.create, user=user)
        orgas  = [
            create_orga(name='AAA'),
            create_orga(name='AAA inc.'),
            create_orga(name='AAB inc.'),
        ]

        cell = EntityCellRegularField.build(model=FakeOrganisation, name='name')
        hfilter = self._create_orga_hfilter()
        serialized_extra_q = QSerializer().dumps(Q(name__contains='inc.'))
        response = self.assertGET200(
            self._build_visit_uri(
                FakeOrganisation,
                sort=cell.key, hfilter=hfilter.pk, extra_q=serialized_extra_q,
            ),
            follow=True,
        )
        self.assertVisitRedirects(
            response,
            entity=orgas[1], hfilter=hfilter, sort=cell, extra_q=serialized_extra_q, index=0,
        )

        visitor = response.context.get('visitor')
        self.assertEqual(serialized_extra_q, visitor.serialized_extra_q)

        url2 = self._build_visit_uri(
            FakeOrganisation,
            hfilter=hfilter.pk, sort=cell.key, extra_q=serialized_extra_q,
            page={'type': 'first'}, index=0,
        )
        self.assertURLEqual(url2, visitor.uri)

    def test_extra_q_distinct(self):
        user = self.login_as_root_and_get()

        create_orga = partial(FakeOrganisation.objects.create, user=user)
        orgas  = [
            create_orga(name='AABebop'),  # No Relation => avoided by our filter
            create_orga(name='ABebop'),   # 2 Relations => should be visited only once
            create_orga(name='ABebop inc.'),
        ]

        piloted = RelationType.objects.smart_update_or_create(
            ('test-subject_pilots', 'pilots'),
            ('test-object_pilots',  'is piloted by'),
        )[1]

        create_contact = partial(FakeContact.objects.create, user=self.create_user())
        spike = create_contact(first_name='Spike',  last_name='Spiegel')
        jet   = create_contact(first_name='Jet',    last_name='Black')

        create_rel = partial(Relation.objects.create, user=user, type=piloted)
        create_rel(subject_entity=orgas[1], object_entity=spike)
        create_rel(subject_entity=orgas[1], object_entity=jet)
        create_rel(subject_entity=orgas[2], object_entity=jet)

        cell = EntityCellRegularField.build(model=FakeOrganisation, name='name')
        serialized_extra_q = QSerializer().dumps(Q(relations__type=piloted.id))
        hfilter = self._create_orga_hfilter()
        response1 = self.assertGET200(
            self._build_visit_uri(
                FakeOrganisation, sort=cell.key, hfilter=hfilter.pk, extra_q=serialized_extra_q,
            ),
            follow=True,
        )
        self.assertVisitRedirects(
            response1,
            entity=orgas[1], hfilter=hfilter, sort=cell, extra_q=serialized_extra_q, index=0,
        )

        visitor1 = response1.context.get('visitor')
        response2 = self.assertGET200(
            visitor1.uri,
            follow=True,
        )
        self.assertVisitRedirects(
            response2,
            entity=orgas[2], hfilter=hfilter, sort=cell, extra_q=serialized_extra_q, index=1,
        )

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
        response = self.assertGET200(
            self._build_visit_uri(FakeOrganisation, sort=cell.key, hfilter=hfilter.pk, **search),
            follow=True,
        )
        self.assertVisitRedirects(
            response,
            entity=orgas[1], sort=cell, hfilter=hfilter, index=0, search=search,
        )

        visitor = response.context.get('visitor')
        self.assertEqual(search, visitor.search_dict)

        url2 = self._build_visit_uri(
            FakeOrganisation,
            hfilter=hfilter.pk, sort=cell.key,
            page={'type': 'first'}, index=0,
            **search
        )
        self.assertURLEqual(url2, visitor.uri)

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
        with self.assertNoException():
            visitor3 = ctxt3['visitor']

        # ---
        ctxt4 = self.assertGET200(visitor3.uri, follow=True).context
        self.assertEqual(orgas[3], ctxt4['object'])
        with self.assertNoException():
            visitor4 = ctxt4['visitor']

        # Next => end of visit
        response5 = self.assertGET200(visitor4.uri)
        self.assertTemplateUsed(response5, 'creme_core/visit-end.html')

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
        self.assertTemplateUsed(response6, 'creme_core/visit-end.html')

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
        # self.login()
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
        hfilter = HeaderFilter.objects.create_if_needed(
            pk='creme_core-visit_contact',
            model=FakeContact,
            name='Simple contact view',
            cells_desc=[(EntityCellRegularField, {'name': 'last_name'})],
        )
        self.assertGET404(build_uri(hfilter=hfilter.id))

        # HeaderFilter is not allowed
        private_hf = HeaderFilter.objects.create_if_needed(
            pk='creme_core-visit_orga_private',
            model=FakeOrganisation,
            name='Simple contact view',
            is_custom=True, user=self.create_user(), is_private=True,
            cells_desc=[(EntityCellRegularField, {'name': 'email'})],
        )
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
        # self.login()
        self.login_as_root()
        self.assertGET(
            400,
            self._build_visit_uri(
                model=FakeOrganisation,
                hfilter=self._create_orga_hfilter().id,
                sort=EntityCellRegularField.build(model=FakeOrganisation, name='name').key,
                extra_q='[]',  # <===
            ),
        )

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
