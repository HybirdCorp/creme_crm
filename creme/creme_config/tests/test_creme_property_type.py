# -*- coding: utf-8 -*-

try:
    from django.contrib.contenttypes.models import ContentType
    from django.core.urlresolvers import reverse

    from creme.creme_core.models import CremePropertyType, CremeProperty
    from creme.creme_core.tests.base import CremeTestCase
    from creme.creme_core.tests.fake_models import FakeContact, FakeOrganisation
except Exception as e:
    print('Error in <%s>: %s' % (__name__, e))


class PropertyTypeTestCase(CremeTestCase):
    ADD_URL = reverse('creme_config__create_ptype')
    DELETE_URL = reverse('creme_config__delete_ptype')

    def setUp(self):
        self.login()

    def _build_edit_url(self, ptype):
        return reverse('creme_config__edit_ptype', args=(ptype.id,))

    def test_portal(self):
        create_ptype = CremePropertyType.create
        ptype1  = create_ptype(str_pk='test-prop_hairy', text='is hairy')
        ptype2  = create_ptype(str_pk='test-prop_beard', text='is bearded')

        url = CremePropertyType.get_lv_absolute_url()
        self.assertEqual(reverse('creme_config__ptypes'), url)

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
        ct_ids = [get_ct(FakeContact).id, get_ct(FakeOrganisation).id]
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
        pt = CremePropertyType.create('test-foobar', 'is beautiful', [get_ct(FakeContact)], is_custom=False)

        self.assertGET404(self._build_edit_url(pt))

    def test_edit02(self):
        get_ct = ContentType.objects.get_for_model
        pt = CremePropertyType.create('test-foobar', 'is beautiful', [get_ct(FakeContact)], is_custom=True)
        uri = self._build_edit_url(pt)
        self.assertGET200(uri)

        ct_orga = get_ct(FakeOrganisation)
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
        self.assertPOST404(self.DELETE_URL, data={'id': pt.id})

    def test_delete02(self):
        create_ptype = CremePropertyType.create
        pt1 = create_ptype('test-foo', 'is beautiful', [], is_custom=True)
        pt2 = create_ptype('test-bar', 'is smart')

        zap = FakeContact.objects.create(user=self.user, first_name='Zap', last_name='Brannigan')
        prop = CremeProperty.objects.create(creme_entity=zap, type=pt1)

        self.assertPOST200(self.DELETE_URL, data={'id': pt1.id})
        self.assertDoesNotExist(pt1)
        self.assertDoesNotExist(prop)

        self.assertStillExists(pt2)

