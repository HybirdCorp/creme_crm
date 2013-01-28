# -*- coding: utf-8 -*-

try:
    from django.utils.translation import ugettext as _
    from django.contrib.contenttypes.models import ContentType

    from creme_core.models import CremePropertyType, CremeProperty, CremeEntity, SetCredentials
    from creme_core.tests.views.base import ViewsTestCase
except Exception as e:
    print 'Error in <%s>: %s' % (__name__, e)


__all__ = ('PropertyViewsTestCase', )


class PropertyViewsTestCase(ViewsTestCase):
    @classmethod
    def setUpClass(cls):
        cls.populate('creme_config')
        cls.centity_ct = ContentType.objects.get_for_model(CremeEntity)

    def test_add(self):
        self.login()

        create_ptype = CremePropertyType.create
        ptype01 = create_ptype(str_pk='test-prop_foobar01', text='wears strange hats')
        ptype02 = create_ptype(str_pk='test-prop_foobar02', text='wears strange pants')
        ptype03 = create_ptype(str_pk='test-prop_foobar02', text='wears strange shoes')
        entity  = CremeEntity.objects.create(user=self.user)
        self.assertFalse(entity.properties.all())

        url = '/creme_core/property/add/%s' % entity.id
        self.assertEqual(200, self.client.get(url).status_code)

        self.assertNoFormError(self.client.post(url, data={'types': [ptype01.id, ptype02.id]}))

        properties = entity.properties.all()
        self.assertEqual(2, len(properties))
        self.assertEqual(set([ptype01, ptype02]), set(p.type for p in properties))

        #-----------------------------------------------------------------------
        response = self.client.post(url, data={'types': [ptype01.id, ptype03.id]}) #one new and one old property
        self.assertEqual(200, response.status_code)
        self.assertFormError(response, 'form', 'types',
                             [_(u'Select a valid choice. %s is not one of the available choices.') % ptype01.id]
                            )

    def test_delete(self):
        self.login()

        ptype  = CremePropertyType.create(str_pk='test-prop_foobar', text='hairy')
        entity = CremeEntity.objects.create(user=self.user)
        prop   = CremeProperty.objects.create(type=ptype, creme_entity=entity)
        ct     = ContentType.objects.get_for_model(CremeProperty)

        response = self.client.post('/creme_core/entity/delete_related/%s' % ct.id, data={'id': prop.id})
        self.assertEqual(302, response.status_code)
        self.assertEqual(0,   CremeProperty.objects.filter(pk=prop.id).count())

    def assertEntityHasProperty(self, ptype, entity):
        self.assertTrue(entity.properties.filter(type=ptype).exists())

    def assertEntityHasntProperty(self, ptype, entity):
        self.assertFalse(entity.properties.filter(type=ptype).exists())

    def _build_bulk_url(self, ct, *entities):
        return '/creme_core/property/add_to_entities/%s/?persist=ids&ids=%s' % (
                    ct.id,
                    '&ids='.join(str(e.id) for e in entities)
                )

    def test_add_properties_bulk01(self):
        self.login()

        create_ptype = CremePropertyType.create
        ptype01 = create_ptype(str_pk='test-prop_foobar01', text='wears strange hats')
        ptype02 = create_ptype(str_pk='test-prop_foobar02', text='wears strange pants')
        ptype03 = create_ptype(str_pk='test-prop_foobar03', text='wears strange shoes')

        create_entity = CremeEntity.objects.create
        entities = [create_entity(user=self.user) for i in xrange(15)]

        for entity in entities:
            self.assertEqual(0, entity.properties.count())

        url = self._build_bulk_url(self.centity_ct, *entities)
        self.assertGET200(url)

        response = self.client.post(url, data={'entities':     ','.join(str(e.id) for e in entities),
                                               'types':        [ptype01.id, ptype02.id],
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

        create_entity = CremeEntity.objects.create
        entity01 = create_entity(user=self.other_user)
        entity02 = create_entity(user=self.other_user)
        entity03 = create_entity(user=self.user)
        entity04 = create_entity(user=self.user)

        create_ptype = CremePropertyType.create
        ptype01 = create_ptype(str_pk='test-prop_foobar01', text='wears strange hats')
        ptype02 = create_ptype(str_pk='test-prop_foobar02', text='wears strange pants')

        self.assertFalse(entity01.can_change(self.user))
        self.assertFalse(entity02.can_change(self.user))
        self.assertTrue(entity03.can_change(self.user))

        url = self._build_bulk_url(self.centity_ct, entity01, entity02, entity03, entity04)
        response = self.client.get(url)
        self.assertEqual(200, response.status_code)

        with self.assertNoException():
            label = response.context['form'].fields['bad_entities_lbl']

        format_str = _(u'Entity #%s (not viewable)')
        self.assertEqual(u'%s, %s' % (format_str % entity01.id,
                                      format_str % entity02.id
                                     ),
                         label.initial
                        )

        response = self.client.post(url,
                                    data={'entities_lbl':     'do not care',
                                          'bad_entities_lbl': 'do not care',
                                          'entities':         '%s,%s' % (entity03.id, entity04.id),
                                          'types':            [ptype01.id, ptype02.id],
                                         }
                                   )
        self.assertNoFormError(response)

        self.assertEqual(0, entity01.properties.count())
        self.assertEqual(0, entity02.properties.count())
        self.assertEqual(2, entity03.properties.count())
        self.assertEqual(2, entity04.properties.count())

        self.assertEntityHasntProperty(ptype01, entity01)
        self.assertEntityHasntProperty(ptype02, entity01)
        self.assertEntityHasntProperty(ptype01, entity02)
        self.assertEntityHasntProperty(ptype02, entity02)

        self.assertEntityHasProperty(ptype01, entity03)
        self.assertEntityHasProperty(ptype02, entity03)
        self.assertEntityHasProperty(ptype01, entity04)
        self.assertEntityHasProperty(ptype02, entity04)

    def test_add_properties_bulk03(self):
        self.login(is_superuser=False)

        self._set_all_creds_except_one(excluded=SetCredentials.CRED_CHANGE)
        uneditable = CremeEntity.objects.create(user=self.other_user)

        self.assertTrue(uneditable.can_view(self.user))
        self.assertFalse(uneditable.can_change(self.user))

        response = self.client.get(self._build_bulk_url(self.centity_ct, uneditable))
        self.assertEqual(200, response.status_code)

        with self.assertNoException():
            label = response.context['form'].fields['bad_entities_lbl']

        self.assertEqual(unicode(uneditable), label.initial)

    def test_add_properties_bulk04(self):
        self.login(is_superuser=False)

        create_ptype = CremePropertyType.create
        ptype01 = create_ptype(str_pk='test-prop_foobar01', text='wears strange hats')
        ptype02 = create_ptype(str_pk='test-prop_foobar02', text='wears strange pants')

        entity01 = CremeEntity.objects.create(user=self.user)

        url = self._build_bulk_url(self.centity_ct, entity01)
        self.assertGET200(url)

        self._set_all_creds_except_one(excluded=SetCredentials.CRED_CHANGE)
        uneditable = CremeEntity.objects.create(user=self.other_user)

        response = self.client.post(url, data={'entities_lbl': 'd:p',
                                               'entities':     '%s' % (uneditable.id,),
                                               'types':        [ptype01.id, ptype02.id],
                                              }
                                   )
        self.assertEqual(200, response.status_code)
        self.assertFormError(response, 'form', None,
                             [_(u"Some entities are not editable: %s") % uneditable]
                            )
