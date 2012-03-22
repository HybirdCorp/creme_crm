# -*- coding: utf-8 -*-

try:
    from datetime import timedelta
    from tempfile import NamedTemporaryFile

    from django.utils.translation import ugettext as _

    from creme_core.models import (RelationType, Relation, SetCredentials,
                                   CremePropertyType, CremeProperty, Language)
    from creme_core.tests.views.base import ViewsTestCase

    from media_managers.models import Image

    from persons.models import Organisation, Contact
except Exception as e:
    print 'Error in <%s>: %s' % (__name__, e)


__all__ = ('MergeViewsTestCase', )


class MergeViewsTestCase(ViewsTestCase):
    @classmethod
    def setUpClass(cls):
        cls.populate('creme_core', 'creme_config', 'persons') #'persons' for HeaderFilter

    def build_select_url(self, e1):
         return '/creme_core/entity/merge/select_other/%s' % e1.id

    def build_merge_url(self, e1, e2):
         return '/creme_core/entity/merge/%s,%s' % (e1.id, e2.id)

    def _oldify(self, entity, hours_delta=1):
        mdate = entity.modified - timedelta(hours=hours_delta)
        entity.__class__.objects.filter(pk=entity.pk).update(modified=mdate)

    def _create_image(self, ident=1): #TODO factorise ? (see tests.models.entity._create_image)
        tmpfile = NamedTemporaryFile()
        tmpfile.width = tmpfile.height = 0
        tmpfile._committed = True
        tmpfile.path = 'upload/file_%s.jpg' % ident

        return Image.objects.create(user=self.user, image=tmpfile,
                                    name=u'Image #%s' % ident,
                                    description=u"Desc"
                                   )

    def test_select_entity_for_merge01(self):
        self.login()

        user = self.user
        create_orga = Organisation.objects.create
        orga01 = create_orga(user=user, name='Genshiken')
        orga02 = create_orga(user=user, name='Gen-shi-ken')
        orga03 = create_orga(user=user, name='Manga Club')

        response = self.client.get(self.build_select_url(orga01))
        self.assertEqual(200, response.status_code)

        with self.assertNoException():
            contacts = response.context['entities'].object_list

        contacts = set(contacts)
        self.assertIn(orga02, contacts)
        self.assertIn(orga03, contacts)
        self.assertNotIn(orga01, contacts)

    def test_select_entity_for_merge02(self): #view credentials
        self.login(is_superuser=False, allowed_apps=['persons'])

        SetCredentials.objects.create(
                role=self.role,
                value=SetCredentials.CRED_VIEW | SetCredentials.CRED_CHANGE | SetCredentials.CRED_DELETE,
                set_type=SetCredentials.ESET_OWN
            )
        orga = Organisation.objects.create(user=self.other_user, name='Genshiken')
        self.assertFalse(orga.can_view(self.user))
        self.assertEqual(403, self.client.get(self.build_select_url(orga)).status_code)

    def test_select_entity_for_merge03(self): #edit credentials
        self.login(is_superuser=False, allowed_apps=['persons'])

        SetCredentials.objects.create(role=self.role,
                                      value=SetCredentials.CRED_VIEW,
                                      set_type=SetCredentials.ESET_ALL
                                     )
        orga = Organisation.objects.create(user=self.other_user, name='Genshiken')
        self.assertTrue(orga.can_view(self.user))
        self.assertFalse(orga.can_change(self.user))
        self.assertEqual(403, self.client.get(self.build_select_url(orga)).status_code)

    def test_merge01(self):
        self.login()

        rtype = RelationType.create(('test-subject_member', 'is a member of'),
                                    ('test-object_member',  'has as a member')
                                   )[0]

        create_ptype = CremePropertyType.create
        ptype01 = create_ptype(str_pk='test-prop_manga', text='Manga related')
        ptype02 = create_ptype(str_pk='test-prop_anime', text='Anime related')

        user = self.user
        create_orga = Organisation.objects.create
        orga01 = create_orga(user=user, name='Genshiken',   description='Otaku band.',   phone='8787878')
        orga02 = create_orga(user=user, name='Gen-shi-ken', description='A great club.', email='genshiken@univ.jp')

        create_contact = Contact.objects.create
        contact01 = create_contact(user=user, first_name='Chika',       last_name='Ogiue')
        contact02 = create_contact(user=user, first_name=u'Souichirou', last_name='Tanaka')

        # contact01 linked with the 2 organisations -> after merge, we expect only one relation, not 2
        # contact02 should be linked to the merged entity
        create_rel = Relation.objects.create
        rel1 = create_rel(subject_entity=contact01, type=rtype, object_entity=orga01, user=user)
        rel2 = create_rel(subject_entity=contact01, type=rtype, object_entity=orga02, user=user)
        rel3 = create_rel(subject_entity=contact02, type=rtype, object_entity=orga02, user=user)

        #'prop3 'should be deleted, because orga01 has already a property with the same type
        create_prop = CremeProperty.objects.create
        prop1 = create_prop(type=ptype01, creme_entity=orga01)
        prop2 = create_prop(type=ptype02, creme_entity=orga02)
        prop3 = create_prop(type=ptype01, creme_entity=orga02)

        old_modified = orga01.modified
        self._oldify(orga01)
        assert old_modified > self.refresh(orga01).modified

        url = self.build_merge_url(orga01, orga02)
        response = self.client.get(url)
        self.assertEqual(200, response.status_code)

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
        self.assertEqual(200, response.status_code)
        self.assertNoFormError(response)
        self.assertTrue(response.redirect_chain)
        self.assertEqual(1, len(response.redirect_chain))
        self.assertEqual(u"http://testserver%s" % orga01.get_absolute_url(),
                         response.redirect_chain[0][0]
                        )

        self.assertFalse(Organisation.objects.filter(pk=orga02).exists())

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

        #rel2 should have been deleted (no doublon)
        self.assertRelationCount(1, contact01, rtype.id, orga01)

        prop1 = self.refresh(prop1)
        self.assertEqual(ptype01,   prop1.type)
        self.assertEqual(orga01.id, prop1.creme_entity_id)

        prop2 = self.refresh(prop2)
        self.assertEqual(ptype02,   prop2.type)
        self.assertEqual(orga01.id, prop2.creme_entity_id)

        #prop3 should have been deleted (no doublon)
        self.assertFalse(CremeProperty.objects.filter(pk=prop3.pk).exists())

    #TODO: we need an other Entity with a M2M to test the fusion of M2M fields (language is now uneditable)
    def test_merge02(self): #other ct, M2M, foreign key to CremeEntities
        self.login()

        image1 = self._create_image(ident=1)
        image2 = self._create_image(ident=2)
        image3 = self._create_image(ident=3) #should not be proposed by the form

        user = self.user
        create_contact = Contact.objects.create
        contact01 = create_contact(user=user, first_name='Makoto', last_name='Kosaka', image=image1)
        contact02 = create_contact(user=user, first_name='Makoto', last_name='Kousaka', image=image2)

        #language1, language2 = Language.objects.all()[:2]
        #language3 = Language.objects.create(name=u'Klingon', code='KLN')

        #contact01.language = [language1]
        #contact02.language = [language1, language2]

        url = self.build_merge_url(contact01, contact02)
        response = self.client.get(url)
        self.assertEqual(200, response.status_code)

        with self.assertNoException():
            f_image = response.context['form'].fields['image']

        self.assertFalse(f_image.required)
        self.assertEqual([image1.id,  image2.id,  image1.id],  f_image.initial)
        self.assertEqual(set([(image1.id, unicode(image1)), (image2.id, unicode(image2))]), #not image3 !
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
        self.assertEqual(200, response.status_code)
        self.assertNoFormError(response)
        self.assertEqual(u"http://testserver%s" % contact01.get_absolute_url(),
                         response.redirect_chain[0][0]
                        )

        self.assertFalse(Contact.objects.filter(pk=contact02).exists())

        new_contact01 = self.refresh(contact01)
        self.assertEqual(contact01.first_name, new_contact01.first_name)
        self.assertEqual(contact01.last_name,  new_contact01.last_name)
        #self.assertEqual([language3],          list(new_contact01.language.all()))
        self.assertEqual(image2,               new_contact01.image)

    def test_merge03(self): #initial values come in priority from the last edited entity
        self.login()

        user = self.user
        create_orga = Organisation.objects.create
        orga01 = create_orga(user=user, name='Genshiken')
        orga02 = create_orga(user=user, name='Gen-shi-ken')

        old_modified = orga01.modified
        self._oldify(orga02)
        assert old_modified > self.refresh(orga02).modified

        response = self.client.get(self.build_merge_url(orga01, orga02))
        self.assertEqual(200, response.status_code)

        with self.assertNoException():
            f_name = response.context['form'].fields['name']

        self.assertEqual([orga01.name, orga02.name, orga02.name], f_name.initial)

    def test_merge04(self): #nullable foreign key to CremeEntities
        self.login()

        image = self._create_image()

        user = self.user
        create_contact = Contact.objects.create
        contact01 = create_contact(user=user, first_name='Makoto', last_name='Kosaka', image=image)
        contact02 = create_contact(user=user, first_name='Makoto', last_name='Kousaka')

        response = self.client.get(self.build_merge_url(contact01, contact02))
        self.assertEqual(200, response.status_code)

        with self.assertNoException():
            f_image = response.context['form'].fields['image']

        self.assertEqual([image.id,  None,  image.id],  f_image.initial)
        self.assertEqual(set([(image.id, unicode(image)), ('', '---------')]),
                         set(f_image._original_field.choices)
                        )

    def test_error01(self): #merge 2 entities with different types
        self.login()

        user = self.user
        orga = Organisation.objects.create(user=user, name='Genshiken')
        contact = Contact.objects.create(user=user, first_name='Chika', last_name='Ogiue')

        self.assertEqual(404, self.client.get(self.build_merge_url(orga, contact)).status_code)

    def test_error02(self):
        self.login()

        user = self.user
        create_orga = Organisation.objects.create
        orga01 = create_orga(user=user, name='Genshiken')
        orga02 = create_orga(user=user, name='Gen-shi-ken')

        response = self.client.post(self.build_merge_url(orga01, orga02), follow=True,
                                    data={'user_1':      user.id,
                                          'user_2':      user.id,
                                          #'user_merged': user.id, #<============

                                          'name_1':      orga01.name,
                                          'name_2':      orga02.name,
                                          'name_merged': '', #<======
                                         }
                                   )
        self.assertEqual(200, response.status_code)
        self.assertFormError(response, 'form', 'user', [_(u'This field is required.')])
        self.assertFormError(response, 'form', 'name', [_(u'This field is required.')])

    def test_perm01(self):
        self.login(is_superuser=False, allowed_apps=['persons'])

        SetCredentials.objects.create(
                role=self.role,
                value=SetCredentials.CRED_VIEW | SetCredentials.CRED_CHANGE | SetCredentials.CRED_DELETE,
                set_type=SetCredentials.ESET_OWN
            )

        user = self.user
        create_orga = Organisation.objects.create
        orga01 = create_orga(user=user,            name='Genshiken')
        orga02 = create_orga(user=self.other_user, name='Gen-shi-ken')

        self.assertTrue(orga01.can_view(user));  self.assertTrue(orga01.can_change(user))
        self.assertFalse(orga02.can_view(user)); self.assertFalse(orga02.can_delete(user))

        self.assertEqual(403, self.client.get(self.build_merge_url(orga01, orga02)).status_code)
        self.assertEqual(403, self.client.get(self.build_merge_url(orga02, orga01)).status_code)

