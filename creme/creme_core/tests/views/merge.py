# -*- coding: utf-8 -*-

try:
    from datetime import timedelta
    from functools import partial

    from django.contrib.contenttypes.models import ContentType
    from django.utils.translation import ugettext as _

    from .base import ViewsTestCase
    from creme.creme_core.auth.entity_credentials import EntityCredentials
    from creme.creme_core.models import (RelationType, Relation, SetCredentials,
            CremePropertyType, CremeProperty, CustomField, CustomFieldEnumValue) #Language
    from creme.creme_core.models.history import (HistoryLine, TYPE_EDITION,
            TYPE_RELATION, TYPE_RELATION_DEL, TYPE_SYM_REL_DEL,
            TYPE_PROP_ADD, TYPE_PROP_DEL)

    from creme.persons.models import Organisation, Contact
except Exception as e:
    print('Error in <%s>: %s' % (__name__, e))


__all__ = ('MergeViewsTestCase', )


class MergeViewsTestCase(ViewsTestCase):
    @classmethod
    def setUpClass(cls):
        cls.populate('creme_core', 'creme_config', 'persons') #'persons' for HeaderFilter

    def _build_select_url(self, e1):
        return '/creme_core/entity/merge/select_other/%s' % e1.id

    def _oldify(self, entity, hours_delta=1):
        mdate = entity.modified - timedelta(hours=hours_delta)
        entity.__class__.objects.filter(pk=entity.pk).update(modified=mdate)

    def test_select_entity_for_merge01(self):
        self.login()

        create_orga = partial(Organisation.objects.create, user=self.user)
        orga01 = create_orga(name='Genshiken')
        orga02 = create_orga(name='Gen-shi-ken')
        orga03 = create_orga(name='Manga Club')

        response = self.assertGET200(self._build_select_url(orga01))

        with self.assertNoException():
            contacts = response.context['entities'].object_list

        contacts = set(contacts)
        self.assertIn(orga02, contacts)
        self.assertIn(orga03, contacts)
        self.assertNotIn(orga01, contacts)

    def test_select_entity_for_merge02(self):
        "View credentials"
        self.login(is_superuser=False, allowed_apps=['persons'])

        SetCredentials.objects.create(
                role=self.role,
                value=EntityCredentials.VIEW | EntityCredentials.CHANGE | EntityCredentials.DELETE,
                set_type=SetCredentials.ESET_OWN
            )
        orga = Organisation.objects.create(user=self.other_user, name='Genshiken')
        self.assertFalse(self.user.has_perm_to_view(orga))
        self.assertGET403(self._build_select_url(orga))

    def test_select_entity_for_merge03(self):
        "Edit credentials"
        self.login(is_superuser=False, allowed_apps=['persons'])

        SetCredentials.objects.create(role=self.role,
                                      value=EntityCredentials.VIEW,
                                      set_type=SetCredentials.ESET_ALL
                                     )
        orga = Organisation.objects.create(user=self.other_user, name='Genshiken')
        self.assertTrue(self.user.has_perm_to_view(orga))
        self.assertFalse(self.user.has_perm_to_change(orga))
        self.assertGET403(self._build_select_url(orga))

    def test_merge01(self):
        "2 Organisations"
        self.login()

        rtype = RelationType.create(('test-subject_member', 'is a member of'),
                                    ('test-object_member',  'has as a member')
                                   )[0]

        create_ptype = CremePropertyType.create
        ptype01 = create_ptype(str_pk='test-prop_manga', text='Manga related')
        ptype02 = create_ptype(str_pk='test-prop_anime', text='Anime related')

        user = self.user
        create_orga = partial(Organisation.objects.create, user=user)
        orga01 = create_orga(name='Genshiken',   description='Otaku band.',   phone='8787878')
        orga02 = create_orga(name='Gen-shi-ken', description='A great club.', email='genshiken@univ.jp')

        create_contact = partial(Contact.objects.create, user=user)
        contact01 = create_contact(first_name='Chika',       last_name='Ogiue')
        contact02 = create_contact(first_name=u'Souichirou', last_name='Tanaka')

        # contact01 linked with the 2 organisations -> after merge, we expect only one relation, not 2
        # contact02 should be linked to the merged entity
        create_rel = partial(Relation.objects.create, user=user, type=rtype)
        rel1 = create_rel(subject_entity=contact01, object_entity=orga01)
        rel2 = create_rel(subject_entity=contact01, object_entity=orga02)
        rel3 = create_rel(subject_entity=contact02, object_entity=orga02)

        #'prop3 'should be deleted, because orga01 has already a property with the same type
        create_prop = CremeProperty.objects.create
        prop1 = create_prop(type=ptype01, creme_entity=orga01)
        prop2 = create_prop(type=ptype02, creme_entity=orga02)
        prop3 = create_prop(type=ptype01, creme_entity=orga02)

        last_hline_id = HistoryLine.objects.order_by('-id')[0].id

        old_modified = orga01.modified
        self._oldify(orga01)
        assert old_modified > self.refresh(orga01).modified

        url = self.build_merge_url(orga01, orga02)
        response = self.assertGET200(url)

        with self.assertNoException():
            fields = response.context['form'].fields
            f_name = fields['name']
            f_email = fields['email']

        self.assertTrue(f_name.required)
        self.assertEqual([orga01.name,  orga02.name,  orga01.name],  f_name.initial)
        self.assertEqual([orga01.email, orga02.email, orga02.email], f_email.initial) #orga01.email is empty

        self.assertFalse(fields['capital'].required)

        description = ' '.join([orga01.description, orga02.description])
        response = self.client.post(url, follow=True,
                                    data={'user_1':      user.id,
                                          'user_2':      user.id,
                                          'user_merged': user.id,

                                          'name_1':      orga01.name,
                                          'name_2':      orga02.name,
                                          'name_merged': orga01.name, #<======

                                          'description_1':      orga01.description,
                                          'description_2':      orga02.description,
                                          'description_merged': description, #<======

                                          'email_1':      orga01.email,
                                          'email_2':      orga02.email,
                                          'email_merged': orga02.email, #<======

                                         }
                                   )
        self.assertNoFormError(response)
        self.assertRedirects(response, orga01.get_absolute_url())

        self.assertDoesNotExist(orga02)

        new_orga01 = self.refresh(orga01)
        self.assertEqual(orga01.name,  new_orga01.name)
        self.assertEqual(description,  new_orga01.description)
        self.assertEqual(orga02.email, new_orga01.email)

        rel1 = self.refresh(rel1)
        self.assertEqual(contact01.id,  rel1.subject_entity_id)
        self.assertEqual(rtype,         rel1.type)
        self.assertEqual(new_orga01.id, rel1.object_entity_id)

        rel3 = self.refresh(rel3)
        self.assertEqual(contact02.id,  rel3.subject_entity_id)
        self.assertEqual(rtype,         rel3.type)
        self.assertEqual(new_orga01.id, rel3.object_entity_id)
        sym_rel3 = rel3.symmetric_relation
        self.assertEqual(new_orga01.id, sym_rel3.subject_entity_id)
        self.assertEqual(contact02.id,  sym_rel3.object_entity_id)

        #rel2 should have been deleted (no doublon)
        self.assertDoesNotExist(rel2)
        self.assertRelationCount(1, contact01, rtype.id, orga01)

        prop1 = self.refresh(prop1)
        self.assertEqual(ptype01,   prop1.type)
        self.assertEqual(orga01.id, prop1.creme_entity_id)

        prop2 = self.refresh(prop2)
        self.assertEqual(ptype02,   prop2.type)
        self.assertEqual(orga01.id, prop2.creme_entity_id)

        #prop3 should have been deleted (no doublon)
        self.assertDoesNotExist(prop3)

        #HistoryLines: duplicated relations/properties that are deleted are do not generate line
        hline_types = set(HistoryLine.objects.filter(id__gt=last_hline_id).values_list('type', flat=True))
        self.assertIn(TYPE_EDITION,  hline_types)
        self.assertIn(TYPE_RELATION, hline_types)
        self.assertIn(TYPE_PROP_ADD, hline_types)

        self.assertNotIn(TYPE_PROP_DEL, hline_types)
        self.assertNotIn(TYPE_RELATION_DEL, hline_types)
        self.assertNotIn(TYPE_SYM_REL_DEL, hline_types)

    #TODO: we need an other Entity with a M2M to test the fusion of M2M fields (language is now uneditable)
    def test_merge02(self):
        "2 Contacts, M2M, foreign key to CremeEntities"
        self.login()

        image1 = self.create_image(ident=1)
        image2 = self.create_image(ident=2)
        self.create_image(ident=3) #image3 should not be proposed by the form

        user = self.user
        create_contact = partial(Contact.objects.create, user=user)
        contact01 = create_contact(first_name='Makoto', last_name='Kosaka',  image=image1)
        contact02 = create_contact(first_name='Makoto', last_name='Kousaka', image=image2)

        #language1, language2 = Language.objects.all()[:2]
        #language3 = Language.objects.create(name=u'Klingon', code='KLN')

        #contact01.language = [language1]
        #contact02.language = [language1, language2]

        url = self.build_merge_url(contact01, contact02)
        response = self.assertGET200(url)

        with self.assertNoException():
            f_image = response.context['form'].fields['image']

        self.assertFalse(f_image.required)
        self.assertEqual([image1.id,  image2.id,  image1.id],  f_image.initial)
        self.assertEqual({(image1.id, unicode(image1)), (image2.id, unicode(image2))}, #not image3 !
                         set(f_image._original_field.choices)
                        )

        response = self.client.post(url, follow=True,
                                    data={'user_1':      user.id,
                                          'user_2':      user.id,
                                          'user_merged': user.id,

                                          'first_name_1':      contact01.first_name,
                                          'first_name_2':      contact02.first_name,
                                          'first_name_merged': contact01.first_name,

                                          'last_name_1':      contact01.last_name,
                                          'last_name_2':      contact02.last_name,
                                          'last_name_merged': contact01.last_name,

                                          #'language_1':      [language1.id],
                                          #'language_2':      [language1.id, language2.id],
                                          #'language_merged': [language3.id], #<======

                                          'image_1':      image1.id,
                                          'image_2':      image2.id,
                                          'image_merged': image2.id,
                                         }
                                   )
        self.assertNoFormError(response)
        self.assertRedirects(response, contact01.get_absolute_url())

        self.assertDoesNotExist(contact02)

        new_contact01 = self.refresh(contact01)
        self.assertEqual(contact01.first_name, new_contact01.first_name)
        self.assertEqual(contact01.last_name,  new_contact01.last_name)
        #self.assertEqual([language3],          list(new_contact01.language.all()))
        self.assertEqual(image2,               new_contact01.image)

    def test_merge03(self):
        "Initial values come in priority from the last edited entity"
        self.login()

        create_orga = partial(Organisation.objects.create, user=self.user)
        orga01 = create_orga(name='Genshiken')
        orga02 = create_orga(name='Gen-shi-ken')

        old_modified = orga01.modified
        self._oldify(orga02)
        assert old_modified > self.refresh(orga02).modified

        response = self.assertGET200(self.build_merge_url(orga01, orga02))

        with self.assertNoException():
            f_name = response.context['form'].fields['name']

        self.assertEqual([orga01.name, orga02.name, orga02.name], f_name.initial)

    def test_merge04(self):
        "Nullable foreign key to CremeEntities"
        self.login()

        image = self.create_image()

        create_contact = partial(Contact.objects.create, user=self.user)
        contact01 = create_contact(first_name='Makoto', last_name='Kosaka', image=image)
        contact02 = create_contact(first_name='Makoto', last_name='Kousaka')

        response = self.assertGET200(self.build_merge_url(contact01, contact02))

        with self.assertNoException():
            f_image = response.context['form'].fields['image']

        self.assertEqual([image.id,  None,  image.id],  f_image.initial)
        self.assertEqual({(image.id, unicode(image)), ('', '---------')},
                         set(f_image._original_field.choices)
                        )

    def test_merge_customfields(self):
        self.login()

        create_cf = partial(CustomField.objects.create, field_type=CustomField.INT,
                            content_type=ContentType.objects.get_for_model(Contact),
                           )
        cf_01 = create_cf(name='Number of manga')
        cf_02 = create_cf(name='Number of anime')
        cf_03 = create_cf(name='Club', field_type=CustomField.ENUM)

        create_evalue = CustomFieldEnumValue.objects.create
        enum_val1_1 = create_evalue(custom_field=cf_03, value='Club Manga')
        create_evalue(custom_field=cf_03, value='Club Anime')

        user = self.user
        create_contact = partial(Contact.objects.create, user=user)
        contact01 = create_contact(first_name='Makoto', last_name='Kosaka')
        contact02 = create_contact(first_name='Makoto', last_name='Kousaka')

        create_cfval_01 = partial(cf_01.get_value_class().objects.create, custom_field=cf_01)
        cf_01_value01 = create_cfval_01(entity=contact01, value=500)
        cf_01_value02 = create_cfval_01(entity=contact02, value=510)

        cf_02_value01 = cf_02.get_value_class().objects.create(custom_field=cf_02, entity=contact01, value=100)

        cf_03_value02 = cf_03.get_value_class()(custom_field=cf_03, entity=contact02)
        cf_03_value02.set_value_n_save(enum_val1_1.id)

        url = self.build_merge_url(contact01, contact02)
        response = self.assertGET200(url)

        with self.assertNoException():
            fields = response.context['form'].fields
            f_cf_01 = fields['custom_field_0']
            f_cf_02 = fields['custom_field_1']
            f_cf_03 = fields['custom_field_2']

        self.assertFalse(f_cf_01.required)
        self.assertEqual([500,  510,  500],  f_cf_01.initial)
        self.assertEqual([100,  None, 100],  f_cf_02.initial)
        self.assertEqual([None, enum_val1_1.id, enum_val1_1.id], f_cf_03.initial)

        response = self.client.post(url, follow=True,
                                    data={'user_1':      user.id,
                                          'user_2':      user.id,
                                          'user_merged': user.id,

                                          'first_name_1':      contact01.first_name,
                                          'first_name_2':      contact02.first_name,
                                          'first_name_merged': contact01.first_name,

                                          'last_name_1':      contact01.last_name,
                                          'last_name_2':      contact02.last_name,
                                          'last_name_merged': contact01.last_name,

                                          'custom_field_0_1':      500,
                                          'custom_field_0_2':      510,
                                          'custom_field_0_merged': 510,

                                          'custom_field_1_1':      100,
                                          'custom_field_1_2':      '',
                                          'custom_field_1_merged': '',

                                          'custom_field_2_1':      '',
                                          'custom_field_2_2':      enum_val1_1.id,
                                          'custom_field_2_merged': enum_val1_1.id,
                                         }
                                   )
        self.assertNoFormError(response)
        self.assertRedirects(response, contact01.get_absolute_url())

        self.assertDoesNotExist(contact02)

        new_contact01 = self.refresh(contact01)
        self.assertEqual(contact01.first_name, new_contact01.first_name)
        self.assertEqual(contact01.last_name,  new_contact01.last_name)

        cf_01_values = cf_01.get_value_class().objects.filter(id__in=(cf_01_value01.id, cf_01_value02.id))
        self.assertEqual(1, len(cf_01_values))

        cf_01_value = cf_01_values[0]
        self.assertEqual(contact01.id, cf_01_value.entity_id)
        self.assertEqual(510, cf_01_value.value)

        self.assertDoesNotExist(cf_02_value01)

        cf_03_values = cf_03.get_value_class().objects.filter(custom_field=cf_03)
        self.assertEqual(1, len(cf_03_values))

        cf_03_value = cf_03_values[0]
        self.assertEqual(contact01.id, cf_03_value.entity_id)
        self.assertEqual(enum_val1_1, cf_03_value.value)

    def test_error01(self):
        "Try to merge 2 entities with different types"
        self.login()

        user = self.user
        orga = Organisation.objects.create(user=user, name='Genshiken')
        contact = Contact.objects.create(user=user, first_name='Chika', last_name='Ogiue')

        self.assertGET409(self.build_merge_url(orga, contact))

    def test_error02(self):
        self.login()

        user = self.user
        create_orga = partial(Organisation.objects.create, user=user)
        orga01 = create_orga(name='Genshiken')
        orga02 = create_orga(name='Gen-shi-ken')

        response = self.assertPOST200(self.build_merge_url(orga01, orga02),
                                      follow=True,
                                      data={'user_1':      user.id,
                                            'user_2':      user.id,
                                            #'user_merged': user.id, #<============

                                            'name_1':      orga01.name,
                                            'name_2':      orga02.name,
                                            'name_merged': '', #<======
                                           }
                                     )
        self.assertFormError(response, 'form', 'user', [_(u'This field is required.')])
        self.assertFormError(response, 'form', 'name', [_(u'This field is required.')])

    def test_perm01(self):
        self.login(is_superuser=False, allowed_apps=['persons'])

        SetCredentials.objects.create(
                role=self.role,
                value=EntityCredentials.VIEW | EntityCredentials.CHANGE | EntityCredentials.DELETE,
                set_type=SetCredentials.ESET_OWN
            )

        user = self.user
        create_orga = Organisation.objects.create
        orga01 = create_orga(user=user,            name='Genshiken')
        orga02 = create_orga(user=self.other_user, name='Gen-shi-ken')

        can_view = user.has_perm_to_view
        self.assertTrue(can_view(orga01));  self.assertTrue(user.has_perm_to_change(orga01))
        self.assertFalse(can_view(orga02)); self.assertFalse(user.has_perm_to_delete(orga02))

        self.assertGET403(self.build_merge_url(orga01, orga02))
        self.assertGET403(self.build_merge_url(orga02, orga01))

