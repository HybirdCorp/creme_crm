from functools import partial

from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from django.utils.translation import gettext as _

from creme.creme_core.auth.entity_credentials import EntityCredentials
from creme.creme_core.bricks import PropertiesBrick
from creme.creme_core.models import (
    CremeEntity,
    CremeProperty,
    CremePropertyType,
)

from ..fake_models import FakeContact, FakeOrganisation
from .base import BrickTestCaseMixin, ViewsTestCase


class PropertyViewsTestCase(ViewsTestCase, BrickTestCaseMixin):
    ADD_TYPE_URL = reverse('creme_core__create_ptype')

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.centity_ct = ContentType.objects.get_for_model(CremeEntity)

    def assertEntityHasProperty(self, ptype, entity):
        self.assertTrue(entity.properties.filter(type=ptype).exists())

    def assertEntityHasntProperty(self, ptype, entity):
        self.assertFalse(entity.properties.filter(type=ptype).exists())

    @staticmethod
    def _build_bulk_url(ct, *entities, **kwargs):
        url = reverse('creme_core__add_properties_bulk', args=(ct.id,))

        if kwargs.get('GET', False):
            url += '?' + '&'.join(f'ids={e.id}' for e in entities)

        return url

    def test_add(self):
        # user = self.login()
        user = self.login_as_root_and_get()

        create_ptype = CremePropertyType.objects.smart_update_or_create
        ptype01 = create_ptype(str_pk='test-prop_foobar01', text='Wears strange gloves')
        ptype02 = create_ptype(str_pk='test-prop_foobar02', text='Wears strange glasses')
        ptype03 = create_ptype(
            str_pk='test-prop_foobar03', text='Wears strange hats',
            subject_ctypes=[FakeContact],
        )
        ptype04 = create_ptype(
            str_pk='test-prop_foobar04', text='Is a fundation',
            subject_ctypes=[FakeOrganisation],
        )

        ptype05 = create_ptype(str_pk='test-prop_disabled', text='Disabled')
        ptype05.enabled = False
        ptype05.save()

        entity = FakeContact.objects.create(
            user=user, first_name='Spike', last_name='Spiegel',
        )
        self.assertFalse(entity.properties.all())

        url = reverse('creme_core__add_properties', args=(entity.id,))
        context1 = self.assertGET200(url).context
        self.assertEqual(
            _('New properties for «{entity}»').format(entity=entity),
            context1.get('title'),
        )
        self.assertEqual(_('Add the properties'), context1.get('submit_label'))

        with self.assertNoException():
            choices = context1['form'].fields['types'].choices

        # Choices are sorted with 'text'
        choices = [*choices]
        i1 = self.assertIndex((ptype02.id, ptype02.text), choices)
        i2 = self.assertIndex((ptype01.id, ptype01.text), choices)
        i3 = self.assertIndex((ptype03.id, ptype03.text), choices)
        self.assertLess(i1, i2)
        self.assertLess(i2, i3)

        self.assertNotInChoices(value=ptype04.id, choices=choices)
        self.assertNotInChoices(value=ptype05.id, choices=choices)

        self.assertNoFormError(self.client.post(url, data={'types': [ptype01.id, ptype02.id]}))
        self.assertCountEqual([ptype01, ptype02], [p.type for p in entity.properties.all()])

        # ----------------------------------------------------------------------
        # One new and one old property
        response2 = self.assertPOST200(url, data={'types': [ptype01.id, ptype03.id]})
        self.assertFormError(
            response2.context['form'],
            field='types',
            errors=_(
                'Select a valid choice. %(value)s is not one of the available choices.'
            ) % {'value': ptype01.id},
        )

    def test_properties_brick(self):
        # user = self.login()
        user = self.login_as_root_and_get()

        create_ptype = CremePropertyType.objects.smart_update_or_create
        ptype01 = create_ptype(str_pk='test-prop_foobar01', text='Uses guns')
        ptype02 = create_ptype(str_pk='test-prop_foobar02', text='Uses blades')
        ptype03 = create_ptype(str_pk='test-prop_foobar03', text='Uses drugs')

        rita = FakeContact.objects.create(
            user=user, last_name='Vrataski', first_name='Rita',
        )

        create_prop = partial(CremeProperty.objects.create, creme_entity=rita)
        create_prop(type=ptype01)
        create_prop(type=ptype02)

        response = self.assertGET200(rita.get_absolute_url())
        doc = self.get_html_tree(response.content)
        brick_node = self.get_brick_node(doc, brick=PropertiesBrick)
        self.assertInstanceLink(brick_node, ptype01)
        self.assertInstanceLink(brick_node, ptype02)
        self.assertNoInstanceLink(brick_node, ptype03)

    def test_add_type01(self):
        # self.login()
        self.login_as_root()

        url = self.ADD_TYPE_URL
        referer_url = reverse('creme_core__my_page')
        # response1 = self.assertGET200(url, HTTP_REFERER='http://testserver' + referer_url)
        response1 = self.assertGET200(url, headers={'referer': f'http://testserver{referer_url}'})
        self.assertTemplateUsed(response1, 'creme_core/generics/blockform/add.html')

        get_ctxt = response1.context.get
        self.assertEqual(CremePropertyType.creation_label, get_ctxt('title'))
        self.assertEqual(_('Save the type of property'),   get_ctxt('submit_label'))
        self.assertEqual(referer_url,                      get_ctxt('cancel_url'))

        text = 'is beautiful'
        self.assertFalse(CremePropertyType.objects.filter(text=text))

        # ---
        response2 = self.client.post(url, follow=True, data={'text': text})
        self.assertNoFormError(response2)

        ptype = self.get_object_or_fail(CremePropertyType, text=text)
        self.assertFalse(ptype.subject_ctypes.all())
        self.assertFalse(ptype.is_copiable)

        self.assertRedirects(response2, ptype.get_absolute_url())

    def test_add_type02(self):
        "Constraints on ContentTypes, 'is_copiable'."
        # self.login()
        self.login_as_root()

        get_ct = ContentType.objects.get_for_model
        models = [FakeContact, FakeOrganisation]
        text = 'is beautiful'
        response = self.client.post(
            self.ADD_TYPE_URL,
            follow=True,
            data={
                'text':           text,
                'subject_ctypes': [get_ct(model).id for model in models],
                'is_copiable':    'on',
            },
        )
        self.assertNoFormError(response)

        ptype = self.get_object_or_fail(CremePropertyType, text=text)
        self.assertTrue(ptype.is_copiable)
        self.assertCountEqual(models, [*ptype.subject_models])

    def test_add_type03(self):
        "Not allowed."
        # self.login(is_superuser=False)
        self.login_as_standard()
        self.assertGET403(self.ADD_TYPE_URL)

    def test_add_type04(self):
        "Not super-user."
        # self.login(is_superuser=False, admin_4_apps=('creme_core',))
        self.login_as_standard(admin_4_apps=('creme_core',))
        self.assertGET200(self.ADD_TYPE_URL)

    def test_edit_type01(self):
        "is_custom=False."
        # self.login()
        self.login_as_root()
        ptype = CremePropertyType.objects.smart_update_or_create(
            str_pk='test-foobar', text='is beautiful',
            subject_ctypes=[FakeContact],
            is_custom=False,
        )

        self.assertGET404(ptype.get_edit_absolute_url())

    def test_edit_type02(self):
        # self.login()
        self.login_as_root()

        ptype = CremePropertyType.objects.smart_update_or_create(
            str_pk='test-foobar', text='is beautiful',
            subject_ctypes=[FakeContact], is_custom=True,
        )

        url = ptype.get_edit_absolute_url()
        referer_url = reverse('creme_core__my_page')
        # response1 = self.assertGET200(url, HTTP_REFERER='http://testserver' + referer_url)
        response1 = self.assertGET200(url, headers={'referer': f'http://testserver{referer_url}'})
        self.assertTemplateUsed(response1, 'creme_core/generics/blockform/edit.html')

        get_ctxt = response1.context.get
        self.assertEqual(_('Edit «{object}»').format(object=ptype), get_ctxt('title'))
        self.assertEqual(_('Save the modifications'),               get_ctxt('submit_label'))
        self.assertEqual(referer_url,                               get_ctxt('cancel_url'))

        # ---
        model = FakeOrganisation
        text = 'is very beautiful'
        response2 = self.client.post(
            url,
            follow=True,
            data={
                'text':           text,
                'subject_ctypes': [ContentType.objects.get_for_model(model).id],
            },
        )
        self.assertNoFormError(response2)
        self.assertRedirects(response2, ptype.get_absolute_url())

        ptype = self.refresh(ptype)
        self.assertEqual(text, ptype.text)
        self.assertListEqual([model], [*ptype.subject_models])

    def test_edit_type03(self):
        "Not allowed."
        # self.login(is_superuser=False)
        self.login_as_standard()
        ptype = CremePropertyType.objects.smart_update_or_create(
            str_pk='test-foobar', text='is beautiful', is_custom=True,
        )
        self.assertGET403(ptype.get_edit_absolute_url())

    def test_edit_type04(self):
        "Not super-user."
        # self.login(is_superuser=False, admin_4_apps=('creme_core',))
        self.login_as_standard(admin_4_apps=('creme_core',))
        ptype = CremePropertyType.objects.smart_update_or_create(
            str_pk='test-foobar', text='is beautiful', is_custom=True,
        )
        self.assertGET200(ptype.get_edit_absolute_url())

    def test_edit_type05(self):
        "Disabled=True."
        # self.login()
        self.login_as_root()
        ptype = CremePropertyType.objects.smart_update_or_create(
            str_pk='test-foobar', text='is beautiful', is_custom=True,
        )
        ptype.enabled = False
        ptype.save()

        self.assertGET404(ptype.get_edit_absolute_url())

    def test_delete_related01(self):
        # user = self.login(is_superuser=False)
        user = self.login_as_standard()
        self._set_all_perms_on_own(user)

        ptype = CremePropertyType.objects.smart_update_or_create(
            str_pk='test-prop_foobar', text='hairy',
        )
        entity = FakeContact.objects.create(user=user, last_name='Vrataski')
        prop = CremeProperty.objects.create(type=ptype, creme_entity=entity)
        get_ct = ContentType.objects.get_for_model
        ct = get_ct(CremeProperty)

        response = self.assertPOST200(
            reverse('creme_core__delete_related_to_entity', args=(ct.id,)),
            follow=True, data={'id': prop.id},
        )
        self.assertRedirects(response, entity.get_absolute_url())
        self.assertDoesNotExist(prop)

        # ---
        self.assertPOST409(
            reverse('creme_core__delete_related_to_entity', args=(get_ct(CremeEntity).id,)),
            follow=True, data={'id': entity.id},
        )
        self.assertPOST409(
            reverse('creme_core__delete_related_to_entity', args=(get_ct(CremePropertyType).id,)),
            follow=True, data={'id': ptype.id},
        )

    def test_delete_related02(self):
        "Not allowed to change the related entity."
        # self.login(is_superuser=False)
        user = self.login_as_standard()
        # self._set_all_creds_except_one(EntityCredentials.CHANGE)
        self._set_all_creds_except_one(user=user, excluded=EntityCredentials.CHANGE)

        ptype = CremePropertyType.objects.smart_update_or_create(
            str_pk='test-prop_foobar', text='hairy',
        )
        # entity = FakeContact.objects.create(user=self.other_user, last_name='Vrataski')
        entity = FakeContact.objects.create(user=self.get_root_user(), last_name='Vrataski')
        prop = CremeProperty.objects.create(type=ptype, creme_entity=entity)
        ct = ContentType.objects.get_for_model(CremeProperty)

        self.assertPOST403(
            reverse('creme_core__delete_related_to_entity', args=(ct.id,)),
            follow=True, data={'id': prop.id},
        )

    def test_delete_from_type(self):
        # user = self.login()
        user = self.login_as_root_and_get()

        ptype = CremePropertyType.objects.smart_update_or_create(
            str_pk='test-prop_foobar', text='hairy',
        )

        create_entity = partial(CremeEntity.objects.create, user=user)
        entity1 = create_entity()
        entity2 = create_entity()

        create_prop = partial(CremeProperty.objects.create, type=ptype)
        prop1 = create_prop(creme_entity=entity1)
        prop2 = create_prop(creme_entity=entity2)

        response = self.assertPOST200(
            reverse('creme_core__remove_property'), follow=True,
            data={'ptype_id': ptype.id, 'entity_id': entity1.id},
        )
        self.assertRedirects(response, ptype.get_absolute_url())
        self.assertDoesNotExist(prop1)
        self.assertStillExists(prop2)

    def test_delete_type01(self):
        # self.login()
        self.login_as_root()
        ptype = CremePropertyType.objects.smart_update_or_create(
            str_pk='test-foobar', text='is beautiful', is_custom=False,
        )
        self.assertPOST404(ptype.get_delete_absolute_url())

    def test_delete_type02(self):
        # self.login(is_superuser=False, admin_4_apps=['creme_core'])
        self.login_as_standard(admin_4_apps=['creme_core'])
        ptype = CremePropertyType.objects.smart_update_or_create(
            str_pk='test-foobar', text='is beautiful', is_custom=True,
        )
        response = self.assertPOST200(ptype.get_delete_absolute_url(), follow=True)
        self.assertDoesNotExist(ptype)
        self.assertRedirects(response, CremePropertyType.get_lv_absolute_url())

    def test_delete_type03(self):
        "Not allowed to admin <creme_core>."
        # self.login(is_superuser=False)
        self.login_as_standard()
        ptype = CremePropertyType.objects.smart_update_or_create(
            str_pk='test-foobar', text='is beautiful', is_custom=True,
        )
        self.assertPOST403(ptype.get_delete_absolute_url(), follow=True)

    def test_add_properties_bulk01(self):
        # user = self.login()
        user = self.login_as_root_and_get()

        create_ptype = CremePropertyType.objects.smart_update_or_create
        ptype01 = create_ptype(str_pk='test-prop_blip', text='Makes BLIPs')
        ptype02 = create_ptype(str_pk='test-prop_holo', text='Projects holograms')
        ptype03 = create_ptype(
            str_pk='test-prop_droid', text='Is a droid', subject_ctypes=[FakeContact],
        )
        ptype04 = create_ptype(
            str_pk='test-prop_ship', text='Is a ship', subject_ctypes=[FakeOrganisation],
        )

        ptype05 = create_ptype(str_pk='test-prop_disabled', text='Disabled')
        ptype05.enabled = False
        ptype05.save()

        create_contact = partial(FakeContact.objects.create, user=user)
        entities = [
            create_contact(first_name=f'R{i}', last_name=f'D{i}')
            for i in range(1, 6)
        ]

        for entity in entities:
            self.assertEqual(0, entity.properties.count())

        response1 = self.assertGET200(
            self._build_bulk_url(entities[0].entity_type, *entities, GET=True)
        )
        self.assertTemplateUsed(response1, 'creme_core/generics/blockform/add-popup.html')

        context1 = response1.context
        get_ctxt1 = context1.get
        self.assertEqual(_('Multiple adding of properties'), get_ctxt1('title'))
        self.assertEqual(_('Add the properties'),            get_ctxt1('submit_label'))

        with self.assertNoException():
            ptypes_choices = context1['form'].fields['types'].choices

        choices = [(choice[0].value, choice[1]) for choice in ptypes_choices]
        self.assertInChoices(value=ptype03.id, label=ptype03.text, choices=choices)
        self.assertInChoices(value=ptype01.id, label=ptype01.text, choices=choices)
        self.assertInChoices(value=ptype02.id, label=ptype02.text, choices=choices)

        self.assertNotInChoices(ptype04.id, choices)
        self.assertNotInChoices(ptype05.id, choices)

        # ---
        url = self._build_bulk_url(self.centity_ct)
        ids = [e.id for e in entities]
        response2 = self.assertPOST200(url, data={'types': [], 'ids': ids})
        self.assertFormError(
            response2.context['form'],
            field='types', errors=_('This field is required.'),
        )

        # ---
        response3 = self.client.post(
            url,
            data={
                'types': [ptype01.id, ptype02.id],
                'ids': ids,
                'entities_lbl': '',
            },
        )
        self.assertNoFormError(response3)

        for entity in entities:
            self.assertEqual(2, entity.properties.count())
            self.assertEntityHasProperty(ptype01,   entity)
            self.assertEntityHasProperty(ptype02,   entity)
            self.assertEntityHasntProperty(ptype03, entity)

    def test_add_properties_bulk02(self):
        # user = self.login(is_superuser=False)
        user = self.login_as_standard()
        self._set_all_perms_on_own(user)
        # other_user = self.other_user
        other_user = self.get_root_user()

        create_entity = CremeEntity.objects.create
        entity1 = create_entity(user=other_user)
        entity2 = create_entity(user=other_user)
        entity3 = create_entity(user=user)
        entity4 = create_entity(user=user)

        create_ptype = CremePropertyType.objects.smart_update_or_create
        ptype1 = create_ptype(str_pk='test-prop_foobar1', text='wears strange hats')
        ptype2 = create_ptype(str_pk='test-prop_foobar2', text='wears strange pants')

        has_perm = user.has_perm_to_change
        self.assertFalse(has_perm(entity1))
        self.assertFalse(has_perm(entity2))
        self.assertTrue(has_perm(entity3))

        response = self.assertGET200(
            self._build_bulk_url(
                self.centity_ct, entity1, entity2, entity3, entity4,
                GET=True,
            )
        )

        with self.assertNoException():
            label = response.context['form'].fields['bad_entities_lbl']

        msg_fmt = _('Entity #{id} (not viewable)').format
        self.assertCountEqual(
            [msg_fmt(id=entity1.id), msg_fmt(id=entity2.id)],
            label.initial.split(', '),
        )

        response = self.client.post(
            self._build_bulk_url(self.centity_ct),
            data={
                'entities_lbl':     'do not care',
                'bad_entities_lbl': 'do not care',
                'types': [ptype1.id, ptype2.id],
                'ids': [entity1.id, entity2.id, entity3.id, entity4.id],
            },
        )
        self.assertNoFormError(response)

        self.assertEqual(0, entity1.properties.count())
        self.assertEqual(0, entity2.properties.count())
        self.assertEqual(2, entity3.properties.count())
        self.assertEqual(2, entity4.properties.count())

        self.assertEntityHasntProperty(ptype1, entity1)
        self.assertEntityHasntProperty(ptype2, entity1)
        self.assertEntityHasntProperty(ptype1, entity2)
        self.assertEntityHasntProperty(ptype2, entity2)

        self.assertEntityHasProperty(ptype1, entity3)
        self.assertEntityHasProperty(ptype2, entity3)
        self.assertEntityHasProperty(ptype1, entity4)
        self.assertEntityHasProperty(ptype2, entity4)

    def test_add_properties_bulk03(self):
        # self.login(is_superuser=False)
        user = self.login_as_standard()

        # self._set_all_creds_except_one(excluded=EntityCredentials.CHANGE)
        self._set_all_creds_except_one(user=user, excluded=EntityCredentials.CHANGE)
        # uneditable = CremeEntity.objects.create(user=self.other_user)
        uneditable = CremeEntity.objects.create(user=self.get_root_user())

        self.assertTrue(user.has_perm_to_view(uneditable))
        self.assertFalse(user.has_perm_to_change(uneditable))

        response = self.assertGET200(
            self._build_bulk_url(self.centity_ct, uneditable, GET=True)
        )

        with self.assertNoException():
            label = response.context['form'].fields['bad_entities_lbl']

        self.assertEqual(str(uneditable), label.initial)

    def test_add_properties_bulk04(self):
        # user =self.login(is_superuser=False)
        user = self.login_as_standard()
        self._set_all_perms_on_own(user)

        create_ptype = CremePropertyType.objects.smart_update_or_create
        ptype01 = create_ptype(str_pk='test-prop_foobar01', text='wears strange hats')
        ptype02 = create_ptype(str_pk='test-prop_foobar02', text='wears strange pants')

        # self._set_all_creds_except_one(excluded=EntityCredentials.CHANGE)
        self._set_all_creds_except_one(user=user, excluded=EntityCredentials.CHANGE)
        entity = CremeEntity.objects.create(user=user)
        # uneditable = CremeEntity.objects.create(user=self.other_user)
        uneditable = CremeEntity.objects.create(user=self.get_root_user())

        self.assertGET200(
            self._build_bulk_url(self.centity_ct, entity, uneditable, GET=True)
        )

        response = self.client.post(
            self._build_bulk_url(self.centity_ct),
            data={
                'entities_lbl': 'd:p',
                'types': [ptype01.id, ptype02.id],
                'ids': [entity.id, uneditable.id],
            },
        )
        self.assertNoFormError(response)

        def tagged_entities(ptype):
            return [
                p.creme_entity for p in CremeProperty.objects.filter(type=ptype)
            ]

        self.assertListEqual([entity], tagged_entities(ptype01))
        self.assertListEqual([entity], tagged_entities(ptype02))

    def test_not_copiable_properties(self):
        # user = self.login()
        user = self.login_as_root_and_get()

        create_ptype = CremePropertyType.objects.smart_update_or_create
        ptype01 = create_ptype(
            str_pk='test-prop_foobar01', text='wears strange hats', is_copiable=False,
        )
        ptype02 = create_ptype(
            str_pk='test-prop_foobar02', text='wears strange pants',
        )

        entity = CremeEntity.objects.create(user=user)

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
        # user = self.login()
        user = self.login_as_root_and_get()
        ptype = CremePropertyType.objects.smart_update_or_create(
            str_pk='test-prop_murica', text='is american',
        )

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
        self.assertEqual(
            reverse('creme_core__reload_ptype_bricks', args=(ptype.id,)),
            response.context.get('bricks_reload_url'),
        )

        with self.assertNoException():
            ctxt_ptype = response.context['object']
        self.assertEqual(ptype, ctxt_ptype)

        doc = self.get_html_tree(response.content)
        self.get_brick_node(doc, 'block_creme_core-property_type_info')

        contacts_brick_node = self.get_brick_node(
            doc, 'block_creme_core-tagged-creme_core-fakecontact',
        )
        self.assertBrickHasNotClass(contacts_brick_node, 'is-empty')
        self.assertInstanceLink(contacts_brick_node, tagged_contact)
        self.assertNoInstanceLink(contacts_brick_node, untagged_contact)
        self.assertNoInstanceLink(contacts_brick_node, tagged_orga)

        orgas_brick_node = self.get_brick_node(
            doc, 'block_creme_core-tagged-creme_core-fakeorganisation',
        )
        self.assertInstanceLink(orgas_brick_node, tagged_orga)
        self.assertNoInstanceLink(orgas_brick_node, tagged_contact)

        self.assertNoBrick(doc, 'block_creme_core-tagged-billing-fakeimage')
        self.assertNoBrick(doc, 'block_creme_core-misc_tagged_entities')

    def test_detailview02(self):
        "Misc brick."
        # user = self.login()
        user = self.login_as_root_and_get()
        ptype = CremePropertyType.objects.smart_update_or_create(
            str_pk='test-prop_murica', text='is american',
            subject_ctypes=[FakeContact],
        )

        rita = FakeContact.objects.create(
            user=user, last_name='Vrataski', first_name='Rita',
        )
        udf = FakeOrganisation.objects.create(user=user, name='US Defense Force')

        create_prop = partial(CremeProperty.objects.create, type=ptype)
        create_prop(creme_entity=rita)
        create_prop(creme_entity=udf)

        response = self.assertGET200(ptype.get_absolute_url())
        doc = self.get_html_tree(response.content)

        contacts_brick_node = self.get_brick_node(
            doc, 'block_creme_core-tagged-creme_core-fakecontact',
        )
        self.assertInstanceLink(contacts_brick_node, rita)
        self.assertNoInstanceLink(contacts_brick_node, udf)

        misc_brick_node = self.get_brick_node(doc, 'block_creme_core-misc_tagged_entities')
        self.assertInstanceLink(misc_brick_node, udf)
        self.assertNoInstanceLink(misc_brick_node, rita)

        self.assertNoBrick(doc, 'block_creme_core-tagged-creme_core-fakeorganisation')

    def test_reload_ptype_bricks01(self):
        # user = self.login()
        user = self.login_as_root_and_get()
        ptype = CremePropertyType.objects.smart_update_or_create(
            str_pk='test-prop_murica', text='is american',
        )

        rita = FakeContact.objects.create(user=user, last_name='Vrataski', first_name='Rita')
        CremeProperty.objects.create(type=ptype, creme_entity=rita)

        brick_id = 'block_creme_core-tagged-creme_core-fakecontact'
        url = reverse('creme_core__reload_ptype_bricks', args=(ptype.id,))
        response = self.assertGET200(url, data={'brick_id': brick_id})

        with self.assertNoException():
            results = response.json()

        self.assertIsList(results, length=1)

        result = results[0]
        self.assertIsList(result, length=2)
        self.assertEqual(brick_id, result[0])

        document = self.get_html_tree(result[1])
        brick_node = self.get_brick_node(document, brick_id)
        self.assertInstanceLink(brick_node, rita)

        self.assertGET404(url, data={'brick_id': 'invalid_brickid'})
        self.assertGET404(url, data={'brick_id': 'block_creme_core-tagged-persons-invalidmodel'})
        self.assertGET404(url, data={'brick_id': 'block_creme_core-tagged-persons-civility'})

    def test_reload_ptype_bricks02(self):
        "Misc brick + info brick."
        # user = self.login()
        user = self.login_as_root_and_get()
        ptype = CremePropertyType.objects.smart_update_or_create(
            str_pk='test-prop_murica', text='is american',
            subject_ctypes=[FakeOrganisation],
        )

        rita = FakeContact.objects.create(
            user=user, last_name='Vrataski', first_name='Rita',
        )
        CremeProperty.objects.create(type=ptype, creme_entity=rita)

        misc_brick_id = 'block_creme_core-misc_tagged_entities'
        info_brick_id = 'block_creme_core-property_type_info'

        response = self.assertGET200(
            reverse('creme_core__reload_ptype_bricks', args=(ptype.id,)),
            data={'brick_id': [misc_brick_id, info_brick_id]},
        )

        with self.assertNoException():
            result = response.json()

        self.assertEqual(2, len(result))

        doc1 = self.get_html_tree(result[0][1])
        self.get_brick_node(doc1, misc_brick_id)

        doc2 = self.get_html_tree(result[1][1])
        self.get_brick_node(doc2, info_brick_id)

    def test_reload_ptype_bricks03(self):
        "Empty brick."
        # self.login()
        self.login_as_root()
        ptype = CremePropertyType.objects.smart_update_or_create(
            str_pk='test-prop_murica', text='is american',
        )

        brick_id = 'block_creme_core-tagged-persons-contact'
        response = self.assertGET200(
            reverse('creme_core__reload_ptype_bricks', args=(ptype.id,)),
            data={'brick_id': brick_id},
            # HTTP_X_REQUESTED_WITH='XMLHttpRequest',
            headers={'X-Requested-With': 'XMLHttpRequest'},
        )

        with self.assertNoException():
            result = response.json()

        brick_data = self.get_alone_element(result)
        doc = self.get_html_tree(brick_data[1])
        brick_node = self.get_brick_node(doc, brick_id)
        self.assertBrickHasClass(brick_node, 'is-empty')
