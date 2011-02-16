# -*- coding: utf-8 -*-

from django.test import TestCase
from django.http import Http404
from django.core.serializers.json import simplejson
from django.utils.translation import ugettext as _
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType

from creme_core.models import *
from creme_core.models.header_filter import HFI_FIELD
from creme_core.management.commands.creme_populate import Command as PopulateCommand

from persons.models import Contact, Organisation #TODO: find a way to create model that inherit CremeEntity in the unit tests ??


class ViewsTestCase(TestCase):
    def login(self, is_superuser=True):
        password = 'test'

        superuser = User.objects.create(username='Kirika')
        superuser.set_password(password)
        superuser.is_superuser = True
        superuser.save()

        role = UserRole.objects.create(name='Basic')
        role.allowed_apps = ['creme_core']
        role.save()
        SetCredentials.objects.create(role=role,
                                      value=SetCredentials.CRED_VIEW   | \
                                            SetCredentials.CRED_CHANGE | \
                                            SetCredentials.CRED_DELETE | \
                                            SetCredentials.CRED_LINK   | \
                                            SetCredentials.CRED_UNLINK,
                                      set_type=SetCredentials.ESET_OWN)
        basic_user = User.objects.create(username='Mireille', role=role)
        basic_user.set_password(password)
        basic_user.save()

        self.user, self.other_user = (superuser, basic_user) if is_superuser else \
                                     (basic_user, superuser)

        logged = self.client.login(username=self.user.username, password=password)
        self.assert_(logged, 'Not logged in')

    def assertNoFormError(self, response): #TODO: move in a CremeTestCase ??? (copied from creme_config)
        try:
            errors = response.context['form'].errors
        except Exception, e:
            pass
        else:
            if errors:
                self.fail(errors)

    def test_home(self): #TODO: improve test
        self.login()
        self.assertEqual(200, self.client.get('/').status_code)

    def test_clean(self):
        self.login()

        try:
            response = self.client.get('/creme_core/clean/', follow=True)
        except Exception, e:
            self.fail(str(e))

        self.assertEqual(200, response.status_code)
        self.assertEqual(2,   len(response.redirect_chain))

        last = response.redirect_chain[-1]
        self.assert_(last[0].endswith('/creme_login/'))
        self.assertEqual(302, last[1])

    def test_get_fields(self):
        self.login()

        ct_id = ContentType.objects.get_for_model(CremeEntity).id
        response = self.client.post('/creme_core/get_fields', data={'ct_id': ct_id})
        self.assertEqual(200,               response.status_code)
        self.assertEqual('text/javascript', response['Content-Type'])

        content = simplejson.loads(response.content)
        self.assertEqual(7, len(content))
        self.assertEqual(content[0],    ["created",          "Creme entity - " + _('Creation date')])
        self.assertEqual(content[1],    ["modified",         "Creme entity - " + _("Last modification")])
        self.assertEqual(content[2],    ["user__username",   _("User") + " - " + _("Username")])
        self.assertEqual(content[3],    ["user__first_name", _("User") + " - " + _("First name")])
        self.assertEqual(content[4],    ["user__last_name",  _("User") + " - " + _("Last name")])
        self.assertEqual(content[5][0], "user__email")
        self.assertEqual(content[6][0], "user__is_team")

        response = self.client.post('/creme_core/get_fields', data={'ct_id': 0})
        self.assertEqual(404,               response.status_code)
        self.assertEqual('text/javascript', response['Content-Type'])

        response = self.client.post('/creme_core/get_fields', data={'ct_id': 'notint'})
        self.assertEqual(400,               response.status_code)
        self.assertEqual('text/javascript', response['Content-Type'])

        response = self.client.post('/creme_core/get_fields', data={'ct_id': ct_id, 'deep': 'notint'})
        self.assertEqual(400,               response.status_code)
        self.assertEqual('text/javascript', response['Content-Type'])

    def test_get_function_fields(self):
        self.login()

        ct_id = ContentType.objects.get_for_model(CremeEntity).id
        response = self.client.post('/creme_core/get_function_fields', data={'ct_id': ct_id})
        self.assertEqual(200,               response.status_code)
        self.assertEqual('text/javascript', response['Content-Type'])

        content = simplejson.loads(response.content)
        self.assertEqual(content, [['get_pretty_properties', _('Properties')]])

        response = self.client.post('/creme_core/get_function_fields', data={'ct_id': 0})
        self.assertEqual(404,               response.status_code)
        self.assertEqual('text/javascript', response['Content-Type'])

        response = self.client.post('/creme_core/get_function_fields', data={'ct_id': 'notint'})
        self.assertEqual(400,               response.status_code)
        self.assertEqual('text/javascript', response['Content-Type'])

    def test_get_custom_fields(self):
        self.login()

        ct = ContentType.objects.get_for_model(CremeEntity)
        response = self.client.post('/creme_core/get_custom_fields', data={'ct_id': ct.id})
        self.assertEqual(200,               response.status_code)
        self.assertEqual('text/javascript', response['Content-Type'])
        self.assertEqual([], simplejson.loads(response.content))

        CustomField.objects.create(name='cf01', content_type=ct, field_type=CustomField.INT)
        CustomField.objects.create(name='cf02', content_type=ct, field_type=CustomField.FLOAT)

        response = self.client.post('/creme_core/get_custom_fields', data={'ct_id': ct.id})
        self.assertEqual([['cf01', 'cf01'], ['cf02', 'cf02']], simplejson.loads(response.content))

        response = self.client.post('/creme_core/get_custom_fields', data={'ct_id': 0})
        self.assertEqual(404,               response.status_code)
        self.assertEqual('text/javascript', response['Content-Type'])

        response = self.client.post('/creme_core/get_custom_fields', data={'ct_id': 'notint'})
        self.assertEqual(400,               response.status_code)
        self.assertEqual('text/javascript', response['Content-Type'])

    def test_get_creme_entity_as_json01(self):
        self.login()

        try:
            entity = CremeEntity.objects.create(user=self.user)
        except Exception, e:
            self.fail(str(e))

        response = self.client.post('/creme_core/entity/json', data={'pk': entity.id})
        self.assertEqual(200,               response.status_code)
        self.assertEqual('text/javascript', response['Content-Type'])

        json_data = simplejson.loads(response.content)
        #[{'pk': 1,
        #  'model': 'creme_core.cremeentity',
        #  'fields': {'is_actived': False,
        #             'is_deleted': False,
        #             'created': '2010-11-09 14:34:04',
        #             'header_filter_search_field': '',
        #             'entity_type': 100,
        #             'modified': '2010-11-09 14:34:04',
        #             'user': 1
        #            }
        #}]
        try:
            dic = json_data[0]
            pk     = dic['pk']
            model  = dic['model']
            fields = dic['fields']
            user = fields['user']
        except Exception, e:
            self.fail(str(e))

        self.assertEqual(entity.id, pk)
        self.assertEqual('creme_core.cremeentity', model)
        self.assertEqual(self.user.id, user)

    def test_get_creme_entity_as_json02(self):
        self.login()

        try:
            entity = CremeEntity.objects.create(user=self.user)
        except Exception, e:
            self.fail(str(e))

        response = self.client.post('/creme_core/entity/json', data={'pk': entity.id, 'fields': ['user', 'entity_type']})
        self.assertEqual(200, response.status_code)

        json_data = simplejson.loads(response.content)
        #[{'pk': 1,
        #  'model': 'creme_core.cremeentity',
        #  'fields': {'user': 1, 'entity_type': 100}}
        #]
        try:
            fields = json_data[0]['fields']
            user = fields['user']
            entity_type = fields['entity_type']
        except Exception, e:
            self.fail(str(e))

            self.assertEqual(self.user.id, user)
            self.assertEqual(ContentType.objects.get_for_model(CremeEntity).id, entity_type)

    def test_get_creme_entity_repr(self):
        self.login()

        try:
            entity = CremeEntity.objects.create(user=self.user)
        except Exception, e:
            self.fail(str(e))

        response = self.client.get('/creme_core/entity/get_repr/%s' % entity.id)
        self.assertEqual(200,               response.status_code)
        self.assertEqual('text/javascript', response['Content-Type'])
        self.assertEqual('Creme entity: %s' % entity.id, response.content)

    def test_delete_entity01(self):
        self.login()

        entity = Organisation.objects.create(user=self.user, name='Nerv') #to get a get_lv_absolute_url() method

        response = self.client.post('/creme_core/entity/delete/%s' % entity.id)
        self.assertEqual(302, response.status_code)
        self.assertEqual(0,   Organisation.objects.filter(pk=entity.id).count())

    def test_delete_entity02(self):
        self.login(is_superuser=False)

        entity = Organisation.objects.create(user=self.other_user, name='Nerv')

        response = self.client.post('/creme_core/entity/delete/%s' % entity.id)
        self.assertEqual(403, response.status_code)
        self.assertEqual(1,   Organisation.objects.filter(pk=entity.id).count())

    def test_delete_entity03(self):
        self.login()

        entity01 = Organisation.objects.create(user=self.other_user, name='Nerv')
        entity02 = Organisation.objects.create(user=self.other_user, name='Seele')

        rtype, srtype = RelationType.create(('test-subject_linked', 'is linked to'),
                                            ('test-object_linked',  'is linked to')
                                           )
        Relation.objects.create(user=self.user, type=rtype, subject_entity=entity01, object_entity=entity02)

        response = self.client.post('/creme_core/entity/delete/%s' % entity01.id)
        #self.assertEqual(400, response.status_code)
        self.assertEqual(2,   Organisation.objects.filter(pk__in=[entity01.id, entity02.id]).count())

    def test_delete_entities01(self):
        self.login()

        entity01 = CremeEntity.objects.create(user=self.user)
        entity02 = CremeEntity.objects.create(user=self.user)
        entity03 = CremeEntity.objects.create(user=self.user)

        response = self.client.post('/creme_core/delete_js',
                                    data={'ids': '%s,%s,' % (entity01.id, entity02.id)}
                                   )
        self.assertEqual(200, response.status_code)
        self.assertEqual(0,   CremeEntity.objects.filter(pk__in=[entity01.id, entity02.id]).count())
        self.assertEqual(1,   CremeEntity.objects.filter(pk=entity03.id).count())

    def test_delete_entities02(self):
        self.login()

        entity01 = CremeEntity.objects.create(user=self.user)
        entity02 = CremeEntity.objects.create(user=self.user)

        response = self.client.post('/creme_core/delete_js',
                                    data={'ids': '%s,%s,' % (entity01.id, entity02.id + 1)}
                                   )
        self.assertEqual(404, response.status_code)
        self.assertEqual(0,   CremeEntity.objects.filter(pk=entity01.id).count())
        self.assertEqual(1,   CremeEntity.objects.filter(pk=entity02.id).count())

    def test_delete_entities03(self):
        self.login(is_superuser=False)

        forbidden = CremeEntity.objects.create(user=self.other_user)
        allowed   = CremeEntity.objects.create(user=self.user)
        response = self.client.post('/creme_core/delete_js',
                                    data={'ids': '%s,%s,' % (forbidden.id, allowed.id)}
                                   )
        self.assertEqual(403, response.status_code)
        self.assertEqual(0,   CremeEntity.objects.filter(pk=allowed.id).count())
        self.assertEqual(1,   CremeEntity.objects.filter(pk=forbidden.id).count())

    def test_delete_entities04(self):
        self.login()

        entity01 = CremeEntity.objects.create(user=self.user)
        entity02 = CremeEntity.objects.create(user=self.user)
        entity03 = CremeEntity.objects.create(user=self.user) #not linked => can be deleted

        rtype, srtype = RelationType.create(('test-subject_linked', 'is linked to'),
                                            ('test-object_linked',  'is linked to')
                                           )
        Relation.objects.create(user=self.user, type=rtype, subject_entity=entity01, object_entity=entity02)

        response = self.client.post('/creme_core/delete_js',
                                    data={'ids': '%s,%s,%s,' % (entity01.id, entity02.id, entity03.id)}
                                   )
        self.assertEqual(400, response.status_code)
        self.assertEqual(2,   CremeEntity.objects.filter(pk__in=[entity01.id, entity02.id]).count())
        self.assertEqual(0,   CremeEntity.objects.filter(pk=entity03.id).count())

    ########################### Properties #####################################

    def test_add_property(self):
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

    def test_delete_property(self):
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
            property = entity.properties.get(type=ptype)
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

    ############################################################################

    def _aux_test_add_relations(self, is_superuser=True):
        self.login(is_superuser)

        create_entity = CremeEntity.objects.create
        self.subject01 = create_entity(user=self.user)
        self.subject02 = create_entity(user=self.user)
        self.object01  = create_entity(user=self.user)
        self.object02  = create_entity(user=self.user)

        self.ct_id = ContentType.objects.get_for_model(CremeEntity).id

        self.rtype01, srtype01 = RelationType.create(('test-subject_foobar1', 'is loving'),
                                                     ('test-object_foobar1',  'is loved by')
                                                    )
        self.rtype02, srtype02 = RelationType.create(('test-subject_foobar2', 'is hating'),
                                                     ('test-object_foobar2',  'is hated by')
                                                    )

    def _set_all_creds_except_one(self, excluded):
        value = SetCredentials.CRED_NONE

        for cred in (SetCredentials.CRED_VIEW, SetCredentials.CRED_CHANGE,
                     SetCredentials.CRED_DELETE, SetCredentials.CRED_LINK,
                     SetCredentials.CRED_UNLINK):
            if cred != excluded:
                value |= cred

        SetCredentials.objects.create(role=self.user.role,
                                      value=value,
                                      set_type=SetCredentials.ESET_ALL)

    def assertEntiTyHasRelation(self, subject_entity, rtype, object_entity):
        try:
            relation = subject_entity.relations.get(type=rtype)
        except Exception, e:
            self.fail(str(e))
        else:
            self.assertEqual(object_entity.id, relation.object_entity_id)

    def test_add_relations01(self):
        self._aux_test_add_relations()
        self.assertEqual(0, self.subject01.relations.count())

        response = self.client.get('/creme_core/relation/add/%s' % self.subject01.id)
        self.assertEqual(200, response.status_code)

        response = self.client.post('/creme_core/relation/add/%s' % self.subject01.id,
                                    data={
                                            'relations': '(%s,%s,%s);(%s,%s,%s);' % (
                                                                self.rtype01.id, self.ct_id, self.object01.id,
                                                                self.rtype02.id, self.ct_id, self.object02.id,
                                                            ),
                                         }
                                   )
        self.assertNoFormError(response)
        self.assertEqual(2, self.subject01.relations.count())

        self.assertEntiTyHasRelation(self.subject01, self.rtype01, self.object01)
        self.assertEntiTyHasRelation(self.subject01, self.rtype02, self.object02)

    def test_add_relations02(self):
        self.login(is_superuser=False)
        subject = CremeEntity.objects.create(user=self.other_user)
        response = self.client.get('/creme_core/relation/add/%s' % subject.id)
        self.assertEqual(403, response.status_code)

    def test_add_relations03(self):
        self._aux_test_add_relations(is_superuser=False)
        self._set_all_creds_except_one(excluded=SetCredentials.CRED_LINK)

        unlinkable = CremeEntity.objects.create(user=self.other_user)
        self.assert_(unlinkable.can_view(self.user))
        self.failIf(unlinkable.can_link(self.user))

        response = self.client.post('/creme_core/relation/add/%s' % self.subject01.id,
                                    data={
                                            'relations': '(%s,%s,%s);(%s,%s,%s);' % (
                                                                self.rtype01.id, self.ct_id, self.object01.id,
                                                                self.rtype02.id, self.ct_id, unlinkable.id,
                                                            ),
                                         }
                                   )
        try:
            form = response.context['form']
        except Exception, e:
            self.fail('No form in context ? (%s)', str(e))

        if not form.errors:
            self.fail('Not the excepted error in form.')

        self.assertEqual(1, len(form.errors.get('__all__', [])))
        self.assertEqual(0, self.subject01.relations.count())

    def test_add_relations_bulk01(self):
        self._aux_test_add_relations()

        #this relation should not be recreated by the view
        Relation.objects.create(user=self.user,
                                subject_entity=self.subject02,
                                type=self.rtype02,
                                object_entity=self.object02
                               )

        url = '/creme_core/relation/add_to_entities/%s/%s,%s,' % (self.ct_id, self.subject01.id, self.subject02.id)
        self.assertEqual(200, self.client.get(url).status_code)

        response = self.client.post(url, data={
                                                'entities_lbl': 'wtf',
                                                'relations': '(%s,%s,%s);(%s,%s,%s);' % (
                                                                self.rtype01.id, self.ct_id, self.object01.id,
                                                                self.rtype02.id, self.ct_id, self.object02.id,
                                                               ),
                                              })
        self.assertNoFormError(response)
        self.assertEqual(200, response.status_code)

        self.assertEqual(2, self.subject01.relations.count())
        self.assertEntiTyHasRelation(self.subject01, self.rtype01, self.object01)
        self.assertEntiTyHasRelation(self.subject01, self.rtype02, self.object02)

        self.assertEqual(2, self.subject02.relations.count()) #and not 3
        self.assertEntiTyHasRelation(self.subject02, self.rtype01, self.object01)
        self.assertEntiTyHasRelation(self.subject02, self.rtype02, self.object02)

    def test_add_relations_bulk02(self):
        self._aux_test_add_relations(is_superuser=False)

        unviewable = CremeEntity.objects.create(user=self.other_user)
        self.failIf(unviewable.can_view(self.user))

        url = '/creme_core/relation/add_to_entities/%s/%s,%s,' % (self.ct_id, self.subject01.id, unviewable.id)
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
                                                'relations':        '(%s,%s,%s);(%s,%s,%s);' % (
                                                                        self.rtype01.id, self.ct_id, self.object01.id,
                                                                        self.rtype02.id, self.ct_id, self.object02.id,
                                                                       ),
                                              })
        self.assertNoFormError(response)
        self.assertEqual(200, response.status_code)
        self.assertEqual(2,   self.subject01.relations.count())
        self.assertEqual(0,   unviewable.relations.count())

    def test_add_relations_bulk03(self):
        self._aux_test_add_relations(is_superuser=False)

        self._set_all_creds_except_one(excluded=SetCredentials.CRED_LINK)
        unlinkable = CremeEntity.objects.create(user=self.other_user)
        self.assert_(unlinkable.can_view(self.user))
        self.failIf(unlinkable.can_link(self.user))

        response = self.client.get('/creme_core/relation/add_to_entities/%s/%s,%s,' % (self.ct_id, self.subject01.id, unlinkable.id))
        self.assertEqual(200, response.status_code)

        try:
            label = response.context['form'].fields['bad_entities_lbl']
        except Exception, e:
            self.fail(str(e))

        self.assertEqual(unicode(unlinkable), label.initial)

    def test_add_relations_bulk04(self):
        self._aux_test_add_relations(is_superuser=False)

        url = '/creme_core/relation/add_to_entities/%s/%s,' % (self.ct_id, self.subject01.id)
        self.assertEqual(200, self.client.get(url).status_code)

        self._set_all_creds_except_one(excluded=SetCredentials.CRED_LINK)
        unlinkable = CremeEntity.objects.create(user=self.other_user)

        response = self.client.post(url, data={
                                                'entities_lbl': 'wtf',
                                                'relations':    '(%s,%s,%s);' % (self.rtype01.id, self.ct_id, unlinkable.id),
                                              })
        self.assertEqual(200, response.status_code)

        try:
            form = response.context['form']
        except Exception, e:
            self.fail('No form in context ? (%s)', str(e))

        if not form.errors:
            self.fail('Not the excepted error in form.')

        self.assertEqual(1, len(form.errors.get('__all__', [])))

    def _aux_relation_objects_to_link_selection(self):
        PopulateCommand().handle(application=['creme_core', 'persons'])

        self.login()

        self.assertEqual(1, Contact.objects.count())
        self.contact01 = Contact.objects.all()[0] #NB: Fulbert Creme

        self.subject   = CremeEntity.objects.create(user=self.user)
        self.contact02 = Contact.objects.create(user=self.user, first_name='Laharl', last_name='Overlord')
        self.contact03 = Contact.objects.create(user=self.user, first_name='Etna',   last_name='Devil')
        self.orga01    = Organisation.objects.create(user=self.user, name='Earth Defense Force')

        self.ct_contact = ContentType.objects.get_for_model(Contact)

        self.rtype, sym_rtype = RelationType.create(('test-subject_foobar', 'is loving',   [Contact]),
                                                    ('test-object_foobar',  'is loved by', [Contact])
                                                   )

    def test_relation_objects_to_link_selection01(self):
        self._aux_relation_objects_to_link_selection()

        response = self.client.get('/creme_core/relation/objects2link/rtype/%s/entity/%s/%s' % \
                                        (self.rtype.id, self.subject.id, self.ct_contact.id)
                                  )
        self.assertEqual(200, response.status_code)

        try:
            entities = response.context['entities']
        except Exception, e:
            self.fail('%s : %s' % (e.__class__.__name__, str(e)))

        contacts = entities.object_list
        self.assertEqual(3, len(contacts))
        self.assert_(all(isinstance(c, Contact) for c in contacts))
        self.assertEqual(set([self.contact01.id, self.contact02.id, self.contact03.id]),
                         set(c.id for c in contacts)
                        )

    def test_relation_objects_to_link_selection02(self):
        self._aux_relation_objects_to_link_selection()

        #contact03 will not be proposed by the listview
        Relation.objects.create(user=self.user, type=self.rtype, subject_entity=self.subject, object_entity=self.contact03)

        response = self.client.get('/creme_core/relation/objects2link/rtype/%s/entity/%s/%s' % \
                                        (self.rtype.id, self.subject.id, self.ct_contact.id)
                                  )
        self.assertEqual(200, response.status_code)

        contacts = response.context['entities'].object_list
        self.assertEqual(2, len(contacts))
        self.assertEqual(set([self.contact01.id, self.contact02.id]), set(c.id for c in contacts))

    def test_relation_objects_to_link_selection03(self):
        self._aux_relation_objects_to_link_selection()

        ptype01 = CremePropertyType.create(str_pk='test-prop_foobar01', text='Is lovable')
        ptype02 = CremePropertyType.create(str_pk='test-prop_foobar02', text='Is a girl')

        contact04 = Contact.objects.create(user=self.user, first_name='Flonne', last_name='Angel')

        #contact02 will not be proposed by the listview
        create_property = CremeProperty.objects.create
        create_property(type=ptype01, creme_entity=self.contact01)
        create_property(type=ptype02, creme_entity=self.contact03)
        create_property(type=ptype01, creme_entity=contact04)
        create_property(type=ptype02, creme_entity=contact04)

        rtype, sym_rtype = RelationType.create(('test-subject_loving', 'is loving',   [Contact]),
                                               ('test-object_loving',  'is loved by', [Contact], [ptype01, ptype02])
                                              )

        response = self.client.get('/creme_core/relation/objects2link/rtype/%s/entity/%s/%s' % \
                                        (rtype.id, self.subject.id, self.ct_contact.id)
                                  )
        self.assertEqual(200, response.status_code)

        contacts = response.context['entities'].object_list
        self.assertEqual(3, len(contacts))
        self.assertEqual(set([self.contact01.id, self.contact03.id, contact04.id]), set(c.id for c in contacts))

    def test_relation_objects_to_link_selection04(self):
        self.login()

        subject = CremeEntity.objects.create(user=self.user)
        ct_id = ContentType.objects.get_for_model(Contact).id
        rtype, sym_rtype = RelationType.create(('test-subject_foobar', 'is loving',   [Contact]),
                                               ('test-object_foobar',  'is loved by', [Contact]),
                                               is_internal=True
                                              )

        response = self.client.get('/creme_core/relation/objects2link/rtype/%s/entity/%s/%s' % \
                                        (rtype.id, subject.id, ct_id)
                                  )
        self.assertEqual(404, response.status_code)

    def _aux_add_relations_with_same_type(self):
        self.subject  = CremeEntity.objects.create(user=self.user)
        self.object01 = CremeEntity.objects.create(user=self.user)
        self.object02 = CremeEntity.objects.create(user=self.user)
        self.rtype, sym_rtype = RelationType.create(('test-subject_foobar', 'is loving',),
                                                    ('test-object_foobar',  'is loved by',)
                                                   )

    def test_add_relations_with_same_type01(self): #no errors
        self.login()
        self._aux_add_relations_with_same_type()

        object_ids = [self.object01.id, self.object02.id]
        response = self.client.post('/creme_core/relation/add_from_predicate/save',
                                    data={
                                            'subject_id':   self.subject.id,
                                            'predicate_id': self.rtype.id,
                                            'entities':     object_ids,
                                         }
                                   )
        self.assertEqual(200, response.status_code)
        self.assertEqual(2,   Relation.objects.filter(type=self.rtype.id).count())

        relations = self.subject.relations.filter(type=self.rtype.id)
        self.assertEqual(2, len(relations))
        self.assertEqual(set(object_ids), set(r.object_entity_id for r in relations))

    def test_add_relations_with_same_type02(self): #an entity does not exist
        self.login()
        self._aux_add_relations_with_same_type()

        response = self.client.post('/creme_core/relation/add_from_predicate/save',
                                    data={
                                            'subject_id':   self.subject.id,
                                            'predicate_id': self.rtype.id,
                                            'entities':     [self.object01.id, self.object02.id, self.object02.id + 1],
                                         }
                                   )
        self.assertEqual(404, response.status_code)
        self.assertEqual(2,   Relation.objects.filter(type=self.rtype.id).count())

    def test_add_relations_with_same_type03(self): #errors
        self.login()
        self._aux_add_relations_with_same_type()
        post = self.client.post

        self.assertEqual(404, post('/creme_core/relation/add_from_predicate/save',
                                    data={
                                            'subject_id':   self.subject.id,
                                            'predicate_id': 'IDONOTEXIST',
                                            'entities':     [self.object01.id],
                                         }
                                  ).status_code
                        )
        self.assertEqual(404, post('/creme_core/relation/add_from_predicate/save',
                                    data={
                                            'subject_id':   1024,
                                            'predicate_id': self.rtype.id,
                                            'entities':     [self.object01.id],
                                         }
                                  ).status_code
                        )
        self.assertEqual(404, post('/creme_core/relation/add_from_predicate/save',
                                    data={
                                            'predicate_id': self.rtype.id,
                                            'entities':     [self.object01.id],
                                         }
                                  ).status_code
                        )
        self.assertEqual(404, post('/creme_core/relation/add_from_predicate/save',
                                    data={
                                            'subject_id': self.subject.id,
                                            'entities':   [self.object01.id],
                                         }
                                  ).status_code
                        )
        self.assertEqual(404, post('/creme_core/relation/add_from_predicate/save',
                                    data={
                                            'subject_id':   self.subject.id,
                                            'predicate_id': self.rtype.id,
                                         }
                                  ).status_code
                        )

    def test_add_relations_with_same_type04(self): #credentials errors
        self.login(is_superuser=False)
        self._set_all_creds_except_one(excluded=SetCredentials.CRED_LINK)

        forbidden = CremeEntity.objects.create(user=self.other_user)
        allowed01 = CremeEntity.objects.create(user=self.user)
        allowed02 = CremeEntity.objects.create(user=self.user)
        rtype, sym_rtype = RelationType.create(('test-subject_foobar', 'is loving',),
                                               ('test-object_foobar',  'is loved by',)
                                              )

        post = self.client.post

        self.failIf(forbidden.can_link(self.user))
        self.assert_(allowed01.can_link(self.user))

        self.assertEqual(403, post('/creme_core/relation/add_from_predicate/save',
                                    data={
                                            'subject_id':   forbidden.id,
                                            'predicate_id': rtype.id,
                                            'entities':     [allowed01.id, allowed02.id],
                                         }
                                  ).status_code
                        )
        self.assertEqual(0, Relation.objects.filter(type=rtype.id).count())

        self.assertEqual(403, post('/creme_core/relation/add_from_predicate/save',
                                    data={
                                            'subject_id':   allowed01.id,
                                            'predicate_id': rtype.id,
                                            'entities':     [forbidden.id, allowed02.id, 1024],
                                         }
                                  ).status_code
                        )
        relations = Relation.objects.filter(type=rtype.id)
        self.assertEqual(1, len(relations))

        relation = relations[0]
        self.assertEqual(allowed01.id, relation.subject_entity_id)
        self.assertEqual(allowed02.id, relation.object_entity_id)

    def test_add_relations_with_same_type05(self): #ct constraint errors
        self.login()

        orga01    = Organisation.objects.create(user=self.user, name='orga01')
        orga02    = Organisation.objects.create(user=self.user, name='orga02')
        contact01 = Contact.objects.create(user=self.user, first_name='John', last_name='Doe')
        contact02 = Contact.objects.create(user=self.user, first_name='Joe',  last_name='Gohn')

        rtype, sym_rtype = RelationType.create(('test-subject_foobar', 'manages',       [Contact]),
                                               ('test-object_foobar',  'is managed by', [Organisation])
                                              )

        post = self.client.post

        self.assertEqual(404, post('/creme_core/relation/add_from_predicate/save',
                                    data={
                                            'subject_id':   orga01.id,
                                            'predicate_id': rtype.id,
                                            'entities':     [orga02.id],
                                         }
                                  ).status_code
                        )
        self.assertEqual(0, Relation.objects.filter(type=rtype.id).count())

        self.assertEqual(404, post('/creme_core/relation/add_from_predicate/save',
                                    data={
                                            'subject_id':   contact01.id,
                                            'predicate_id': rtype.id,
                                            'entities':     [orga01.id, contact02.id],
                                         }
                                  ).status_code
                        )
        relations = Relation.objects.filter(type=rtype.id)
        self.assertEqual(1,         len(relations))
        self.assertEqual(orga01.id, relations[0].object_entity_id)

    def test_add_relations_with_same_type06(self): #property constraint errors
        self.login()

        subject_ptype = CremePropertyType.create(str_pk='test-prop_foobar01', text='Subject property')
        object_ptype  = CremePropertyType.create(str_pk='test-prop_foobar02', text='Contact property')

        bad_subject  = CremeEntity.objects.create(user=self.user)
        good_subject = CremeEntity.objects.create(user=self.user)
        bad_object   = CremeEntity.objects.create(user=self.user)
        good_object  = CremeEntity.objects.create(user=self.user)

        CremeProperty.objects.create(type=subject_ptype, creme_entity=good_subject)
        CremeProperty.objects.create(type=object_ptype, creme_entity=good_object)

        rtype, sym_rtype = RelationType.create(('test-subject_foobar', 'manages',       [], [subject_ptype]),
                                               ('test-object_foobar',  'is managed by', [], [object_ptype])
                                              )

        post = self.client.post

        self.assertEqual(404, post('/creme_core/relation/add_from_predicate/save',
                                    data={
                                            'subject_id':   bad_subject.id,
                                            'predicate_id': rtype.id,
                                            'entities':     [good_object.id],
                                         }
                                  ).status_code
                        )
        self.assertEqual(0, Relation.objects.filter(type=rtype.id).count())

        self.assertEqual(404, post('/creme_core/relation/add_from_predicate/save',
                                    data={
                                            'subject_id':   good_subject.id,
                                            'predicate_id': rtype.id,
                                            'entities':     [good_object.id, bad_object.id],
                                         }
                                  ).status_code
                        )
        relations = Relation.objects.filter(type=rtype.id)
        self.assertEqual(1,              len(relations))
        self.assertEqual(good_object.id, relations[0].object_entity_id)

    def test_add_relations_with_same_type07(self): #is_internal
        self.login()

        subject  = CremeEntity.objects.create(user=self.user)
        object01 = CremeEntity.objects.create(user=self.user)
        object02 = CremeEntity.objects.create(user=self.user)
        rtype, sym_rtype = RelationType.create(('test-subject_foobar', 'is loving',),
                                               ('test-object_foobar',  'is loved by',),
                                               is_internal=True
                                              )
        response = self.client.post('/creme_core/relation/add_from_predicate/save',
                                    data={
                                            'subject_id':   subject.id,
                                            'predicate_id': rtype.id,
                                            'entities':     [object01.id, object02.id],
                                         }
                                   )
        self.assertEqual(404, response.status_code)
        self.assertEqual(0,   Relation.objects.filter(type=rtype.id).count())

    def test_relation_delete01(self):
        self.login()

        subject_entity = CremeEntity.objects.create(user=self.user)
        object_entity  = CremeEntity.objects.create(user=self.user)

        rtype, sym_rtype = RelationType.create(('test-subject_foobar', 'is loving'), ('test-object_foobar',  'is loved by'))
        relation = Relation.objects.create(user=self.user, type=rtype, subject_entity=subject_entity, object_entity=object_entity)
        sym_relation = relation.symmetric_relation
        self.assert_(rtype.is_not_internal_or_die() is None)

        response = self.client.post('/creme_core/relation/delete', data={'id': relation.id})
        self.assertEqual(302, response.status_code)

        self.assertEqual(0, Relation.objects.filter(pk__in=[relation.pk, sym_relation.pk]).count())

    def test_relation_delete02(self):
        self.login(is_superuser=False)

        self._set_all_creds_except_one(excluded=SetCredentials.CRED_UNLINK)

        allowed   = CremeEntity.objects.create(user=self.user)
        forbidden = CremeEntity.objects.create(user=self.other_user)
        rtype, sym_rtype = RelationType.create(('test-subject_foobar', 'is loving'), ('test-object_foobar', 'is loved by'))

        relation = Relation.objects.create(user=self.user, type=rtype, subject_entity=allowed, object_entity=forbidden)
        self.assertEqual(403, self.client.post('/creme_core/relation/delete', data={'id': relation.id}).status_code)
        self.assertEqual(1,   Relation.objects.filter(pk=relation.pk).count())

        relation = Relation.objects.create(user=self.user, type=rtype, subject_entity=forbidden, object_entity=allowed)
        self.assertEqual(403, self.client.post('/creme_core/relation/delete', data={'id': relation.id}).status_code)
        self.assertEqual(1,   Relation.objects.filter(pk=relation.pk).count())

    def test_relation_delete03(self): #is internal
        self.login()

        subject_entity = CremeEntity.objects.create(user=self.user)
        object_entity  = CremeEntity.objects.create(user=self.user)

        rtype, sym_rtype = RelationType.create(('test-subject_foobar', 'is loving'), ('test-object_foobar',  'is loved by'), is_internal=True)
        self.assert_(rtype.is_internal)
        self.assert_(sym_rtype.is_internal)
        self.assertRaises(Http404, rtype.is_not_internal_or_die)

        relation = Relation.objects.create(user=self.user, type=rtype, subject_entity=subject_entity, object_entity=object_entity)
        self.assertEqual(404, self.client.post('/creme_core/relation/delete', data={'id': relation.id}).status_code)
        self.assertEqual(1, Relation.objects.filter(pk=relation.pk).count())

    def test_relation_delete_similar01(self):
        self.login()

        subject_entity01 = CremeEntity.objects.create(user=self.user)
        object_entity01  = CremeEntity.objects.create(user=self.user)

        subject_entity02 = CremeEntity.objects.create(user=self.user)
        object_entity02  = CremeEntity.objects.create(user=self.user)

        rtype01, useless = RelationType.create(('test-subject_love', 'is loving'), ('test-object_love', 'is loved by'))
        rtype02, useless = RelationType.create(('test-subject_son',  'is son of'), ('test-object_son',  'is parent of'))

        #will be deleted (normally)
        relation01 = Relation.objects.create(user=self.user, type=rtype01, subject_entity=subject_entity01, object_entity=object_entity01)
        relation02 = Relation.objects.create(user=self.user, type=rtype01, subject_entity=subject_entity01, object_entity=object_entity01)

        #won't be deleted (normally)
        relation03 = Relation.objects.create(user=self.user, type=rtype01, subject_entity=subject_entity01, object_entity=object_entity02) #different object
        relation04 = Relation.objects.create(user=self.user, type=rtype01, subject_entity=subject_entity02, object_entity=object_entity01) #different subject
        relation05 = Relation.objects.create(user=self.user, type=rtype02, subject_entity=subject_entity01, object_entity=object_entity01) #different type

        self.assertEqual(10, Relation.objects.count())

        response = self.client.post('/creme_core/relation/delete/similar',
                                    data={
                                            'subject_id': subject_entity01.id,
                                            'type':       rtype01.id,
                                            'object_id':  object_entity01.id,
                                         }
                                   )
        self.assertEqual(302, response.status_code)
        self.assertEqual(0,   Relation.objects.filter(pk__in=[relation01.pk, relation02.pk]).count())
        self.assertEqual(3,   Relation.objects.filter(pk__in=[relation03.pk, relation04.pk, relation05.pk]).count())

    def test_relation_delete_similar02(self):
        self.login(is_superuser=False)
        self._set_all_creds_except_one(excluded=SetCredentials.CRED_UNLINK)

        allowed   = CremeEntity.objects.create(user=self.user)
        forbidden = CremeEntity.objects.create(user=self.other_user)

        rtype, useless = RelationType.create(('test-subject_love', 'is loving'), ('test-object_love', 'is loved by'))
        relation01 = Relation.objects.create(user=self.user, type=rtype, subject_entity=allowed,   object_entity=forbidden)
        relation02 = Relation.objects.create(user=self.user, type=rtype, subject_entity=forbidden, object_entity=allowed)
        self.assertEqual(4, Relation.objects.count())

        response = self.client.post('/creme_core/relation/delete/similar',
                                    data={
                                            'subject_id': allowed.id,
                                            'type':       rtype.id,
                                            'object_id':  forbidden.id,
                                         }
                                   )
        self.assertEqual(403, response.status_code)
        self.assertEqual(4,   Relation.objects.count())

        response = self.client.post('/creme_core/relation/delete/similar',
                                    data={
                                            'subject_id': forbidden.id,
                                            'type':       rtype.id,
                                            'object_id':  allowed.id,
                                         }
                                   )
        self.assertEqual(403, response.status_code)
        self.assertEqual(4,   Relation.objects.count())

    def test_relation_delete_similar03(self): #is internal
        self.login()

        subject_entity = CremeEntity.objects.create(user=self.user)
        object_entity  = CremeEntity.objects.create(user=self.user)
        rtype, useless = RelationType.create(('test-subject_love', 'is loving'), ('test-object_love', 'is loved by'), is_internal=True)
        relation = Relation.objects.create(user=self.user, type=rtype, subject_entity=subject_entity, object_entity=object_entity)

        response = self.client.post('/creme_core/relation/delete/similar',
                                    data={
                                            'subject_id': subject_entity.id,
                                            'type':       rtype.id,
                                            'object_id':  object_entity.id,
                                         }
                                   )
        self.assertEqual(404, response.status_code)
        self.assertEqual(1,   Relation.objects.filter(pk=relation.pk).count())

    #TODO: test other relation views...

    def test_headerfilter_create(self): #TODO: test several HFI, other types of HFI
        self.login()

        ct = ContentType.objects.get_for_model(CremeEntity)
        self.assertEqual(0, HeaderFilter.objects.filter(entity_type=ct).count())

        uri = '/creme_core/header_filter/add/%s' % ct.id
        response = self.client.get(uri)
        self.assertEqual(200, response.status_code)

        try:
            form = response.context['form']
            fields_field = form.fields['fields']
        except KeyError, e:
            self.fail(str(e))

        for i, (fname, fvname) in enumerate(fields_field.choices):
            if fname == 'created': created_index = i; break
        else:
            self.fail('No "created" field')

        name = 'DefaultHeaderFilter'
        response = self.client.post(uri,
                                    data={
                                            'name':                            name,
                                            'fields_check_%s' % created_index: 'on',
                                            'fields_value_%s' % created_index: 'created',
                                            'fields_order_%s' % created_index: 1,
                                         }
                                   )
        self.assertNoFormError(response)
        self.assertEqual(302, response.status_code)

        hfilters = HeaderFilter.objects.filter(entity_type=ct)
        self.assertEqual(1, len(hfilters))

        hfilter = hfilters[0]
        self.assertEqual(name, hfilter.name)

        hfitems = hfilter.header_filter_items.all()
        self.assertEqual(1, len(hfitems))

        hfitem = hfitems[0]
        self.assertEqual('created',        hfitem.name)
        self.assertEqual(1,                hfitem.order)
        self.assertEqual(1,                hfitem.type)
        self.assertEqual('created__range', hfitem.filter_string)
        self.failIf(hfitem.is_hidden)

    def test_headerfilter_edit01(self): #not editable
        self.login()

        ct = ContentType.objects.get_for_model(CremeEntity)
        hf = HeaderFilter.objects.create(pk='tests-hf_entity', name='Entity view', entity_type_id=ct.id, is_custom=False)
        HeaderFilterItem.objects.create(pk='tests-hfi_entity_created', order=1, name='created',
                                        title='Created', type=HFI_FIELD, header_filter=hf,
                                        has_a_filter=True, editable=True,  filter_string="created__range"
                                       )

        response = self.client.get('/creme_core/header_filter/edit/%s' % hf.id)
        self.assertEqual(404, response.status_code)

    def test_headerfilter_edit02(self):
        self.login()

        ct = ContentType.objects.get_for_model(Contact)
        hf = HeaderFilter.objects.create(pk='tests-hf_contact', name='Contact view', entity_type_id=ct.id, is_custom=True)
        HeaderFilterItem.objects.create(pk='tests-hfi_entity_first_name', order=1,
                                        name='first_name', title='First name',
                                        type=HFI_FIELD, header_filter=hf,
                                        filter_string="first_name__icontains"
                                       )

        uri = '/creme_core/header_filter/edit/%s' % hf.id
        response = self.client.get(uri)
        self.assertEqual(200, response.status_code)

        try:
            form = response.context['form']
            fields_field = form.fields['fields']
        except KeyError, e:
            self.fail(str(e))

        first_name_index  = None
        last_name_index = None
        for i, (fname, fvname) in enumerate(fields_field.choices):
            if   fname == 'first_name': first_name_index = i
            elif fname == 'last_name':  last_name_index  = i

        if first_name_index is None: self.fail('No "first_name" field')
        if last_name_index  is None: self.fail('No "last_name" field')

        name = 'Entity view v2'
        response = self.client.post(uri,
                                    data={
                                            'name':                               name,
                                            'fields_check_%s' % first_name_index: 'on',
                                            'fields_value_%s' % first_name_index: 'first_name',
                                            'fields_order_%s' % first_name_index: 1,
                                            'fields_check_%s' % last_name_index:  'on',
                                            'fields_value_%s' % last_name_index:  'last_name',
                                            'fields_order_%s' % last_name_index:  2,
                                         }
                                   )
        self.assertNoFormError(response)
        self.assertEqual(302, response.status_code)

        hf = HeaderFilter.objects.get(pk=hf.id)
        self.assertEqual(name, hf.name)

        hfitems = hf.header_filter_items.all()
        self.assertEqual(2,            len(hfitems))
        self.assertEqual('first_name', hfitems[0].name)
        self.assertEqual('last_name',  hfitems[1].name)

    #TODO: def test_headerfilter_delete(self): #editable and not editable

    def test_csv_export(self): #TODO: test other hfi type...
        self.login()

        ct = ContentType.objects.get_for_model(Contact)
        hf = HeaderFilter.objects.create(id='test-hf_contact', name='Contact view', entity_type=ct)
        create_hfi = HeaderFilterItem.objects.create
        create_hfi(id='test-hfi_lastname',  order=1, name='last_name',  title='Last name',  type=HFI_FIELD, header_filter=hf, has_a_filter=True, editable=True, filter_string="last_name__icontains")
        create_hfi(id='test-hfi_firstname', order=2, name='first_name', title='First name', type=HFI_FIELD, header_filter=hf, has_a_filter=True, editable=True, filter_string="first_name__icontains")

        for first_name, last_name in [('Spike', 'Spiegel'), ('Jet', 'Black'), ('Faye', 'Valentine'), ('Edward', 'Wong')]:
            Contact.objects.create(user=self.user, first_name=first_name, last_name=last_name)

        lv_url = Contact.get_lv_absolute_url()
        self.assertEqual(200, self.client.get(lv_url).status_code) #set the current list view state...

        response = self.client.get('/creme_core/list_view/dl_csv/%s' % ct.id, data={'list_url': lv_url})
        self.assertEqual(200, response.status_code)
        self.assertEqual(['"Last name","First name"', '"Black","Jet"', '"Spiegel","Spike"', '"Valentine","Faye"', '"Wong","Edward"'],
                         response.content.splitlines()
                        )
