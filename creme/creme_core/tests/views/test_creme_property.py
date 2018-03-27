# -*- coding: utf-8 -*-

try:
    from functools import partial
    import json

    from django.contrib.contenttypes.models import ContentType
    from django.urls import reverse
    from django.utils.translation import ugettext as _

    from .base import ViewsTestCase, BrickTestCaseMixin

    from ..fake_models import FakeContact, FakeOrganisation
    from creme.creme_core.auth.entity_credentials import EntityCredentials
    from creme.creme_core.bricks import PropertiesBrick
    from creme.creme_core.models import CremePropertyType, CremeProperty, CremeEntity
except Exception as e:
    print('Error in <%s>: %s' % (__name__, e))


class PropertyViewsTestCase(ViewsTestCase, BrickTestCaseMixin):
    ADD_TYPE_URL = reverse('creme_core__create_ptype')

    @classmethod
    def setUpClass(cls):
        super(PropertyViewsTestCase, cls).setUpClass()
        cls.centity_ct = ContentType.objects.get_for_model(CremeEntity)

    def assertEntityHasProperty(self, ptype, entity):
        self.assertTrue(entity.properties.filter(type=ptype).exists())

    def assertEntityHasntProperty(self, ptype, entity):
        self.assertFalse(entity.properties.filter(type=ptype).exists())

    def _build_bulk_url(self, ct, *entities, **kwargs):
        url = reverse('creme_core__add_properties_bulk', args=(ct.id,))

        if kwargs.get('GET', False):
            url += '?persist=ids' + ''.join('&ids={}'.format(e.id) for e in entities)

        return url

    def test_add(self):
        user = self.login()

        create_ptype = CremePropertyType.create
        ptype01 = create_ptype(str_pk='test-prop_foobar01', text=u'Wears strange gloves')
        ptype02 = create_ptype(str_pk='test-prop_foobar02', text=u'Wears strange glasses')
        ptype03 = create_ptype(str_pk='test-prop_foobar03', text=u'Wears strange hats')

        entity = CremeEntity.objects.create(user=user)
        self.assertFalse(entity.properties.all())

        url = reverse('creme_core__add_properties', args=(entity.id,))
        response = self.assertGET200(url)

        with self.assertNoException():
            choices = response.context['form'].fields['types'].choices

        # Choices are sorted with 'text'
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

        # ----------------------------------------------------------------------
        response = self.assertPOST200(url, data={'types': [ptype01.id, ptype03.id]})  # One new and one old property
        self.assertFormError(response, 'form', 'types',
                             _(u'Select a valid choice. %(value)s is not one of the available choices.') % {
                                    'value': ptype01.id,
                                }
                            )

    def test_properties_brick(self):
        user = self.login()

        create_ptype = CremePropertyType.create
        ptype01 = create_ptype(str_pk='test-prop_foobar01', text=u'Uses guns')
        ptype02 = create_ptype(str_pk='test-prop_foobar02', text=u'Uses blades')
        ptype03 = create_ptype(str_pk='test-prop_foobar03', text=u'Uses drugs')

        rita = FakeContact.objects.create(user=user, last_name='Vrataski', first_name='Rita')

        create_prop = partial(CremeProperty.objects.create, creme_entity=rita)
        create_prop(type=ptype01)
        create_prop(type=ptype02)

        response = self.assertGET200(rita.get_absolute_url())
        doc = self.get_html_tree(response.content)
        brick_node = self.get_brick_node(doc, PropertiesBrick.id_)
        self.assertInstanceLink(brick_node, ptype01)
        self.assertInstanceLink(brick_node, ptype02)
        self.assertNoInstanceLink(brick_node, ptype03)

    def test_add_type01(self):
        self.login()

        url = self.ADD_TYPE_URL
        self.assertGET200(url)

        text = 'is beautiful'
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
        ct_ids = [get_ct(FakeContact).id, get_ct(FakeOrganisation).id]
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
                                         [ContentType.objects.get_for_model(FakeContact)],
                                         is_custom=False,
                                        )

        self.assertGET404(ptype.get_edit_absolute_url())

    def test_edit_type02(self):
        self.login()

        get_ct = ContentType.objects.get_for_model
        ptype = CremePropertyType.create('test-foobar', 'is beautiful',
                                         [get_ct(FakeContact)], is_custom=True,
                                        )

        url = ptype.get_edit_absolute_url()
        self.assertGET200(url)

        ct_orga = get_ct(FakeOrganisation)
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

    def test_delete_related(self):
        user = self.login()

        ptype  = CremePropertyType.create(str_pk='test-prop_foobar', text='hairy')
        entity = FakeContact.objects.create(user=user, last_name='Vrataski')
        prop   = CremeProperty.objects.create(type=ptype, creme_entity=entity)
        ct     = ContentType.objects.get_for_model(CremeProperty)

        response = self.assertPOST200(reverse('creme_core__delete_related_to_entity', args=(ct.id,)),
                                      follow=True, data={'id': prop.id},
                                     )
        self.assertRedirects(response, entity.get_absolute_url())
        self.assertDoesNotExist(prop)

    def test_delete_from_type(self):
        user = self.login()

        ptype = CremePropertyType.create(str_pk='test-prop_foobar', text='hairy')

        create_entity = partial(CremeEntity.objects.create, user=user)
        entity1 = create_entity()
        entity2 = create_entity()

        create_prop = partial(CremeProperty.objects.create, type=ptype)
        prop1 = create_prop(creme_entity=entity1)
        prop2 = create_prop(creme_entity=entity2)

        response = self.assertPOST200(reverse('creme_core__remove_property'), follow=True,
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

        self.assertGET200(self._build_bulk_url(self.centity_ct, *entities, GET=True))
        url = self._build_bulk_url(self.centity_ct)
        # self.assertGET200(url)

        ids = [e.id for e in entities]
        response = self.assertPOST200(url,
                                      data={'types': [],
                                            'ids':   ids,
                                           }
                                     )
        self.assertFormError(response, 'form', 'types', _(u'This field is required.'))

        response = self.client.post(url, data={'types': [ptype01.id, ptype02.id],
                                               'ids': ids,
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
        user = self.login(is_superuser=False)

        create_entity = CremeEntity.objects.create
        entity01 = create_entity(user=self.other_user)
        entity02 = create_entity(user=self.other_user)
        entity03 = create_entity(user=user)
        entity04 = create_entity(user=user)

        create_ptype = CremePropertyType.create
        ptype01 = create_ptype(str_pk='test-prop_foobar01', text='wears strange hats')
        ptype02 = create_ptype(str_pk='test-prop_foobar02', text='wears strange pants')

        has_perm = user.has_perm_to_change
        self.assertFalse(has_perm(entity01))
        self.assertFalse(has_perm(entity02))
        self.assertTrue(has_perm(entity03))

        response = self.assertGET200(self._build_bulk_url(self.centity_ct, entity01, entity02, entity03, entity04, GET=True))

        with self.assertNoException():
            label = response.context['form'].fields['bad_entities_lbl']

        format_str = _(u'Entity #%s (not viewable)')
        self.assertEqual(u'%s, %s' % (format_str % entity01.id,
                                      format_str % entity02.id
                                     ),
                         label.initial
                        )

        # response = self.client.post(url,
        response = self.client.post(self._build_bulk_url(self.centity_ct),
                                    data={'entities_lbl':     'do not care',
                                          'bad_entities_lbl': 'do not care',
                                          'types':            [ptype01.id, ptype02.id],
                                          'ids':              [entity01.id, entity02.id, entity03.id, entity04.id],
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

        response = self.assertGET200(self._build_bulk_url(self.centity_ct, uneditable, GET=True))

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

        self.assertGET200(self._build_bulk_url(self.centity_ct, entity01, uneditable, GET=True))

        response = self.client.post(self._build_bulk_url(self.centity_ct),
                                    data={'entities_lbl': 'd:p',
                                          'types':        [ptype01.id, ptype02.id],
                                          'ids':          [entity01.id, uneditable.id],
                                         }
                                   )
        self.assertNoFormError(response)

        def tagged_enties(ptype):
            return [p.creme_entity for p in CremeProperty.objects.filter(type=ptype)]

        self.assertEqual([entity01], tagged_enties(ptype01))
        self.assertEqual([entity01], tagged_enties(ptype02))

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
        user = self.login()
        ptype = CremePropertyType.create(str_pk='test-prop_murica', text='is american')

        create_contact = partial(FakeContact.objects.create, user=user)
        tagged_contact   = create_contact(last_name='Vrataski', first_name='Rita')
        untagged_contact = create_contact(last_name='Kiriya',   first_name='Keiji')

        tagged_orga = FakeOrganisation.objects.create(user=user, name='US Defense Force')

        create_prop = partial(CremeProperty.objects.create, type=ptype)
        create_prop(creme_entity=tagged_contact)
        create_prop(creme_entity=tagged_orga)

        response = self.assertGET200(ptype.get_absolute_url())
        self.assertTemplateUsed(response, 'creme_core/view_property_type.html')
        self.assertTemplateUsed(response, 'creme_core/bricks/ptype-info.html')
        self.assertTemplateUsed(response, 'creme_core/bricks/tagged-entities.html')

        with self.assertNoException():
            ctxt_ptype = response.context['object']
        self.assertEqual(ptype, ctxt_ptype)

        doc = self.get_html_tree(response.content)
        self.get_brick_node(doc, 'block_creme_core-property_type_info')

        contacts_brick_node = self.get_brick_node(doc, 'block_creme_core-tagged-creme_core-fakecontact')
        self.assertBrickHasNotClass(contacts_brick_node, 'is-empty')
        self.assertInstanceLink(contacts_brick_node, tagged_contact)
        self.assertNoInstanceLink(contacts_brick_node, untagged_contact)
        self.assertNoInstanceLink(contacts_brick_node, tagged_orga)

        orgas_brick_node = self.get_brick_node(doc, 'block_creme_core-tagged-creme_core-fakeorganisation')
        self.assertInstanceLink(orgas_brick_node, tagged_orga)
        self.assertNoInstanceLink(orgas_brick_node, tagged_contact)

        self.assertNoBrick(doc, 'block_creme_core-tagged-billing-fakeimage')
        self.assertNoBrick(doc, 'block_creme_core-misc_tagged_entities')

    def test_detailview02(self):
        "Misc brick"
        user = self.login()
        ptype = CremePropertyType.create(str_pk='test-prop_murica', text='is american',
                                         subject_ctypes=[FakeContact],
                                        )

        rita = FakeContact.objects.create(user=user, last_name='Vrataski', first_name='Rita')
        udf = FakeOrganisation.objects.create(user=user, name='US Defense Force')

        create_prop = partial(CremeProperty.objects.create, type=ptype)
        create_prop(creme_entity=rita)
        create_prop(creme_entity=udf)

        response = self.assertGET200(ptype.get_absolute_url())
        doc = self.get_html_tree(response.content)

        contacts_brick_node = self.get_brick_node(doc, 'block_creme_core-tagged-creme_core-fakecontact')
        self.assertInstanceLink(contacts_brick_node, rita)
        self.assertNoInstanceLink(contacts_brick_node, udf)

        misc_brick_node = self.get_brick_node(doc, 'block_creme_core-misc_tagged_entities')
        self.assertInstanceLink(misc_brick_node, udf)
        self.assertNoInstanceLink(misc_brick_node, rita)

        self.assertNoBrick(doc, 'block_creme_core-tagged-creme_core-fakeorganisation')

    # def test_reload_block01(self):
    #     user = self.login()
    #     ptype = CremePropertyType.create(str_pk='test-prop_murica', text='is american')
    #
    #     rita = FakeContact.objects.create(user=user, last_name='Vrataski', first_name='Rita')
    #     CremeProperty.objects.create(type=ptype, creme_entity=rita)
    #
    #     block_id = 'block_creme_core-tagged-creme_core-fakecontact'
    #     response = self.assertGET200(reverse('creme_core__reload_ptype_blocks', args=(ptype.id, block_id)))
    #
    #     with self.assertNoException():
    #         result = json.loads(response.content)
    #
    #     self.assertIsInstance(result, list)
    #     self.assertEqual(1, len(result))
    #
    #     result = result[0]
    #     self.assertIsInstance(result, list)
    #     self.assertEqual(2, len(result))
    #     self.assertEqual(block_id, result[0])
    #
    #     block_html = result[1]
    #     self.assertIn(' id="%s"' % block_id, block_html)
    #     self.assertIn(unicode(rita), block_html)
    #
    #     self.assertGET404(reverse('creme_core__reload_ptype_blocks', args=(ptype.id, 'invalid_blockid')))
    #     self.assertGET404(reverse('creme_core__reload_ptype_blocks', args=(ptype.id, 'block_creme_core-tagged-persons-invalidmodel')))
    #     self.assertGET404(reverse('creme_core__reload_ptype_blocks', args=(ptype.id, 'block_creme_core-tagged-persons-civility')))

    # def test_reload_block02(self):
    #     "Misc block + info block"
    #     user = self.login()
    #     ptype = CremePropertyType.create(str_pk='test-prop_murica', text='is american',
    #                                      subject_ctypes=[FakeOrganisation],
    #                                      )
    #
    #     rita = FakeContact.objects.create(user=user, last_name='Vrataski', first_name='Rita')
    #     CremeProperty.objects.create(type=ptype, creme_entity=rita)
    #
    #     misc_block_id = 'block_creme_core-misc_tagged_entities'
    #     info_block_id = 'block_creme_core-property_type_info'
    #
    #     response = self.assertGET200(reverse('creme_core__reload_ptype_blocks', args=(ptype.id, misc_block_id)),
    #                                  data={misc_block_id + '_deps': info_block_id},
    #                                 )
    #
    #     with self.assertNoException():
    #         result = json.loads(response.content)
    #
    #     self.assertEqual(2, len(result))
    #     self.assertIn(' id="%s"' % misc_block_id, result[0][1])
    #     self.assertIn(' id="%s"' % info_block_id, result[1][1])

    def test_reload_ptype_bricks01(self):
        user = self.login()
        ptype = CremePropertyType.create(str_pk='test-prop_murica', text='is american')

        rita = FakeContact.objects.create(user=user, last_name='Vrataski', first_name='Rita')
        CremeProperty.objects.create(type=ptype, creme_entity=rita)

        brick_id = 'block_creme_core-tagged-creme_core-fakecontact'
        url = reverse('creme_core__reload_ptype_bricks', args=(ptype.id,))
        response = self.assertGET200(url, data={'brick_id': brick_id})

        with self.assertNoException():
            result = json.loads(response.content)

        self.assertIsInstance(result, list)
        self.assertEqual(1, len(result))

        result = result[0]
        self.assertIsInstance(result, list)
        self.assertEqual(2, len(result))
        self.assertEqual(brick_id, result[0])

        document = self.get_html_tree(result[1])
        brick_node = self.get_brick_node(document, brick_id)
        self.assertInstanceLink(brick_node, rita)

        self.assertGET404(url, data={'brick_id': 'invalid_brickid'})
        self.assertGET404(url, data={'brick_id': 'block_creme_core-tagged-persons-invalidmodel'})
        self.assertGET404(url, data={'brick_id': 'block_creme_core-tagged-persons-civility'})

    def test_reload_ptype_bricks02(self):
        "Misc brick + info brick"
        user = self.login()
        ptype = CremePropertyType.create(str_pk='test-prop_murica', text='is american',
                                         subject_ctypes=[FakeOrganisation],
                                        )

        rita = FakeContact.objects.create(user=user, last_name='Vrataski', first_name='Rita')
        CremeProperty.objects.create(type=ptype, creme_entity=rita)

        misc_brick_id = 'block_creme_core-misc_tagged_entities'
        info_brick_id = 'block_creme_core-property_type_info'

        response = self.assertGET200(reverse('creme_core__reload_ptype_bricks', args=(ptype.id,)),
                                     data={'brick_id': [misc_brick_id, info_brick_id]},
                                    )

        with self.assertNoException():
            result = json.loads(response.content)

        self.assertEqual(2, len(result))

        doc1 = self.get_html_tree(result[0][1])
        self.get_brick_node(doc1, misc_brick_id)

        doc2 = self.get_html_tree(result[1][1])
        self.get_brick_node(doc2, info_brick_id)

    def test_reload_ptype_bricks03(self):
        "Empty block"
        self.login()
        ptype = CremePropertyType.create(str_pk='test-prop_murica', text='is american')

        brick_id = 'block_creme_core-tagged-persons-contact'
        response = self.assertGET200(reverse('creme_core__reload_ptype_bricks', args=(ptype.id,)),
                                     data={'brick_id': brick_id},
                                     HTTP_X_REQUESTED_WITH='XMLHttpRequest',
                                    )

        with self.assertNoException():
            result = json.loads(response.content)

        self.assertEqual(1, len(result))
        doc = self.get_html_tree(result[0][1])
        brick_node = self.get_brick_node(doc, brick_id)
        self.assertBrickHasClass(brick_node,'is-empty')

    def test_inneredit(self):
        user = self.login()
        ptype  = CremePropertyType.create(str_pk='test-prop_foobar', text='hairy')
        entity = CremeEntity.objects.create(user=user)
        prop   = CremeProperty.objects.create(type=ptype, creme_entity=entity)

        build_url = self.build_inneredit_url
        self.assertGET(400, build_url(prop, 'type'))
        self.assertGET(400, build_url(prop, 'creme_entity'))
