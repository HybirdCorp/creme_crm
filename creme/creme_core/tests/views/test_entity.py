# -*- coding: utf-8 -*-

try:
#    from os.path import join, exists
    from datetime import date
    from decimal import Decimal
    from functools import partial
    from json import loads as load_json
#    from tempfile import NamedTemporaryFile

    from django.conf import settings
    from django.contrib.contenttypes.models import ContentType
    from django.contrib.auth import get_user_model
    from django.core.exceptions import ValidationError
    from django.db.models import Max
    from django.utils.translation import ugettext as _

    from .base import ViewsTestCase
    from ..fake_models import (FakeContact as Contact, FakeOrganisation as Organisation,
            FakePosition as Position, FakeSector as Sector, FakeAddress as Address,
            FakeImage as Image, FakeImageCategory as MediaCategory)
    from creme.creme_core.auth.entity_credentials import EntityCredentials
    from creme.creme_core.models import (CremeEntity, RelationType, Relation,
            CremePropertyType, CremeProperty, HistoryLine, FieldsConfig,
            CustomField, CustomFieldInteger, CustomFieldFloat, CustomFieldBoolean,
            CustomFieldString, CustomFieldDateTime,
            CustomFieldEnum, CustomFieldMultiEnum, CustomFieldEnumValue)
    from creme.creme_core.models import history
    from creme.creme_core.gui.bulk_update import bulk_update_registry
    from creme.creme_core.blocks import trash_block
    from creme.creme_core.forms.bulk import _CUSTOMFIELD_FORMAT, BulkDefaultEditForm
    from creme.creme_core.utils import safe_unicode

    #from creme.media_managers.models import Image, MediaCategory

    #from creme.persons.models import Contact, Organisation, Position, Sector, Address
except Exception as e:
    print('Error in <%s>: %s' % (__name__, e))


class EntityViewsTestCase(ViewsTestCase):
    CLONE_URL        = '/creme_core/entity/clone'
    DEL_ENTITIES_URL = '/creme_core/entity/delete/multi'
    EMPTY_TRASH_URL  = '/creme_core/entity/trash/empty'
    SEARCHNVIEW_URL  = '/creme_core/entity/search_n_view'

    @classmethod
    def setUpClass(cls):
        ViewsTestCase.setUpClass()
        cls.populate('creme_core')

    def _build_delete_url(self, entity):
        return '/creme_core/entity/delete/%s' % entity.id

    def _build_restore_url(self, entity):
        return '/creme_core/entity/restore/%s' % entity.id

    def test_json_entity_get01(self):
        user = self.login()
        url_fmt = '/creme_core/relation/entity/%s/json'
        rei = Contact.objects.create(user=user, first_name='Rei', last_name='Ayanami')
        nerv = Organisation.objects.create(user=user, name='Nerv')

        url = url_fmt % rei.id
        self.assertGET(400, url)

        response = self.assertGET200(url, data={'fields': ['id']})
        self.assertEqual([[rei.id]], load_json(response.content))

        response = self.assertGET200(url, data={'fields': ['unicode']})
        self.assertEqual([[unicode(rei)]], load_json(response.content))

        response = self.assertGET200(url_fmt % nerv.id, data={'fields': ['id', 'unicode']})
        self.assertEqual([[nerv.id, unicode(nerv)]], load_json(response.content))

        self.assertGET(400, url_fmt % 1024)
        self.assertGET403(url, data={'fields': ['id', 'unknown']})

    def test_json_entity_get02(self):
        self.login(is_superuser=False)

        nerv = Organisation.objects.create(user=self.other_user, name='Nerv')
        self.assertGET(400, '/creme_core/relation/entity/%s/json' % nerv.id)

    def test_get_creme_entities_repr01(self):
        user = self.login()

        with self.assertNoException():
            entity = CremeEntity.objects.create(user=user)

        response = self.assertGET200('/creme_core/entity/get_repr/%s' % entity.id)
        self.assertEqual('text/javascript', response['Content-Type'])

        self.assertEqual([{'id':   entity.id,
                           'text': 'Creme entity: %s' % entity.id,
                          }
                         ],
                         load_json(response.content)
                        )

    def test_get_creme_entities_repr02(self):
        "Several entities, several ContentTypes, credentials"
