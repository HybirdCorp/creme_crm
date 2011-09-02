# -*- coding: utf-8 -*-

try:
    from django.contrib.contenttypes.models import ContentType

    from creme_core.models import RelationType, CremeEntity, CremePropertyType
    from creme_core.tests.base import CremeTestCase

    from persons.models import Contact, Organisation #need CremeEntity
except Exception, e:
    print 'Error:', e


__all__ = ('RelationTypeTestCase',)


class RelationTypeTestCase(CremeTestCase):
    def setUp(self): #in CremeConfigTestCase ??
        self.populate('creme_core', 'creme_config')
        self.login()

    def test_portal(self):
        self.assertEqual(200, self.client.get('/creme_config/relation_type/portal/').status_code)

    def _find_relation_type(self, relation_types, predicate):
        for relation_type in relation_types:
            if relation_type.predicate == predicate:
                return relation_type

        self.fail('No relation type <%s>' % predicate)

    def test_create01(self):
        url = '/creme_config/relation_type/add/'
        self.assertEqual(200, self.client.get(url).status_code)
        rel_type_core_populate_count = 2

        self.assertEqual(rel_type_core_populate_count, RelationType.objects.count())#4 from creme_core populate

        subject_pred = 'loves'
        object_pred  = 'is loved by'
        response = self.client.post(url, data={
                                                'subject_predicate': subject_pred,
                                                'object_predicate':  object_pred,
                                              }
                                   )
        self.assertNoFormError(response)
        self.assertEqual(200, response.status_code)

        rel_types = RelationType.objects.all()
        self.assertEqual(rel_type_core_populate_count + 2, len(rel_types))#4 from creme_core populate + 2freshly created

        rel_type = self._find_relation_type(rel_types, subject_pred)
        self.assert_(rel_type.is_custom)
        self.assertEqual(object_pred, rel_type.symmetric_type.predicate)
        self.assertEqual(0,           rel_type.subject_ctypes.count())
        self.assertEqual(0,           rel_type.object_ctypes.count())
        self.assertEqual(0,           rel_type.subject_properties.count())
        self.assertEqual(0,           rel_type.object_properties.count())

    def test_create02(self):
        pt_sub = CremePropertyType.create('test-pt_sub', 'has cash',  [Organisation])
        pt_obj = CremePropertyType.create('test-pt_sub', 'need cash', [Contact])

        get_ct     = ContentType.objects.get_for_model
        ct_orga    = get_ct(Organisation)
        ct_contact = get_ct(Contact)

        subject_pred = 'employs'
        response = self.client.post('/creme_config/relation_type/add/',
                                    data={
                                            'subject_predicate':  subject_pred,
                                            'object_predicate':   'is employed by',
                                            'subject_ctypes':     [ct_orga.id],
                                            'subject_properties': [pt_sub.id],
                                            'object_ctypes':      [ct_contact.id],
                                            'object_properties':  [pt_obj.id],
                                          }
                                   )
        self.assertNoFormError(response)
        self.assertEqual(200, response.status_code)

        rel_type = self._find_relation_type(RelationType.objects.all(), subject_pred)
        self.assertEqual([ct_orga.id],    [ct.id for ct in rel_type.subject_ctypes.all()])
        self.assertEqual([ct_contact.id], [ct.id for ct in rel_type.object_ctypes.all()])
        self.assertEqual([pt_sub.id],     [pt.id for pt in rel_type.subject_properties.all()])
        self.assertEqual([pt_obj.id],     [pt.id for pt in rel_type.object_properties.all()])

    def test_edit01(self):
        rt, srt = RelationType.create(('test-subfoo', 'subject_predicate'),
                                      ('test-objfoo', 'object_predicate'), is_custom=False
                                     )
        self.assertEqual(404, self.client.get('/creme_config/relation_type/edit/%s' % rt.id).status_code)

    def test_edit02(self):
        rt, srt = RelationType.create(('test-subfoo', 'subject_predicate'),
                                      ('test-objfoo', 'object_predicate'),
                                      is_custom=True
                                     )
        url = '/creme_config/relation_type/edit/%s' % rt.id
        self.assertEqual(200, self.client.get(url).status_code)

        subject_pred = 'loves'
        object_pred  = 'is loved by'
        response = self.client.post(url,
                                    data={
                                            'subject_predicate': subject_pred,
                                            'object_predicate':  object_pred,
                                          }
                                   )
        self.assertNoFormError(response)
        self.assertEqual(200, response.status_code)

        rel_type = RelationType.objects.get(pk=rt.id)
        self.assertEqual(subject_pred, rel_type.predicate)
        self.assertEqual(object_pred,  rel_type.symmetric_type.predicate)

    def test_delete01(self):
        rt, srt = RelationType.create(('test-subfoo', 'subject_predicate'), ('test-subfoo', 'object_predicate'), is_custom=False)
        self.assertEqual(404, self.client.post('/creme_config/relation_type/delete', data={'id': rt.id}).status_code)

    def test_delete02(self):
        rt, srt = RelationType.create(('test-subfoo', 'subject_predicate'), ('test-subfoo', 'object_predicate'), is_custom=True)
        self.assertEqual(200, self.client.post('/creme_config/relation_type/delete', data={'id': rt.id}).status_code)
        self.assertEqual(0,   RelationType.objects.filter(pk__in=[rt.id, srt.id]).count())
