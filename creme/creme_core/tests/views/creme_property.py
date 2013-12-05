# -*- coding: utf-8 -*-

try:
    from django.utils.translation import ugettext as _
    from django.contrib.contenttypes.models import ContentType

    from creme.creme_core.auth.entity_credentials import EntityCredentials
    from creme.creme_core.models import CremePropertyType, CremeProperty, CremeEntity
    from .base import ViewsTestCase
except Exception as e:
    print 'Error in <%s>: %s' % (__name__, e)


__all__ = ('PropertyViewsTestCase', )


class PropertyViewsTestCase(ViewsTestCase):
    @classmethod
    def setUpClass(cls):
        cls.populate('creme_config')
        cls.centity_ct = ContentType.objects.get_for_model(CremeEntity)

        CremePropertyType.objects.all().delete()

    def test_add(self):
        self.login()

        create_ptype = CremePropertyType.create
        ptype01 = create_ptype(str_pk='test-prop_foobar01', text=u'Wears strange gloves')
        ptype02 = create_ptype(str_pk='test-prop_foobar02', text=u'Wears strange glasses')
        ptype03 = create_ptype(str_pk='test-prop_foobar03', text=u'Wears strange hats')

        entity  = CremeEntity.objects.create(user=self.user)
        self.assertFalse(entity.properties.all())

        url = '/creme_core/property/add/%s' % entity.id
        response = self.assertGET200(url)

        with self.assertNoException():
            choices = response.context['form'].fields['types'].choices

        #choices are sorted with 'text'
        self.assertEqual([(ptype02.id, ptype02.text),
                          (ptype01.id, ptype01.text),
                          (ptype03.id, ptype03.text),
                         ],
                         list(choices)
                        )

        self.assertNoFormError(self.client.post(url, data={'types': [ptype01.id, ptype02.id]}))

        properties = entity.properties.all()
        self.assertEqual(2, len(properties))
        self.assertEqual(set([ptype01, ptype02]), set(p.type for p in properties))

        #-----------------------------------------------------------------------
        response = self.assertPOST200(url, data={'types': [ptype01.id, ptype03.id]}) #one new and one old property
        self.assertFormError(response, 'form', 'types',
                             [_(u'Select a valid choice. %s is not one of the available choices.') % ptype01.id]
                            )

    def test_delete(self):
        self.login()

        ptype  = CremePropertyType.create(str_pk='test-prop_foobar', text='hairy')
        entity = CremeEntity.objects.create(user=self.user)
        prop   = CremeProperty.objects.create(type=ptype, creme_entity=entity)
        ct     = ContentType.objects.get_for_model(CremeProperty)

        self.assertPOST(302, '/creme_core/entity/delete_related/%s' % ct.id, data={'id': prop.id})
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

        has_perm = self.user.has_perm_to_change
        self.assertFalse(has_perm(entity01))
        self.assertFalse(has_perm(entity02))
        self.assertTrue(has_perm(entity03))

        url = self._build_bulk_url(self.centity_ct, entity01, entity02, entity03, entity04)
        response = self.assertGET200(url)

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

        self._set_all_creds_except_one(excluded=EntityCredentials.CHANGE)
        uneditable = CremeEntity.objects.create(user=self.other_user)

        self.assertTrue(self.user.has_perm_to_view(uneditable))
        self.assertFalse(self.user.has_perm_to_change(uneditable))

        response = self.assertGET200(self._build_bulk_url(self.centity_ct, uneditable))

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

        self._set_all_creds_except_one(excluded=EntityCredentials.CHANGE)
        uneditable = CremeEntity.objects.create(user=self.other_user)

        response = self.assertPOST200(url, data={'entities_lbl': 'd:p',
                                                 'entities':     '%s' % (uneditable.id,),
                                                 'types':        [ptype01.id, ptype02.id],
                                                }
                                     )
        self.assertFormError(response, 'form', None,
                             [_(u"Some entities are not editable: %s") % uneditable]
                            )

    def test_not_copiable_properties(self):
        self.login()

        create_ptype = CremePropertyType.create
        ptype01 = create_ptype(str_pk='test-prop_foobar01', text='wears strange hats', is_copiable=False)
        ptype02 = create_ptype(str_pk='test-prop_foobar02', text='wears strange pants')

        entity = CremeEntity.objects.create(user=self.user)

        CremeProperty.objects.create(type=ptype01, creme_entity=entity)
        CremeProperty.objects.create(type=ptype02, creme_entity=entity)

        self.assertEqual(1, CremeProperty.objects.filter(type=ptype01).count())
        self.assertEqual(1, CremeProperty.objects.filter(type=ptype02).count())

        entity.clone()

        self.assertEqual(1, CremeProperty.objects.filter(type=ptype01).count())
        self.assertEqual(2, CremeProperty.objects.filter(type=ptype02).count())