#        self.login(is_superuser=False, allowed_apps=['persons'])
        user = self.login(is_superuser=False)

        create_c = Contact.objects.create
        rei   = create_c(user=user,            first_name='Rei',   last_name='Ayanami')
        asuka = create_c(user=user,            first_name='Asuka', last_name='Langley')
        mari  = create_c(user=self.other_user, first_name='Mari',  last_name='Makinami')

        nerv = Organisation.objects.create(user=user, name='Nerv')

        self.assertTrue(user.has_perm_to_view(rei))
        self.assertFalse(user.has_perm_to_view(mari))

        unknown_id = 1024
        self.assertFalse(CremeEntity.objects.filter(id=unknown_id))

        response = self.assertGET200('/creme_core/entity/get_repr/%s,%s,%s,%s,%s' % (
                                            mari.id, rei.id, nerv.id, unknown_id, asuka.id
                                        )
                                    )
        self.assertEqual([{'id': mari.id,  'text': _(u'Entity #%s (not viewable)') % mari.id},
                          {'id': rei.id,   'text': unicode(rei)},
                          {'id': nerv.id,  'text': unicode(nerv)},
                          {'id': asuka.id, 'text': unicode(asuka)},
                         ],
                         load_json(response.content)
                        )

    def test_delete_entity01(self):
        "is_deleted=False -> trash"
        user = self.login()

        entity = Organisation.objects.create(user=user, name='Nerv')
        self.assertTrue(hasattr(entity, 'is_deleted'))
        self.assertIs(entity.is_deleted, False)
        self.assertGET200(entity.get_edit_absolute_url())

        absolute_url = entity.get_absolute_url()
        edit_url = entity.get_edit_absolute_url()

        response = self.assertGET200(absolute_url)
        self.assertContains(response, unicode(entity))
        self.assertContains(response, edit_url)

        url = self._build_delete_url(entity)
        self.assertGET404(url)
        self.assertRedirects(self.client.post(url), entity.get_lv_absolute_url())

        with self.assertNoException():
            entity = self.refresh(entity)

        self.assertIs(entity.is_deleted, True)

        self.assertGET403(edit_url)

        response = self.assertGET200(absolute_url)
        self.assertContains(response, unicode(entity))
        self.assertNotContains(response, edit_url)

    def test_delete_entity02(self):
        "is_deleted=True -> real deletion"
        user = self.login()

        #to get a get_lv_absolute_url() method
        entity = Organisation.objects.create(user=user, name='Nerv', is_deleted=True)

        url = self._build_delete_url(entity)
        self.assertGET404(url)
        self.assertRedirects(self.client.post(url), entity.get_lv_absolute_url())
        self.assertDoesNotExist(entity)

    def test_delete_entity03(self):
        "No DELETE credentials"
        self.login(is_superuser=False)

        entity = Organisation.objects.create(user=self.other_user, name='Nerv')

        self.assertPOST403(self._build_delete_url(entity))
        #self.get_object_or_fail(Organisation, pk=entity.id)
        self.assertStillExists(entity)

    def test_delete_entity04(self):
        "Relations (not internal ones) & properties are deleted correctly"
        user = self.login()

        create_orga = partial(Organisation.objects.create, user=user)
        entity01 = create_orga(name='Nerv', is_deleted=True)
        entity02 = create_orga(name='Seele')
        entity03 = create_orga(name='Neo tokyo')

        create_rtype = RelationType.create
        rtype1 = create_rtype(('test-subject_linked', 'is linked to'),
                              ('test-object_linked',  'is linked to'),
                              is_custom=True,
                             )[0]
        rtype2 = create_rtype(('test-subject_provides', 'provides'),
                              ('test-object_provides',  'provided by'),
                              is_custom=False,
                             )[0]
        creat_rel = partial(Relation.objects.create, user=user, subject_entity=entity01)
        rel1 = creat_rel(type=rtype1, object_entity=entity02)
        rel2 = creat_rel(type=rtype2, object_entity=entity03)
        rel3 = creat_rel(type=rtype2, object_entity=entity03, subject_entity=entity02)

        ptype = CremePropertyType.create(str_pk='test-prop_eva', text='has eva')
        create_prop = partial(CremeProperty.objects.create, type=ptype)
        prop1 = create_prop(creme_entity=entity01)
        prop2 = create_prop(creme_entity=entity02)

        hlines_ids = list(HistoryLine.objects.values_list('id', flat=True))
        self.assertPOST200(self._build_delete_url(entity01), follow=True)

        self.assertDoesNotExist(entity01)
        self.assertStillExists(entity02)
        self.assertStillExists(entity03)

        self.assertDoesNotExist(rel1)
        self.assertDoesNotExist(rel2)
        self.assertStillExists(rel3)

        self.assertDoesNotExist(prop1)
        self.assertStillExists(prop2)

        self.assertEqual({history.TYPE_RELATION_DEL, history.TYPE_SYM_REL_DEL,
                          history.TYPE_PROP_DEL, history.TYPE_DELETION,
                         },
                         set(HistoryLine.objects.exclude(id__in=hlines_ids)
                                                .values_list('type', flat=True)
                            )
                        )

    def test_delete_entity05(self):#TODO: detect dependencies when trashing ??
        "Dependencies problem (with internal Relations)"
        user = self.login()

        create_orga = partial(Organisation.objects.create, user=user)
        entity01 = create_orga(name='Nerv', is_deleted=True)
        entity02 = create_orga(name='Seele')

        rtype = RelationType.create(('test-subject_linked', 'is linked to'),
                                    ('test-object_linked',  'is linked to'),
                                    is_internal=True,
                                   )[0]
        Relation.objects.create(user=user, type=rtype, subject_entity=entity01, object_entity=entity02)

        response = self.assertPOST403(self._build_delete_url(entity01), follow=True)
        self.assertTemplateUsed(response, 'creme_core/forbidden.html')
        self.assertStillExists(entity01)
        self.assertStillExists(entity02)

    def test_delete_entity06(self):
        "is_deleted=False -> trash (AJAX version)"
        user = self.login()

        entity = Organisation.objects.create(user=user, name='Nerv')
        self.assertPOST200(self._build_delete_url(entity), HTTP_X_REQUESTED_WITH='XMLHttpRequest')

        with self.assertNoException():
            entity = self.refresh(entity)

        self.assertIs(entity.is_deleted, True)

    def test_delete_entities01(self):
        "NB: for the deletion of auxiliary entities => see billing app"
        user = self.login()

        create_entity = partial(CremeEntity.objects.create, user=user)
        entity01, entity02 = (create_entity() for i in xrange(2))
        entity03, entity04 = (create_entity(is_deleted=True) for i in xrange(2))

        response = self.assertPOST200(self.DEL_ENTITIES_URL,
                                      data={'ids': '%s,%s,%s' % (entity01.id, entity02.id, entity03.id)}
                                     )

        self.assertEqual(safe_unicode(response.content), _(u'Operation successfully completed'))

        entity01 = self.get_object_or_fail(CremeEntity, pk=entity01.id)
        self.assertTrue(entity01.is_deleted)

        entity02 = self.get_object_or_fail(CremeEntity, pk=entity02.id)
        self.assertTrue(entity02.is_deleted)

        self.assertDoesNotExist(entity03)
        self.assertStillExists(entity04)

    def test_delete_entities_missing(self):
        "Some entities doesn't exist"
        user = self.login()

        create_entity = partial(CremeEntity.objects.create, user=user)
        entity01, entity02 = (create_entity() for i in xrange(2))

        response = self.assertPOST404(self.DEL_ENTITIES_URL,
                                      data={'ids': '%s,%s,' % (entity01.id, entity02.id + 1)}
                                     )

        self.assertDictEqual({'count': 2,
                              'errors': [_(u"%s entities doesn't exist / doesn't exist any more") % 1]
                             },
                             load_json(response.content))

        #self.assertFalse(CremeEntity.objects.filter(pk=entity01.id))
        entity01 = self.get_object_or_fail(CremeEntity, pk=entity01.id)
        self.assertTrue(entity01.is_deleted)

        self.get_object_or_fail(CremeEntity, pk=entity02.id)

    def test_delete_entities_not_allowed(self):
        "Some entities deletion is not allowed"
        user = self.login(is_superuser=False)

        forbidden = CremeEntity.objects.create(user=self.other_user)
        allowed   = CremeEntity.objects.create(user=user)

        response = self.assertPOST403(self.DEL_ENTITIES_URL, data={'ids': '%s,%s,' % (forbidden.id, allowed.id)})

        self.assertDictEqual({'count': 2,
                              'errors': [_(u'%s : <b>Permission denied</b>') % forbidden.allowed_unicode(user)]
                             },
                             load_json(response.content))

        #self.assertFalse(CremeEntity.objects.filter(pk=allowed.id))
        allowed = self.get_object_or_fail(CremeEntity, pk=allowed.id)
        self.assertTrue(allowed.is_deleted)

        self.get_object_or_fail(CremeEntity, pk=forbidden.id)

    #TODO ??
    #def test_delete_entities04(self):
        #self.login()

        #create_entity = partial(CremeEntity.objects.create, user=self.user)
        #entity01 = create_entity()
        #entity02 = create_entity()
        #entity03 = create_entity() #not linked => can be deleted

        #rtype, srtype = RelationType.create(('test-subject_linked', 'is linked to'),
                                            #('test-object_linked',  'is linked to')
                                           #)
        #Relation.objects.create(user=self.user, type=rtype, subject_entity=entity01, object_entity=entity02)

        #self.assertPOST(400, self.DEL_ENTITIES_URL,
                        #data={'ids': '%s,%s,%s,' % (entity01.id, entity02.id, entity03.id)}
                       #)
        #self.assertEqual(2, CremeEntity.objects.filter(pk__in=[entity01.id, entity02.id]).count())
        #self.assertFalse(CremeEntity.objects.filter(pk=entity03.id))

    def test_trash_view(self):
        user = self.login()

        create_orga = partial(Organisation.objects.create, user=user)
        entity1 = create_orga(name='Nerv', is_deleted=True)
        entity2 = create_orga(name='Seele')

        response = self.assertGET200('/creme_core/entity/trash')
        self.assertTemplateUsed(response, 'creme_core/trash.html')
        self.assertContains(response, 'id="%s"' % trash_block.id_)
        self.assertContains(response, unicode(entity1))
        self.assertNotContains(response, unicode(entity2))

    def test_restore_entity01(self):
        "No trashed"
        user = self.login()

        entity = Organisation.objects.create(user=user, name='Nerv')
        url = self._build_restore_url(entity)
        self.assertGET404(url)
        self.assertPOST404(url)

    def test_restore_entity02(self):
        user = self.login()

        entity = Organisation.objects.create(user=user, name='Nerv', is_deleted=True)
        url = self._build_restore_url(entity)

        self.assertGET404(url)
        self.assertRedirects(self.client.post(url), entity.get_absolute_url())

        entity = self.get_object_or_fail(Organisation, pk=entity.pk)
        self.assertFalse(entity.is_deleted)

    def test_restore_entity03(self):
        user = self.login()

        entity = Organisation.objects.create(user=user, name='Nerv', is_deleted=True)
        self.assertPOST200(self._build_restore_url(entity), HTTP_X_REQUESTED_WITH='XMLHttpRequest')

        entity = self.get_object_or_fail(Organisation, pk=entity.pk)
        self.assertFalse(entity.is_deleted)

    def test_empty_trash01(self):
        user = self.login(is_superuser=False, allowed_apps=('creme_core', 'persons'))

        create_contact = partial(Contact.objects.create, user=user, is_deleted=True)
        contact1 = create_contact(first_name='Lawrence', last_name='Kraft')
        contact2 = create_contact(first_name='Holo',     last_name='Wolf')
        contact3 = create_contact(first_name='Nora',     last_name='Alend', user=self.other_user)

        self.assertTrue(user.has_perm_to_delete(contact1))
        self.assertFalse(user.has_perm_to_delete(contact3))

        url = self.EMPTY_TRASH_URL
        self.assertGET404(url)
        self.assertPOST200(url)
        #self.assertFalse(Contact.objects.filter(id__in=[contact1.id, contact2.id, contact3.id]))
        #self.assertEqual([contact3], list(Contact.objects.only_deleted()))
        #self.assertEqual([contact3], list(Contact.objects.even_deleted()))
        #self.assertEqual([contact3], list(Contact.objects.all()))
        self.assertFalse(Contact.objects.filter(id__in=[contact1.id, contact2.id]))
        self.assertStillExists(contact3)

    def test_empty_trash02(self):
        "Dependencies problem"
        user = self.login()

        create_entity = partial(CremeEntity.objects.create, user=user, is_deleted=True)
        entity01 = create_entity()
        entity02 = create_entity()
        entity03 = create_entity() #not linked => can be deleted

        rtype = RelationType.create(('test-subject_linked', 'is linked to'),
                                    ('test-object_linked',  'is linked to'),
                                    is_internal=True,
                                   )[0]
        Relation.objects.create(user=user, type=rtype, subject_entity=entity01, object_entity=entity02)

        self.assertPOST(409, self.EMPTY_TRASH_URL)
        self.assertStillExists(entity01)
        self.assertStillExists(entity02)
        self.assertDoesNotExist(entity03)

    def _build_test_get_info_fields_url(self, model):
        ct = ContentType.objects.get_for_model(model)

        return '/creme_core/entity/get_info_fields/%s/json' % ct.id

    def test_get_info_fields01(self):
        self.login()

        response = self.assertGET200(self._build_test_get_info_fields_url(Contact))
        json_data = load_json(response.content)
        self.assertIsInstance(json_data, list)
        self.assertTrue(all(isinstance(elt, list) for elt in json_data))
        self.assertTrue(all(len(elt) == 2 for elt in json_data))

        names = ['created', 'modified', 'first_name', 'last_name', 'description',
                 'phone', 'mobile', 'email', 'birthday', 'url_site',
                 'is_a_nerd',
#                 'skype', 'fax', 
                ]
        self.assertFalse(set(names).symmetric_difference({name for name, vname in json_data}))
        self.assertEqual(len(names), len(json_data))

        json_dict = dict(json_data)
        self.assertEqual(_(u'First name'), json_dict['first_name'])
        self.assertEqual(_(u'%s [CREATION]') % _(u'Last name'),
                         json_dict['last_name']
                        )

    def test_get_info_fields02(self):
        self.login()

        response = self.client.get(self._build_test_get_info_fields_url(Organisation))
        json_data = load_json(response.content)

        names = ['created', 'modified', 'name', 'description', 'url_site',
                 'phone', 'email', 'creation_date',  'subject_to_vat', 'capital',
#                 'fax', 'naf', 'siren', 'rcs', 'tvaintra', 'annual_revenue', 'siret', 
                ]
        self.assertFalse(set(names).symmetric_difference({name for name, vname in json_data}))
        self.assertEqual(len(names), len(json_data))

        json_dict = dict(json_data)
        self.assertEqual(_(u'Description'), json_dict['description'])
        self.assertEqual(_(u'%s [CREATION]') % _(u'Name'), 
                         json_dict['name']
                        )

    def test_get_info_fields03(self):
        "With FieldsConfig"
        self.login()

        FieldsConfig.create(Contact,
                            descriptions=[('birthday', {FieldsConfig.HIDDEN: True})],
                           )

        response = self.assertGET200(self._build_test_get_info_fields_url(Contact))
        json_data = load_json(response.content)
        names = ['created', 'modified', 'first_name', 'last_name', 'description',
                 'phone', 'mobile', 'email', 'url_site', 'is_a_nerd',
                 #'birthday', #<===
                ]
        self.assertFalse(set(names).symmetric_difference({name for name, vname in json_data}))
        self.assertEqual(len(names), len(json_data))

    def test_clone01(self):
        user = self.login()
        url = self.CLONE_URL
        mario = Contact.objects.create(user=user, first_name="Mario", last_name="Bros")

        self.assertPOST200(url, data={'id': mario.id}, follow=True)
        self.assertPOST404(url, data={})
        self.assertPOST404(url, data={'id': 0})

    def test_clone02(self):
        self.login(is_superuser=False)

        mario = Contact.objects.create(user=self.other_user, first_name="Mario", last_name="Bros")
        self.assertPOST403(self.CLONE_URL, data={'id': mario.id}, follow=True)

    def test_clone03(self):
        self.login(is_superuser=False,
                   #creatable_models=[ct.model_class() for ct in ContentType.objects.all()]
                   creatable_models=[Contact],
                  )
        self._set_all_creds_except_one(EntityCredentials.VIEW)

        mario = Contact.objects.create(user=self.other_user, first_name="Mario", last_name="Bros")
        self.assertPOST403(self.CLONE_URL, data={'id': mario.id}, follow=True)

    def test_clone04(self):
