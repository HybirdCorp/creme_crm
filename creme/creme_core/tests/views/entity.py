# -*- coding: utf-8 -*-

try:
    from datetime import date # datetime
    from decimal import Decimal
    from functools import partial
    from tempfile import NamedTemporaryFile

    from django.core.serializers.json import simplejson
    from django.utils.translation import ugettext as _
    from django.contrib.contenttypes.models import ContentType
    from django.conf import settings

    from .base import ViewsTestCase
    from creme.creme_core.auth.entity_credentials import EntityCredentials
    from creme.creme_core.models import *
    from creme.creme_core.forms.base import _CUSTOM_NAME
    from creme.creme_core.gui.bulk_update import bulk_update_registry
    from creme.creme_core.blocks import trash_block

    from creme.media_managers.models.image import Image

    from creme.persons.models import Contact, Organisation, Position, Sector, Address
except Exception as e:
    print 'Error in <%s>: %s' % (__name__, e)


__all__ = ('EntityViewsTestCase', 'BulkEditTestCase', 'InnerEditTestCase')


class EntityViewsTestCase(ViewsTestCase):
    CLONE_URL        = '/creme_core/entity/clone'
    DEL_ENTITIES_URL = '/creme_core/entity/delete/multi'
    EMPTY_TRASH_URL  = '/creme_core/entity/trash/empty'
    SEARCHNVIEW_URL  = '/creme_core/entity/search_n_view'

    @classmethod
    def setUpClass(cls):
        cls.populate('creme_core', 'creme_config')

    def _build_delete_url(self, entity):
        return '/creme_core/entity/delete/%s' % entity.id

    def _build_restore_url(self, entity):
        return '/creme_core/entity/restore/%s' % entity.id

    def test_get_fields(self):
        self.login()

        url = '/creme_core/entity/get_fields'
        ct_id = ContentType.objects.get_for_model(CremeEntity).id
        response = self.assertPOST200(url, data={'ct_id': ct_id})
        self.assertEqual('text/javascript', response['Content-Type'])

        content = simplejson.loads(response.content)
        self.assertIsInstance(content, list)
        self.assertEqual(7, len(content))

        fmt = u'[%s] - %s'
        #user_str = _('User')
        user_str = _('Owner user')
        self.assertEqual(content[0],    ['created',          _('Creation date')])
        self.assertEqual(content[1],    ['modified',         _('Last modification')])
        self.assertEqual(content[2],    ['user__username',   fmt % (user_str, _('username'))]) #TODO: hook user to set 'Username' ??
        self.assertEqual(content[3],    ['user__first_name', fmt % (user_str, _('first name'))]) #TODO: idem
        self.assertEqual(content[4][0], 'user__last_name')
        self.assertEqual(content[5][0], 'user__email')
        self.assertEqual(content[6][0], 'user__is_team')

        response = self.assertPOST404(url, data={'ct_id': 0})
        self.assertEqual('text/javascript', response['Content-Type'])

        response = self.assertPOST(400, url, data={'ct_id': 'notint'})
        self.assertEqual('text/javascript', response['Content-Type'])

        response = self.assertPOST(400, url, data={'ct_id': ct_id, 'deep': 'notint'})
        self.assertEqual('text/javascript', response['Content-Type'])

    def test_get_function_fields(self):
        self.login()

        url = '/creme_core/entity/get_function_fields'

        ct_id = ContentType.objects.get_for_model(CremeEntity).id
        response = self.assertPOST200(url, data={'ct_id': ct_id})
        self.assertEqual('text/javascript', response['Content-Type'])

        content = simplejson.loads(response.content)
        self.assertIsInstance(content, list)
        self.assertEqual(len(list(CremeEntity.function_fields)), len(content))
        self.assertIn(['get_pretty_properties', _('Properties')], content)

        response = self.assertPOST404(url, data={'ct_id': 0})
        self.assertEqual('text/javascript', response['Content-Type'])

        response = self.assertPOST(400, url, data={'ct_id': 'notint'})
        self.assertEqual('text/javascript', response['Content-Type'])

    def test_get_custom_fields(self):
        self.login()

        def get_cf(ct_id):
            return self.client.post('/creme_core/entity/get_custom_fields',
                                    data={'ct_id': ct_id}
                                   )

        ct = ContentType.objects.get_for_model(CremeEntity)
        response = get_cf(ct.id)
        self.assertEqual(200,               response.status_code)
        self.assertEqual('text/javascript', response['Content-Type'])
        self.assertEqual([], simplejson.loads(response.content))

        create_cf = partial(CustomField.objects.create, content_type=ct)
        cf1 = create_cf(name='Size',   field_type=CustomField.INT)
        cf2 = create_cf(name='Weight', field_type=CustomField.FLOAT)

        response = get_cf(ct.id)
        self.assertEqual([[cf1.id, cf1.name], [cf2.id, cf2.name]],
                         simplejson.loads(response.content)
                        )

        response = get_cf(0)
        self.assertEqual(404,               response.status_code)
        self.assertEqual('text/javascript', response['Content-Type'])

        response = get_cf('notint')
        self.assertEqual(400,               response.status_code)
        self.assertEqual('text/javascript', response['Content-Type'])

    #def test_get_creme_entity_as_json01(self):
        #self.login()

        #with self.assertNoException():
            #entity = CremeEntity.objects.create(user=self.user)

        #response = self.assertPOST200('/creme_core/entity/json', data={'pk': entity.id})
        #self.assertEqual('text/javascript', response['Content-Type'])

        #json_data = simplejson.loads(response.content)
        ##[{'pk': 1,
        ##  'model': 'creme_core.cremeentity',
        ##  'fields': {'is_actived': False,
        ##             'is_deleted': False,
        ##             'created': '2010-11-09 14:34:04',
        ##             'header_filter_search_field': '',
        ##             'entity_type': 100,
        ##             'modified': '2010-11-09 14:34:04',
        ##             'user': 1
        ##            }
        ##}]
        #with self.assertNoException():
            #dic = json_data[0]
            #pk     = dic['pk']
            #model  = dic['model']
            #fields = dic['fields']
            #user = fields['user']

        #self.assertEqual(entity.id, pk)
        #self.assertEqual('creme_core.cremeentity', model)
        #self.assertEqual(self.user.id, user)

    #def test_get_creme_entity_as_json02(self):
        #self.login()

        #with self.assertNoException():
            #entity = CremeEntity.objects.create(user=self.user)

        #response = self.assertPOST200('/creme_core/entity/json',
                                      #data={'pk':     entity.id,
                                            #'fields': ['user', 'entity_type'],
                                           #}
                                     #)

        #json_data = simplejson.loads(response.content)
        ##[{'pk': 1,
        ##  'model': 'creme_core.cremeentity',
        ##  'fields': {'user': 1, 'entity_type': 100}}
        ##]
        #with self.assertNoException():
            #fields = json_data[0]['fields']
            #user = fields['user']
            #entity_type = fields['entity_type']

        #self.assertEqual(self.user.id, user)
        #self.assertEqual(ContentType.objects.get_for_model(CremeEntity).id, entity_type)

    def test_json_entity_get01(self):
        self.login()
        url_fmt = '/creme_core/relation/entity/%s/json'
        rei = Contact.objects.create(user=self.user, first_name='Rei', last_name='Ayanami')
        nerv = Organisation.objects.create(user=self.user, name='Nerv')

        url = url_fmt % rei.id
        self.assertGET(400, url)

        response = self.assertGET200(url, data={'fields': ['id']})
        self.assertEqual([[rei.id]], simplejson.loads(response.content))

        response = self.assertGET200(url, data={'fields': ['unicode']})
        self.assertEqual([[unicode(rei)]], simplejson.loads(response.content))

        response = self.assertGET200(url_fmt % nerv.id, data={'fields': ['id', 'unicode']})
        self.assertEqual([[nerv.id, unicode(nerv)]], simplejson.loads(response.content))

        self.assertGET(400, url_fmt % 1024)
        self.assertGET403(url, data={'fields': ['id', 'unknown']})

    def test_json_entity_get02(self):
        self.login(is_superuser=False)

        nerv = Organisation.objects.create(user=self.other_user, name='Nerv')
        self.assertGET(400, '/creme_core/relation/entity/%s/json' % nerv.id)

    def test_get_creme_entities_repr(self): #TODO: test with no permissons
        self.login()

        with self.assertNoException():
            entity = CremeEntity.objects.create(user=self.user)

        response = self.assertGET200('/creme_core/entity/get_repr/%s' % entity.id)
        self.assertEqual('text/javascript', response['Content-Type'])
        json_data = simplejson.loads(response.content)
        self.assertEqual('Creme entity: %s' % entity.id, json_data[0]['text'])

    def test_delete_entity01(self):
        "is_deleted=False -> trash"
        self.login()

        entity = Organisation.objects.create(user=self.user, name='Nerv')
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
        self.login()

        #to get a get_lv_absolute_url() method
        entity = Organisation.objects.create(user=self.user, name='Nerv', is_deleted=True)

        url = self._build_delete_url(entity)
        self.assertGET404(url)
        self.assertRedirects(self.client.post(url), entity.get_lv_absolute_url())
        self.assertFalse(Organisation.objects.filter(pk=entity.id))

    def test_delete_entity03(self):
        "No DELETE credentials"
        self.login(is_superuser=False)

        entity = Organisation.objects.create(user=self.other_user, name='Nerv')

        self.assertPOST403(self._build_delete_url(entity))
        self.get_object_or_fail(Organisation, pk=entity.id)

    def test_delete_entity04(self):#TODO: detect dependencies when trashing ??
        "Dependencies problem"
        self.login()

        create_orga = partial(Organisation.objects.create, user=self.other_user, is_deleted=True)
        entity01 = create_orga(name='Nerv')
        entity02 = create_orga(name='Seele')

        rtype, srtype = RelationType.create(('test-subject_linked', 'is linked to'),
                                            ('test-object_linked',  'is linked to')
                                           )
        Relation.objects.create(user=self.user, type=rtype, subject_entity=entity01, object_entity=entity02)

        response = self.assertPOST403(self._build_delete_url(entity01))
        self.assertTemplateUsed(response, 'creme_core/forbidden.html')
        self.assertEqual(2, Organisation.objects.filter(pk__in=[entity01.id, entity02.id]).count())

    def test_delete_entity05(self):
        "is_deleted=False -> trash"
        self.login()

        entity = Organisation.objects.create(user=self.user, name='Nerv')
        self.assertPOST200(self._build_delete_url(entity), HTTP_X_REQUESTED_WITH='XMLHttpRequest')

        with self.assertNoException():
            entity = self.refresh(entity)

        self.assertIs(entity.is_deleted, True)

    def test_delete_entities01(self):
        "NB: for the deletion of auxiliary entities => see billing app"
        self.login()

        create_entity = partial(CremeEntity.objects.create, user=self.user)
        entity01, entity02 = (create_entity() for i in xrange(2))
        entity03, entity04 = (create_entity(is_deleted=True) for i in xrange(2))

        self.assertPOST200(self.DEL_ENTITIES_URL,
                           data={'ids': '%s,%s,%s' % (entity01.id, entity02.id, entity03.id)}
                          )
        entity01 = self.get_object_or_fail(CremeEntity, pk=entity01.id)
        self.assertTrue(entity01.is_deleted)

        entity02 = self.get_object_or_fail(CremeEntity, pk=entity02.id)
        self.assertTrue(entity02.is_deleted)

        self.assertFalse(CremeEntity.objects.filter(pk=entity03.id).exists())
        self.assertTrue(CremeEntity.objects.filter(pk=entity04.id).exists())

    def test_delete_entities02(self):
        self.login()

        create_entity = partial(CremeEntity.objects.create, user=self.user)
        entity01, entity02 = (create_entity() for i in xrange(2))

        self.assertPOST404(self.DEL_ENTITIES_URL,
                           data={'ids': '%s,%s,' % (entity01.id, entity02.id + 1)}
                          )
        #self.assertFalse(CremeEntity.objects.filter(pk=entity01.id))
        entity01 = self.get_object_or_fail(CremeEntity, pk=entity01.id)
        self.assertTrue(entity01.is_deleted)

        self.get_object_or_fail(CremeEntity, pk=entity02.id)

    def test_delete_entities03(self):
        self.login(is_superuser=False)

        forbidden = CremeEntity.objects.create(user=self.other_user)
        allowed   = CremeEntity.objects.create(user=self.user)

        self.assertPOST403(self.DEL_ENTITIES_URL, data={'ids': '%s,%s,' % (forbidden.id, allowed.id)})
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
        self.login()

        create_orga = partial(Organisation.objects.create, user=self.user)
        entity1 = create_orga(name='Nerv', is_deleted=True)
        entity2 = create_orga(name='Seele')

        response = self.assertGET200('/creme_core/entity/trash')
        self.assertTemplateUsed(response, 'creme_core/trash.html')
        self.assertContains(response, 'id="%s"' % trash_block.id_)
        self.assertContains(response, unicode(entity1))
        self.assertNotContains(response, unicode(entity2))

    def test_restore_entity01(self):
        "No trashed"
        self.login()

        entity = Organisation.objects.create(user=self.user, name='Nerv')
        url = self._build_restore_url(entity)
        self.assertGET404(url)
        self.assertPOST404(url)

    def test_restore_entity02(self):
        self.login()

        entity = Organisation.objects.create(user=self.user, name='Nerv', is_deleted=True)
        url = self._build_restore_url(entity)

        self.assertGET404(url)
        self.assertRedirects(self.client.post(url), entity.get_absolute_url())

        entity = self.get_object_or_fail(Organisation, pk=entity.pk)
        self.assertFalse(entity.is_deleted)

    def test_restore_entity03(self):
        self.login()

        entity = Organisation.objects.create(user=self.user, name='Nerv', is_deleted=True)
        self.assertPOST200(self._build_restore_url(entity), HTTP_X_REQUESTED_WITH='XMLHttpRequest')

        entity = self.get_object_or_fail(Organisation, pk=entity.pk)
        self.assertFalse(entity.is_deleted)

    def test_empty_trash01(self):
        self.login(is_superuser=False, allowed_apps=('creme_core', 'persons'))

        user = self.user
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
        self.get_object_or_fail(Contact, pk=contact3.pk)

    def test_empty_trash02(self):
        self.login()

        create_entity = partial(CremeEntity.objects.create, user=self.user, is_deleted=True)
        entity01 = create_entity()
        entity02 = create_entity()
        entity03 = create_entity() #not linked => can be deleted

        rtype, srtype = RelationType.create(('test-subject_linked', 'is linked to'),
                                            ('test-object_linked',  'is linked to')
                                           )
        Relation.objects.create(user=self.user, type=rtype, subject_entity=entity01, object_entity=entity02)

        self.assertPOST(400, self.EMPTY_TRASH_URL)
        self.assertEqual(2, CremeEntity.objects.filter(pk__in=[entity01.id, entity02.id]).count())
        self.assertFalse(CremeEntity.objects.filter(pk=entity03.id))

    def test_get_info_fields01(self):
        self.login()

        furl = '/creme_core/entity/get_info_fields/%s/json'
        ct = ContentType.objects.get_for_model(Contact)
        response = self.assertGET200(furl % ct.id)

        json_data = simplejson.loads(response.content)
        #print json_data
        self.assertIsInstance(json_data, list)
        self.assertTrue(all(isinstance(elt, list) for elt in json_data))
        self.assertTrue(all(len(elt) == 2 for elt in json_data))

        names = ['created', 'modified', 'first_name', 'last_name', 'description',
                 'skype', 'phone', 'mobile', 'fax', 'email', 'url_site', 'birthday'
                ]
        diff = set(names) - set(name for name, vname in json_data)
        self.assertFalse(diff, diff)
        self.assertEqual(len(names), len(json_data))

        json_dict = dict(json_data)
        self.assertEqual(_(u'First name'), json_dict['first_name'])
        self.assertEqual(_(u'%s [CREATION]') % _(u'Last name'),
                         json_dict['last_name']
                        )

    def test_get_info_fields02(self):
        self.login()

        furl = '/creme_core/entity/get_info_fields/%s/json'
        ct = ContentType.objects.get_for_model(Organisation)
        json_data = simplejson.loads(self.client.get(furl % ct.id).content)
        #print json_data

        names = ['created', 'modified', 'name', 'description', 'annual_revenue',
                 'url_site', 'fax', 'naf', 'siren', 'phone', 'siret', 'rcs', 'email',
                 'creation_date',  'tvaintra', 'subject_to_vat', 'capital'
                ]
        self.assertEqual(set(names), set(name for name, vname in json_data))
        self.assertEqual(len(names), len(json_data))

        json_dict = dict(json_data)
        self.assertEqual(_(u'Description'), json_dict['description'])
        self.assertEqual(_(u'%s [CREATION]') % _(u'Name'), 
                         json_dict['name']
                        )

    def test_clone01(self):
        self.login()
        url = self.CLONE_URL
        mario = Contact.objects.create(user=self.user, first_name="Mario", last_name="Bros")

        self.assertPOST200(url, data={'id': mario.id}, follow=True)
        self.assertPOST404(url, data={})
        self.assertPOST404(url, data={'id': 0})

    def test_clone02(self):
        self.login(is_superuser=False)

        mario = Contact.objects.create(user=self.other_user, first_name="Mario", last_name="Bros")
        self.assertPOST403(self.CLONE_URL, data={'id': mario.id}, follow=True)

    def test_clone03(self):
        self.login(is_superuser=False, creatable_models=[ct.model_class() for ct in ContentType.objects.all()])
        self._set_all_creds_except_one(EntityCredentials.VIEW)

        mario = Contact.objects.create(user=self.other_user, first_name="Mario", last_name="Bros")
        self.assertPOST403(self.CLONE_URL, data={'id': mario.id}, follow=True)

    def test_clone04(self):
        self.login(is_superuser=False, allowed_apps=('creme_core', 'persons'),
                   creatable_models=[ct.model_class() for ct in ContentType.objects.all()],
                  )
        self._set_all_creds_except_one(None)

        mario = Contact.objects.create(user=self.user, first_name="Mario", last_name="Bros")
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

    def _assert_detailview(self, response, entity):
        self.assertEqual(200, response.status_code)
        self.assertRedirects(response, entity.get_absolute_url())

    def test_search_and_view01(self):
        self.login()

        phone = '123456789'
        url = self.SEARCHNVIEW_URL
        data = {'models': 'persons-contact',
                'fields': 'phone',
                'value':  phone,
               }
        self.assertGET404(url, data=data)

        create_contact = partial(Contact.objects.create, user=self.user)
        onizuka = create_contact(first_name='Eikichi', last_name='Onizuka')
        create_contact(first_name='Ryuji', last_name='Danma', phone='987654', mobile=phone)
        self.assertGET404(url, data=data)

        onizuka.phone = phone
        onizuka.save()
        self._assert_detailview(self.client.get(url, data=data, follow=True), onizuka)

    def test_search_and_view02(self):
        self.login()

        phone = '999999999'
        url = self.SEARCHNVIEW_URL
        data = {'models': 'persons-contact',
                'fields': 'phone,mobile',
                'value':  phone,
               }
        self.assertGET404(url, data=data)

        create_contact = partial(Contact.objects.create, user=self.user)
        onizuka  = create_contact(first_name='Eikichi', last_name='Onizuka', mobile=phone)
        create_contact(first_name='Ryuji', last_name='Danma', phone='987654')
        self._assert_detailview(self.client.get(url, data=data, follow=True), onizuka)

    def test_search_and_view03(self):
        self.login()

        phone = '696969'
        url = self.SEARCHNVIEW_URL
        data = {'models':  'persons-contact,persons-organisation',
                'fields': 'phone,mobile',
                'value': phone,
               }
        self.assertGET404(url, data=data)

        create_contact = partial(Contact.objects.create, user=self.user)
        onizuka = create_contact(first_name='Eikichi', last_name='Onizuka', mobile='55555')
        create_contact(first_name='Ryuji',   last_name='Danma',   phone='987654')

        onibaku = Organisation.objects.create(user=self.user, name='Onibaku', phone=phone)
        self._assert_detailview(self.client.get(url, data=data, follow=True), onibaku)

        onizuka.mobile = phone
        onizuka.save()
        self._assert_detailview(self.client.get(url, data=data, follow=True), onizuka)

    def test_search_and_view04(self):
        "Errors"
        self.login()

        url = self.SEARCHNVIEW_URL
        base_data = {'models': 'persons-contact,persons-organisation',
                     'fields': 'mobile,phone',
                     'value':  '696969',
                    }
        create_contact = partial(Contact.objects.create, user=self.user)
        create_contact(first_name='Eikichi', last_name='Onizuka', mobile='55555')
        create_contact(first_name='Ryuji',   last_name='Danma', phone='987654')
        Organisation.objects.create(user=self.user, name='Onibaku', phone='54631357')

        self.assertGET404(url, data=dict(base_data, models='foo-bar'))
        self.assertGET404(url, data=dict(base_data, models='foobar'))
        self.assertGET404(url, data=dict(base_data, values=''))
        self.assertGET404(url, data=dict(base_data, models=''))
        self.assertGET404(url, data=dict(base_data), fields='')
        self.assertGET404(url, data=dict(base_data, models='persons-civility')) #not CremeEntity

    def test_search_and_view05(self): #creds
        self.login(is_superuser=False)
        self.role.allowed_apps = ['creme_core', 'persons']
        self.role.save()

        phone = '44444'
        url = self.SEARCHNVIEW_URL
        data = {'models': 'persons-contact,persons-organisation',
                'fields': 'phone,mobile',
                'value':  phone,
               }
        user = self.user
        create_contact = Contact.objects.create
        onizuka = create_contact(user=self.other_user, first_name='Eikichi', last_name='Onizuka', mobile=phone) #phone Ok and but not readable
        ryuji   = create_contact(user=user,            first_name='Ryuji',   last_name='Danma',   phone='987654') #phone KO
        onibaku = Organisation.objects.create(user=user, name='Onibaku', phone=phone) #phone Ok and readable

        has_perm = user.has_perm_to_view
        self.assertFalse(has_perm(onizuka))
        self.assertTrue(has_perm(ryuji))
        self.assertTrue(has_perm(onibaku))
        self._assert_detailview(self.client.get(url, data=data, follow=True), onibaku)

    def test_search_and_view06(self):
        "App credentials"
        self.login(is_superuser=False)
        self.role.allowed_apps = ['creme_core'] #not 'persons'
        self.role.save()

        phone = '31337'
        data = {'models': 'persons-contact',
                'fields': 'phone',
                'value':  phone,
               }
        Contact.objects.create(user=self.user, first_name='Eikichi', last_name='Onizuka', phone=phone)#would match if apps was allowed
        self.assertGET403(self.SEARCHNVIEW_URL, data=data)


