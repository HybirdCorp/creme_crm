# -*- coding: utf-8 -*-

from django.contrib.contenttypes.models import ContentType

from creme_core.models import CremePropertyType, CremeProperty, CremeEntity, SetCredentials
from creme_core.tests.views.base import ViewsTestCase


__all__ = ('PropertyViewsTestCase', )


class PropertyViewsTestCase(ViewsTestCase):
    def test_add(self):
        self.login()

        ptype01 = CremePropertyType.create(str_pk='test-prop_foobar01', text='wears strange hats')
        ptype02 = CremePropertyType.create(str_pk='test-prop_foobar02', text='wears strange pants')
        entity  = CremeEntity.objects.create(user=self.user)
        self.assertEqual(0, entity.properties.count())

        response = self.client.get('/creme_core/property/add/%s' % entity.id)
        self.assertEqual(200, response.status_code)

        response = self.client.post('/creme_core/property/add/%s' % entity.id,
                                    data={'types': [ptype01.id, ptype02.id]}
                                   )
        self.assertEqual(200, response.status_code)

        properties = entity.properties.all()
        self.assertEqual(2, len(properties))
        self.assertEqual(set([ptype01.id, ptype02.id]), set(p.type_id for p in properties))

    def test_delete(self):
        self.login()

        ptype  = CremePropertyType.create(str_pk='test-prop_foobar', text='hairy')
        entity = CremeEntity.objects.create(user=self.user)
        prop   = CremeProperty.objects.create(type=ptype, creme_entity=entity)
        ct     = ContentType.objects.get_for_model(CremeProperty)

        response = self.client.post('/creme_core/entity/delete_related/%s' % ct.id, data={'id': prop.id})
        self.assertEqual(302, response.status_code)
        self.assertEqual(0,   CremeProperty.objects.filter(pk=prop.id).count())

    #TODO: test get_property_types_for_ct(), add_to_entities()

    def assertEntityHasProperty(self, ptype, entity):
        try:
            entity.properties.get(type=ptype)
        except Exception, e:
            self.fail(str(e))

    def assertEntityHasntProperty(self, ptype, entity):
        self.assertRaises(CremeProperty.DoesNotExist, entity.properties.get, type=ptype)

    def test_add_properties_bulk01(self):
        self.login()

        ptype01 = CremePropertyType.create(str_pk='test-prop_foobar01', text='wears strange hats')
        ptype02 = CremePropertyType.create(str_pk='test-prop_foobar02', text='wears strange pants')
        ptype03 = CremePropertyType.create(str_pk='test-prop_foobar03', text='wears strange shoes')

        entities = [CremeEntity.objects.create(user=self.user) for i in xrange(15)]
        centity_ct_id = ContentType.objects.get_for_model(CremeEntity).id

        for entity in entities:
            self.assertEqual(0, entity.properties.count())

        comma_sep_ids = ','.join([str(entity.id) for entity in entities])

        response = self.client.get('/creme_core/property/add_to_entities/%s/%s' % (centity_ct_id, comma_sep_ids))
        self.assertEqual(200, response.status_code)

        response = self.client.post('/creme_core/property/add_to_entities/%s/%s' % (centity_ct_id, comma_sep_ids),
                                    data={
                                        'entities': comma_sep_ids,
                                        'types': [ptype01.id, ptype02.id],
                                        'entities_lbl': '',
                                    }
                                   )
        self.assertNoFormError(response)

        for entity in entities:
            self.assertEqual(2, entity.properties.count())
            self.assertEntityHasProperty(ptype01,   entity)
            self.assertEntityHasProperty(ptype02,   entity)
            self.assertEntityHasntProperty(ptype03, entity)

    def test_add_properties_bulk02(self):
        self.login(is_superuser=False)

        entity01 = CremeEntity.objects.create(user=self.other_user)
        entity02 = CremeEntity.objects.create(user=self.other_user)
        entity03 = CremeEntity.objects.create(user=self.user)
        entity04 = CremeEntity.objects.create(user=self.user)

        ptype01 = CremePropertyType.create(str_pk='test-prop_foobar01', text='wears strange hats')
        ptype02 = CremePropertyType.create(str_pk='test-prop_foobar02', text='wears strange pants')

        comma_sep_ids = '%s,%s,%s,%s' % (entity01.id, entity02.id, entity03.id,  entity04.id)
        centity_ct_id = ContentType.objects.get_for_model(CremeEntity).id

        self.failIf(entity01.can_change(self.user))
        self.failIf(entity02.can_change(self.user))

        self.assertTrue(entity03.can_change(self.user))

        url = '/creme_core/property/add_to_entities/%s/%s' % (centity_ct_id, comma_sep_ids)
        response = self.client.get(url)
        self.assertEqual(200, response.status_code)

        try:
            label = response.context['form'].fields['bad_entities_lbl']
        except Exception, e:
            self.fail(str(e))

        self.assert_(label.initial)

        response = self.client.post(url, data={
                                        'entities_lbl':     'do not care',
                                        'bad_entities_lbl': 'do not care',
                                        'entities':         '%s,%s' % (
                                                                entity03.id,
                                                                entity04.id,
                                                               ),
                                        'types':            [ptype01.id, ptype02.id],
                                      })

        self.assertNoFormError(response)
        self.assertEqual(200, response.status_code)

        self.assertEqual(0,   entity01.properties.count())
        self.assertEqual(0,   entity02.properties.count())
        self.assertEqual(2,   entity03.properties.count())
        self.assertEqual(2,   entity04.properties.count())

        self.assertEntityHasntProperty(ptype01,   entity01)
        self.assertEntityHasntProperty(ptype02,   entity01)
        self.assertEntityHasntProperty(ptype01,   entity02)
        self.assertEntityHasntProperty(ptype02,   entity02)

        self.assertEntityHasProperty(ptype01,   entity03)
        self.assertEntityHasProperty(ptype02,   entity03)
        self.assertEntityHasProperty(ptype01,   entity04)
        self.assertEntityHasProperty(ptype02,   entity04)

    def test_add_properties_bulk03(self):
        self.login(is_superuser=False)

        ptype01 = CremePropertyType.create(str_pk='test-prop_foobar01', text='wears strange hats')
        centity_ct_id = ContentType.objects.get_for_model(CremeEntity).id

        self._set_all_creds_except_one(excluded=SetCredentials.CRED_CHANGE)
        uneditable = CremeEntity.objects.create(user=self.other_user)

        self.assert_(uneditable.can_view(self.user))
        self.failIf(uneditable.can_change(self.user))

        response = self.client.get('/creme_core/property/add_to_entities/%s/%s' % (centity_ct_id, uneditable.id))
        self.assertEqual(200, response.status_code)

        try:
            label = response.context['form'].fields['bad_entities_lbl']
        except Exception, e:
            self.fail(str(e))

        self.assertEqual(unicode(uneditable), label.initial)

    def test_add_properties_bulk04(self):
        self.login(is_superuser=False)

        ptype01 = CremePropertyType.create(str_pk='test-prop_foobar01', text='wears strange hats')
        ptype02 = CremePropertyType.create(str_pk='test-prop_foobar02', text='wears strange pants')

        centity_ct_id = ContentType.objects.get_for_model(CremeEntity).id
        entity01 = CremeEntity.objects.create(user=self.user)

        url = '/creme_core/property/add_to_entities/%s/%s' % (centity_ct_id, entity01.id)
        self.assertEqual(200, self.client.get(url).status_code)

        self._set_all_creds_except_one(excluded=SetCredentials.CRED_CHANGE)
        uneditable = CremeEntity.objects.create(user=self.other_user)

        response = self.client.post(url, data={
                                                'entities_lbl': 'd:p',
                                                'entities':     '%s' % (uneditable.id,),
                                                'types':        [ptype01.id, ptype02.id],
                                              })
        self.assertEqual(200, response.status_code)

        try:
            form = response.context['form']
        except Exception, e:
            self.fail('No form in context ? (%s)', str(e))

        if not form.errors:
            self.fail('Not the excepted error in form.')

        self.assertEqual(1, len(form.errors.get('__all__', [])))