#        user = self.login(is_superuser=False, allowed_apps=('creme_core', 'persons'),
        user = self.login(is_superuser=False,
                          #creatable_models=[ct.model_class() for ct in ContentType.objects.all()],
                          creatable_models=[Contact],
                         )
        self._set_all_creds_except_one(None)

        mario = Contact.objects.create(user=user, first_name="Mario", last_name="Bros")
        self.assertPOST200(self.CLONE_URL, data={'id': mario.id}, follow=True)

    def test_clone05(self):
        self.login()

        first_name = "Mario"
        mario = Contact.objects.create(user=self.other_user, first_name=first_name, last_name="Bros")

        count = Contact.objects.count()
        response = self.assertPOST200(self.CLONE_URL, data={'id': mario.id}, follow=True)
        self.assertEqual(count + 1, Contact.objects.count())

        with self.assertNoException():
            mario = Contact.objects.filter(first_name=first_name).order_by('created')[0]
            oiram = Contact.objects.filter(first_name=first_name).order_by('created')[1]

        self.assertEqual(mario.last_name, oiram.last_name)
        self.assertRedirects(response, oiram.get_absolute_url())

    def test_clone06(self):
        """Not clonable entity type"""
        user = self.login()

        image = Image.objects.create(user=user, name='Img1')
        self.assertPOST404(self.CLONE_URL, data={'id': image.id}, follow=True)

    def _assert_detailview(self, response, entity):
        self.assertEqual(200, response.status_code)
        self.assertRedirects(response, entity.get_absolute_url())

    def test_search_and_view01(self):
        user = self.login()

        phone = '123456789'
        url = self.SEARCHNVIEW_URL
