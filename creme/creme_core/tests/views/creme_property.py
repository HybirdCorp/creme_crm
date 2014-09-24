# -*- coding: utf-8 -*-

try:
    from functools import partial

    from django.contrib.contenttypes.models import ContentType
    from django.core.serializers.json import simplejson
    from django.utils.translation import ugettext as _

    from creme.creme_core.auth.entity_credentials import EntityCredentials
    from creme.creme_core.models import CremePropertyType, CremeProperty, CremeEntity
    from .base import ViewsTestCase

    from creme.persons.models import Contact, Organisation
except Exception as e:
    print('Error in <%s>: %s' % (__name__, e))


__all__ = ('PropertyViewsTestCase', )


class PropertyViewsTestCase(ViewsTestCase):
    ADD_TYPE_URL = '/creme_core/property/type/add'

    @classmethod
    def setUpClass(cls):
        cls.populate('creme_config', 'creme_core')
        cls.centity_ct = ContentType.objects.get_for_model(CremeEntity)

    def assertEntityHasProperty(self, ptype, entity):
        self.assertTrue(entity.properties.filter(type=ptype).exists())

    def assertEntityHasntProperty(self, ptype, entity):
        self.assertFalse(entity.properties.filter(type=ptype).exists())

    def _build_bulk_url(self, ct, *entities):
        return '/creme_core/property/add_to_entities/%s/?persist=ids&ids=%s' % (
                    ct.id,
                    '&ids='.join(str(e.id) for e in entities)
                )

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
        choices = list(choices)
        i1 = self.assertIndex((ptype02.id, ptype02.text), choices)
        i2 = self.assertIndex((ptype01.id, ptype01.text), choices)
        i3 = self.assertIndex((ptype03.id, ptype03.text), choices)
        self.assertLess(i1, i2)
        self.assertLess(i2, i3)

        self.assertNoFormError(self.client.post(url, data={'types': [ptype01.id, ptype02.id]}))

        properties = entity.properties.all()
        self.assertEqual(2, len(properties))
        self.assertEqual({ptype01, ptype02}, {p.type for p in properties})

        #-----------------------------------------------------------------------
        response = self.assertPOST200(url, data={'types': [ptype01.id, ptype03.id]}) #one new and one old property
        self.assertFormError(response, 'form', 'types',
                             _(u'Select a valid choice. %s is not one of the available choices.') % ptype01.id
                            )

    def test_add_type01(self):
        self.login()

        url = self.ADD_TYPE_URL
        self.assertGET200(url)

        text = 'is beautiful'
        #count = CremePropertyType.objects.count()
        self.assertFalse(CremePropertyType.objects.filter(text=text))

        response = self.client.post(url, follow=True, data={'text': text})
        self.assertNoFormError(response)

        ptype = self.get_object_or_fail(CremePropertyType, text=text)
        self.assertFalse(ptype.subject_ctypes.all())
        self.assertFalse(ptype.is_copiable)

        self.assertRedirects(response, ptype.get_absolute_url())

    def test_add_type02(self):
        self.login()

        get_ct = ContentType.objects.get_for_model
        ct_ids = [get_ct(Contact).id, get_ct(Organisation).id]
        text   = 'is beautiful'
        response = self.client.post(self.ADD_TYPE_URL, follow=True,
                                    data={'text':           text,
                                          'subject_ctypes': ct_ids,
                                          'is_copiable':    'on',
                                         }
                                   )
        self.assertNoFormError(response)

        ptype = self.get_object_or_fail(CremePropertyType, text=text)
        self.assertTrue(ptype.is_copiable)

        ctypes = ptype.subject_ctypes.all()
        self.assertEqual(2,           len(ctypes))
        self.assertEqual(set(ct_ids), {ct.id for ct in ctypes})

    def test_edit_type01(self):
        "is_custom=False"
        self.login()
        ptype = CremePropertyType.create('test-foobar', 'is beautiful',
                                      [ContentType.objects.get_for_model(Contact)],
                                      is_custom=False,
                                     )

        self.assertGET404(ptype.get_edit_absolute_url())

    def test_edit_type02(self):
        self.login()

        get_ct = ContentType.objects.get_for_model
        ptype = CremePropertyType.create('test-foobar', 'is beautiful',
                                         [get_ct(Contact)], is_custom=True,
                                        )

        url = ptype.get_edit_absolute_url()
        self.assertGET200(url)

        ct_orga = get_ct(Organisation)
        text = 'is very beautiful'
        response = self.client.post(url, follow=True,
                                    data={'text':           text,
                                          'subject_ctypes': [ct_orga.id],
                                         }
                                   )
        self.assertNoFormError(response)
        self.assertRedirects(response, ptype.get_absolute_url())

        ptype = self.refresh(ptype)
        self.assertEqual(text,      ptype.text)
        self.assertEqual([ct_orga], list(ptype.subject_ctypes.all()))

    #def test_list_types(self):
        #self.login()

        #create_ptype = CremePropertyType.create
        #ptype1  = create_ptype(str_pk='test-prop_hairy', text='is hairy')
        #ptype2  = create_ptype(str_pk='test-prop_beard', text='is bearded')

        #response = self.assertGET200(CremePropertyType.get_lv_absolute_url())
        #self.assertTemplateUsed(response, 'creme_core/list_property_types.html')

        #self.assertContains(response, unicode(ptype1))
        #self.assertContains(response, unicode(ptype2))

    def test_delete_related(self):
        self.login()

        ptype  = CremePropertyType.create(str_pk='test-prop_foobar', text='hairy')
        entity = Contact.objects.create(user=self.user, last_name='Vrataski')
        prop   = CremeProperty.objects.create(type=ptype, creme_entity=entity)
        ct     = ContentType.objects.get_for_model(CremeProperty)

        response = self.assertPOST200('/creme_core/entity/delete_related/%s' % ct.id, 
                                      follow=True, data={'id': prop.id},
                                     )
        self.assertRedirects(response, entity.get_absolute_url())
        self.assertDoesNotExist(prop)

    def test_delete_from_type(self):
        self.login()

        ptype = CremePropertyType.create(str_pk='test-prop_foobar', text='hairy')

        create_entity = partial(CremeEntity.objects.create, user=self.user)
        entity1 = create_entity()
        entity2 = create_entity()

        create_prop = partial(CremeProperty.objects.create, type=ptype)
        prop1 = create_prop(creme_entity=entity1)
        prop2 = create_prop(creme_entity=entity2)

        response = self.assertPOST200('/creme_core/property/delete_from_type', follow=True,
                                      data={'ptype_id': ptype.id, 'entity_id': entity1.id},
                                     )
        self.assertRedirects(response, ptype.get_absolute_url())
        self.assertDoesNotExist(prop1)
        self.assertStillExists(prop2)

    def test_delete_type01(self):
        self.login()
        ptype = CremePropertyType.create('test-foobar', 'is beautiful', [], is_custom=False)
        self.assertPOST404(ptype.get_delete_absolute_url(), data={'id': ptype.id})

    def test_delete_type02(self):
        self.login()
        ptype = CremePropertyType.create('test-foobar', 'is beautiful', [], is_custom=True)
        response = self.assertPOST200(ptype.get_delete_absolute_url(),
                                      data={'id': ptype.id}, follow=True,
                                     )
        self.assertDoesNotExist(ptype)
        self.assertRedirects(response, CremePropertyType.get_lv_absolute_url())

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

        response = self.assertPOST200(self._build_bulk_url(self.centity_ct, *entities),
                                      data={'types': []}
                                    )
        self.assertFormError(response, 'form', 'types', _(u'This field is required.'))

        response = self.client.post(url, data={#'entities':     ','.join(str(e.id) for e in entities),
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
                                          #'entities':         '%s,%s' % (entity03.id, entity04.id),
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

        self._set_all_creds_except_one(excluded=EntityCredentials.CHANGE)
        entity01 = CremeEntity.objects.create(user=self.user)
        uneditable = CremeEntity.objects.create(user=self.other_user)

        url = self._build_bulk_url(self.centity_ct, entity01, uneditable)
        self.assertGET200(url)

        #response = self.assertPOST200(url, data={'entities_lbl': 'd:p',
                                                 #'entities':     '%s' % (uneditable.id,),
                                                 #'types':        [ptype01.id, ptype02.id],
                                                #}
                                     #)
        #self.assertFormError(response, 'form', None,
                             #[_(u"Some entities are not editable: %s") % uneditable]
                            #)
        response = self.client.post(url, data={'entities_lbl': 'd:p',
                                               #'entities':     '%s' % (uneditable.id,),
                                               'types':        [ptype01.id, ptype02.id],
                                              }
                                   )
        self.assertNoFormError(response)

        self.assertEqual([entity01], [p.creme_entity for p in CremeProperty.objects.filter(type=ptype01)])
        self.assertEqual([entity01], [p.creme_entity for p in CremeProperty.objects.filter(type=ptype02)])

    def test_not_copiable_properties(self):
        self.login()

        create_ptype = CremePropertyType.create
        ptype01 = create_ptype(str_pk='test-prop_foobar01', text='wears strange hats', is_copiable=False)
        ptype02 = create_ptype(str_pk='test-prop_foobar02', text='wears strange pants')

        entity = CremeEntity.objects.create(user=self.user)

        create_prop = partial(CremeProperty.objects.create, creme_entity=entity)
        create_prop(type=ptype01)
        create_prop(type=ptype02)

        filter_prop = CremeProperty.objects.filter
        self.assertEqual(1, filter_prop(type=ptype01).count())
        self.assertEqual(1, filter_prop(type=ptype02).count())

        entity.clone()

        self.assertEqual(1, filter_prop(type=ptype01).count())
        self.assertEqual(2, filter_prop(type=ptype02).count())

    def test_detailview01(self):
        self.login()
        user = self.user

        ptype = CremePropertyType.create(str_pk='test-prop_murica', text='is american')

        create_contact = partial(Contact.objects.create, user=user)
        entity1 = create_contact(last_name='Vrataski', first_name='Rita')
        entity2 = create_contact(last_name='Kiriya',   first_name='Keiji')

        entity3 = Organisation.objects.create(user=user, name='US Defense Force')

        create_prop = partial(CremeProperty.objects.create, type=ptype)
        create_prop(creme_entity=entity1)
        create_prop(creme_entity=entity3)

        response = self.assertGET200(ptype.get_absolute_url())
        self.assertTemplateUsed(response, 'creme_core/view_property_type.html')

        with self.assertNoException():
            ctxt_ptype = response.context['object']

        self.assertEqual(ptype, ctxt_ptype)

        self.assertContains(response,    ' id="block_creme_core-tagged-persons-contact"')
        self.assertContains(response,    ' id="block_creme_core-tagged-persons-organisation"')
        self.assertNotContains(response, ' id="block_creme_core-tagged-billing-invoice"')
        self.assertNotContains(response, ' id="block_creme_core-misc_tagged_entities"')

        self.assertContains(response, unicode(entity1))
        self.assertNotContains(response, unicode(entity2))
        self.assertContains(response, unicode(entity3))

    def test_detailview02(self):
        self.login()
        user = self.user

        ptype = CremePropertyType.create(str_pk='test-prop_murica', text='is american',
                                         subject_ctypes=[Contact],
                                        )

        rita = Contact.objects.create(user=user, last_name='Vrataski', first_name='Rita')
        udf = Organisation.objects.create(user=user, name='US Defense Force')

        create_prop = partial(CremeProperty.objects.create, type=ptype)
        create_prop(creme_entity=rita)
        create_prop(creme_entity=udf)

        response = self.assertGET200(ptype.get_absolute_url())

        self.assertContains(response,    ' id="block_creme_core-tagged-persons-contact"')
        self.assertNotContains(response, ' id="block_creme_core-tagged-persons-organisation"')
        self.assertContains(response,    ' id="block_creme_core-misc_tagged_entities"')

        self.assertContains(response, unicode(rita), 1)
        self.assertContains(response, unicode(udf), 1)

    def test_reload_block01(self):
        self.login()
        ptype = CremePropertyType.create(str_pk='test-prop_murica', text='is american')

        rita = Contact.objects.create(user=self.user, last_name='Vrataski', first_name='Rita')
        CremeProperty.objects.create(type=ptype, creme_entity=rita)

        url_fmt = '/creme_core/property/type/%s/reload_block/%s/'
        block_id = 'block_creme_core-tagged-persons-contact'
        response = self.assertGET200(url_fmt % (ptype.id, block_id))

        with self.assertNoException():
            result = simplejson.loads(response.content)

        self.assertIsInstance(result, list)
        self.assertEqual(1, len(result))

        result = result[0]
        self.assertIsInstance(result, list)
        self.assertEqual(2, len(result))
        self.assertEqual(block_id, result[0])
        self.assertIn(' id="%s"' % block_id, result[1])

        self.assertGET404(url_fmt % (ptype.id, 'invalid_blockid'))
        self.assertGET404(url_fmt % (ptype.id, 'block_creme_core-tagged-persons-invalidmodel'))
        self.assertGET404(url_fmt % (ptype.id, 'block_creme_core-tagged-persons-civility'))

    def test_reload_block02(self):
        self.login()
        ptype = CremePropertyType.create(str_pk='test-prop_murica', text='is american',
                                         subject_ctypes=[Organisation],
                                        )

        rita = Contact.objects.create(user=self.user, last_name='Vrataski', first_name='Rita')
        CremeProperty.objects.create(type=ptype, creme_entity=rita)

        url_fmt = '/creme_core/property/type/%s/reload_block/%s/'
        block_id = 'block_creme_core-misc_tagged_entities'
        response = self.assertGET200(url_fmt % (ptype.id, block_id))

        #with self.assertNoException():
            #result = simplejson.loads(response.content)

        #self.assertIsInstance(result, list)
        #self.assertEqual(1, len(result))

        #result = result[0]
        #self.assertIsInstance(result, list)
        #self.assertEqual(2, len(result))
        #self.assertEqual(block_id, result[0])
        #self.assertIn(' id="%s"' % block_id, result[1])

        #self.assertGET404(url_fmt % (ptype.id, 'invalid_blockid'))
        #self.assertGET404(url_fmt % (ptype.id, 'block_creme_core-tagged-persons-invalidmodel'))
        #self.assertGET404(url_fmt % (ptype.id, 'block_creme_core-tagged-persons-civility'))
