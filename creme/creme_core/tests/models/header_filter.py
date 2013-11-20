# -*- coding: utf-8 -*-

try:
    from functools import partial
    from json import loads as jsonloads, dumps as jsondumps

    from django.conf import settings
    from django.utils.translation import ugettext as _
    from django.contrib.contenttypes.models import ContentType

    from creme.creme_core.core.entity_cell import (EntityCellRegularField,
            EntityCellCustomField, EntityCellFunctionField, EntityCellRelation)
    from creme.creme_core.models import (RelationType, Relation, HeaderFilter,
            CustomField, CustomFieldEnumValue)
    from ..base import CremeTestCase

    from creme.persons.models import Contact, Organisation, Position, Sector
except Exception as e:
    print 'Error in <%s>: %s' % (__name__, e)


__all__ = ('HeaderFiltersTestCase',)


#TODO: move some tests to core.py (EntityCell)
class HeaderFiltersTestCase(CremeTestCase):
    @classmethod
    def setUpClass(cls):
        get_ct = ContentType.objects.get_for_model
        cls.contact_ct = get_ct(Contact)
        cls.orga_ct    = get_ct(Organisation)

        create_hf = partial(HeaderFilter.create, is_custom=True)
        cls.hf_contact = create_hf(pk='hftest_tests-hf_contact', name='Test Contact view', model=Contact)
        cls.hf_orga    = create_hf(pk='hftest_tests-hf_orga',    name='Test Orga view',    model=Organisation)

    def assertCellEqual(self, cell1, cell2):
        self.assertIs(cell1.__class__, cell2.__class__)
        self.assertEqual(cell1.value, cell2.value)

    def test_create01(self):
        self.login()

        name = 'Contact view'
        pk   = 'tests-hf_contact'
        hf   = HeaderFilter.create(pk=pk, name=name, model=Contact, is_custom=True)
        self.assertEqual(pk,   hf.pk)
        self.assertEqual(name, hf.name)
        self.assertIsNone(hf.user)
        self.assertEqual(self.contact_ct, hf.entity_type)
        self.assertIs(hf.is_custom, True)
        self.assertEqual('[]', hf.json_cells)
        self.assertFalse(hf.cells)

        hf.cells = [EntityCellRegularField.build(model=Contact, name='first_name')]
        hf.save()

        hf = self.refresh(hf)
        self.assertEqual(1, len(hf.cells))

        with self.assertNoException():
            deserialized = jsonloads(hf.json_cells)

        self.assertEqual([{'type': 'regular_field', 'value': 'first_name'}],
                         deserialized
                        )

        name += 'v2'
        hf = HeaderFilter.create(pk=pk, name=name, model=Organisation, is_custom=False, user=self.user)
        self.assertEqual(name,         hf.name)
        self.assertEqual(self.user,    hf.user)
        self.assertEqual(self.orga_ct, hf.entity_type)
        self.assertIs(hf.is_custom, False)
        self.assertFalse(hf.cells)

    def test_create02(self):
        "With cells"
        self.login()

        create_rtype = RelationType.create
        loves = create_rtype(('test-subject_love', u'Is loving'),
                             ('test-object_love',  u'Is loved by')
                            ) [0]
        likes = create_rtype(('test-subject_like', u'Is liking'),
                             ('test-object_like',  u'Is liked by')
                            ) [0]

        hf = HeaderFilter.create(pk='tests-hf_contact', name='Contact view',
                                 model=Contact, is_custom=True,
                                 cells_desc=[(EntityCellRegularField, {'name': 'last_name'}),
                                              EntityCellRelation(loves),
                                             (EntityCellRelation, {'rtype_id': likes.id}),
                                             None,
                                            ],
                                )

        cells = self.refresh(hf).cells
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

    def test_ct_cache(self):
        hf = HeaderFilter.create(pk='tests-hf_contact', name='Contact view',
                                 model=Contact, is_custom=True,
                                )

        with self.assertNumQueries(0):
            ContentType.objects.get_for_id(hf.entity_type_id)

        hf = self.refresh(hf)

        with self.assertNumQueries(0):
            hf.entity_type

    def test_build_4_field01(self):
        field_name = 'first_name'
        cell = EntityCellRegularField.build(model=Contact, name=field_name)
        self.assertIsInstance(cell, EntityCellRegularField)
        self.assertEqual(field_name,      cell.value)
        self.assertEqual(_('First name'), cell.title)
        self.assertIs(cell.has_a_filter, True)
        self.assertIs(cell.editable, True)
        self.assertIs(cell.sortable, True)
        self.assertEqual('first_name__icontains', cell.filter_string)

    def test_build_4_field02(self):
        "Date field"
        cell = EntityCellRegularField.build(model=Contact, name='birthday')
        self.assertEqual('birthday__range', cell.filter_string)
        self.assertEqual(settings.CSS_DEFAULT_LISTVIEW,     cell.listview_css_class)
        self.assertEqual(settings.CSS_DATE_HEADER_LISTVIEW, cell.header_listview_css_class)

    def test_build_4_field03(self):
        "Boolean field"
        cell = EntityCellRegularField.build(model=Organisation, name='subject_to_vat')
        self.assertEqual('subject_to_vat__creme-boolean', cell.filter_string)
        self.assertEqual(settings.CSS_DEFAULT_LISTVIEW, cell.listview_css_class)

    def test_build_4_field04(self):
        "ForeignKey"
        cell = EntityCellRegularField.build(model=Contact, name='position')
        self.assertEqual('position', cell.filter_string)
        self.assertEqual(settings.CSS_DEFAULT_LISTVIEW, cell.listview_css_class)

        cell = EntityCellRegularField.build(model=Contact, name='image')
        self.assertEqual('image__header_filter_search_field__icontains',
                         cell.filter_string
                        )
        self.assertEqual(settings.CSS_DEFAULT_LISTVIEW, cell.listview_css_class)

    def test_build_4_field05(self):
        "Basic ForeignKey subfield"
        cell = EntityCellRegularField.build(model=Contact, name='position__title')
        self.assertEqual('position__title__icontains', cell.filter_string)

        cell = EntityCellRegularField.build(model=Contact, name='image__name')
        self.assertEqual('image__name__icontains', cell.filter_string)

    def test_build_4_field06(self):
        "Date ForeignKey subfield"
        cell = EntityCellRegularField.build(model=Contact, name='image__created')
        self.assertEqual(u'%s - %s' % (_('Photograph'), _('Creation date')), cell.title)
        self.assertEqual('image__created__range', cell.filter_string)

    def test_build_4_field07(self):
        "ManyToMany"
        cell = EntityCellRegularField.build(model=Contact, name='language')
        self.assertIs(cell.has_a_filter, False)
        self.assertIs(cell.sortable, False)

        cell = EntityCellRegularField.build(model=Contact, name='language__name')
        self.assertIs(cell.has_a_filter, False)

    def test_build_4_field_errors(self):
        build = partial(EntityCellRegularField.build, model=Contact)
        self.assertIsNone(build(name='unknown_field'))
        self.assertIsNone(build(name='user__unknownfield'))

    def test_build_4_customfield01(self):
        "INT CustomField"
        name = u'Size (cm)'
        customfield = CustomField.objects.create(name=name, field_type=CustomField.INT,
                                                 content_type=self.contact_ct
                                                )

        cell = EntityCellCustomField(customfield)
        self.assertIsInstance(cell, EntityCellCustomField)
        self.assertEqual(str(customfield.id), cell.value)
        self.assertEqual(name,                cell.title)
        self.assertIs(cell.has_a_filter, True)
        self.assertIs(cell.editable,     False)
        self.assertIs(cell.sortable,     False)
        self.assertEqual('customfieldinteger__value__icontains', cell.filter_string)
        self.assertEqual(settings.CSS_NUMBER_LISTVIEW,         cell.listview_css_class)
        self.assertEqual(settings.CSS_DEFAULT_HEADER_LISTVIEW, cell.header_listview_css_class)

        cell = EntityCellCustomField.build(Contact, customfield.id)
        self.assertIsInstance(cell, EntityCellCustomField)
        self.assertEqual(str(customfield.id), cell.value)

        self.assertIsNone(EntityCellCustomField.build(Contact, 1000))

    def test_build_4_customfield02(self):
        "FLOAT CustomField"
        customfield = CustomField.objects.create(name=u'Weight', field_type=CustomField.FLOAT,
                                                 content_type=self.contact_ct
                                                )

        cell = EntityCellCustomField(customfield)
        self.assertEqual('customfieldfloat__value__icontains', cell.filter_string)
        self.assertEqual(settings.CSS_NUMBER_LISTVIEW,         cell.listview_css_class)
        self.assertEqual(settings.CSS_DEFAULT_HEADER_LISTVIEW, cell.header_listview_css_class)

    def test_build_4_customfield03(self):
        "DATE CustomField"
        customfield = CustomField.objects.create(name=u'Day', field_type=CustomField.DATETIME,
                                                 content_type=self.contact_ct
                                                )

        cell = EntityCellCustomField(customfield)
        self.assertEqual('customfielddatetime__value__range', cell.filter_string)
        self.assertEqual(settings.CSS_DEFAULT_LISTVIEW,     cell.listview_css_class)
        self.assertEqual(settings.CSS_DATE_HEADER_LISTVIEW, cell.header_listview_css_class)


    def test_build_4_customfield04(self):
        "BOOL CustomField"
        customfield = CustomField.objects.create(name=u'Is fun ?', field_type=CustomField.BOOL,
                                                 content_type=self.contact_ct
                                                )

        cell = EntityCellCustomField(customfield)
        self.assertEqual('customfieldboolean__value__creme-boolean', cell.filter_string)
        self.assertEqual(settings.CSS_DEFAULT_LISTVIEW,        cell.listview_css_class)
        self.assertEqual(settings.CSS_DEFAULT_HEADER_LISTVIEW, cell.header_listview_css_class)

    def test_build_4_customfield05(self):
        "ENUM CustomField"
        customfield = CustomField.objects.create(name='Eva', field_type=CustomField.ENUM,
                                                 content_type=self.contact_ct
                                                )

        create_enumvalue = partial(CustomFieldEnumValue.objects.create, custom_field=customfield)
        create_enumvalue(value='Eva-00')
        create_enumvalue(value='Eva-01')

        cell = EntityCellCustomField(customfield)
        self.assertEqual('customfieldenum__value__exact', cell.filter_string)
        self.assertEqual(settings.CSS_DEFAULT_LISTVIEW,        cell.listview_css_class)
        self.assertEqual(settings.CSS_DEFAULT_HEADER_LISTVIEW, cell.header_listview_css_class)

    def test_build_4_customfield06(self):
        "MULTI_ENUM CustomField"
        customfield = CustomField.objects.create(name='Eva', field_type=CustomField.MULTI_ENUM,
                                                 content_type=self.contact_ct
                                                )

        create_enumvalue = partial(CustomFieldEnumValue.objects.create, custom_field=customfield)
        create_enumvalue(value='Eva-00')
        create_enumvalue(value='Eva-01')

        cell = EntityCellCustomField(customfield)
        self.assertEqual('customfieldmultienum__value__exact', cell.filter_string)
        self.assertEqual(settings.CSS_DEFAULT_LISTVIEW,        cell.listview_css_class)
        self.assertEqual(settings.CSS_DEFAULT_HEADER_LISTVIEW, cell.header_listview_css_class)

    def test_build_4_relation(self):
        loves = RelationType.create(('test-subject_love', u'Is loving'),
                                    ('test-object_love',  u'Is loved by')
                                   ) [0]
        cell = EntityCellRelation(rtype=loves)
        self.assertIsInstance(cell, EntityCellRelation)
        self.assertEqual(str(loves.id),   cell.value)
        self.assertEqual(loves.predicate, cell.title)
        self.assertIs(cell.has_a_filter, True)
        self.assertIs(cell.editable,     False)
        self.assertIs(cell.sortable,     False)
        self.assertEqual('',    cell.filter_string)
        self.assertEqual(loves, cell.relation_type)
        self.assertEqual(settings.CSS_DEFAULT_LISTVIEW,        cell.listview_css_class)
        self.assertEqual(settings.CSS_DEFAULT_HEADER_LISTVIEW, cell.header_listview_css_class)

    def test_build_4_functionfield(self):
        name = 'get_pretty_properties'
        funfield = Contact.function_fields.get(name)
        self.assertIsNotNone(funfield)

        cell = EntityCellFunctionField(func_field=funfield)
        self.assertIsInstance(cell, EntityCellFunctionField)
        self.assertEqual(name,            cell.value)
        self.assertEqual(unicode(funfield.verbose_name), cell.title)
        self.assertIs(cell.has_a_filter, False) #TODO: test with a filterable FunctionField
        self.assertIs(cell.editable,     False)
        self.assertIs(cell.sortable,     False)
        self.assertIs(cell.is_hidden,    False)
        self.assertEqual('', cell.filter_string)
        self.assertEqual(settings.CSS_DEFAULT_LISTVIEW,        cell.listview_css_class)
        self.assertEqual(settings.CSS_DEFAULT_HEADER_LISTVIEW, cell.header_listview_css_class)

        cell = EntityCellFunctionField.build(Contact, func_field_name=name)
        self.assertIsInstance(cell, EntityCellFunctionField)
        self.assertEqual(name, cell.value)

        self.assertIsNone(EntityCellFunctionField.build(Contact, func_field_name='invalid'))

    def test_cells_property01(self):
        build_cell = partial(EntityCellRegularField.build, model=Contact)
        cells = [build_cell(name=fn) for fn in ('first_name', 'last_name')]
        hf = HeaderFilter.create(pk='test-hf01', name=u'Contact view', model=Contact,
                                 cells_desc=cells,
                                )

        cells.append(build_cell(name='phone'))
        hf.cells = cells
        hf.save()
        self.assertEqual(3, len(self.refresh(hf).cells))

    def test_cells_property02(self):
        "None value are ignored"
        hf = HeaderFilter.create(pk='test-hf01', name=u'Contact view', model=Contact)

        build_cell = partial(EntityCellRegularField.build, model=Contact)
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
        user = self.user

        ffield_name = 'get_pretty_properties'
        rfield_name = 'last_name'
        hf = HeaderFilter.create(pk='test-hf', name=u'Contact view', model=Contact,
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

        #---------------------------------------------------------------------
        HeaderFilter.objects.filter(id=hf.id) \
                            .update(json_cells=jsondumps([{'type': 'function_field'},
                                                          {'type': 'regular_field', 'value': rfield_name},
                                                         ]))

        hf = self.refresh(hf)
        cells = hf.cells
        self.assertEqual(1, len(cells))
        self.assertIsInstance(cells[0], EntityCellRegularField)

        #---------------------------------------------------------------------
        HeaderFilter.objects.filter(id=hf.id) \
                            .update(json_cells=jsondumps([{'type': 'function_field'}, #not 'value' key
                                                          {'type': 'regular_field', 'value': rfield_name},
                                                         ]))
        hf = self.refresh(hf)
        cells = hf.cells
        self.assertEqual(1, len(cells))
        self.assertIsInstance(cells[0], EntityCellRegularField)

        #---------------------------------------------------------------------
        HeaderFilter.objects.filter(id=hf.id) \
                            .update(json_cells=jsondumps([{}, #no 'type' key
                                                          {'type': 'regular_field', 'value': rfield_name},
                                                         ]))
        hf = self.refresh(hf)
        cells = hf.cells
        self.assertEqual(1, len(cells))
        self.assertIsInstance(cells[0], EntityCellRegularField)

        #---------------------------------------------------------------------
        HeaderFilter.objects.filter(id=hf.id).update(json_cells=jsondumps([1])) #not a dict
        self.assertEqual(0, len(self.refresh(hf).cells))

        #---------------------------------------------------------------------
        HeaderFilter.objects.filter(id=hf.id).update(json_cells=jsondumps(1)) #not a list
        self.assertEqual(0, len(self.refresh(hf).cells))

    def test_populate_entities_fields01(self):
        "Regular fields: no FK"
        self.login()
        user = self.user
        hf = HeaderFilter.create(pk='test-hf', name=u'Contact view', model=Contact,
                                 cells_desc=[(EntityCellRegularField, {'name': 'last_name'}),
                                             (EntityCellRegularField, {'name': 'first_name'}),
                                            ])

        pos = Position.objects.create(title='Pilot')
        create_contact = partial(Contact.objects.create, user=user, position_id=pos.id)
        contacts = [create_contact(first_name='Nagate',  last_name='Tanikaze'),
                    create_contact(first_name='Shizuka', last_name='Hoshijiro'),
                   ]

        with self.assertNumQueries(0):
            hf.populate_entities(contacts, user)

        with self.assertNumQueries(1):
            contacts[0].position

    def test_populate_entities_fields02(self):
        "Regular fields: FK"
        self.login()
        user = self.user
        build = partial(EntityCellRegularField.build, model=Contact)
        hf = HeaderFilter.create(pk='test-hf', name=u'Contact view', model=Contact,
                                 cells_desc=[build(name='last_name'), build(name='first_name'),
                                             build(name='position'),  build(name='sector__title'),
                                            ],
                                )

        pos = Position.objects.create(title='Pilot')
        sector = Sector.objects.create(title='Army')
        create_contact = partial(Contact.objects.create, user=user, position_id=pos.id, sector_id=sector.id)
        contacts = [create_contact(first_name='Nagate',  last_name='Tanikaze'),
                    create_contact(first_name='Shizuka', last_name='Hoshijiro'),
                   ]

        with self.assertNumQueries(2):
            hf.populate_entities(contacts, user)

        with self.assertNumQueries(0):
            contacts[0].position
            contacts[1].position
            contacts[0].sector
            contacts[1].sector

    def test_populate_entities_fields03(self):
        "Regular fields: invalid fields are removed automatically."
        self.login()
        user = self.user

        cell1 = EntityCellRegularField.build(model=Contact, name='last_name')

        cell2 = EntityCellRegularField.build(model=Contact, name='first_name')
        cell2.value = 'invalid' #filter_string='invalid__icontains',

        hf = HeaderFilter.create(pk='test-hf', name=u'Contact view',
                                 model=Contact, cells_desc=[cell1, cell2],
                                )

        create_contact = partial(Contact.objects.create, user=user)
        contacts = [create_contact(first_name='Nagate',  last_name='Tanikaze'),
                    create_contact(first_name='Shizuka', last_name='Hoshijiro'),
                   ]

        hf = self.refresh(hf)
        new_cells = hf.cells
        #TODO: assertCellsEqual
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

        cell1 = EntityCellRegularField.build(model=Contact, name='last_name')

        cell2 = EntityCellRegularField.build(model=Contact, name='user__username')
        cell2.value = 'user__invalid' #filter_string='__icontains',

        hf = HeaderFilter.create(pk='test-hf', name=u'Contact view', model=Contact,
                                 cells_desc=[cell1, cell2],
                                )

        create_contact = partial(Contact.objects.create, user=self.user)
        create_contact(first_name='Nagate',  last_name='Tanikaze')
        create_contact(first_name='Shizuka', last_name='Hoshijiro')

        hf = self.refresh(hf)
        new_cells = hf.cells
        self.assertEqual(1, len(new_cells))
        self.assertCellEqual(cell1, hf.cells[0])

    def test_populate_entities_relations01(self):
        self.login()
        user = self.user

        create_rt = RelationType.create
        loved = create_rt(('test-subject_love', u'Is loving'), ('test-object_love', u'Is loved by'))[1]
        hated = create_rt(('test-subject_hate', u'Is hating'), ('test-object_hate', u'Is hated by'))[1]

        hf = HeaderFilter.create(pk='test-hf', name=u'Contact view', model=Contact,
                                 cells_desc=[EntityCellRegularField.build(model=Contact, name='last_name'),
                                             EntityCellRelation(rtype=loved),
                                             EntityCellRelation(rtype=hated),
                                            ],
                                )

        create_contact = partial(Contact.objects.create, user=user)
        nagate  = create_contact(first_name='Nagate',  last_name='Tanikaze')
        shizuka = create_contact(first_name='Shizuka', last_name='Hoshijiro')
        izana   = create_contact(first_name='Izana',   last_name='Shinatose')
        norio   = create_contact(first_name='Norio',   last_name='Kunato')

        create_rel = partial(Relation.objects.create, user=user)
        create_rel(subject_entity=nagate,  type=loved, object_entity=izana)
        create_rel(subject_entity=nagate,  type=hated, object_entity=norio)
        create_rel(subject_entity=shizuka, type=loved, object_entity=norio)

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

    #TODO: test for other types: EntityCellCustomField, EntityCellFunctionField