#        data = {'models': 'persons-contact',
        data = {'models': 'creme_core-fakecontact',
                'fields': 'phone',
                'value':  phone,
               }
        self.assertGET404(url, data=data)

        create_contact = partial(Contact.objects.create, user=user)
        onizuka = create_contact(first_name='Eikichi', last_name='Onizuka')
        create_contact(first_name='Ryuji', last_name='Danma', phone='987654', mobile=phone)
        self.assertGET404(url, data=data)

        onizuka.phone = phone
        onizuka.save()
        self._assert_detailview(self.client.get(url, data=data, follow=True), onizuka)

    def test_search_and_view02(self):
        user = self.login()

        phone = '999999999'
        url = self.SEARCHNVIEW_URL
#        data = {'models': 'persons-contact',
        data = {'models': 'creme_core-fakecontact',
                'fields': 'phone,mobile',
                'value':  phone,
               }
        self.assertGET404(url, data=data)

        create_contact = partial(Contact.objects.create, user=user)
        onizuka  = create_contact(first_name='Eikichi', last_name='Onizuka', mobile=phone)
        create_contact(first_name='Ryuji', last_name='Danma', phone='987654')
        self._assert_detailview(self.client.get(url, data=data, follow=True), onizuka)

    def test_search_and_view03(self):
        user = self.login()

        phone = '696969'
        url = self.SEARCHNVIEW_URL
#        data = {'models':  'persons-contact,persons-organisation',
        data = {'models':  'creme_core-fakecontact,creme_core-fakeorganisation',
                'fields': 'phone,mobile',
                'value': phone,
               }
        self.assertGET404(url, data=data)

        create_contact = partial(Contact.objects.create, user=user)
        onizuka = create_contact(first_name='Eikichi', last_name='Onizuka', mobile='55555')
        create_contact(first_name='Ryuji',   last_name='Danma',   phone='987654')

        onibaku = Organisation.objects.create(user=user, name='Onibaku', phone=phone)
        self._assert_detailview(self.client.get(url, data=data, follow=True), onibaku)

        onizuka.mobile = phone
        onizuka.save()
        self._assert_detailview(self.client.get(url, data=data, follow=True), onizuka)

    def test_search_and_view04(self):
        "Errors"
        user = self.login()

        url = self.SEARCHNVIEW_URL
#        base_data = {'models': 'persons-contact,persons-organisation',
        base_data = {'models': 'creme_core-fakecontact,creme_core-fakeorganisation',
                     'fields': 'mobile,phone',
                     'value':  '696969',
                    }
        create_contact = partial(Contact.objects.create, user=user)
        create_contact(first_name='Eikichi', last_name='Onizuka', mobile='55555')
        create_contact(first_name='Ryuji',   last_name='Danma', phone='987654')
        Organisation.objects.create(user=user, name='Onibaku', phone='54631357')

        self.assertGET404(url, data=dict(base_data, models='foo-bar'))
        self.assertGET404(url, data=dict(base_data, models='foobar'))
        self.assertGET404(url, data=dict(base_data, values=''))
        self.assertGET404(url, data=dict(base_data, models=''))
        self.assertGET404(url, data=dict(base_data), fields='')
        self.assertGET404(url, data=dict(base_data, models='persons-civility'))  # Not CremeEntity

    def test_search_and_view05(self):
        "Credentials"
#        user = self.login(is_superuser=False)
#        self.role.allowed_apps = ['creme_core', 'persons']
#        self.role.save()
        user = self.login(is_superuser=False)

        phone = '44444'
        url = self.SEARCHNVIEW_URL
#        data = {'models': 'persons-contact,persons-organisation',
        data = {'models': 'creme_core-fakecontact,creme_core-fakeorganisation',
                'fields': 'phone,mobile',
                'value':  phone,
               }

        create_contact = Contact.objects.create
        onizuka = create_contact(user=self.other_user, first_name='Eikichi', last_name='Onizuka', mobile=phone)  # phone Ok and but not readable
        ryuji   = create_contact(user=user,            first_name='Ryuji',   last_name='Danma',   phone='987654') # phone KO

        onibaku = Organisation.objects.create(user=user, name='Onibaku', phone=phone)  # phone Ok and readable

        has_perm = user.has_perm_to_view
        self.assertFalse(has_perm(onizuka))
        self.assertTrue(has_perm(ryuji))
        self.assertTrue(has_perm(onibaku))
        self._assert_detailview(self.client.get(url, data=data, follow=True), onibaku)

    def test_search_and_view06(self):
        "App credentials"
#        user = self.login(is_superuser=False)
#        self.role.allowed_apps = ['creme_core'] #not 'persons'
#        self.role.save()
        user = self.login(is_superuser=False, allowed_apps=['documents'])  # Not 'creme_core'

        phone = '31337'
#        data = {'models': 'persons-contact',
        data = {'models': 'creme_core-fakecontact',
                'fields': 'phone',
                'value':  phone,
               }
        Contact.objects.create(user=user, first_name='Eikichi', last_name='Onizuka', phone=phone)  # Would match if apps was allowed
        self.assertGET403(self.SEARCHNVIEW_URL, data=data)

    def test_search_and_view07(self):
        "FieldsConfig"
        self.login()

        FieldsConfig.create(Contact,
                            descriptions=[('phone',  {FieldsConfig.HIDDEN: True})],
                           )

        self.assertGET409(self.SEARCHNVIEW_URL,
                          data={'models': 'creme_core-fakecontact',
                                'fields': 'phone',
                                'value':  '123456789',
                               },
                         )


class _BulkEditTestCase(ViewsTestCase):
    GET_WIDGET_URL = '/creme_core/entity/get_widget/%s'

    def get_cf_values(self, cf, entity):
        return cf.get_value_class().objects.get(custom_field=cf, entity=entity)

#    @classmethod
#    def setUpClass(cls):
#        cls.populate('creme_config')

    def create_image(self, name, user, categories=()):
#        path = join(settings.CREME_ROOT, 'static', 'chantilly', 'images', 'creme_22.png')
#        self.assertTrue(exists(path))
#
#        image_file = open(path, 'rb')
#
#        response = self.client.post('/media_managers/image/add',
#                         data={'user':        user.pk,
#                               'name':        name,
#                               'description': '',
#                               'image':       image_file,
#                               'categories':  [c.id for c in categories],
#                              }
#                        )
#
#        self.assertEquals(response.status_code, 302)
#
#        return Image.objects.get(name=name)
        image = Image.objects.create(user=user, name=name)
        image.categories = categories

        return image