class _BulkEditTestCase(ViewsTestCase):
    def get_cf_values(self, cf, entity):
        return cf.get_value_class().objects.get(custom_field=cf, entity=entity)

    @classmethod
    def setUpClass(cls):
        cls.populate('creme_config')


class BulkEditTestCase(_BulkEditTestCase):
    GET_WIDGET_URL = '/creme_core/entity/get_widget/%s'

    @classmethod
    def setUpClass(cls):
        _BulkEditTestCase.setUpClass()
        cls.contact_ct = ContentType.objects.get_for_model(Contact)

    def _build_url(self, *contact_ids):
        return '/creme_core/entity/bulk_update/%s/?persist=ids&ids=%s' % ( #TODO: odd url &ids=&ids=12&ids=16
                    self.contact_ct.id,
                    "&ids=".join(str(id_) for id_ in contact_ids),
                )

    def create_2_contacts_n_url(self, mario_kwargs=None, luigi_kwargs=None):
        create_contact = partial(Contact.objects.create, user=self.user)
        mario = create_contact(first_name="Mario", last_name="Bros", **(mario_kwargs or {}))
        luigi = create_contact(first_name="Luigi", last_name="Bros", **(luigi_kwargs or {}))

        return mario, luigi, self._build_url(mario.id, luigi.id)

    def test_regular_field01(self):
        self.login()

        self.assertGET404('/creme_core/entity/bulk_update/%s/' % self.contact_ct.id)
        self.assertGET404(self._build_url(0))
        self.assertGET404(self._build_url(*range(10)))

        mario = Contact.objects.create(user=self.user, first_name="Mario", last_name="Bros")
        self.assertGET200(self._build_url(mario.id))

    def test_regular_field02(self):
        self.login()

        create_pos = Position.objects.create
        unemployed   = create_pos(title='unemployed')
        plumber      = create_pos(title='plumber')
        ghost_hunter = create_pos(title='ghost hunter')

        mario, luigi, url = self.create_2_contacts_n_url(mario_kwargs={'position': plumber},
                                                         luigi_kwargs={'position': ghost_hunter}
                                                        )
        self.assertGET200(url)

        response = self.client.post(url, data={'field_name':   'position',
                                               'field_value':  unemployed.id,
                                               'entities_lbl': 'whatever',
                                              }
                                   )
        self.assertNoFormError(response)
        self.assertEqual(unemployed, self.refresh(mario).position)
        self.assertEqual(unemployed, self.refresh(luigi).position)

    def test_regular_field03(self):
        self.login()
        user =  self.user

        plumbing = Sector.objects.create(title='Plumbing')
        games    = Sector.objects.create(title='Games')

        create_contact = partial(Contact.objects.create, user=user, sector=games)
        mario = create_contact(user=user, first_name='Mario', last_name='Bros')
        luigi = create_contact(user=user, first_name='Luigi', last_name='Bros')

        nintendo = Organisation.objects.create(user=user, name='Nintendo', sector=games)

        url = self._build_url(mario.id, luigi.id, nintendo.id)
        self.assertGET200(url)

        response = self.client.post(url, data={'field_name':   'sector',
                                               'field_value':  plumbing.id,
                                               'entities_lbl': 'whatever',
                                              }
                                   )
        self.assertNoFormError(response)
        self.assertEqual(plumbing, self.refresh(mario).sector)
        self.assertEqual(plumbing, self.refresh(luigi).sector)
        self.assertEqual(games,    self.refresh(nintendo).sector)

    def test_regular_field04(self):
        self.login()

        mario, luigi, url = self.create_2_contacts_n_url()
        response = self.client.post(url, data={'field_name':   'last_name',
                                               'field_value':  '',
                                               'entities_lbl': 'whatever',
                                              }
                                   )
        self.assertFormError(response, 'form', None, [_(u'This field is required.')])

    def test_regular_field05(self):
        self.login()

        fname = 'position'
        bulk_update_registry.register((Contact, [fname, ]))

        unemployed = Position.objects.create(title='unemployed')
        mario, luigi, url = self.create_2_contacts_n_url()
        response = self.client.post(url, data={'field_name':   fname,
                                               'field_value':  unemployed.id,
                                               'entities_lbl': 'whatever',
                                              }
                                   )
        self.assertFormError(response, 'form', 'field_name',
                            [_(u'Select a valid choice. %(value)s is not one of the available choices.') % {
                                        'value': fname,
                                    }
                            ]
                           )

    def test_regular_field06(self):
        self.login()

        mario, luigi, url = self.create_2_contacts_n_url(mario_kwargs={'description': "Luigi's brother"},
                                                         luigi_kwargs={'description': "Mario's brother"}
                                                        )
        response = self.client.post(url, data={'field_name':      'description',
                                               'field_value':     '',
                                               'entities_lbl':    'whatever',
                                               'bad_entities_lbl':'whatever',
                                              }
                                   )
        self.assertNoFormError(response)
        self.assertEqual('', self.refresh(mario).description)
        self.assertEqual('', self.refresh(luigi).description)

    def test_regular_field07(self):
        self.login(is_superuser=False, allowed_apps=('creme_core', 'persons'))

        mario_desc = u"Luigi's brother"
        create_bros = partial(Contact.objects.create, last_name='Bros')
        mario = create_bros(user=self.other_user, first_name='Mario', description=mario_desc)
        luigi = create_bros(user=self.user,       first_name='Luigi', description="Mario's brother")

        response = self.client.post(self._build_url(mario.id, luigi.id),
                                    data={'field_name':      'description',
                                          'field_value':     '',
                                          'entities_lbl':    'whatever',
                                          'bad_entities_lbl':'whatever',
                                         }
                                   )
        self.assertNoFormError(response)
        self.assertEqual(mario_desc, self.refresh(mario).description)
        self.assertEqual('',         self.refresh(luigi).description)

    def test_regular_field08(self):
        self.login()

        mario, luigi, url = self.create_2_contacts_n_url()
        response = self.client.post(url, data={'field_name':   'birthday',
                                               'field_value':  'bad date',
                                               'entities_lbl': 'whatever',
                                              }
                                   )
        self.assertFormError(response, 'form', None, [_(u'Enter a valid date.')])

        settings.DATE_INPUT_FORMATS += ("-%dT%mU%Y-",) #This weird format have few chances to be present in settings
        self.client.post(url, data={'field_name':   'birthday',
                                    'field_value':  '-31T01U2000-',
                                    'entities_lbl': 'whatever',
                                   }
                       )
        birthday = date(2000, 1, 31)
        self.assertEqual(birthday, self.refresh(mario).birthday)
        self.assertEqual(birthday, self.refresh(luigi).birthday)

    #TODO: uncomment this test when image is bulk-updatable once again
    #def test_regular_field09(self):
        #self.login(is_superuser=False, allowed_apps=('creme_core', 'persons', 'media_managers'))

        #create_bros = partial(Contact.objects.create, last_name='Bros')
        #mario = create_bros(user=self.other_user, first_name='Mario', description=u"Luigi's brother")
        #luigi = create_bros(user=self.user,       first_name='Luigi', description="Mario's brother")

        #tmpfile = NamedTemporaryFile()
        #tmpfile.width = tmpfile.height = 0
        #tmpfile._committed = True

        #create_img = partial(Image.objects.create, image=tmpfile)
        #unallowed = create_img(user=self.other_user, name='unallowed')
        #allowed   = create_img(user=self.user,       name='allowed')

        #url = self._build_url(mario.id, luigi.id)
        #response = self.client.post(url, data={'field_name':      'image',
                                               #'field_value':     unallowed.id,
                                               #'entities_lbl':    'whatever',
                                               #'bad_entities_lbl':'whatever',
                                              #}
                                   #)
        #self.assertFormError(response, 'form', None, [_(u"You can't view this value, so you can't set it.")])

        #self.client.post(url, data={'field_name':       'image',
                                    #'field_value':      allowed.id,
                                    #'entities_lbl':     'whatever',
                                    #'bad_entities_lbl': 'whatever',
                                   #}
                        #)
        #self.assertNotEqual(allowed, self.refresh(mario).image)
        #self.assertEqual(allowed,    self.refresh(luigi).image)

    def test_custom_field01(self):
        self.login()

        cf_int = CustomField.objects.create(name='int', content_type=self.contact_ct, field_type=CustomField.INT)
        mario, luigi, url = self.create_2_contacts_n_url()

        #Int
        response = self.client.post(url, data={'field_name': _CUSTOM_NAME % cf_int.id,
                                               'field_value': 10,
                                               'entities_lbl': 'whatever',
                                              }
                                   )
        self.assertNoFormError(response)
        self.assertEqual(10, self.get_cf_values(cf_int, self.refresh(mario)).value)
        self.assertEqual(10, self.get_cf_values(cf_int, self.refresh(luigi)).value)

        #Int empty
        response = self.client.post(url, data={'field_name': _CUSTOM_NAME % cf_int.id,
                                               'field_value': '',
                                               'entities_lbl': 'whatever',
                                              }
                                   )
        self.assertNoFormError(response)
        self.assertRaises(CustomFieldInteger.DoesNotExist, self.get_cf_values, cf_int, self.refresh(mario))
        self.assertRaises(CustomFieldInteger.DoesNotExist, self.get_cf_values, cf_int, self.refresh(luigi))

    def test_custom_field02(self):
        self.login()

        mario, luigi, url = self.create_2_contacts_n_url()
        cf_float = CustomField.objects.create(name='float', content_type=self.contact_ct, field_type=CustomField.FLOAT)

        #Float
        response = self.client.post(url, data={'field_name':   _CUSTOM_NAME % cf_float.id,
                                               'field_value':  '10.2',
                                               'entities_lbl': 'whatever',
                                              }
                                   )
        self.assertNoFormError(response)
        self.assertEqual(Decimal("10.2"), self.get_cf_values(cf_float, self.refresh(mario)).value)
        self.assertEqual(Decimal("10.2"), self.get_cf_values(cf_float, self.refresh(luigi)).value)

        #Float empty
        response = self.client.post(url, data={'field_name':   _CUSTOM_NAME % cf_float.id,
                                               'field_value':  '',
                                               'entities_lbl': 'whatever',
                                             }
                                   )
        self.assertNoFormError(response)
        self.assertRaises(CustomFieldFloat.DoesNotExist, self.get_cf_values, cf_float, self.refresh(mario))
        self.assertRaises(CustomFieldFloat.DoesNotExist, self.get_cf_values, cf_float, self.refresh(luigi))

    def test_custom_field03(self):
        self.login()

        mario, luigi, url = self.create_2_contacts_n_url()
        cf_bool = CustomField.objects.create(name='bool', content_type=self.contact_ct, field_type=CustomField.BOOL)

        #Bool
        response = self.client.post(url, data={'field_name': _CUSTOM_NAME % cf_bool.id,
                                               'field_value': True,
                                               'entities_lbl': 'whatever',
                                              }
                                   )
        self.assertNoFormError(response)
        self.assertEqual(True, self.get_cf_values(cf_bool, self.refresh(mario)).value)
        self.assertEqual(True, self.get_cf_values(cf_bool, self.refresh(luigi)).value)

        #Bool false
        response = self.client.post(url, data={'field_name': _CUSTOM_NAME % cf_bool.id,
                                               'field_value': False,
                                               'entities_lbl': 'whatever',
                                              }
                                   )
        self.assertNoFormError(response)
        self.assertEqual(False, self.get_cf_values(cf_bool, self.refresh(mario)).value)
        self.assertEqual(False, self.get_cf_values(cf_bool, self.refresh(luigi)).value)

        #Bool empty
        response = self.client.post(url, data={'field_name':   _CUSTOM_NAME % cf_bool.id,
                                               'field_value':  None,
                                               'entities_lbl': 'whatever',
                                              }
                                   )
        self.assertNoFormError(response)
        self.assertRaises(CustomFieldBoolean.DoesNotExist, self.get_cf_values, cf_bool, self.refresh(mario))
        self.assertRaises(CustomFieldBoolean.DoesNotExist, self.get_cf_values, cf_bool, self.refresh(luigi))

    def test_custom_field04(self):
        self.login()

        mario, luigi, url = self.create_2_contacts_n_url()
        cf_str  = CustomField.objects.create(name='str', content_type=self.contact_ct, field_type=CustomField.STR)

        #Str
        response = self.client.post(url, data={'field_name':   _CUSTOM_NAME % cf_str.id,
                                               'field_value':  'str',
                                               'entities_lbl': 'whatever',
                                              }
                                   )
        self.assertNoFormError(response)
        self.assertEqual('str', self.get_cf_values(cf_str, self.refresh(mario)).value)
        self.assertEqual('str', self.get_cf_values(cf_str, self.refresh(luigi)).value)

        #Str empty
        response = self.client.post(url, data={'field_name':   _CUSTOM_NAME % cf_str.id,
                                               'field_value':  '',
                                               'entities_lbl': 'whatever',
                                              }
                           )
        self.assertNoFormError(response)
        self.assertRaises(CustomFieldString.DoesNotExist, self.get_cf_values, cf_str, self.refresh(mario))
        self.assertRaises(CustomFieldString.DoesNotExist, self.get_cf_values, cf_str, self.refresh(luigi))

    def test_custom_field05(self):
        self.login()

        get_cf_values = self.get_cf_values
        mario, luigi, url = self.create_2_contacts_n_url()
        cf_date = CustomField.objects.create(name='date', content_type=self.contact_ct, field_type=CustomField.DATETIME)

        #Date
        settings.DATETIME_INPUT_FORMATS += ("-%dT%mU%Y-",) #This weird format have few chances to be present in settings
        response = self.client.post(url, data={'field_name':   _CUSTOM_NAME % cf_date.id,
                                               'field_value':  '-31T01U2000-',
                                               'entities_lbl': 'whatever',
                                             }
                                   )
        self.assertNoFormError(response)

        #dt = datetime(2000, 1, 31)
        dt = self.create_datetime(2000, 1, 31)
        self.assertEqual(dt, get_cf_values(cf_date, self.refresh(mario)).value)
        self.assertEqual(dt, get_cf_values(cf_date, self.refresh(luigi)).value)

        #Date
        response = self.client.post(url, data={'field_name':   _CUSTOM_NAME % cf_date.id,
                                               'field_value':  '',
                                               'entities_lbl': 'whatever',
                                              }
                                   )
        self.assertNoFormError(response)
        self.assertRaises(CustomFieldDateTime.DoesNotExist, get_cf_values, cf_date, self.refresh(mario))
        self.assertRaises(CustomFieldDateTime.DoesNotExist, get_cf_values, cf_date, self.refresh(luigi))

    def test_custom_field06(self):
        self.login()
        get_cf_values = self.get_cf_values
        mario, luigi, url = self.create_2_contacts_n_url()

        cf_enum = CustomField.objects.create(name='enum', content_type=self.contact_ct, field_type=CustomField.ENUM)
        enum1 = CustomFieldEnumValue.objects.create(custom_field= cf_enum, value=u"Enum1")
        CustomFieldEnumValue.objects.create(custom_field= cf_enum,         value=u"Enum2")

        #Enum
        response = self.client.post(url, data={'field_name':   _CUSTOM_NAME % cf_enum.id,
                                               'field_value':  enum1.id,
                                               'entities_lbl': 'whatever',
                                              }
                                   )
        self.assertNoFormError(response)
        self.assertEqual(enum1, get_cf_values(cf_enum, self.refresh(mario)).value)
        self.assertEqual(enum1, get_cf_values(cf_enum, self.refresh(luigi)).value)

        #Enum empty
        response = self.client.post(url, data={'field_name':   _CUSTOM_NAME % cf_enum.id,
                                               'field_value':  '',
                                               'entities_lbl': 'whatever',
                                              }
                           )
        self.assertNoFormError(response)
        self.assertRaises(CustomFieldEnum.DoesNotExist, get_cf_values, cf_enum, self.refresh(mario))
        self.assertRaises(CustomFieldEnum.DoesNotExist, get_cf_values, cf_enum, self.refresh(luigi))

    def test_custom_field07(self):
        self.login()
        get_cf_values = self.get_cf_values

        cf_multi_enum = CustomField.objects.create(name='multi_enum', content_type=self.contact_ct,
                                                   field_type=CustomField.MULTI_ENUM
                                                  )

        create_cfvalue = partial(CustomFieldEnumValue.objects.create, custom_field=cf_multi_enum)
        m_enum1 = create_cfvalue(value='MEnum1')
        create_cfvalue(value='MEnum2')
        m_enum3 = create_cfvalue(value='MEnum3')

        mario, luigi, url = self.create_2_contacts_n_url()
        self.assertGET200(url)

        #Multi-Enum
        self.assertNoFormError(self.client.post(url, data={'field_name':   _CUSTOM_NAME % cf_multi_enum.id,
                                                           'field_value':  [m_enum1.id, m_enum3.id],
                                                           'entities_lbl': 'whatever',
                                                          }
                                               )
                              )
        mario = self.refresh(mario)
        luigi = self.refresh(luigi)

        values_set = set(get_cf_values(cf_multi_enum, mario).value.values_list('pk', flat=True))
        self.assertIn(m_enum1.id, values_set)
        self.assertIn(m_enum3.id, values_set)

        values_set = set(get_cf_values(cf_multi_enum, luigi).value.values_list('pk', flat=True))
        self.assertIn(m_enum1.id, values_set)
        self.assertIn(m_enum3.id, values_set)

        #Multi-Enum empty
        self.assertNoFormError(self.client.post(url, data={'field_name':   _CUSTOM_NAME % cf_multi_enum.id,
                                                           'field_value':  [],
                                                           'entities_lbl': 'whatever',
                                                          }
                                               )
                              )
        self.assertRaises(CustomFieldMultiEnum.DoesNotExist, get_cf_values, cf_multi_enum, self.refresh(mario))
        self.assertRaises(CustomFieldMultiEnum.DoesNotExist, get_cf_values, cf_multi_enum, self.refresh(luigi))

    def test_get_widget01(self):
        "Regular field"
        self.login()

        url = self.GET_WIDGET_URL
        response = self.assertPOST200(url % self.contact_ct.id,
                                      data={'field_name':       'first_name',
                                            'field_value_name': 'field_value',
                                           }
                                     )
        self.assertEqual('text/javascript', response['Content-Type'])
        #self.assertTrue(simplejson.loads(response.content)['rendered'])
        self.assertEqual('<input id="id_field_value" type="text" name="field_value" maxlength="100" />',
                         simplejson.loads(response.content)['rendered']
                        )

        response = self.assertPOST404(url % 0)
        self.assertEqual('text/javascript', response['Content-Type'])

        self.assertPOST404(url % 'notint')

        #TODO: test unknown field

    def test_get_widget02(self):
        "Custom field"
        self.login()

        cf_int = CustomField.objects.create(name='int', content_type=self.contact_ct, field_type=CustomField.INT)
        Contact.objects.create(user=self.user, first_name="Mario", last_name="Bros")

        response = self.assertPOST200(self.GET_WIDGET_URL % self.contact_ct.id,
                                      data={'field_name':       _CUSTOM_NAME % cf_int.id, #'first_name',
                                            'field_value_name': 'field_value', #??
                                           }
                                     )
        self.assertEqual('text/javascript', response['Content-Type'])
        self.assertEqual('<input type="text" name="field_value" id="id_field_value" />',
                         simplejson.loads(response.content)['rendered']
                        )


