# -*- coding: utf-8 -*-

try:
    from django.contrib.contenttypes.models import ContentType

    from creme.creme_core.models import CremePropertyType
    from creme.creme_core.tests.base import CremeTestCase

    from creme.persons.models import Contact, Organisation #need CremeEntity
except Exception as e:
    print('Error in <%s>: %s' % (__name__, e))


__all__ = ('PropertyTypeTestCase',)


class PropertyTypeTestCase(CremeTestCase):
    ADD_URL = '/creme_config/property_type/add/'

    @classmethod
    def setUpClass(cls):
        cls.populate('creme_core', 'creme_config')

    def setUp(self):
        self.login()

    def _build_edit_url(self, ptype):
        return '/creme_config/property_type/edit/%s' % ptype.id

    def test_portal(self):
        create_ptype = CremePropertyType.create
        ptype1  = create_ptype(str_pk='test-prop_hairy', text='is hairy')
        ptype2  = create_ptype(str_pk='test-prop_beard', text='is bearded')

        url = CremePropertyType.get_lv_absolute_url()
        self.assertEqual('/creme_config/property_type/portal/', url)

        response = self.assertGET200(url)
        self.assertTemplateUsed(response, 'creme_config/property_type_portal.html')

        self.assertContains(response, unicode(ptype1))
        self.assertContains(response, unicode(ptype2))

    def _find_property_type(self, prop_types, text):
        for prop_type in prop_types:
            if prop_type.text == text:
                return prop_type

        self.fail('No property <%s>' % text)

    def test_create01(self):
        url = self.ADD_URL
        self.assertGET200(url)

        count = CremePropertyType.objects.count()

        text = 'is beautiful'
        self.assertNoFormError(self.client.post(url, data={'text': text}))

        prop_types = CremePropertyType.objects.all()
        self.assertEqual(count + 1, len(prop_types))

        prop_type = self._find_property_type(prop_types, text)
        self.assertFalse(prop_type.subject_ctypes.all())

    def test_create02(self):
        get_ct = ContentType.objects.get_for_model
        ct_ids = [get_ct(Contact).id, get_ct(Organisation).id]
        text   = 'is beautiful'
        response = self.client.post(self.ADD_URL,
                                    data={'text':           text,
                                          'subject_ctypes': ct_ids,
                                         }
                                   )
        self.assertNoFormError(response)

        prop_type = self.get_object_or_fail(CremePropertyType, text=text)
        ctypes = prop_type.subject_ctypes.all()
        self.assertEqual(2,           len(ctypes))
        self.assertEqual(set(ct_ids), {ct.id for ct in ctypes})

    def test_edit01(self):
        get_ct = ContentType.objects.get_for_model
        pt = CremePropertyType.create('test-foobar', 'is beautiful', [get_ct(Contact)], is_custom=False)

        self.assertGET404(self._build_edit_url(pt))

    def test_edit02(self):
        get_ct = ContentType.objects.get_for_model
        pt = CremePropertyType.create('test-foobar', 'is beautiful', [get_ct(Contact)], is_custom=True)
        uri = self._build_edit_url(pt)
        self.assertGET200(uri)

        ct_orga = get_ct(Organisation)
        text   = 'is very beautiful'
        response = self.client.post(uri, data={'text':           text,
                                               'subject_ctypes': [ct_orga.id],
                                              }
                                   )
        self.assertNoFormError(response)

        pt = self.refresh(pt)
        self.assertEqual(text,         pt.text)
        self.assertEqual([ct_orga.id], [ct.id for ct in pt.subject_ctypes.all()])

    def test_delete01(self):
        pt = CremePropertyType.create('test-foobar', 'is beautiful', [], is_custom=False)
        self.assertPOST404('/creme_config/property_type/delete', data={'id': pt.id})

    def test_delete02(self):
        pt = CremePropertyType.create('test-foobar', 'is beautiful', [], is_custom=True)
        self.assertPOST200('/creme_config/property_type/delete', data={'id': pt.id})
        self.assertDoesNotExist(pt)