class BulkEditTestCase(_BulkEditTestCase):
    @classmethod
    def setUpClass(cls):
        _BulkEditTestCase.setUpClass()
        cls.contact_ct = ContentType.objects.get_for_model(Contact)
        cls.contact_bulk_status = bulk_update_registry.status(Contact)

    def tearDown(self):
        super(BulkEditTestCase, self).tearDown()
        bulk_update_registry.status(Contact)._innerforms = {}

    def _build_contact_url(self, field_name, *contact_ids):
        url = '/creme_core/entity/edit/bulk/%(ct)s/%(id)s/field/%(field)s'
        return url % {'ct': self.contact_ct.id,
                      'id': ','.join(str(id) for id in contact_ids),
                      'field': field_name,
                     }

    def create_2_contacts_n_url(self, mario_kwargs=None, luigi_kwargs=None, field='first_name'):
        create_contact = partial(Contact.objects.create, user=self.user)
        mario = create_contact(first_name="Mario", last_name="Bros", **(mario_kwargs or {}))
        luigi = create_contact(first_name="Luigi", last_name="Bros", **(luigi_kwargs or {}))

        return mario, luigi, self._build_contact_url(field, mario.id, luigi.id)

    def test_regular_field_error01(self):
        self.login()

        build_url = self._build_contact_url
        self.assertGET404('/creme_core/entity/bulk_update/%s/' % self.contact_ct.id)
        self.assertGET404(build_url('first_name', 0))
        self.assertGET404(build_url('first_name', *range(1024, 1034)))

    def test_regular_field01(self):
        user = self.login()

        mario = Contact.objects.create(user=user, first_name="Mario", last_name="Bros")
        build_url = self._build_contact_url
        url = build_url('first_name', mario.id)
        response = self.assertGET200(url)

        with self.assertNoException():
            choices = response.context['form'].fields['_bulk_fieldname'].choices

        self.assertIn((url, _('First name')), choices)
        self.assertIn((build_url('user', mario.id), _('Owner user')), choices)

        for k, v in choices:
            if k == _(u'Billing address'):
                baddr_choices = v
                break
        else:
            self.fail("No 'Billing address' choice")

#        self.assertIn((build_url('billing_address__city', mario.id), _('City')),
        self.assertIn((build_url('address__city', mario.id), _('City')),
                      baddr_choices
                     )

        fisrt_name = 'Marioooo'
        self.assertNoFormError(self.client.post(url, data={'field_value': fisrt_name}))
        self.assertEqual(fisrt_name, self.refresh(mario).first_name)

    def test_regular_field02(self):
        self.login()

        create_pos = Position.objects.create
        unemployed   = create_pos(title='unemployed')
        plumber      = create_pos(title='plumber')
        ghost_hunter = create_pos(title='ghost hunter')

        mario, luigi, url = self.create_2_contacts_n_url(mario_kwargs={'position': plumber},
                                                         luigi_kwargs={'position': ghost_hunter},
                                                         field='position',
                                                        )
        self.assertGET200(url)

        response = self.client.post(url, data={'field_value': unemployed.id})
        self.assertNoFormError(response)
        self.assertEqual(unemployed, self.refresh(mario).position)
        self.assertEqual(unemployed, self.refresh(luigi).position)

    def test_regular_field03(self):
        user = self.login()

        plumbing = Sector.objects.create(title='Plumbing')
        games    = Sector.objects.create(title='Games')

        create_contact = partial(Contact.objects.create, user=user, sector=games)
        mario = create_contact(user=user, first_name='Mario', last_name='Bros')
        luigi = create_contact(user=user, first_name='Luigi', last_name='Bros')

        nintendo = Organisation.objects.create(user=user, name='Nintendo', sector=games)

        url = self._build_contact_url('sector', mario.id, luigi.id, nintendo.id)
        self.assertGET200(url)

        response = self.client.post(url, data={'field_value': plumbing.id,})
        self.assertNoFormError(response)
        self.assertEqual(plumbing, self.refresh(mario).sector)
        self.assertEqual(plumbing, self.refresh(luigi).sector)
        self.assertEqual(games,    self.refresh(nintendo).sector)

    def test_regular_field04(self):
        self.login()

        mario, luigi, url = self.create_2_contacts_n_url(field='last_name')
        response = self.assertPOST200(url, data={'field_value': ''})
        self.assertFormError(response, 'form', 'field_value', _(u'This field is required.'))

    def test_regular_field_not_editable(self):
        self.login()

        fname = 'position'
        bulk_update_registry.register(Contact, exclude=[fname])
        self.assertFalse(bulk_update_registry.is_updatable(Contact, 'position'))

        unemployed = Position.objects.create(title='unemployed')
        mario, luigi, url = self.create_2_contacts_n_url(field=fname)
        self.assertPOST(400, url, data={'field_value': unemployed.id})

    def test_regular_field06(self):
        self.login()

        mario, luigi, url = self.create_2_contacts_n_url(mario_kwargs={'description': "Luigi's brother"},
                                                         luigi_kwargs={'description': "Mario's brother"},
                                                         field='description',
                                                        )
        response = self.client.post(url, data={'field_value': ''})
        self.assertNoFormError(response)
        self.assertEqual('', self.refresh(mario).description)
        self.assertEqual('', self.refresh(luigi).description)

    def test_regular_field07(self):
#        user = self.login(is_superuser=False, allowed_apps=('creme_core', 'persons'))
        user = self.login(is_superuser=False)

        mario_desc = u"Luigi's brother"
        create_bros = partial(Contact.objects.create, last_name='Bros')
        mario = create_bros(user=self.other_user, first_name='Mario', description=mario_desc)
        luigi = create_bros(user=user,            first_name='Luigi', description="Mario's brother")

        response = self.client.post(self._build_contact_url('description', mario.id, luigi.id),
                                    data={'field_value': ''},
                                   )
        self.assertNoFormError(response)
        self.assertEqual(mario_desc, self.refresh(mario).description)
        self.assertEqual('',         self.refresh(luigi).description)

    def test_regular_field08(self):
        self.login()

        mario, luigi, url = self.create_2_contacts_n_url(field='birthday')
        response = self.client.post(url, data={'field_value': 'bad date',})
        self.assertFormError(response, 'form', 'field_value', _(u'Enter a valid date.'))

        settings.DATE_INPUT_FORMATS += ("-%dT%mU%Y-",) #This weird format have few chances to be present in settings
        self.client.post(url, data={'field_value': '-31T01U2000-'})
        birthday = date(2000, 1, 31)
        self.assertEqual(birthday, self.refresh(mario).birthday)
        self.assertEqual(birthday, self.refresh(luigi).birthday)

    def test_regular_field09(self):
#        user = self.login(is_superuser=False, allowed_apps=('creme_core', 'persons', 'media_managers'))
        user = self.login(is_superuser=False)
        other_user = self.other_user

        create_bros = partial(Contact.objects.create, last_name='Bros')
        mario = create_bros(user=other_user, first_name='Mario')
        luigi = create_bros(user=user,       first_name='Luigi')

#        tmpfile = NamedTemporaryFile()
#        tmpfile.width = tmpfile.height = 0
#        tmpfile._committed = True