class InnerEditTestCase(_BulkEditTestCase):
    url = '/creme_core/entity/edit/%s/%s/field/%s'

    def create_contact(self):
        return Contact.objects.create(user=self.user, first_name="Mario", last_name="Bros")

    def create_orga(self):
        return Organisation.objects.create(user=self.user, name="Organisation")

    def test_regular_field_01(self):
        self.login()

        mario = self.create_contact()
        url = self.url % (mario.entity_type_id, mario.id, 'first_name')
        self.assertGET200(url)

        first_name = 'Luigi'
        response = self.client.post(url, data={'entities_lbl': [unicode(mario)],
                                               'field_value':  first_name,
                                              }
                                   )
        self.assertNoFormError(response)
        self.assertEqual(first_name, self.refresh(mario).first_name)

    def test_regular_field_02(self):
        self.login()

        mario = self.create_contact()
        response = self.client.post(self.url % (mario.entity_type_id, mario.id, 'birthday'),
                                    data={'entities_lbl': [unicode(mario)],
                                          'field_value':  'whatever',
                                         }
                                   )
        self.assertFormError(response, 'form', '', [_(u'Enter a valid date.')])

    def test_regular_field_03(self):
        "No permissons"
        self.login(is_superuser=False, creatable_models=[Contact])
        self._set_all_creds_except_one(EntityCredentials.CHANGE)

        mario = self.create_contact()
        self.assertFalse(self.user.has_perm_to_change(mario))

        self.assertGET403(self.url % (mario.entity_type_id, mario.id, 'first_name'))

    def test_regular_field_04(self):
        "Not editable"
        self.login()

        mario = self.create_contact()
        self.assertFalse(mario._meta.get_field('is_user').editable)

        url = self.url % (mario.entity_type_id, mario.id, 'is_user')
        self.assertGET404(url)
        self.assertPOST404(url, data={'entities_lbl': [unicode(mario)],
                                      'field_value':  self.other_user.id,
                                     }
                          )

    def test_custom_field(self):
        self.login()
        mario = self.create_contact()
        cfield = CustomField.objects.create(name='custom 1', content_type=mario.entity_type, field_type=CustomField.STR)
        url = self.url % (mario.entity_type_id, mario.id, cfield.id)
        self.assertGET200(url)

        value = 'hihi'
        response = self.client.post(url, data={'entities_lbl': [unicode(mario)],
                                               'field_value':  value,
                                              }
                                   )
        self.assertNoFormError(response)
        self.assertEqual(value, self.get_cf_values(cfield, self.refresh(mario)).value)

    def test_related_field(self):
        self.login()
        orga = self.create_orga()
        address = Address.objects.create(owner=orga, name='adress 1')
        ct_address = ContentType.objects.get_for_model(Address)

        url = self.url % (ct_address.pk, address.pk, 'city')
        self.assertGET200(url)

        city = 'Marseille'
        response = self.client.post(url, data={'entities_lbl': [unicode(address)],
                                               'field_value':  city,
                                              }
                                   )
        self.assertNoFormError(response)
        self.assertEqual(city, self.refresh(address).city)

