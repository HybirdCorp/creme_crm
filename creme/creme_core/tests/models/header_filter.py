# -*- coding: utf-8 -*-

try:
    from functools import partial

    from django.utils.translation import ugettext as _
    from django.contrib.contenttypes.models import ContentType

    from creme_core.models import RelationType, Relation, CustomField, CustomFieldEnumValue
    from creme_core.models.header_filter import (HeaderFilter, HeaderFilterItem,
                                                 HFI_FIELD, HFI_CUSTOM, HFI_RELATION, HFI_FUNCTION
                                                )
    from creme_core.tests.base import CremeTestCase

    from persons.models import Contact, Organisation, Position, Sector
except Exception as e:
    print 'Error in <%s>: %s' % (__name__, e)


__all__ = ('HeaderFiltersTestCase',)


class HeaderFiltersTestCase(CremeTestCase):
    @classmethod
    def setUpClass(cls):
        get_ct = ContentType.objects.get_for_model
        cls.contact_ct = get_ct(Contact)
        cls.orga_ct    = get_ct(Organisation)

    def test_create(self):
        self.login()

        name = 'Contact view'
        pk   = 'tests-hf_contact'
        hf   = HeaderFilter.create(pk=pk, name=name, model=Contact, is_custom=True)
        self.assertEqual(pk, hf.pk)
        self.assertEqual(name, hf.name)
        self.assertIsNone(hf.user)
        self.assertEqual(self.contact_ct, hf.entity_type)
        self.assertIs(hf.is_custom, True)

        hf.set_items([HeaderFilterItem.build_4_field(model=Contact, name='first_name')])
        name += 'v2'
        hf = HeaderFilter.create(pk=pk, name=name, model=Organisation, is_custom=False, user=self.user)
        self.assertEqual(name,         hf.name)
        self.assertEqual(self.user,    hf.user)
        self.assertEqual(self.orga_ct, hf.entity_type)
        self.assertIs(hf.is_custom, False)

    def test_build_4_field01(self):
        field_name = 'first_name'
        hfi = HeaderFilterItem.build_4_field(model=Contact, name=field_name)
        self.assertIsInstance(hfi, HeaderFilterItem)
        self.assertEqual(field_name,      hfi.name)
        self.assertEqual(_('First name'), hfi.title)
        self.assertEqual(HFI_FIELD,       hfi.type)
        self.assertIs(hfi.has_a_filter, True)
        self.assertIs(hfi.editable, True)
        self.assertIs(hfi.sortable, True)
        self.assertEqual('first_name__icontains', hfi.filter_string)

    def test_build_4_field02(self):
        "Date field"
        hfi = HeaderFilterItem.build_4_field(model=Contact, name='birthday')
        self.assertEqual('birthday__range', hfi.filter_string)

    def test_build_4_field03(self):
        "Boolean field"
        hfi = HeaderFilterItem.build_4_field(model=Organisation, name='subject_to_vat')
        self.assertEqual('subject_to_vat__creme-boolean', hfi.filter_string)

    def test_build_4_field04(self):
        "ForeignKey"
        hfi = HeaderFilterItem.build_4_field(model=Contact, name='position')
        self.assertEqual('position', hfi.filter_string)

    def test_build_4_field05(self):
        "Basic ForeignKey subfield"
        hfi = HeaderFilterItem.build_4_field(model=Contact, name='position__title')
        self.assertEqual('position__title__icontains', hfi.filter_string)

    def test_build_4_field06(self):
        "Date ForeignKey subfield"
        hfi = HeaderFilterItem.build_4_field(model=Contact, name='image__created')
        self.assertEqual(u'%s - %s' % (_('Photograph'), _('Creation date')), hfi.title)
        self.assertEqual('image__created__range', hfi.filter_string)

    def test_build_4_field07(self):
        "ManyToMany"
        hfi = HeaderFilterItem.build_4_field(model=Contact, name='language')
        self.assertIs(hfi.has_a_filter, True)

        hfi = HeaderFilterItem.build_4_field(model=Contact, name='language__name')
        self.assertIs(hfi.has_a_filter, False)

    def test_build_4_field_errors(self):
        #self.assertRaises(HeaderFilterItem.ValueError, HeaderFilterItem.build_4_field, model=Contact, name='unknown_field')
        build = partial(HeaderFilterItem.build_4_field, model=Contact)
        self.assertIsNone(build(name='unknown_field'))
        self.assertIsNone(build(name='user__unknownfield'))

    def test_build_4_customfield01(self):
        "INT CustomField"
        name = u'Size (cm)'
        customfield = CustomField.objects.create(name=name, field_type=CustomField.INT,
                                                 content_type=self.contact_ct
                                                )

        hfi = HeaderFilterItem.build_4_customfield(customfield=customfield)
        self.assertIsInstance(hfi, HeaderFilterItem)
        self.assertEqual(str(customfield.id), hfi.name)
        self.assertEqual(name,                hfi.title)
        self.assertEqual(HFI_CUSTOM,          hfi.type)
        self.assertIs(hfi.has_a_filter, True)
        self.assertIs(hfi.editable,     False)
        self.assertIs(hfi.sortable,     False)
        self.assertEqual('customfieldinteger__value__icontains', hfi.filter_string)

    def test_build_4_customfield02(self):
        "FLOAT CustomField"
        customfield = CustomField.objects.create(name=u'Weight', field_type=CustomField.FLOAT,
                                                 content_type=self.contact_ct
                                                )

        hfi = HeaderFilterItem.build_4_customfield(customfield=customfield)
        self.assertEqual('customfieldfloat__value__icontains', hfi.filter_string)

    def test_build_4_customfield03(self):
        "DATE CustomField"
        customfield = CustomField.objects.create(name=u'Day', field_type=CustomField.DATE,
                                                 content_type=self.contact_ct
                                                )

        hfi = HeaderFilterItem.build_4_customfield(customfield=customfield)
        self.assertEqual('customfielddatetime__value__range', hfi.filter_string)

    def test_build_4_customfield04(self):
        "BOOL CustomField"
        customfield = CustomField.objects.create(name=u'Is fun ?', field_type=CustomField.BOOL,
                                                 content_type=self.contact_ct
                                                )

        hfi = HeaderFilterItem.build_4_customfield(customfield=customfield)
        self.assertEqual('customfieldboolean__value__creme-boolean', hfi.filter_string)

    def test_build_4_customfield05(self):
        "ENUM CustomField"
        customfield = CustomField.objects.create(name='Eva', field_type=CustomField.ENUM,
                                                 content_type=self.contact_ct
                                                )

        create_enumvalue = partial(CustomFieldEnumValue.objects.create, custom_field=customfield)
        create_enumvalue(value='Eva-00')
        create_enumvalue(value='Eva-01')

        hfi = HeaderFilterItem.build_4_customfield(customfield=customfield)
        self.assertEqual('customfieldenum__value__exact', hfi.filter_string)

    def test_build_4_customfield06(self):
        "MULTI_ENUM CustomField"
        customfield = CustomField.objects.create(name='Eva', field_type=CustomField.MULTI_ENUM,
                                                 content_type=self.contact_ct
                                                )

        create_enumvalue = partial(CustomFieldEnumValue.objects.create, custom_field=customfield)
        create_enumvalue(value='Eva-00')
        create_enumvalue(value='Eva-01')

        hfi = HeaderFilterItem.build_4_customfield(customfield=customfield)
        self.assertEqual('customfieldmultienum__value__exact', hfi.filter_string)

    def test_build_4_relation(self):
        loves, loved = RelationType.create(('test-subject_love', u'Is loving'),
                                           ('test-object_love',  u'Is loved by')
                                          )
        hfi = HeaderFilterItem.build_4_relation(rtype=loves)
        self.assertIsInstance(hfi, HeaderFilterItem)
        self.assertEqual(str(loves.id),   hfi.name)
        self.assertEqual(loves.predicate, hfi.title)
        self.assertEqual(HFI_RELATION,    hfi.type)
        self.assertIs(hfi.has_a_filter, True)
        self.assertIs(hfi.editable,     False)
        self.assertIs(hfi.sortable,     False)
        self.assertEqual('',    hfi.filter_string)
        self.assertEqual(loves, hfi.relation_predicat)

    def test_build_4_functionfield(self):
        name = 'get_pretty_properties'
        funfield = Contact.function_fields.get(name)
        self.assertIsNotNone(funfield)

        hfi = HeaderFilterItem.build_4_functionfield(func_field=funfield)
        self.assertIsInstance(hfi, HeaderFilterItem)
        self.assertEqual(name, hfi.name)
        self.assertEqual(unicode(funfield.verbose_name), hfi.title)
        self.assertEqual(HFI_FUNCTION,    hfi.type)
        self.assertIs(hfi.has_a_filter, False) #TODO: test with a filterable FunctionField
        self.assertIs(hfi.editable,     False)
        self.assertIs(hfi.sortable,     False)
        self.assertIs(hfi.is_hidden,    False)
        self.assertEqual('', hfi.filter_string)

    def test_set_items01(self):
        hfilter = HeaderFilter.create(pk='test-hf01', name=u'Contact view', model=Contact)

        build_item = partial(HeaderFilterItem.build_4_field, model=Contact)
        hf_items = [build_item(name=fn) for fn in ('first_name', 'last_name')]

        hfilter.set_items(hf_items)
        hfilter = self.refresh(hfilter) #refresh caches
        items = list(hfilter.header_filter_items.all())
        self.assertEqual(hf_items, items)
        self.assertEqual([1, 2],   [hfi.order for hfi in items])

        with self.assertNumQueries(1):
            hfilter.entity_type

        with self.assertNumQueries(1):
            prop_items = hfilter.items

        self.assertEqual(hf_items, prop_items)

        with self.assertNumQueries(0):
            prop_items = hfilter.items

    def test_set_items02(self):
        "None value are ignored"
        hfilter = HeaderFilter.create(pk='test-hf01', name=u'Contact view', model=Contact)

        build_item = partial(HeaderFilterItem.build_4_field, model=Contact)
        hfi01 = build_item(name='first_name')
        hfi02 = build_item(name='invalid_field')
        hfi03 = build_item(name='last_name')
        self.assertIsNone(hfi02)

        hfilter.set_items([hfi01, hfi02, hfi03])

        hfilter = self.refresh(hfilter)
        items = list(hfilter.header_filter_items.all())
        valid_items = [hfi01, hfi03]
        self.assertEqual(valid_items, items)
        self.assertEqual([1, 2],      [hfi.order for hfi in items])
        self.assertEqual(valid_items, hfilter.items)

    def test_delete_relationtype01(self):
        self.login()

        create_rt = RelationType.create
        loves, loved = create_rt(('test-subject_love', u'Is loving'), ('test-object_love',  u'Is loved by'))
        hates, hated = create_rt(('test-subject_hate', u'Is hating'), ('test-object_hate',  u'Is hated by'))

        hf = HeaderFilter.create(pk='test-hf01', name=u'Contact view', model=Contact)
        hfi01 = HeaderFilterItem.build_4_field(model=Contact, name='last_name')
        hfi02 = HeaderFilterItem.build_4_relation(rtype=loves)
        hfi03 = HeaderFilterItem.build_4_relation(rtype=loved)
        hfi04 = HeaderFilterItem.build_4_relation(rtype=hates)
        hf.set_items([hfi01, hfi02, hfi03, hfi04])
        self.assertEqual(4, hf.header_filter_items.count())

        loves.delete()
        self.assertFalse(RelationType.objects.filter(pk=loves.id))
        self.assertEqual([hfi01, hfi04], list(hf.header_filter_items.all()))

    def test_delete_customfield(self):
        self.login()

        create_cfield = partial(CustomField.objects.create,
                                content_type=self.contact_ct, field_type=CustomField.INT
                               )
        custom_field01 = create_cfield(name='Size (cm)')
        custom_field02 = create_cfield(name='IQ')

        hf = HeaderFilter.create(pk='test-hf01', name=u'Contact view', model=Contact)
        hfi01 = HeaderFilterItem.build_4_field(model=Contact, name='last_name')
        hfi02 = HeaderFilterItem.build_4_customfield(customfield=custom_field01)
        hfi03 = HeaderFilterItem.build_4_customfield(customfield=custom_field02)
        hf.set_items([hfi01, hfi02, hfi03])
        self.assertEqual(3, hf.header_filter_items.count())

        custom_field01.delete()
        self.assertEqual([hfi01, hfi03], list(hf.header_filter_items.all()))

    def test_populate_entities_fields01(self):
        "Regular fields: no FK"
        self.login()
        user = self.user
        hf = HeaderFilter.create(pk='test-hf', name=u'Contact view', model=Contact)

        build = partial(HeaderFilterItem.build_4_field, model=Contact)
        hf.set_items([build(name='last_name'), build(name='first_name')])

        pos = Position.objects.create(title='Pilot')
        create_contact = partial(Contact.objects.create, user=user, position_id=pos.id)
        contacts = [create_contact(first_name='Nagate',  last_name='Tanikaze'),
                    create_contact(first_name='Shizuka', last_name='Hoshijiro'),
                   ]

        hf.items #fill cache TODO: set_items fills the cache ??

        with self.assertNumQueries(0):
            hf.populate_entities(contacts, user)

        with self.assertNumQueries(1):
            contacts[0].position

    def test_populate_entities_fields02(self):
        "Regular fields: FK"
        self.login()
        user = self.user
        hf = HeaderFilter.create(pk='test-hf', name=u'Contact view', model=Contact)

        build = partial(HeaderFilterItem.build_4_field, model=Contact)
        hf.set_items([build(name='last_name'), build(name='first_name'),
                      build(name='position'),  build(name='sector__title'),
                     ]
                    )

        pos = Position.objects.create(title='Pilot')
        sector = Sector.objects.create(title='Army')
        create_contact = partial(Contact.objects.create, user=user, position_id=pos.id, sector_id=sector.id)
        contacts = [create_contact(first_name='Nagate',  last_name='Tanikaze'),
                    create_contact(first_name='Shizuka', last_name='Hoshijiro'),
                   ]

        hf.items #fill cache

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
        hf = HeaderFilter.create(pk='test-hf', name=u'Contact view', model=Contact)

        hfi1 = HeaderFilterItem.build_4_field(model=Contact, name='last_name')
        hfi2 = HeaderFilterItem(name='invalid', title='Invalid', type=HFI_FIELD,
                                 has_a_filter=True, editable=True,
                                 filter_string='__icontains',
                                )
        hf.set_items([hfi1, hfi2])

        create_contact = partial(Contact.objects.create, user=user)
        contacts = [create_contact(first_name='Nagate',  last_name='Tanikaze'),
                    create_contact(first_name='Shizuka', last_name='Hoshijiro'),
                   ]

        self.assertEqual([hfi1], hf.items)
        self.assertFalse(HeaderFilterItem.objects.filter(pk=hfi2.pk).exists())

        with self.assertNoException():
            with self.assertNumQueries(0):
                hf.populate_entities(contacts, user)

    def test_populate_entities_fields04(self):
        "Regular fields: invalid subfields."
        self.login()
        user = self.user
        hf = HeaderFilter.create(pk='test-hf', name=u'Contact view', model=Contact)

        hfi1 = HeaderFilterItem.build_4_field(model=Contact, name='last_name')
        hfi2 = HeaderFilterItem(name='user__invalid', title='Invalid user field',
                                type=HFI_FIELD,
                                has_a_filter=True, editable=True,
                                filter_string='__icontains',
                               )
        hf.set_items([hfi1, hfi2])

        create_contact = partial(Contact.objects.create, user=user)
        contacts = [create_contact(first_name='Nagate',  last_name='Tanikaze'),
                    create_contact(first_name='Shizuka', last_name='Hoshijiro'),
                   ]

        self.assertEqual([hfi1], hf.items)
        self.assertFalse(HeaderFilterItem.objects.filter(pk=hfi2.pk).exists())

    def test_populate_entities_relations01(self):
        self.login()
        user = self.user

        create_rt = RelationType.create
        loved = create_rt(('test-subject_love', u'Is loving'), ('test-object_love', u'Is loved by'))[1]
        hated = create_rt(('test-subject_hate', u'Is hating'), ('test-object_hate', u'Is hated by'))[1]

        hf = HeaderFilter.create(pk='test-hf', name=u'Contact view', model=Contact)
        hf.set_items([HeaderFilterItem.build_4_field(model=Contact, name='last_name'),
                      HeaderFilterItem.build_4_relation(rtype=loved),
                      HeaderFilterItem.build_4_relation(rtype=hated),
                     ])

        create_contact = partial(Contact.objects.create, user=user)
        nagate  = create_contact(first_name='Nagate',  last_name='Tanikaze')
        shizuka = create_contact(first_name='Shizuka', last_name='Hoshijiro')
        izana   = create_contact(first_name='Izana',   last_name='Shinatose')
        norio   = create_contact(first_name='Norio',   last_name='Kunato')

        create_rel = partial(Relation.objects.create, user=user)
        create_rel(subject_entity=nagate,  type=loved, object_entity=izana)
        create_rel(subject_entity=nagate,  type=hated, object_entity=norio)
        create_rel(subject_entity=shizuka, type=loved, object_entity=norio)

        hf.items #fill cache

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

    #TODO: test for other types: HFI_CUSTOM, HFI_FUNCTION