#        create_img = partial(Image.objects.create, image=tmpfile)
        create_img = Image.objects.create
        unallowed = create_img(user=other_user, name='unallowed')
        allowed   = create_img(user=user,       name='allowed')
        self.assertFalse(user.has_perm_to_view(unallowed))
        self.assertTrue(user.has_perm_to_view(allowed))

        url = self._build_contact_url('image', mario.id, luigi.id)
        response = self.assertPOST200(url, data={'field_value': unallowed.id})
        self.assertFormError(response, 'form', 'field_value',
                             _(u"You can't view this value, so you can't set it.")
                            )

        self.client.post(url, data={'field_value': allowed.id,})
        self.assertNotEqual(allowed, self.refresh(mario).image)
        self.assertEqual(allowed,    self.refresh(luigi).image)

    def test_regular_field10(self):
        self.login()

        class _InnerEditBirthday(BulkDefaultEditForm):
            pass

        bulk_update_registry.register(Contact, innerforms={'birthday': _InnerEditBirthday})

        mario, luigi, url = self.create_2_contacts_n_url(field='birthday')
        response = self.client.post(url, data={'field_value': '31-01-2000'})
        self.assertNoFormError(response)

        birthday = date(2000, 1, 31)
        self.assertEqual(birthday, self.refresh(mario).birthday)
        self.assertEqual(birthday, self.refresh(luigi).birthday)

    def test_regular_field11(self):
        """Fix a bug with the field list when bulk editing user
        (ie: a field of the parent class CremeEntity)
        """
        user = self.login()

        mario = Contact.objects.create(user=user, first_name="Mario", last_name="Bros")
        build_url = self._build_contact_url
        url = build_url('user', mario.id)
        response = self.assertGET200(url)

        with self.assertNoException():
            choices = response.context['form'].fields['_bulk_fieldname'].choices

        self.assertIn((url, _('Owner user')), choices)
        self.assertIn((build_url('first_name', mario.id), _('First name')), choices)

    def test_regular_field_many2many(self):
        user = self.login()

        categories = [MediaCategory.objects.create(name=name) for name in ('A', 'B', 'C')]

        image1 = self.create_image('image1', user, categories)
        image2 = self.create_image('image2', user, categories[:1])

        self.assertListEqual(list(image1.categories.all()), categories)
        self.assertListEqual(list(image2.categories.all()), categories[:1])

        url = self.build_bulkedit_url([image1, image2], 'categories')
        response = self.client.post(url, data={'field_value': [categories[0].pk,
                                                               categories[2].pk,
                                                              ],
                                              }
                                   )
        self.assertNoFormError(response)

        expected = [categories[0], categories[2]]
        self.assertListEqual(list(image1.categories.all()), expected)
        self.assertListEqual(list(image2.categories.all()), expected)

    def test_regular_field_many2many_invalid(self):
        user = self.login()

        categories = [MediaCategory.objects.create(name=name) for name in ('A', 'B', 'C')]

        image1 = self.create_image('image1', user, categories)
        image2 = self.create_image('image2', user, categories[:1])

        self.assertListEqual(list(image1.categories.all()), categories)
        self.assertListEqual(list(image2.categories.all()), categories[:1])

        url = self.build_bulkedit_url([image1, image2], 'categories')
        #invalid_pk = 12
        invalid_pk = (MediaCategory.objects.aggregate(Max('id'))['id__max'] or 0) + 1
        response = self.client.post(url, data={'field_value': [categories[0].pk, invalid_pk]})
        self.assertFormError(response, 'form', 'field_value',
                             _('Select a valid choice. %(value)s is not one of the available choices.') % {
                                    'value': invalid_pk,
                                }
                            )

        self.assertListEqual(list(image1.categories.all()), categories)
        self.assertListEqual(list(image2.categories.all()), categories[:1])

    def test_custom_field01(self):
        self.login()

        cf_int = CustomField.objects.create(name='int',
                                            content_type=self.contact_ct,
                                            field_type=CustomField.INT,
                                           )
        mario, luigi, url = self.create_2_contacts_n_url(field=_CUSTOMFIELD_FORMAT % cf_int.id)

        #Int
        response = self.client.post(url, data={'field_value': 10})
        self.assertNoFormError(response)
        self.assertEqual(10, self.get_cf_values(cf_int, self.refresh(mario)).value)
        self.assertEqual(10, self.get_cf_values(cf_int, self.refresh(luigi)).value)

        #Int empty
        response = self.client.post(url, data={'field_value': ''})
        self.assertNoFormError(response)
        self.assertRaises(CustomFieldInteger.DoesNotExist, self.get_cf_values, cf_int, self.refresh(mario))
        self.assertRaises(CustomFieldInteger.DoesNotExist, self.get_cf_values, cf_int, self.refresh(luigi))

    def test_custom_field02(self):
        self.login()

        cf_float = CustomField.objects.create(name='float',
                                              content_type=self.contact_ct,
                                              field_type=CustomField.FLOAT,
                                             )
        mario, luigi, url = self.create_2_contacts_n_url(field=_CUSTOMFIELD_FORMAT % cf_float.id)

        #Float
        response = self.client.post(url, data={'field_value': '10.2'})
        self.assertNoFormError(response)
        self.assertEqual(Decimal("10.2"), self.get_cf_values(cf_float, self.refresh(mario)).value)
        self.assertEqual(Decimal("10.2"), self.get_cf_values(cf_float, self.refresh(luigi)).value)

        #Float empty
        response = self.client.post(url, data={'field_value': ''})
        self.assertNoFormError(response)
        self.assertRaises(CustomFieldFloat.DoesNotExist, self.get_cf_values, cf_float, self.refresh(mario))
        self.assertRaises(CustomFieldFloat.DoesNotExist, self.get_cf_values, cf_float, self.refresh(luigi))

    def test_custom_field03(self):
        self.login()

        cf_bool = CustomField.objects.create(name='bool',
                                             content_type=self.contact_ct,
                                             field_type=CustomField.BOOL,
                                            )
        mario, luigi, url = self.create_2_contacts_n_url(field=_CUSTOMFIELD_FORMAT % cf_bool.id)

        #Bool
        response = self.client.post(url, data={'field_value': True})
        self.assertNoFormError(response)
        self.assertEqual(True, self.get_cf_values(cf_bool, self.refresh(mario)).value)
        self.assertEqual(True, self.get_cf_values(cf_bool, self.refresh(luigi)).value)

        #Bool false
        response = self.client.post(url, data={'field_value': False})
        self.assertNoFormError(response)
        self.assertEqual(False, self.get_cf_values(cf_bool, self.refresh(mario)).value)
        self.assertEqual(False, self.get_cf_values(cf_bool, self.refresh(luigi)).value)

        #Bool empty
        response = self.client.post(url, data={'field_value': None})
        self.assertNoFormError(response)
        self.assertRaises(CustomFieldBoolean.DoesNotExist, self.get_cf_values, cf_bool, self.refresh(mario))
        self.assertRaises(CustomFieldBoolean.DoesNotExist, self.get_cf_values, cf_bool, self.refresh(luigi))

    def test_custom_field04(self):
        self.login()

        cf_str = CustomField.objects.create(name='str',
                                            content_type=self.contact_ct,
                                            field_type=CustomField.STR,
                                           )
        mario, luigi, url = self.create_2_contacts_n_url(field=_CUSTOMFIELD_FORMAT % cf_str.id)

        #Str
        response = self.client.post(url, data={'field_value': 'str'})
        self.assertNoFormError(response)
        self.assertEqual('str', self.get_cf_values(cf_str, self.refresh(mario)).value)
        self.assertEqual('str', self.get_cf_values(cf_str, self.refresh(luigi)).value)

        #Str empty
        response = self.client.post(url, data={'field_value': ''})
        self.assertNoFormError(response)
        self.assertRaises(CustomFieldString.DoesNotExist, self.get_cf_values, cf_str, self.refresh(mario))
        self.assertRaises(CustomFieldString.DoesNotExist, self.get_cf_values, cf_str, self.refresh(luigi))

    def test_custom_field05(self):
        self.login()

        get_cf_values = self.get_cf_values
        cf_date = CustomField.objects.create(name='date',
                                             content_type=self.contact_ct,
                                             field_type=CustomField.DATETIME,
                                            )
        mario, luigi, url = self.create_2_contacts_n_url(field=_CUSTOMFIELD_FORMAT % cf_date.id)

        #Date
        settings.DATETIME_INPUT_FORMATS += ("-%dT%mU%Y-",) #This weird format have few chances to be present in settings
        response = self.client.post(url, data={'field_value': '-31T01U2000-'})
        self.assertNoFormError(response)

        dt = self.create_datetime(2000, 1, 31)
        self.assertEqual(dt, get_cf_values(cf_date, self.refresh(mario)).value)
        self.assertEqual(dt, get_cf_values(cf_date, self.refresh(luigi)).value)

        #Date
        response = self.client.post(url, data={'field_value': ''})
        self.assertNoFormError(response)
        self.assertRaises(CustomFieldDateTime.DoesNotExist, get_cf_values, cf_date, self.refresh(mario))
        self.assertRaises(CustomFieldDateTime.DoesNotExist, get_cf_values, cf_date, self.refresh(luigi))

    def test_custom_field06(self):
        self.login()
        get_cf_values = self.get_cf_values

        cf_enum = CustomField.objects.create(name='enum',
                                             content_type=self.contact_ct,
                                             field_type=CustomField.ENUM,
                                            )
        enum1 = CustomFieldEnumValue.objects.create(custom_field= cf_enum, value=u"Enum1")
        CustomFieldEnumValue.objects.create(custom_field= cf_enum,         value=u"Enum2")

        mario, luigi, url = self.create_2_contacts_n_url(field=_CUSTOMFIELD_FORMAT % cf_enum.id)

        #Enum
        response = self.client.post(url, data={'field_value': enum1.id})
        self.assertNoFormError(response)
        self.assertEqual(enum1, get_cf_values(cf_enum, self.refresh(mario)).value)
        self.assertEqual(enum1, get_cf_values(cf_enum, self.refresh(luigi)).value)

        #Enum empty
        response = self.client.post(url, data={'field_value': ''})
        self.assertNoFormError(response)
        self.assertRaises(CustomFieldEnum.DoesNotExist, get_cf_values, cf_enum, self.refresh(mario))
        self.assertRaises(CustomFieldEnum.DoesNotExist, get_cf_values, cf_enum, self.refresh(luigi))

    def test_custom_field07(self):
        self.login()
        get_cf_values = self.get_cf_values

        cf_multi_enum = CustomField.objects.create(name='multi_enum',
                                                   content_type=self.contact_ct,
                                                   field_type=CustomField.MULTI_ENUM,
                                                  )

        create_cfvalue = partial(CustomFieldEnumValue.objects.create, custom_field=cf_multi_enum)
        m_enum1 = create_cfvalue(value='MEnum1')
        create_cfvalue(value='MEnum2')
        m_enum3 = create_cfvalue(value='MEnum3')

        mario, luigi, url = self.create_2_contacts_n_url(field=_CUSTOMFIELD_FORMAT % cf_multi_enum.id)
        self.assertGET200(url)

        #Multi-Enum
        self.assertNoFormError(self.client.post(url, data={'field_value': [m_enum1.id, m_enum3.id]}))
        mario = self.refresh(mario)
        luigi = self.refresh(luigi)

        values_set = set(get_cf_values(cf_multi_enum, mario).value.values_list('pk', flat=True))
        self.assertIn(m_enum1.id, values_set)
        self.assertIn(m_enum3.id, values_set)

        values_set = set(get_cf_values(cf_multi_enum, luigi).value.values_list('pk', flat=True))
        self.assertIn(m_enum1.id, values_set)
        self.assertIn(m_enum3.id, values_set)

        #Multi-Enum empty
        self.assertNoFormError(self.client.post(url, data={'field_value': []}))
        self.assertRaises(CustomFieldMultiEnum.DoesNotExist, get_cf_values, cf_multi_enum, self.refresh(mario))
        self.assertRaises(CustomFieldMultiEnum.DoesNotExist, get_cf_values, cf_multi_enum, self.refresh(luigi))

    def test_other_field_validation_error(self):
        user = self.login()
