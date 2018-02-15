# -*- coding: utf-8 -*-

try:
    from functools import partial
    from json import loads as jsonloads, dumps as jsondumps

    from django.contrib.auth import get_user_model
    from django.contrib.contenttypes.models import ContentType

    from ..base import CremeTestCase
    from ..fake_models import FakeContact, FakeOrganisation, FakeCivility, FakePosition
    from creme.creme_core.core.entity_cell import (EntityCellRegularField,
            EntityCellFunctionField, EntityCellRelation)
    from creme.creme_core.models import RelationType, Relation, HeaderFilter, CremeEntity
    from creme.creme_core.models.header_filter import HeaderFilterList
except Exception as e:
    print('Error in <%s>: %s' % (__name__, e))


class HeaderFiltersTestCase(CremeTestCase):
    @classmethod
    def setUpClass(cls):
        super(HeaderFiltersTestCase, cls).setUpClass()

        get_ct = ContentType.objects.get_for_model
        cls.contact_ct = get_ct(FakeContact)  # TODO: used once ?!
        cls.orga_ct    = get_ct(FakeOrganisation)

    def assertCellEqual(self, cell1, cell2):
        self.assertIs(cell1.__class__, cell2.__class__)
        self.assertEqual(cell1.value, cell2.value)

    def test_create01(self):
        self.login()

        name = 'Contact view'
        pk   = 'tests-hf_contact'
        hf   = HeaderFilter.create(pk=pk, name=name, model=FakeContact, is_custom=True)
        self.assertEqual(pk,   hf.pk)
        self.assertEqual(name, hf.name)
        self.assertIsNone(hf.user)
        self.assertEqual(self.contact_ct, hf.entity_type)
        self.assertIs(hf.is_custom, True)
        self.assertIs(hf.is_private, False)
        self.assertEqual('[]', hf.json_cells)
        self.assertFalse(hf.cells)

        hf.cells = [EntityCellRegularField.build(model=FakeContact, name='first_name')]
        hf.save()

        hf = self.refresh(hf)
        self.assertEqual(1, len(hf.cells))

        with self.assertNoException():
            deserialized = jsonloads(hf.json_cells)

        self.assertEqual([{'type': 'regular_field', 'value': 'first_name'}],
                         deserialized
                        )

    def test_create02(self):
        "With cells"
        user = self.login()

        create_rtype = RelationType.create
        loves = create_rtype(('test-subject_love', u'Is loving'),
                             ('test-object_love',  u'Is loved by')
                            )[0]
        likes = create_rtype(('test-subject_like', u'Is liking'),
                             ('test-object_like',  u'Is liked by')
                            )[0]

        hf = HeaderFilter.create(pk='tests-hf_contact', name='Contact view',
                                 model=FakeContact, is_custom=True, is_private=True,
                                 user=user,
                                 cells_desc=[(EntityCellRegularField, {'name': 'last_name'}),
                                              EntityCellRelation(loves),
                                             (EntityCellRelation, {'rtype_id': likes.id}),
                                             None,
                                            ],
                                )

        hf = self.refresh(hf)
        self.assertEqual(user, hf.user)
        self.assertTrue(hf.is_private)

        cells = hf.cells
        self.assertEqual(3, len(cells))

        cell = cells[0]
        self.assertIsInstance(cell, EntityCellRegularField)
        self.assertEqual('last_name', cell.value)

        cell = cells[1]
        self.assertIsInstance(cell, EntityCellRelation)
        self.assertEqual(loves.id, cell.value)

        cell = cells[2]
        self.assertIsInstance(cell, EntityCellRelation)
        self.assertEqual(likes.id, cell.value)

    def test_create03(self):
        "Do not modify if it already exists"
        self.login()

        pk = 'tests-hf_contact'
        name = 'Contact view'
        hf = HeaderFilter.create(pk=pk, name=name,
                                 model=FakeContact, is_custom=False,
                                 cells_desc=[(EntityCellRegularField, {'name': 'last_name'})],
                                )

        hf = HeaderFilter.create(pk=pk, name='Contact view edited', user=self.user,
                                 model=FakeContact, is_custom=False,
                                 cells_desc=[(EntityCellRegularField, {'name': 'first_name'}),
                                             (EntityCellRegularField, {'name': 'last_name'}),
                                            ],
                                )
        self.assertEqual(name, hf.name)
        self.assertIsNone(hf.user)
        self.assertEqual(1, len(hf.cells))

    def test_create_errors(self):
        user = self.login()

        # Private + no user => error
        with self.assertRaises(ValueError):
            HeaderFilter.create(pk='tests-hf_contact', name='Contact view edited',
                                model=FakeContact, is_private=True,
                                cells_desc=[(EntityCellRegularField, {'name': 'last_name'})],
                               )

        # Private + not is_custom => error
        with self.assertRaises(ValueError):
            HeaderFilter.create(pk='tests-hf_contact', name='Contact view edited',
                                user=user, model=FakeContact,
                                is_private=True, is_custom=False,
                                cells_desc=[(EntityCellRegularField, {'name': 'last_name'})],
                               )

    def test_ct_cache(self):
        hf = HeaderFilter.create(pk='tests-hf_contact', name='Contact view',
                                 model=FakeContact, is_custom=True,
                                )

        with self.assertNumQueries(0):
            ContentType.objects.get_for_id(hf.entity_type_id)

        hf = self.refresh(hf)

        with self.assertNumQueries(0):
            hf.entity_type

    def test_cells_property01(self):
        build_cell = partial(EntityCellRegularField.build, model=FakeContact)
        cells = [build_cell(name=fn) for fn in ('first_name', 'last_name')]
        hf = HeaderFilter.create(pk='test-hf01', name=u'Contact view', model=FakeContact,
                                 cells_desc=cells,
                                )

        cells.append(build_cell(name='description'))
        hf.cells = cells
        hf.save()
        self.assertEqual(3, len(self.refresh(hf).cells))

    def test_cells_property02(self):
        "None value are ignored"
        hf = HeaderFilter.create(pk='test-hf01', name=u'Contact view', model=FakeContact)

        build_cell = partial(EntityCellRegularField.build, model=FakeContact)
        cell01 = build_cell(name='first_name')
        cell02 = build_cell(name='invalid_field')
        cell03 = build_cell(name='last_name')
        self.assertIsNone(cell02)

        hf.cells = [cell01, cell02, cell03]
        hf.save()

        self.assertEqual([cell01.value, cell03.value],
                         [cell.value for cell in self.refresh(hf).cells]
                        )

    def test_cells_property_errors01(self):
        self.login()

        ffield_name = 'get_pretty_properties'
        rfield_name = 'last_name'
        hf = HeaderFilter.create(pk='test-hf', name=u'Contact view', model=FakeContact,
                                 cells_desc=[(EntityCellFunctionField, {'func_field_name': ffield_name}),
                                             (EntityCellRegularField,  {'name': rfield_name}),
                                            ],
                                )

        json_data = hf.json_cells

        with self.assertNoException():
            deserialized = jsonloads(json_data)

        self.assertEqual([{'type': 'function_field', 'value': ffield_name},
                          {'type': 'regular_field',  'value': rfield_name},
                         ],
                         deserialized
                        )

        # We use update() in order to bypass the checkings by HeaderFilter
        # methods and inject errors : it simulates an human that modifies
        # directly the DB column.
        HeaderFilter.objects.filter(id=hf.id) \
                            .update(json_cells=json_data.replace('function_field', 'invalid_type'))

        hf = self.refresh(hf)
        self.assertEqual(1, len(hf.cells))

        json_data = hf.json_cells

        with self.assertNoException():
            deserialized = jsonloads(json_data)

        self.assertEqual([{'type': 'regular_field',  'value': rfield_name}],
                         deserialized
                        )

        # ---------------------------------------------------------------------
        HeaderFilter.objects.filter(id=hf.id) \
                            .update(json_cells=jsondumps([{'type': 'function_field'},
                                                          {'type': 'regular_field', 'value': rfield_name},
                                                         ]))

        hf = self.refresh(hf)
        cells = hf.cells
        self.assertEqual(1, len(cells))
        self.assertIsInstance(cells[0], EntityCellRegularField)

        # ---------------------------------------------------------------------
        HeaderFilter.objects.filter(id=hf.id) \
                            .update(json_cells=jsondumps([{'type': 'function_field'},  # Not 'value' key
                                                          {'type': 'regular_field', 'value': rfield_name},
                                                         ]))
        hf = self.refresh(hf)
        cells = hf.cells
        self.assertEqual(1, len(cells))
        self.assertIsInstance(cells[0], EntityCellRegularField)

        # ---------------------------------------------------------------------
        HeaderFilter.objects.filter(id=hf.id) \
                            .update(json_cells=jsondumps([{},  # No 'type' key
                                                          {'type': 'regular_field', 'value': rfield_name},
                                                         ]))
        hf = self.refresh(hf)
        cells = hf.cells
        self.assertEqual(1, len(cells))
        self.assertIsInstance(cells[0], EntityCellRegularField)

        # ---------------------------------------------------------------------
        HeaderFilter.objects.filter(id=hf.id).update(json_cells=jsondumps([1]))  # Not a dict
        self.assertEqual(0, len(self.refresh(hf).cells))

        # ---------------------------------------------------------------------
        HeaderFilter.objects.filter(id=hf.id).update(json_cells=jsondumps(1))  # Not a list
        self.assertEqual(0, len(self.refresh(hf).cells))

    def test_populate_entities_fields01(self):
        "Regular fields: no FK"
        user = self.login()
        hf = HeaderFilter.create(pk='test-hf', name=u'Contact view', model=FakeContact,
                                 cells_desc=[(EntityCellRegularField, {'name': 'last_name'}),
                                             (EntityCellRegularField, {'name': 'first_name'}),
                                            ])

        pos = FakePosition.objects.create(title='Pilot')
        create_contact = partial(FakeContact.objects.create, user=user, position_id=pos.id)
        contacts = [create_contact(first_name='Nagate',  last_name='Tanikaze'),
                    create_contact(first_name='Shizuka', last_name='Hoshijiro'),
                   ]

        with self.assertNumQueries(0):
            hf.populate_entities(contacts, user)

        with self.assertNumQueries(1):
            contacts[0].position

    def test_populate_entities_fields02(self):
        "Regular fields: FK"
        user = self.login()
        build = partial(EntityCellRegularField.build, model=FakeContact)
        hf = HeaderFilter.create(pk='test-hf', name=u'Contact view', model=FakeContact,
                                 cells_desc=[build(name='last_name'), build(name='first_name'),
                                             build(name='position'),
                                             build(name='civility__title'),
                                            ],
                                )

        pos = FakePosition.objects.create(title='Pilot')
        civ = FakeCivility.objects.all()[0]
        create_contact = partial(FakeContact.objects.create, user=user, position_id=pos.id,
                                 civility_id=civ.id,
                                )
        contacts = [create_contact(first_name='Nagate',  last_name='Tanikaze'),
                    create_contact(first_name='Shizuka', last_name='Hoshijiro'),
                   ]

        with self.assertNumQueries(2):
            hf.populate_entities(contacts, user)

        with self.assertNumQueries(0):
            contacts[0].position
            contacts[1].position
            contacts[0].civility
            contacts[1].civility

    def test_populate_entities_fields03(self):
        "Regular fields: invalid fields are removed automatically."
        user = self.login()

        cell1 = EntityCellRegularField.build(model=FakeContact, name='last_name')

        cell2 = EntityCellRegularField.build(model=FakeContact, name='first_name')
        cell2.value = 'invalid'  # filter_string='invalid__icontains'

        hf = HeaderFilter.create(pk='test-hf', name=u'Contact view',
                                 model=FakeContact, cells_desc=[cell1, cell2],
                                )

        create_contact = partial(FakeContact.objects.create, user=user)
        contacts = [create_contact(first_name='Nagate',  last_name='Tanikaze'),
                    create_contact(first_name='Shizuka', last_name='Hoshijiro'),
                   ]

        hf = self.refresh(hf)
        new_cells = hf.cells
        # TODO: assertCellsEqual
        self.assertEqual(1, len(new_cells))
        self.assertCellEqual(cell1, new_cells[0])

        with self.assertNoException():
            deserialized = jsonloads(hf.json_cells)

        self.assertEqual([{'type': 'regular_field', 'value': 'last_name'}],
                         deserialized
                        )

        with self.assertNoException():
            with self.assertNumQueries(0):
                hf.populate_entities(contacts, user)

    def test_populate_entities_fields04(self):
        "Regular fields: invalid subfields."
        self.login()

        cell1 = EntityCellRegularField.build(model=FakeContact, name='last_name')

        cell2 = EntityCellRegularField.build(model=FakeContact, name='user__username')
        cell2.value = 'user__invalid'  # filter_string='__icontains'

        hf = HeaderFilter.create(pk='test-hf', name=u'Contact view', model=FakeContact,
                                 cells_desc=[cell1, cell2],
                                )

        create_contact = partial(FakeContact.objects.create, user=self.user)
        create_contact(first_name='Nagate',  last_name='Tanikaze')
        create_contact(first_name='Shizuka', last_name='Hoshijiro')

        hf = self.refresh(hf)
        new_cells = hf.cells
        self.assertEqual(1, len(new_cells))
        self.assertCellEqual(cell1, hf.cells[0])

    def test_populate_entities_relations01(self):
        user = self.login()

        create_rt = RelationType.create
        loved = create_rt(('test-subject_love', u'Is loving'), ('test-object_love', u'Is loved by'))[1]
        hated = create_rt(('test-subject_hate', u'Is hating'), ('test-object_hate', u'Is hated by'))[1]

        hf = HeaderFilter.create(pk='test-hf', name=u'Contact view', model=FakeContact,
                                 cells_desc=[EntityCellRegularField.build(model=FakeContact, name='last_name'),
                                             EntityCellRelation(rtype=loved),
                                             EntityCellRelation(rtype=hated),
                                            ],
                                )

        create_contact = partial(FakeContact.objects.create, user=user)
        nagate  = create_contact(first_name='Nagate',  last_name='Tanikaze')
        shizuka = create_contact(first_name='Shizuka', last_name='Hoshijiro')
        izana   = create_contact(first_name='Izana',   last_name='Shinatose')
        norio   = create_contact(first_name='Norio',   last_name='Kunato')

        create_rel = partial(Relation.objects.create, user=user)
        create_rel(subject_entity=nagate,  type=loved, object_entity=izana)
        create_rel(subject_entity=nagate,  type=hated, object_entity=norio)
        create_rel(subject_entity=shizuka, type=loved, object_entity=norio)

        # NB: sometimes a query to get this CT is performed when the Relations
        # are retrieved. So we force the cache to be filled has he should be
        ContentType.objects.get_for_model(CremeEntity)

        with self.assertNumQueries(2):
            hf.populate_entities([nagate, shizuka], user)

        with self.assertNumQueries(0):
            r1 = nagate.get_relations(loved.id,  real_obj_entities=True)
            r2 = nagate.get_relations(hated.id,  real_obj_entities=True)
            r3 = shizuka.get_relations(loved.id, real_obj_entities=True)
            r4 = shizuka.get_relations(hated.id, real_obj_entities=True)

        with self.assertNumQueries(0):
            objs1 = [r.object_entity.get_real_entity() for r in r1]
            objs2 = [r.object_entity.get_real_entity() for r in r2]
            objs3 = [r.object_entity.get_real_entity() for r in r3]
            objs4 = [r.object_entity.get_real_entity() for r in r4]

        self.assertEqual([izana], objs1)
        self.assertEqual([norio], objs2)
        self.assertEqual([norio], objs3)
        self.assertEqual([],      objs4)

    def test_filterlist01(self):
        user = self.login()
        create_hf = partial(HeaderFilter.create, name='Orga view',
                            model=FakeOrganisation,
                            cells_desc=[EntityCellRegularField.build(
                                                model=FakeOrganisation, name='name',
                                            ),
                                       ],
                           )
        hf1 = create_hf(pk='test-hf_orga1')
        hf2 = create_hf(pk='test-hf_orga2', user=user)
        hf3 = create_hf(pk='test-hf_contact', model=FakeContact, name='Contact view')
        hf4 = create_hf(pk='test-hf_orga3', user=self.other_user)

        ct = self.orga_ct
        hfl = HeaderFilterList(ct, user)
        self.assertIn(hf1, hfl)
        self.assertIn(hf2, hfl)
        self.assertIn(hf4, hfl)
        self.assertEqual(hf1, hfl.select_by_id(hf1.id))
        self.assertEqual(hf2, hfl.select_by_id(hf2.id))
        self.assertEqual(hf2, hfl.select_by_id('unknown_id', hf2.id))

        self.assertEqual(hf1.can_view(user), (True, 'OK'))
        self.assertEqual(hf1.can_view(user, ct), (True, 'OK'))

        self.assertEqual(hf3.can_view(user, ct), (False, 'Invalid entity type'))
        self.assertNotIn(hf3, hfl)

    def test_filterlist02(self):
        "Private filters + not super user (+ team management)"
        user = self.login(is_superuser=False)
        other_user = self.other_user

        User = get_user_model()
        teammate = User.objects.create(username='fulbertc',
                                       email='fulbnert@creme.org', role=self.role,
                                       first_name='Fulbert', last_name='Creme',
                                      )

        tt_team = User.objects.create(username='TeamTitan', is_team=True)
        tt_team.teammates = [user, teammate]

        a_team = User.objects.create(username='A-Team', is_team=True)
        a_team.teammates = [other_user]

        cells = [EntityCellRegularField.build(model=FakeOrganisation, name='name')]

        def create_hf(id, **kwargs):
            return HeaderFilter.create(pk='test-hf_orga%s' % id,
                                       name='Orga view #%s' % id,
                                       model=FakeOrganisation, cells_desc=cells,
                                       **kwargs
                                      )

        hf01 = create_hf(1)
        hf02 = create_hf(2,  user=user)
        hf03 = create_hf(3,  user=other_user)
        hf04 = create_hf(4,  user=tt_team)
        hf05 = create_hf(5,  user=a_team)
        hf06 = create_hf(6,  user=user,       is_private=True, is_custom=True)
        hf07 = create_hf(7,  user=tt_team,    is_private=True, is_custom=True)
        hf08 = create_hf(8,  user=other_user, is_private=True, is_custom=True)
        hf09 = create_hf(9,  user=a_team,     is_private=True, is_custom=True)
        hf10 = create_hf(10, user=teammate,   is_private=True, is_custom=True)

        hfl = HeaderFilterList(self.orga_ct, user)
        self.assertIn(hf01, hfl)
        self.assertIn(hf02, hfl)
        self.assertIn(hf03, hfl)
        self.assertIn(hf04, hfl)
        self.assertIn(hf05, hfl)
        self.assertIn(hf06, hfl)
        self.assertIn(hf07, hfl)
        self.assertNotIn(hf08, hfl)
        self.assertNotIn(hf09, hfl)
        self.assertNotIn(hf10, hfl)

    def test_filterlist03(self):
        "Staff user -> can see all filters"
        user = self.login(is_staff=True)
        other_user = self.other_user

        cells = [EntityCellRegularField.build(model=FakeOrganisation, name='name')]

        def create_hf(id, **kwargs):
            return HeaderFilter.create(pk='test-hf_orga%s' % id,
                                       name='Orga view #%s' % id,
                                       model=FakeOrganisation, cells_desc=cells,
                                       **kwargs
                                      )

        hf1 = create_hf(1)

        with self.assertRaises(ValueError):
            create_hf(2,  user=user)

        hf3 = create_hf(3,  user=other_user)

        # This,one can not be seen by not staff users
        hf4 = create_hf(4,  user=other_user, is_private=True, is_custom=True)

        hfl = HeaderFilterList(self.orga_ct, user)
        self.assertIn(hf1, hfl)
        self.assertIn(hf3, hfl)
        self.assertIn(hf4, hfl)
