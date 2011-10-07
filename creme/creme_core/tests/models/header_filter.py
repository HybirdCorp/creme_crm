# -*- coding: utf-8 -*-

try:
    from django.utils.translation import ugettext as _
    from django.contrib.contenttypes.models import ContentType

    from creme_core.models import CustomField, CustomFieldEnumValue
    from creme_core.models.header_filter import *
    from creme_core.tests.base import CremeTestCase

    from persons.models import Contact, Organisation
except Exception as e:
    print 'Error:', e


__all__ = ('HeaderFiltersTestCase',)


class HeaderFiltersTestCase(CremeTestCase):
    def test_create(self):
        self.login()

        name = 'Contact view'
        pk   = 'tests-hf_contact'
        hf   = HeaderFilter.create(pk=pk, name=name, model=Contact, is_custom=True)
        self.assertEqual(pk, hf.pk)
        self.assertEqual(name, hf.name)
        self.assertIsNone(hf.user)
        self.assertEqual(ContentType.objects.get_for_model(Contact).id, hf.entity_type.id)
        self.assertIs(hf.is_custom, True)

        hf.set_items([HeaderFilterItem.build_4_field(model=Contact, name='first_name')])
        name += 'v2'
        hf = HeaderFilter.create(pk=pk, name=name, model=Organisation, is_custom=False, user=self.user)
        self.assertEqual(name, hf.name)
        self.assertEqual(self.user, hf.user)
        self.assertEqual(ContentType.objects.get_for_model(Organisation), hf.entity_type)
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

    def test_build_4_field02(self): #date field
        hfi = HeaderFilterItem.build_4_field(model=Contact, name='birthday')
        self.assertEqual('birthday__range', hfi.filter_string)

    def test_build_4_field03(self): #boolean field
        hfi = HeaderFilterItem.build_4_field(model=Organisation, name='subject_to_vat')
        self.assertEqual('subject_to_vat__creme-boolean', hfi.filter_string)

    def test_build_4_field04(self): #fk
        hfi = HeaderFilterItem.build_4_field(model=Contact, name='position')
        self.assertEqual('position', hfi.filter_string)

    def test_build_4_field05(self): #basic fk subfield
        hfi = HeaderFilterItem.build_4_field(model=Contact, name='position__title')
        self.assertEqual('position__title__icontains', hfi.filter_string)

    def test_build_4_field06(self): #date fk subfield
        hfi = HeaderFilterItem.build_4_field(model=Contact, name='image__created')
        self.assertEqual(_('Photograph') + u' - ' + _('Creation date'), hfi.title)
        self.assertEqual('image__created__range', hfi.filter_string)

    def test_build_4_field07(self): #m2m
        hfi = HeaderFilterItem.build_4_field(model=Contact, name='language')
        self.assertIs(hfi.has_a_filter, True)

        hfi = HeaderFilterItem.build_4_field(model=Contact, name='language__name')
        self.assertIs(hfi.has_a_filter, False)

    def test_build_4_field_errors(self):
        self.assertRaises(HeaderFilterItem.ValueError, HeaderFilterItem.build_4_field, model=Contact, name='unknown_field')

    def test_build_4_customfield01(self): #INT
        name = u'Size (cm)'
        customfield = CustomField.objects.create(name=name, field_type=CustomField.INT,
                                                  content_type=ContentType.objects.get_for_model(Contact)
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

    def test_build_4_customfield02(self): #FLOAT
        customfield = CustomField.objects.create(name=u'Weight', field_type=CustomField.FLOAT,
                                                  content_type=ContentType.objects.get_for_model(Contact)
                                                 )

        hfi = HeaderFilterItem.build_4_customfield(customfield=customfield)
        self.assertEqual('customfieldfloat__value__icontains', hfi.filter_string)

    def test_build_4_customfield03(self): #DATE
        customfield = CustomField.objects.create(name=u'Day', field_type=CustomField.DATE,
                                                  content_type=ContentType.objects.get_for_model(Contact)
                                                 )

        hfi = HeaderFilterItem.build_4_customfield(customfield=customfield)
        self.assertEqual('customfielddatetime__value__range', hfi.filter_string)

    def test_build_4_customfield04(self): #BOOL
        customfield = CustomField.objects.create(name=u'Is fun ?', field_type=CustomField.BOOL,
                                                  content_type=ContentType.objects.get_for_model(Contact)
                                                 )

        hfi = HeaderFilterItem.build_4_customfield(customfield=customfield)
        self.assertEqual('customfieldboolean__value__creme-boolean', hfi.filter_string)

    def test_build_4_customfield05(self): #ENUM
        customfield = CustomField.objects.create(name='Eva', field_type=CustomField.ENUM,
                                                 content_type=ContentType.objects.get_for_model(Contact)
                                                )
        CustomFieldEnumValue.objects.create(custom_field=customfield, value='Eva-00')
        CustomFieldEnumValue.objects.create(custom_field=customfield, value='Eva-01')

        hfi = HeaderFilterItem.build_4_customfield(customfield=customfield)
        self.assertEqual('customfieldenum__value__exact', hfi.filter_string)

    def test_build_4_customfield06(self): #MULTI_ENUM
        customfield = CustomField.objects.create(name='Eva', field_type=CustomField.MULTI_ENUM,
                                                 content_type=ContentType.objects.get_for_model(Contact)
                                                )
        CustomFieldEnumValue.objects.create(custom_field=customfield, value='Eva-00')
        CustomFieldEnumValue.objects.create(custom_field=customfield, value='Eva-01')

        hfi = HeaderFilterItem.build_4_customfield(customfield=customfield)
        self.assertEqual('customfieldmultienum__value__exact', hfi.filter_string)

    def test_build_4_relation(self):
        loves, loved = RelationType.create(('test-subject_love', u'Is loving'), ('test-object_love',  u'Is loved by'))
        hfi = HeaderFilterItem.build_4_relation(rtype=loves)
        self.assertIsInstance(hfi, HeaderFilterItem)
        self.assertEqual(str(loves.id),   hfi.name)
        self.assertEqual(loves.predicate, hfi.title)
        self.assertEqual(HFI_RELATION,    hfi.type)
        self.assertIs(hfi.has_a_filter, True)
        self.assertIs(hfi.editable,     False)
        self.assertIs(hfi.sortable,     False)
        self.assertEqual('',       hfi.filter_string)
        self.assertEqual(loves.id, hfi.relation_predicat.id)

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

    def test_set_items(self):
        hfilter = HeaderFilter.create(pk='test-hf01', name=u'Contact view', model=Contact)
        hfi01 = HeaderFilterItem.build_4_field(model=Contact, name='first_name')
        hfi02 = HeaderFilterItem.build_4_field(model=Contact, name='last_name')
        hfilter.set_items([hfi01, hfi02])

        hfilter = HeaderFilter.objects.get(pk=hfilter.pk) #refresh
        items = list(hfilter.header_filter_items.order_by('order'))
        self.assertEqual([hfi01.id, hfi02.id], [hfi.id for hfi in items])
        self.assertEqual([1, 2],               [hfi.order for hfi in items])
        self.assertEqual([hfi01.id, hfi02.id], [hfi.id for hfi in hfilter.items])

    def test_delete_relationtype01(self):
        self.login()

        loves, loved = RelationType.create(('test-subject_love', u'Is loving'), ('test-object_love',  u'Is loved by'))
        hates, hated = RelationType.create(('test-subject_hate', u'Is hating'), ('test-object_hate',  u'Is hated by'))

        hf = HeaderFilter.create(pk='test-hf01', name=u'Contact view', model=Contact)
        hfi01 = HeaderFilterItem.build_4_field(model=Contact, name='last_name')
        hfi02 = HeaderFilterItem.build_4_relation(rtype=loves)
        hfi03 = HeaderFilterItem.build_4_relation(rtype=loved)
        hfi04 = HeaderFilterItem.build_4_relation(rtype=hates)
        hf.set_items([hfi01, hfi02, hfi03, hfi04])
        self.assertEqual(4, hf.header_filter_items.count())

        loves_id = loves.id
        loves.delete()
        self.assertEqual(0, RelationType.objects.filter(pk=loves_id).count())
        self.assertEqual([hfi01.id, hfi04.id], [hfi.id for hfi in hf.header_filter_items.order_by('order')])

    def test_delete_customfield(self):
        self.login()

        contact_ct = ContentType.objects.get_for_model(Contact)
        custom_field01 = CustomField.objects.create(name='Size (cm)', content_type=contact_ct, field_type=CustomField.INT)
        custom_field02 = CustomField.objects.create(name='IQ',        content_type=contact_ct, field_type=CustomField.INT)

        hf = HeaderFilter.create(pk='test-hf01', name=u'Contact view', model=Contact)
        hfi01 = HeaderFilterItem.build_4_field(model=Contact, name='last_name')
        hfi02 = HeaderFilterItem.build_4_customfield(customfield=custom_field01)
        hfi03 = HeaderFilterItem.build_4_customfield(customfield=custom_field02)
        hf.set_items([hfi01, hfi02, hfi03])
        self.assertEqual(3, hf.header_filter_items.count())

        custom_field01.delete()
        self.assertEqual([hfi01.id, hfi03.id], [hfi.id for hfi in hf.header_filter_items.order_by('order')])