#        empty_user1 = User.objects.create_user('empty1')
#        empty_user2 = User.objects.create_user('empty2')
        create_empty_user = partial(get_user_model().objects.create_user,
                                    first_name='', last_name='', email='',
                                   )
        empty_user1 = create_empty_user(username='empty1')
        empty_user2 = create_empty_user(username='empty2')

        create_contact = partial(Contact.objects.create, user=user, first_name='', last_name='')
        empty_contact1 = create_contact(is_user=empty_user1)
        empty_contact2 = create_contact(is_user=empty_user2)
        mario          = create_contact(first_name="Mario", last_name="Bros")

        url = self.build_bulkedit_url([empty_contact1, empty_contact2, mario], 'last_name')
        self.assertGET200(url)

        response = self.client.post(url, data={'field_value': 'Bros'})
        self.assertNoFormError(response)
        self.assertContains(response, _('This Contact is related to a user and must have a first name.'), 2)


class InnerEditTestCase(_BulkEditTestCase):
    def create_contact(self):
        return Contact.objects.create(user=self.user, first_name="Mario", last_name="Bros")

    def create_orga(self):
        return Organisation.objects.create(user=self.user, name="Organisation")

    def test_regular_field_01(self):
        self.login()

        mario = self.create_contact()
        self.assertGET(400, self.build_inneredit_url(mario, 'unknown'))

        url = self.build_inneredit_url(mario, 'first_name')
        self.assertGET200(url)

        first_name = 'Luigi'
        response = self.client.post(url, data={'entities_lbl': [unicode(mario)],
                                               'field_value': first_name,
                                              }
                                   )
        self.assertNoFormError(response)
        self.assertEqual(first_name, self.refresh(mario).first_name)

    def test_regular_field_02(self):
        self.login()

        mario = self.create_contact()
        response = self.client.post(self.build_inneredit_url(mario, 'birthday'),
                                    data={#'entities_lbl': [unicode(mario)],
                                          'field_value': 'whatever',
                                         }
                                   )
        self.assertFormError(response, 'form', 'field_value', _(u'Enter a valid date.'))

    def test_regular_field_03(self):
        "No permission"
        self.login(is_superuser=False, creatable_models=[Contact], allowed_apps='documents')
        self._set_all_creds_except_one(EntityCredentials.CHANGE)

        mario = self.create_contact()
        self.assertFalse(self.user.has_perm_to_change(mario))

        self.assertGET403(self.build_inneredit_url(mario, 'first_name'))

    def test_regular_field_not_editable(self):
        self.login()

        mario = self.create_contact()
        self.assertFalse(mario._meta.get_field('is_user').editable)

        url = self.build_inneredit_url(mario, 'is_user')
        self.assertGET(400, url)
        self.assertPOST(400, url, data={'field_value': self.other_user.id})

    def test_regular_field_fields_config(self):
        self.login()

        hidden_fname = 'phone'
        hidden_fkname = 'image'
        hidden_subfname = 'zipcode'

        create_fconf = FieldsConfig.create
        create_fconf(Contact, descriptions=[(hidden_fname,  {FieldsConfig.HIDDEN: True}),
                                            (hidden_fkname, {FieldsConfig.HIDDEN: True}),
                                           ],
                    )
        create_fconf(Address, descriptions=[(hidden_subfname, {FieldsConfig.HIDDEN: True})])

        mario = self.create_contact()

        build_url = partial(self.build_inneredit_url, mario)
        self.assertGET(400, build_url(hidden_fname))
        self.assertGET(400, build_url(hidden_fkname))
        self.assertGET(400, build_url('address__' + hidden_subfname))

    def test_regular_field_many2many(self):
        user = self.login()

        create_cat = MediaCategory.objects.create
        categories = [create_cat(name='A'), create_cat(name='B'), create_cat(name='C')]

        image = self.create_image('image', user, categories)
        self.assertListEqual(list(image.categories.all()), categories)

        url = self.build_inneredit_url(image, 'categories')
        response = self.client.post(url, data={'field_value': [categories[0].pk, categories[2].pk]})
        self.assertNoFormError(response)

        image = self.refresh(image)
        self.assertListEqual(list(image.categories.all()), [categories[0], categories[2]])

    def test_regular_field_many2many_invalid(self):
        user = self.login()

        create_cat = MediaCategory.objects.create
        categories = [create_cat(name='A'), create_cat(name='B'), create_cat(name='C')]

        image = self.create_image('image', user, categories)
        self.assertEqual(set(image.categories.all()), set(categories))

        invalid_pk = 1024
        self.assertFalse(MediaCategory.objects.filter(id=invalid_pk))

        url = self.build_inneredit_url(image, 'categories')
        response = self.client.post(url, data={'field_value': [categories[0].pk, invalid_pk]})
        self.assertFormError(response, 'form', 'field_value',
                             _('Select a valid choice. %(value)s is not one of the available choices.') % {
                                    'value': invalid_pk,
                                }
                            )

        image = self.refresh(image)
        self.assertEqual(set(image.categories.all()), set(categories))

    def test_regular_field_innerform(self):
        self.login()

        class _InnerEditName(BulkDefaultEditForm):
            def clean(self):
                raise ValidationError('invalid name')

        bulk_update_registry.register(Contact, innerforms={'last_name': _InnerEditName})

        mario = self.create_contact()
        url = self.build_inneredit_url(mario, 'last_name')

        self.assertGET200(url)
        response = self.assertPOST200(url, data={'field_value': 'luigi'}
                                      )

        self.assertFormError(response, 'form', '', 'invalid name')

    def test_regular_field_innerform_fielderror(self):
        self.login()

        class _InnerEditName(BulkDefaultEditForm):
            def _bulk_clean_entity(self, entity, values):
                entity = BulkDefaultEditForm._bulk_clean_entity(self, entity, values)
                raise ValidationError('invalid name')

        bulk_update_registry.register(Contact, innerforms={'last_name': _InnerEditName})

        mario = self.create_contact()
        url = self.build_inneredit_url(mario, 'last_name')
        self.assertGET200(url)

        response = self.assertPOST200(url, data={'field_value': 'luigi'})
        self.assertFormError(response, 'form', None, 'invalid name')

    def test_custom_field(self):
        self.login()
        mario = self.create_contact()
        cfield = CustomField.objects.create(name='custom 1', content_type=mario.entity_type,
                                            field_type=CustomField.STR,
                                           )
        url = self.build_inneredit_url(mario, _CUSTOMFIELD_FORMAT % cfield.id)
        self.assertGET200(url)

        value = 'hihi'
        response = self.client.post(url, data={'field_value': value})
        self.assertNoFormError(response)
        self.assertEqual(value, self.get_cf_values(cfield, self.refresh(mario)).value)

    def test_related_subfield_missing(self):
        self.login()
        orga = self.create_orga()

