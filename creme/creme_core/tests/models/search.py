# -*- coding: utf-8 -*-

try:
    from django.utils.translation import ugettext as _

    from creme.creme_core.models import SearchConfigItem
    from ..base import CremeTestCase

    from creme.persons.models import Contact, Organisation
except Exception as e:
    print 'Error in <%s>: %s' % (__name__, e)


__all__ = ('SearchConfigTestCase', )


class SearchConfigTestCase(CremeTestCase):
    @classmethod
    def setUpClass(cls):
        SearchConfigItem.objects.all().delete()

    def test_create_if_needed01(self):
        self.assertEqual(0, SearchConfigItem.objects.count())

        SearchConfigItem.create_if_needed(Contact, ['first_name', 'last_name'])
        sc_items = SearchConfigItem.objects.all()
        self.assertEqual(1, len(sc_items))

        sc_item = sc_items[0]
        self.assertEqual(Contact, sc_item.content_type.model_class())
        self.assertIsNone(sc_item.user)
        self.assertEqual('first_name,last_name', sc_item.field_names)
        self.assertIs(sc_item.all_fields, False)

        sfields = sc_item.searchfields
        self.assertEqual(2, len(sfields))

        fn_field = sfields[0]
        self.assertEqual('first_name',     fn_field.name)
        self.assertEqual(_(u'First name'), fn_field.verbose_name)
        self.assertEqual(_(u'First name'), unicode(fn_field))

        ln_field = sfields[1]
        self.assertEqual('last_name',     ln_field.name)
        self.assertEqual(_(u'Last name'), ln_field.verbose_name)
        self.assertEqual(_(u'Last name'), unicode(ln_field))

        SearchConfigItem.create_if_needed(Contact, ['first_name', 'last_name'])
        self.assertEqual(1, SearchConfigItem.objects.count())

    def test_create_if_needed02(self):
        "With user"
        self.login()
        user = self.user

        sc_item = SearchConfigItem.create_if_needed(Organisation, ['name'], user)
        self.assertIsInstance(sc_item, SearchConfigItem)

        self.assertEqual(1, SearchConfigItem.objects.count())

        self.assertEqual(Organisation, sc_item.content_type.model_class())
        self.assertEqual(user,         sc_item.user)

    def test_create_if_needed03(self):
        "Invalid fields"
        sc_item = SearchConfigItem.create_if_needed(Contact, ['invalid_field', 'first_name'])

        sfields = sc_item.searchfields
        self.assertEqual(1, len(sfields))
        self.assertEqual('first_name', sfields[0].name)

    def test_allfields01(self):
        "True"
        sc_item = SearchConfigItem.create_if_needed(Organisation, [])
        self.assertTrue(sc_item.all_fields)

        sfields = set(sf.name for sf in sc_item.searchfields)
        self.assertIn('name', sfields)
        self.assertIn('shipping_address__city', sfields)
        self.assertNotIn('creation_date', sfields)

    def test_allfields02(self):
        "False"
        sc_item = SearchConfigItem.create_if_needed(Organisation, ['name', 'phone'])
        self.assertFalse(sc_item.all_fields)

    def test_searchfields01(self):
        "Invalid field are deleted automatically"
        sc_item = SearchConfigItem.create_if_needed(Organisation, ['name', 'phone'])

        sc_item.field_names += ',invalid'
        sc_item.save()

        sc_item = self.refresh(sc_item) #no cache any more

        self.assertEqual(['name', 'phone'], [sf.name for sf in sc_item.searchfields])
        self.assertEqual('name,phone', sc_item.field_names)

    def test_searchfields02(self):
        "Invalid field are deleted automatically => if no more valid field, all are used"
        sc_item = SearchConfigItem.create_if_needed(Organisation, ['name', 'phone'])
        sc_item.field_names = 'invalid01,invalid02'
        sc_item.save()

        sc_item = self.refresh(sc_item) #no cache any more

        sfields = set(sf.name for sf in sc_item.searchfields)
        self.assertIn('name', sfields)
        self.assertIn('capital', sfields)
        self.assertNotIn('created', sfields)

        self.assertTrue(sc_item.all_fields)
        self.assertIsNone(sc_item.field_names)

    def test_searchfields_setter01(self):
        sc_item = SearchConfigItem.create_if_needed(Organisation, ['name', 'phone'])

        sc_item.searchfields = ['capital', 'email', 'invalid']
        sc_item.save()

        sc_item = self.refresh(sc_item)
        self.assertEqual(['capital', 'email'], [sf.name for sf in sc_item.searchfields])
        self.assertFalse(sc_item.all_fields)

        sc_item.searchfields = []
        self.assertIsNone(sc_item.field_names)
        self.assertTrue(sc_item.all_fields)

    def test_searchfields_setter02(self):
        "No fields"
        sc_item = SearchConfigItem.create_if_needed(Organisation, ['name', 'phone'])

        sc_item.searchfields = []
        sc_item.save()
        self.assertIsNone(self.refresh(sc_item).field_names)
        self.assertTrue(sc_item.all_fields)

        sc_item.searchfields = ['name']
        self.assertEqual(['name'], [sf.name for sf in sc_item.searchfields])
        self.assertFalse(sc_item.all_fields)

    def test_searchfields_setter03(self):
        "Invalid fields"
        sc_item = SearchConfigItem.create_if_needed(Organisation, ['name', 'phone'])

        sc_item.searchfields = ['invalid']
        sc_item.save()
        self.assertIsNone(self.refresh(sc_item).field_names)
