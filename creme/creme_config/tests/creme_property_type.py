# -*- coding: utf-8 -*-

try:
    from django.contrib.contenttypes.models import ContentType

    from creme_core.models import CremeEntity, CremePropertyType
    from creme_core.tests.base import CremeTestCase

    from persons.models import Contact, Organisation #need CremeEntity
except Exception as e:
    print 'Error:', e


__all__ = ('PropertyTypeTestCase',)


class PropertyTypeTestCase(CremeTestCase):
    def setUp(self):
        self.populate('creme_core', 'creme_config')
        self.login()

    def test_portal(self):
        self.assertEqual(200, self.client.get('/creme_config/property_type/portal/').status_code)

    def _find_property_type(self, prop_types, text):
        for prop_type in prop_types:
            if prop_type.text == text:
                return prop_type

        self.fail('No property <%s>' % text)

    def test_create01(self):
        url = '/creme_config/property_type/add/'
        self.assertEqual(200, self.client.get(url).status_code)

        self.assertEqual(1, CremePropertyType.objects.count())#The one from creme_core populate

        text = 'is beautiful'
        response = self.client.post(url, data={'text': text})
        self.assertNoFormError(response)
        self.assertEqual(200, response.status_code)

        prop_types = CremePropertyType.objects.all()
        self.assertEqual(2, len(prop_types))

        prop_type = self._find_property_type(prop_types, text)
        self.assertEqual(0, prop_type.subject_ctypes.count())

    def test_create02(self):
        get_ct = ContentType.objects.get_for_model
        ct_ids = [get_ct(Contact).id, get_ct(Organisation).id]
        text   = 'is beautiful'
        response = self.client.post('/creme_config/property_type/add/',
                                    data={
                                            'text':           text,
                                            'subject_ctypes': ct_ids,
                                         }
                                   )
        self.assertNoFormError(response)
        self.assertEqual(200, response.status_code)

        prop_type = self._find_property_type(CremePropertyType.objects.all(), text)
        ctypes = prop_type.subject_ctypes.all()
        self.assertEqual(2,           len(ctypes))
        self.assertEqual(set(ct_ids), set(ct.id for ct in ctypes))

    def test_edit01(self):
        get_ct = ContentType.objects.get_for_model
        pt = CremePropertyType.create('test-foobar', 'is beautiful', [get_ct(Contact)], is_custom=False)

        self.assertEqual(404, self.client.get('/creme_config/property_type/edit/%s' % pt.id).status_code)

    def test_edit02(self):
        get_ct = ContentType.objects.get_for_model
        pt = CremePropertyType.create('test-foobar', 'is beautiful', [get_ct(Contact)], is_custom=True)
        uri = '/creme_config/property_type/edit/%s' % pt.id
        self.assertEqual(200, self.client.get(uri).status_code)

        ct_orga = get_ct(Organisation)
        text   = 'is very beautiful'
        response = self.client.post(uri, data={'text':           text,
                                               'subject_ctypes': [ct_orga.id],
                                              }
                                   )
        self.assertNoFormError(response)
        self.assertEqual(200, response.status_code)

        prop_type = CremePropertyType.objects.get(pk=pt.id)
        self.assertEqual(text,         prop_type.text)
        self.assertEqual([ct_orga.id], [ct.id for ct in prop_type.subject_ctypes.all()])

    def test_delete01(self):
        pt = CremePropertyType.create('test-foobar', 'is beautiful', [], is_custom=False)
        self.assertEqual(404, self.client.post('/creme_config/property_type/delete', data={'id': pt.id}).status_code)

    def test_delete02(self):
        pt = CremePropertyType.create('test-foobar', 'is beautiful', [], is_custom=True)
        self.assertEqual(200, self.client.post('/creme_config/property_type/delete', data={'id': pt.id}).status_code)
        self.assertEqual(0,   CremePropertyType.objects.filter(pk=pt.id).count())