#        url = self.build_inneredit_url(orga, 'billing_address__city')
        url = self.build_inneredit_url(orga, 'address__city')
        self.assertGET200(url)

        city = 'Marseille'
        response = self.client.post(url, data={'field_value': city})
        self.assertFormError(response, 'form', None,
                             _(u'The field %s is empty') % _('Billing address')
                            )

    def test_related_subfield(self):
        self.login()
        orga = self.create_orga()
#        orga.billing_address = Address.objects.create(owner=orga, name='address 1')
        orga.address = Address.objects.create(entity=orga, value='address 1')
        orga.save()

#        url = self.build_inneredit_url(orga, 'billing_address__city')
        url = self.build_inneredit_url(orga, 'address__city')
        self.assertGET200(url)

        city = 'Marseille'
        response = self.client.post(url, data={'field_value': city})
        self.assertNoFormError(response)
#        self.assertEqual(city, self.refresh(orga).billing_address.city)
        self.assertEqual(city, self.refresh(orga).address.city)

    def test_related_field(self):
        self.login()
        orga = self.create_orga()
#        orga.billing_address = Address.objects.create(owner=orga, name='address 1')
        orga.address = Address.objects.create(entity=orga, value='address 1')
        orga.save()

#        url = self.build_inneredit_url(orga, 'billing_address')
        url = self.build_inneredit_url(orga, 'address')
        self.assertGET(400, url)

    def test_manytomany_field(self):
        "Edition of a manytomany field (needs a special hack with initial values for this case)"
        user = self.login()
        image = Image.objects.create(user=user, name='Konoha by nigth')

        url = self.build_inneredit_url(image, 'categories')
        self.assertGET(200, url)

    def test_other_field_validation_error(self):
        user = self.login()
        empty_user = get_user_model().objects.create_user(username='empty',
                                                          first_name="",
                                                          last_name="",
                                                          email="",
                                                         )
        empty_contact = Contact.objects.create(user=user, first_name="",
                                               last_name="", is_user=empty_user,
                                              )

        url = self.build_inneredit_url(empty_contact, 'last_name')
        self.assertGET200(url)

        response = self.client.post(url, data={'field_value': 'Bros'})
        self.assertFormError(response, 'form', None,
                             _('This Contact is related to a user and must have a first name.')
                            )

    def test_both_edited_field_and_field_validation_error(self):
        user = self.login()
        empty_user = get_user_model().objects.create_user(username='empty',
                                                          first_name="",
                                                          last_name="",
                                                          email="",
                                                         )
        empty_contact = Contact.objects.create(user=user, first_name="",
                                               last_name="", is_user=empty_user,
                                              )

        url = self.build_inneredit_url(empty_contact, 'last_name')
        self.assertGET200(url)

        response = self.client.post(url, data={'field_value': ''})
        self.assertFormError(response, 'form', 'field_value',
                             _(u'This field is required.')
                            )
