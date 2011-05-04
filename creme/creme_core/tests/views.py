# -*- coding: utf-8 -*-

from tempfile import NamedTemporaryFile

from django.http import Http404
from django.core.serializers.json import simplejson
from django.utils.translation import ugettext as _
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType

from creme_core.models import *
from creme_core.models.header_filter import HFI_FIELD
from creme_core.tests.base import CremeTestCase
from creme_core.gui.bulk_update import bulk_update_registry

from persons.models import Contact, Organisation, Position, Sector
from persons.constants import REL_OBJ_CUSTOMER_OF, REL_OBJ_EMPLOYED_BY

from documents.models import Document, Folder, FolderCategory #for CSV importing


class ViewsTestCase(CremeTestCase):
    def login(self, is_superuser=True, *args, **kwargs):
        super(ViewsTestCase, self).login(is_superuser, *args, **kwargs)

        SetCredentials.objects.create(role=self.role,
                                      value=SetCredentials.CRED_VIEW   | \
                                            SetCredentials.CRED_CHANGE | \
                                            SetCredentials.CRED_DELETE | \
                                            SetCredentials.CRED_LINK   | \
                                            SetCredentials.CRED_UNLINK,
                                      set_type=SetCredentials.ESET_OWN
                                     )

    def _set_all_creds_except_one(self, excluded): #TODO: in CremeTestCase ?
        value = SetCredentials.CRED_NONE

        for cred in (SetCredentials.CRED_VIEW, SetCredentials.CRED_CHANGE,
                     SetCredentials.CRED_DELETE, SetCredentials.CRED_LINK,
                     SetCredentials.CRED_UNLINK):
            if cred != excluded:
                value |= cred

        SetCredentials.objects.create(role=self.user.role,
                                      value=value,
                                      set_type=SetCredentials.ESET_ALL)


class MiscViewsTestCase(ViewsTestCase):
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


class EntityViewsTestCase(ViewsTestCase):
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

    def test_get_info_fields01(self):
        self.login()

        furl = '/creme_core/entity/get_info_fields/%s/json'
        ct = ContentType.objects.get_for_model(Contact)
        response = self.client.get(furl % ct.id)
        self.assertEqual(200, response.status_code)

        json_data = simplejson.loads(response.content)
        #print json_data
        self.assert_(isinstance(json_data, list))
        self.assert_(all(isinstance(elt, list) for elt in json_data))
        self.assert_(all(len(elt) == 2 for elt in json_data))

        names = ['created', 'modified', 'first_name', 'last_name', 'description',
                 'skype', 'landline', 'mobile', 'fax', 'email', 'url_site', 'birthday'
                ]
        diff = set(names) - set(name for name, vname in json_data)
        self.failIf(diff, diff)

        self.assertEqual(len(names), len(json_data))

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
        translation = _(u'Name')
        self.assert_(json_dict['name'].startswith(translation))
        self.assertNotEqual(translation, json_dict['name'])

    def test_edit_entities_bulk01(self):
        self.login()
        contact_ct_id = ContentType.objects.get_for_model(Contact).id
        
        response = self.client.get('/creme_core/entity/bulk_update/%s/'  % contact_ct_id)
        self.assertEqual(404, response.status_code)

        response = self.client.get('/creme_core/entity/bulk_update/%s/%s' % (contact_ct_id, 0))
        self.assertEqual(404, response.status_code)

        response = self.client.get('/creme_core/entity/bulk_update/%s/%s' % (contact_ct_id, ",".join([str(i) for i in xrange(10)])))
        self.assertEqual(404, response.status_code)

        mario = Contact.objects.create(user=self.user, first_name="Mario", last_name="Bros")
        response = self.client.get('/creme_core/entity/bulk_update/%s/%s' % (contact_ct_id, mario.id))
        self.assertEqual(200, response.status_code)
        

    def test_edit_entities_bulk02(self):
        self.login()
        contact_ct_id = ContentType.objects.get_for_model(Contact).id

        unemployed   = Position.objects.create(title='unemployed')
        plumber      = Position.objects.create(title='plumber')
        ghost_hunter = Position.objects.create(title='ghost hunter')

        mario = Contact.objects.create(user=self.user, first_name="Mario", last_name="Bros", position=plumber)
        luigi = Contact.objects.create(user=self.user, first_name="Luigi", last_name="Bros", position=ghost_hunter)

        comma_sep_ids = ",".join([str(mario.id), str(luigi.id)])

        url = '/creme_core/entity/bulk_update/%s/%s' % (contact_ct_id, comma_sep_ids)

        response = self.client.get(url)
        self.assertEqual(200, response.status_code)

        response = self.client.post(url,
                            data={
                                'field_name': 'position',
                                'field_value': unemployed.id,
                                'entities_lbl': 'whatever',
                            }
                           )
        self.assertNoFormError(response)

        mario = Contact.objects.get(pk=mario.pk)#Refresh
        luigi = Contact.objects.get(pk=luigi.pk)#Refresh

        self.assertEqual(unemployed, mario.position)
        self.assertEqual(unemployed, luigi.position)

    def test_edit_entities_bulk03(self):
        self.login()
        contact_ct_id = ContentType.objects.get_for_model(Contact).id

        plumbing    = Sector.objects.create(title='Plumbing')
        games       = Sector.objects.create(title='Games')

        mario = Contact.objects.create(user=self.user, first_name="Mario", last_name="Bros", sector=games)
        luigi = Contact.objects.create(user=self.user, first_name="Luigi", last_name="Bros", sector=games)
        nintendo = Organisation.objects.create(user=self.user, name='Nintendo', sector=games)

        comma_sep_ids = ",".join([str(mario.id), str(luigi.id), str(nintendo.id)])

        url = '/creme_core/entity/bulk_update/%s/%s' % (contact_ct_id, comma_sep_ids)

        response = self.client.get(url)
        self.assertEqual(200, response.status_code)

        response = self.client.post(url,
                            data={
                                'field_name': 'sector',
                                'field_value': plumbing.id,
                                'entities_lbl': 'whatever',
                            }
                           )
        self.assertNoFormError(response)

        mario    = Contact.objects.get(pk=mario.pk)#Refresh
        luigi    = Contact.objects.get(pk=luigi.pk)#Refresh
        self.assertEqual(plumbing, mario.sector)
        self.assertEqual(plumbing, luigi.sector)

        nintendo = Organisation.objects.get(pk=nintendo.pk)#Refresh
        self.assertEqual(games, nintendo.sector)

    def test_edit_entities_bulk04(self):
        self.login()
        contact_ct_id = ContentType.objects.get_for_model(Contact).id

        mario = Contact.objects.create(user=self.user, first_name="Mario", last_name="Bros")
        luigi = Contact.objects.create(user=self.user, first_name="Luigi", last_name="Bros")

        comma_sep_ids = ",".join([str(mario.id), str(luigi.id)])
        url = '/creme_core/entity/bulk_update/%s/%s' % (contact_ct_id, comma_sep_ids)

        response = self.client.get(url)
        self.assertEqual(200, response.status_code)

        response = self.client.post(url,
                    data={
                        'field_name':   'last_name',
                        'field_value':  '',
                        'entities_lbl': 'whatever',
                    }
                   )

        self.assertFormError(response, 'form', None, [_(u'This field is required.')])

    def test_edit_entities_bulk05(self):
        self.login()
        contact_ct_id = ContentType.objects.get_for_model(Contact).id

        bulk_update_registry.register((Contact, ['position', ]))

        unemployed   = Position.objects.create(title='unemployed')

        mario = Contact.objects.create(user=self.user, first_name="Mario", last_name="Bros")
        luigi = Contact.objects.create(user=self.user, first_name="Luigi", last_name="Bros")

        comma_sep_ids = ",".join([str(mario.id), str(luigi.id)])
        url = '/creme_core/entity/bulk_update/%s/%s' % (contact_ct_id, comma_sep_ids)

        response = self.client.get(url)
        self.assertEqual(200, response.status_code)

        response = self.client.post(url,
                    data={
                        'field_name':   'position',
                        'field_value':  unemployed.id,
                        'entities_lbl': 'whatever',
                    }
                   )

        self.assert_(response.context['form'].errors)
#        self.assertFormError(response, 'form', 'field_name', [_(u'Select a valid choice. %s is not one of the available choices.') % 'position'])

    def test_edit_entities_bulk06(self):
        self.login()
        contact_ct_id = ContentType.objects.get_for_model(Contact).id

        mario = Contact.objects.create(user=self.user, first_name="Mario", last_name="Bros", description="Luigi's brother")
        luigi = Contact.objects.create(user=self.user, first_name="Luigi", last_name="Bros", description="Mario's brother")

        comma_sep_ids = ",".join([str(mario.id), str(luigi.id)])

        url = '/creme_core/entity/bulk_update/%s/%s' % (contact_ct_id, comma_sep_ids)

        response = self.client.get(url)
        self.assertEqual(200, response.status_code)

        response = self.client.post(url,
                            data={
                                'field_name':      'description',
                                'field_value':     '',
                                'entities_lbl':    'whatever',
                                'bad_entities_lbl':'whatever',
                            }
                           )
        self.assertNoFormError(response)

        mario    = Contact.objects.get(pk=mario.pk)#Refresh
        luigi    = Contact.objects.get(pk=luigi.pk)#Refresh
        self.assertEqual('', mario.description)
        self.assertEqual('', luigi.description)


    def test_edit_entities_bulk07(self):
        self.login(is_superuser=False, allowed_apps=('creme_core', 'persons'))
        contact_ct_id = ContentType.objects.get_for_model(Contact).id

        mario_desc = u"Luigi's brother"
        mario = Contact.objects.create(user=self.other_user, first_name="Mario", last_name="Bros", description=mario_desc)
        luigi = Contact.objects.create(user=self.user,       first_name="Luigi", last_name="Bros", description="Mario's brother")

        comma_sep_ids = ",".join([str(mario.id), str(luigi.id)])

        url = '/creme_core/entity/bulk_update/%s/%s' % (contact_ct_id, comma_sep_ids)

        response = self.client.get(url)
        self.assertEqual(200, response.status_code)

        response = self.client.post(url,
                            data={
                                'field_name':      'description',
                                'field_value':     '',
                                'entities_lbl':    'whatever',
                                'bad_entities_lbl':'whatever',
                            }
                           )
        self.assertNoFormError(response)

        mario    = Contact.objects.get(pk=mario.pk)#Refresh
        luigi    = Contact.objects.get(pk=luigi.pk)#Refresh
        
        self.assertEqual(mario_desc, mario.description)
        self.assertEqual('',         luigi.description)



class PropertyViewsTestCase(ViewsTestCase):
    def test_add(self):
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

    def test_delete(self):
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
            entity.properties.get(type=ptype)
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


class RelationViewsTestCase(ViewsTestCase):
    def test_get_ctypes_of_relation(self):
        self.login()
        self.populate('creme_core', 'persons')

        response = self.client.get('/creme_core/relation/predicate/%s/content_types/json' % REL_OBJ_CUSTOMER_OF,
                                   data={'fields': ['id', 'unicode']})

        self.assertEqual(200, response.status_code)
        self.assertEqual('text/javascript', response['Content-Type'])

        json_data = simplejson.loads(response.content)
        get_ct = ContentType.objects.get_for_model
        self.assertEqual(json_data, [[get_ct(Contact).id, Contact._meta.verbose_name],
                                     [get_ct(Organisation).id, Organisation._meta.verbose_name]
                                    ]
                        )

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

        url = '/creme_core/relation/add/%s' % self.subject01.id
        self.assertEqual(200, self.client.get(url).status_code)

        response = self.client.post(url, data={
                                                'relations': """[{"rtype":"%s","ctype":"%s","entity":"%s"},
                                                                 {"rtype":"%s","ctype":"%s","entity":"%s"}]""" % (
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
        self.assertEqual(403, self.client.get('/creme_core/relation/add/%s' % subject.id).status_code)

    def test_add_relations03(self):
        self._aux_test_add_relations(is_superuser=False)
        self._set_all_creds_except_one(excluded=SetCredentials.CRED_LINK)

        unlinkable = CremeEntity.objects.create(user=self.other_user)
        self.assert_(unlinkable.can_view(self.user))
        self.failIf(unlinkable.can_link(self.user))

        response = self.client.post('/creme_core/relation/add/%s' % self.subject01.id,
                                    data={
                                            'relations': """[{"rtype":"%s","ctype":"%s","entity":"%s"},
                                                             {"rtype":"%s","ctype":"%s","entity":"%s"}]""" % (
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

        self.assertEqual(['relations'], form.errors.keys())
        self.assertEqual(0, self.subject01.relations.count())

    def test_add_relations04(self): #duplicates -> error
        self._aux_test_add_relations()

        response = self.client.post('/creme_core/relation/add/%s' % self.subject01.id,
                                    data={
                                            'relations': """[{"rtype":"%s","ctype":"%s","entity":"%s"},
                                                             {"rtype":"%s","ctype":"%s","entity":"%s"},
                                                             {"rtype":"%s","ctype":"%s","entity":"%s"}]""" % (
                                                                self.rtype01.id, self.ct_id, self.object01.id,
                                                                self.rtype02.id, self.ct_id, self.object02.id,
                                                                self.rtype01.id, self.ct_id, self.object01.id,
                                                            ),
                                         }
                                   )
        try:
            form = response.context['form']
        except Exception, e:
            self.fail('No form in context ? (%s)', str(e))

        if not form.errors:
            self.fail('Not the excepted error in form.')

        self.assertEqual(['relations'], form.errors.keys())

    def test_add_relations05(self): #do not recreate existing relations
        self._aux_test_add_relations()

        Relation.objects.create(user=self.user,
                                subject_entity=self.subject01,
                                type=self.rtype02,
                                object_entity=self.object02
                               )
        response = self.client.post('/creme_core/relation/add/%s' % self.subject01.id,
                                    data={
                                            'relations': """[{"rtype":"%s","ctype":"%s","entity":"%s"},
                                                             {"rtype":"%s","ctype":"%s","entity":"%s"}]""" % (
                                                                self.rtype01.id, self.ct_id, self.object01.id,
                                                                self.rtype02.id, self.ct_id, self.object02.id,
                                                            ),
                                          }
                                   )
        self.assertNoFormError(response)
        self.assertEqual(2, self.subject01.relations.count()) #and not 3

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
                                                'relations':    """[{"rtype":"%s","ctype":"%s","entity":"%s"},
                                                                    {"rtype":"%s","ctype":"%s","entity":"%s"}]""" % (
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
                                                'relations':        """[{"rtype":"%s","ctype":"%s","entity":"%s"},
                                                                        {"rtype":"%s","ctype":"%s","entity":"%s"}]""" % (
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
                                                'relations':    '[{"rtype":"%s","ctype":"%s","entity":"%s"}]' % (
                                                                    self.rtype01.id, self.ct_id, unlinkable.id
                                                                   ),
                                              })
        self.assertEqual(200, response.status_code)

        try:
            form = response.context['form']
        except Exception, e:
            self.fail('No form in context ? (%s)', str(e))

        if not form.errors:
            self.fail('Not the excepted error in form.')

        self.assertEqual(['relations'], form.errors.keys())

    def test_add_relations_bulk_fixedrtypes01(self):
        self._aux_test_add_relations()

        #this relation should not be recreated by the view
        Relation.objects.create(user=self.user,
                                subject_entity=self.subject02,
                                type=self.rtype02,
                                object_entity=self.object02
                               )

        url = '/creme_core/relation/add_to_entities/%s/%s,%s,/%s,%s,' % (
                    self.ct_id, self.rtype01.id, self.rtype02.id, self.subject01.id, self.subject02.id
                )
        self.assertEqual(200, self.client.get(url).status_code)

        response = self.client.post(url, data={
                                                'entities_lbl': 'wtf',
                                                'relations':    """[{"rtype":"%s","ctype":"%s","entity":"%s"},
                                                                    {"rtype":"%s","ctype":"%s","entity":"%s"}]""" % (
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

    def test_add_relations_bulk_fixedrtypes02(self):
        self._aux_test_add_relations()

        url = '/creme_core/relation/add_to_entities/%s/%s/%s,%s,' % (
                    self.ct_id, self.rtype01.id, self.subject01.id, self.subject02.id
                )
        self.assertEqual(200, self.client.get(url).status_code)

        response = self.client.post(url, data={
                                                'entities_lbl': 'wtf',
                                                'relations': """[{"rtype":"%s","ctype":"%s","entity":"%s"},
                                                                 {"rtype":"%s","ctype":"%s","entity":"%s"}]"""  % (
                                                                self.rtype02.id, self.ct_id, self.object01.id,
                                                                self.rtype02.id, self.ct_id, self.object02.id,
                                                               ),
                                              })
        self.assertEqual(200, response.status_code)

        try:
            form = response.context['form']
        except Exception, e:
            self.fail('No form in context ? (%s)', str(e))

        if not form.errors:
            self.fail('Not the excepted error in form.')

        self.assertEqual(['relations'], form.errors.keys())

    def _aux_relation_objects_to_link_selection(self):
        self.populate('creme_core', 'persons')
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

    def test_objects_to_link_selection01(self):
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

    def test_objects_to_link_selection02(self):
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

    def test_objects_to_link_selection03(self):
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

    def test_objects_to_link_selection04(self):
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

    def test_delete01(self):
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

    def test_delete02(self):
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

    def test_delete03(self): #is internal
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

    def test_delete_similar01(self):
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

    def test_delete_similar02(self):
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

    def test_delete_similar03(self): #is internal
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

class HeaderFilterViewsTestCase(ViewsTestCase):
    def test_create01(self): #TODO: test several HFI, other types of HFI
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
        self.assert_(hfilter.user is None)

        hfitems = hfilter.header_filter_items.all()
        self.assertEqual(1, len(hfitems))

        hfitem = hfitems[0]
        self.assertEqual('created',        hfitem.name)
        self.assertEqual(1,                hfitem.order)
        self.assertEqual(1,                hfitem.type)
        self.assertEqual('created__range', hfitem.filter_string)
        self.failIf(hfitem.is_hidden)

    def test_create02(self):
        self.login()

        ct = ContentType.objects.get_for_model(CremeEntity)
        uri = '/creme_core/header_filter/add/%s' % ct.id
        response = self.client.get(uri)

        try:
            fields_field = response.context['form'].fields['fields']
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
                                            'user':                            self.user.id,
                                            'fields_check_%s' % created_index: 'on',
                                            'fields_value_%s' % created_index: 'created',
                                            'fields_order_%s' % created_index: 1,
                                         }
                                   )
        self.assertNoFormError(response)

        hfilters = HeaderFilter.objects.filter(name=name)
        self.assertEqual(1,            len(hfilters))
        self.assertEqual(self.user.id, hfilters[0].user_id)

    def test_create03(self): #check app credentials
        self.login(is_superuser=False)

        ct = ContentType.objects.get_for_model(Contact)
        uri = '/creme_core/header_filter/add/%s' % ct.id
        self.assertEqual(404, self.client.get(uri).status_code)

        self.role.allowed_apps = ['persons']
        self.role.save()

        self.assertEqual(200, self.client.get(uri).status_code)

    def test_edit01(self): #not editable
        self.login()

        ct = ContentType.objects.get_for_model(CremeEntity)
        hf = HeaderFilter.objects.create(pk='tests-hf_entity', name='Entity view', entity_type_id=ct.id, is_custom=False)
        HeaderFilterItem.objects.create(pk='tests-hfi_entity_created', order=1, name='created',
                                        title='Created', type=HFI_FIELD, header_filter=hf,
                                        has_a_filter=True, editable=True,  filter_string="created__range"
                                       )

        self.assertEqual(404, self.client.get('/creme_core/header_filter/edit/%s' % hf.id).status_code)

    def test_edit02(self):
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
            fields_field = response.context['form'].fields['fields']
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

    def test_edit03(self): #can not edit HeaderFilter that belongs to another user
        self.login(is_superuser=False)

        ct = ContentType.objects.get_for_model(CremeEntity)
        hf = HeaderFilter.objects.create(pk='tests-hf_contact', name='Contact view',
                                         entity_type_id=ct.id, is_custom=True,
                                         user=self.other_user
                                        )
        self.assertEqual(404, self.client.get('/creme_core/header_filter/edit/%s' % hf.id).status_code)

    def test_edit04(self): #user do not have the app credentials
        self.login(is_superuser=False)

        ct = ContentType.objects.get_for_model(Contact)
        hf = HeaderFilter.objects.create(pk='tests-hf_contact', name='Contact view',
                                         entity_type_id=ct.id, is_custom=True,
                                         user=self.user
                                        )
        self.assertEqual(404, self.client.get('/creme_core/header_filter/edit/%s' % hf.id).status_code)

    def test_delete01(self):
        self.login()

        ct = ContentType.objects.get_for_model(Contact)
        hf = HeaderFilter.objects.create(pk='tests-hf_contact', name='Contact view', entity_type_id=ct.id, is_custom=True)
        HeaderFilterItem.objects.create(pk='tests-hfi_entity_first_name', order=1,
                                        name='first_name', title='First name',
                                        type=HFI_FIELD, header_filter=hf,
                                        filter_string="first_name__icontains"
                                       )

        self.assertEqual(200, self.client.post('/creme_core/header_filter/delete',
                                               data={'id': hf.id}, follow=True
                                              ).status_code
                        )
        self.assertEqual(0, HeaderFilter.objects.filter(pk=hf.id).count())
        self.assertEqual(0, HeaderFilterItem.objects.filter(header_filter=hf.id).count())

    def test_delete02(self): #not custom -> undeletable
        self.login()

        ct = ContentType.objects.get_for_model(Contact)
        hf = HeaderFilter.objects.create(pk='tests-hf_contact', name='Contact view', entity_type_id=ct.id, is_custom=False)
        self.client.post('/creme_core/header_filter/delete', data={'id': hf.id})
        self.assertEqual(1, HeaderFilter.objects.filter(pk=hf.id).count())

    def test_delete03(self): #belongs to another user
        self.login(is_superuser=False)

        self.role.allowed_apps = ['persons']
        self.role.save()

        ct = ContentType.objects.get_for_model(Contact)
        hf = HeaderFilter.objects.create(pk='tests-hf_contact', name='Contact view',
                                         entity_type_id=ct.id, is_custom=True, user=self.other_user
                                        )
        self.client.post('/creme_core/header_filter/delete', data={'id': hf.id})
        self.assertEqual(1, HeaderFilter.objects.filter(pk=hf.id).count())

    def test_delete04(self): #belongs to my team -> ok
        self.login()

        my_team = User.objects.create(username='TeamTitan', is_team=True)
        my_team.teammates = [self.user]

        ct = ContentType.objects.get_for_model(Contact)
        hf = HeaderFilter.objects.create(pk='tests-hf_contact', name='Contact view',
                                         entity_type_id=ct.id, is_custom=True, user=my_team
                                        )
        self.assertEqual(200, self.client.post('/creme_core/header_filter/delete',
                                               data={'id': hf.id}, follow=True
                                              ).status_code
                        )
        self.assertEqual(0, HeaderFilter.objects.filter(pk=hf.id).count())

    def test_delete05(self): #belongs to a team (not mine) -> ko
        self.login(is_superuser=False)

        self.role.allowed_apps = ['persons']
        self.role.save()

        a_team = User.objects.create(username='TeamTitan', is_team=True)
        a_team.teammates = [self.other_user]

        ct = ContentType.objects.get_for_model(Contact)
        hf = HeaderFilter.objects.create(pk='tests-hf_contact', name='Contact view',
                                         entity_type_id=ct.id, is_custom=True, user=a_team
                                        )
        self.client.post('/creme_core/header_filter/delete', data={'id': hf.id}, follow=True)
        self.assertEqual(1, HeaderFilter.objects.filter(pk=hf.id).count())

    def test_delete06(self): #logged as super user
        self.login()

        ct = ContentType.objects.get_for_model(Contact)
        hf = HeaderFilter.objects.create(pk='tests-hf_contact', name='Contact view',
                                         entity_type_id=ct.id, is_custom=True, user=self.other_user
                                        )
        self.client.post('/creme_core/header_filter/delete', data={'id': hf.id})
        self.assertEqual(0, HeaderFilter.objects.filter(pk=hf.id).count())


class ListViewFilterViewsTestCase(ViewsTestCase):
    def setUp(self):
        self.ct = ContentType.objects.get_for_model(Contact)

    def test_create01(self): #check app credentials
        self.login(is_superuser=False)

        ct = ContentType.objects.get_for_model(Contact)
        uri = '/creme_core/filter/add/%s' % ct.id
        self.assertEqual(404, self.client.get(uri).status_code)

        self.role.allowed_apps = ['persons']
        self.role.save()
        self.assertEqual(200, self.client.get(uri).status_code)

    #def test_create02(self): #TODO: to finish

    def test_edit01(self):
        self.login()

        lv_filter = Filter.objects.create(name='Filter01', model_ct=self.ct, is_custom=True)
        url = '/creme_core/filter/edit/%s/%s' % (self.ct.id, lv_filter.id)
        self.assertEqual(200, self.client.get(url).status_code)
        #TODO: complete this test

    def test_edit02(self): #not custom -> can not edit
        self.login()

        lv_filter = Filter.objects.create(name='Filter01', model_ct=self.ct, is_custom=False)
        url = '/creme_core/filter/edit/%s/%s' % (self.ct.id, lv_filter.id)
        self.assertEqual(404, self.client.get(url).status_code)

    def test_edit03(self): #can not edit Filter that belongs to another user
        self.login(is_superuser=False)

        self.role.allowed_apps = ['persons']
        self.role.save()

        lv_filter = Filter.objects.create(name='Filter01', user=self.other_user, model_ct=self.ct, is_custom=True)
        url = '/creme_core/filter/edit/%s/%s' % (self.ct.id, lv_filter.id)
        self.assertEqual(404, self.client.get(url).status_code)

    def test_edit04(self): #user do not have the app credentials
        self.login(is_superuser=False)

        lv_filter = Filter.objects.create(name='Filter01', user=self.user, model_ct=self.ct, is_custom=True)
        url = '/creme_core/filter/edit/%s/%s' % (self.ct.id, lv_filter.id)
        self.assertEqual(404, self.client.get(url).status_code)

    def test_delete01(self):
        self.login()

        lv_filter = Filter.objects.create(name='Filter01', model_ct=self.ct, is_custom=True)
        response = self.client.post('/creme_core/filter/delete', data={'id': lv_filter.id}, follow=True)
        self.assertEqual(200, response.status_code)
        self.assert_(response.redirect_chain)
        self.assert_(response.redirect_chain[-1][0].endswith(Contact.get_lv_absolute_url()))
        self.assertEqual(0, Filter.objects.filter(pk=lv_filter.id).count())

    def test_delete02(self): #not custom -> can not delete
        self.login()

        lv_filter = Filter.objects.create(name='Filter01', model_ct=self.ct, is_custom=False)
        response = self.client.post('/creme_core/filter/delete', data={'id': lv_filter.id})
        self.assertEqual(404, response.status_code)
        self.assertEqual(1, Filter.objects.filter(pk=lv_filter.id).count())

    def test_delete03(self): #belongs to another user
        self.login(is_superuser=False)

        lv_filter = Filter.objects.create(name='Filter01', model_ct=self.ct, is_custom=True, user=self.other_user)
        self.assertEqual(404, self.client.post('/creme_core/filter/delete', data={'id': lv_filter.id}).status_code)
        self.assertEqual(1,   Filter.objects.filter(pk=lv_filter.id).count())

    def test_delete04(self): #belongs to my team -> ok
        self.login(is_superuser=False)

        self.role.allowed_apps = ['persons']
        self.role.save()

        my_team = User.objects.create(username='TeamTitan', is_team=True)
        my_team.teammates = [self.user]

        lv_filter = Filter.objects.create(name='Filter01', model_ct=self.ct, is_custom=True, user=my_team)
        self.assertEqual(200, self.client.post('/creme_core/filter/delete', data={'id': lv_filter.id}, follow=True).status_code)
        self.assertEqual(0,   Filter.objects.filter(pk=lv_filter.id).count())

    def test_delete05(self): #belongs to a team (not mine) -> ko
        self.login(is_superuser=False)

        self.role.allowed_apps = ['persons']
        self.role.save()

        a_team = User.objects.create(username='TeamTitan', is_team=True)
        a_team.teammates = [self.other_user]

        lv_filter = Filter.objects.create(name='Filter01', model_ct=self.ct, is_custom=True, user=a_team)
        self.assertEqual(404, self.client.post('/creme_core/filter/delete', data={'id': lv_filter.id}).status_code)
        self.assertEqual(1, Filter.objects.filter(pk=lv_filter.id).count())

    def test_delete06(self): #logged as superuser
        self.login()

        lv_filter = Filter.objects.create(name='Filter01', model_ct=self.ct, is_custom=True, user=self.other_user)
        self.assertEqual(200, self.client.post('/creme_core/filter/delete', data={'id': lv_filter.id}, follow=True).status_code)
        self.failIf(Filter.objects.filter(pk=lv_filter.id).count())

    #TODO: test other views....
    #(r'^add/(?P<ct_id>\d+)$',                           'add'),
    #(r'^edit/(?P<ct_id>\d+)/(?P<filter_id>\d+)$',       'edit'),
    #(r'^field_has_n_get_fk$',                           'field_has_n_get_fk'),
    #(r'^register/(?P<filter_id>\d*)/(?P<ct_id>\d+)$',   'register_in_session'),
    #(r'^get_session_filter_id/(?P<ct_id>\d+)$',         'get_session_filter_id'),
    #(r'^select_entity_popup/(?P<content_type_id>\d+)$', 'get_list_view_popup_from_ct'),
    #(r'^get_4_ct/(?P<content_type_id>\d+)$',            'get_filters_4_ct'),


class SearchViewTestCase(ViewsTestCase):
    def _build_contacts(self):
        self.linus = Contact.objects.create(user=self.user, first_name='Linus', last_name='Torvalds')
        self.alan  = Contact.objects.create(user=self.user, first_name='Alan',  last_name='Cox')

    def _setup_contacts(self):
        SearchConfigItem.create(Contact, ['first_name', 'last_name']) #TODO: unitest this method
        self._build_contacts()

    def _setup_orgas(self):
        SearchConfigItem.create(Organisation, ['name'])

        self.linusfo = Organisation.objects.create(user=self.user, name='FoobarLinusFoundation')
        self.coxco   = Organisation.objects.create(user=self.user, name='StuffCoxCorp')

    def test_search01(self):
        self.login()
        self._setup_contacts()

        response = self.client.post('/creme_core/search',
                                    data={
                                            'research': 'john',
                                            'ct_id':    ContentType.objects.get_for_model(Contact).id,
                                         }
                                   )
        self.assertEqual(200, response.status_code)

        try:
            results = response.context['results']
            total   = response.context['total']
        except Exception, e:
            self.fail(str(e))

        self.assertEqual(0, total)
        self.assertEqual(1, len(results))

        result = results[0]
        self.assert_(result['model'] is Contact)
        self.assertEqual(0, len(result['entities']))

    def test_search02(self):
        self.login()
        self._setup_contacts()

        response = self.client.post('/creme_core/search',
                                    data={
                                            'research': 'linu',
                                            'ct_id':    ContentType.objects.get_for_model(Contact).id,
                                         }
                                   )
        self.assertEqual(200, response.status_code)

        results = response.context['results']
        self.assertEqual(1, response.context['total'])
        self.assertEqual(1, len(results))

        entities = results[0]['entities']
        self.assertEqual(1, len(entities))

        entity = entities[0]
        self.assert_(isinstance(entity, Contact))
        self.assertEqual(self.linus.id, entity.id)

    def test_search03(self):
        self.login()
        self._setup_contacts()
        self._setup_orgas()

        context = self.client.post('/creme_core/search', data={'research': 'cox'}).context
        self.assertEqual(2, context['total'])

        contacts_result = None
        orgas_result    = None

        for result in context['results']:
            model = result['model']
            if model is Contact:
                self.assert_(contacts_result is None)
                contacts_result = result
            elif model is Organisation:
                self.assert_(orgas_result is None)
                orgas_result = result
            else:
                self.assertEqual(0, len(result['entities']))

        self.assert_(contacts_result is not None)
        self.assert_(orgas_result is not None)

        entities = contacts_result['entities']
        self.assertEqual(1, len(entities))
        self.assertEqual(self.alan.id, entities[0].id)

        entities = orgas_result['entities']
        self.assertEqual(1, len(entities))
        self.assertEqual(self.coxco.id, entities[0].id)

    def test_search04(self): #error
        self.login()
        self._setup_contacts()
        self._setup_orgas()

        self.assert_(self.client.post('/creme_core/search', data={'research': 'ox'}).context['error_message'])
        self.assert_(self.client.post('/creme_core/search').context['error_message'])
        self.assertEqual(404, self.client.post('/creme_core/search',
                                               data={
                                                       'research': 'linus',
                                                       'ct_id':     1024, #DOES NOT EXIST
                                                    }
                                              ).status_code
                        )

    def test_search05(self): #no config for contact
        self.login()
        self._build_contacts()
        self._setup_orgas()

        response = self.client.post('/creme_core/search',
                                    data={
                                            'research': 'torvalds',
                                            'ct_id':    ContentType.objects.get_for_model(Contact).id,
                                         }
                                   )
        results = response.context['results']
        self.assertEqual(1, response.context['total'])
        self.assertEqual(1, len(results))

        entities = results[0]['entities']
        self.assertEqual(1, len(entities))
        self.assertEqual(self.linus.id, entities[0].id)

    def test_search06(self): #search only is configured fields if the config exists
        self.login()
        self._setup_contacts()
        self._setup_orgas()

        self.linus.description = 'He is very smart but wears ugly shorts.'
        self.linus.save()

        response = self.client.post('/creme_core/search',
                                    data={
                                            'research': 'very smart',
                                            'ct_id':    ContentType.objects.get_for_model(Contact).id,
                                         }
                                   )
        self.assertEqual(0, response.context['total'])


class CSVImportViewsTestCase(ViewsTestCase):
    def _build_doc(self, lines):
        content = '\n'.join(','.join('"%s"' % item for item in line) for line in lines)

        tmpfile = NamedTemporaryFile()
        tmpfile.write(content)
        tmpfile.flush()

        tmpfile.file.seek(0)

        category = FolderCategory.objects.create(id=10, name=u'Test category')
        folder = Folder.objects.create(user=self.user, title=u'Test folder',
                                       parent_folder=None,
                                       category=category,
                                      )

        title = 'Test doc'
        response = self.client.post('/documents/document/add', follow=True,
                                    data={
                                            'user':        self.user.id,
                                            'title':       title,
                                            'description': 'CSV file for contacts',
                                            'filedata':    tmpfile.file,
                                            'folder':      folder.id,
                                         }
                                   )
        self.assertNoFormError(response)
        self.assertEqual(200, response.status_code)

        try:
            doc = Document.objects.get(title=title)
        except Exception, e:
            self.fail(str(e))

        return doc

    def test_import01(self):
        self.login()

        self.failIf(Contact.objects.exists())

        lines = [("Ayanami", "Rei"),
                 ("Asuka",   "Langley"),
                ]

        doc = self._build_doc(lines)

        ct = ContentType.objects.get_for_model(Contact)
        url = '/creme_core/list_view/import_csv/%s?list_url=%s' % (ct.id, Contact.get_lv_absolute_url())
        response = self.client.get(url)
        self.assertEqual(200, response.status_code)

        try:
            response.context['form']
        except Exception, e:
            self.fail(str(e))

        response = self.client.post(url, data={
                                                'csv_step':     0,
                                                'csv_document': doc.id,
                                                #csv_has_header
                                              }
                                   )
        self.assertEqual(200, response.status_code)

        try:
            form = response.context['form']
        except Exception, e:
            self.fail(str(e))

        self.assert_('value="1"' in unicode(form['csv_step']))

        response = self.client.post(url, data={
                                                'csv_step':     1,
                                                'csv_document': doc.id,
                                                #csv_has_header

                                                'user': self.user.id,

                                                'civility_colselect':  0,

                                                'first_name_colselect': 1,
                                                'last_name_colselect':  2,

                                                'description_colselect': 0,
                                                'skype_colselect':       0,
                                                'landline_colselect':    0,
                                                'mobile_colselect':      0,
                                                'fax_colselect':         0,
                                                'position_colselect':    0,
                                                'sector_colselect':      0,
                                                'email_colselect':       0,
                                                'url_site_colselect':    0,
                                                'birthday_colselect':    0,
                                                'image_colselect':       0,

                                                #'property_types',
                                                #'fixed_relations',
                                                #'dyn_relations',

                                                'billing_address_colselect':    0,
                                                'billing_po_box_colselect':     0,
                                                'billing_city_colselect':       0,
                                                'billing_state_colselect':      0,
                                                'billing_zipcode_colselect':    0,
                                                'billing_country_colselect':    0,
                                                'billing_department_colselect': 0,

                                                'shipping_address_colselect':    0,
                                                'shipping_po_box_colselect':     0,
                                                'shipping_city_colselect':       0,
                                                'shipping_state_colselect':      0,
                                                'shipping_zipcode_colselect':    0,
                                                'shipping_country_colselect':    0,
                                                'shipping_department_colselect': 0,
                                              }
                                   )
        self.assertEqual(200, response.status_code)

        try:
            form = response.context['form']
        except Exception, e:
            self.fail(str(e))

        self.assertEqual(0,          len(form.import_errors))
        self.assertEqual(len(lines), form.imported_objects_count)
        self.assertEqual(len(lines), form.lines_count)

        self.assertEqual(len(lines), Contact.objects.count())

        for first_name, last_name in lines:
            try:
                contact = Contact.objects.get(first_name=first_name, last_name=last_name)
            except Exception, e:
                self.fail(str(e))

            self.assertEqual(self.user.id, contact.user_id)
            #self.assert_(contact.billing_address is None) #TODO: fail ?!

    def test_import02(self): #use header, default value, model search and create, properties, fixed and dynamic relations
        self.login()

        self.failIf(Position.objects.exists())
        self.failIf(Sector.objects.exists())

        ptype = CremePropertyType.create(str_pk='test-prop_cute', text='Really cure in her suit')

        employed, _srt = RelationType.create(('persons-subject_employed_by', 'is an employee of'),
                                             ('persons-object_employed_by',  'employs')
                                            )
        loves, _srt    = RelationType.create(('test-subject_loving', 'is loving'),
                                             ('test-object_loving',  'is loved by')
                                            )

        nerv = Organisation.objects.create(user=self.user, name='Nerv')
        shinji = Contact.objects.create(user=self.user, first_name='Shinji', last_name='Ikari')

        pos_title = 'Pilot'
        city = 'Tokyo'
        lines = [('First name', 'Last name', 'Position', 'Sector', 'City', 'Organisation'),
                 ('Ayanami',    'Rei',       pos_title,  'Army',   city,   nerv.name),
                 ('Asuka',      'Langley',   pos_title,  'Army',   '',     nerv.name),
                ]

        doc = self._build_doc(lines)
        ct = ContentType.objects.get_for_model(Contact)
        url = '/creme_core/list_view/import_csv/%s?list_url=%s' % (ct.id, Contact.get_lv_absolute_url())
        response = self.client.post(url, data={
                                                'csv_step':       0,
                                                'csv_document':   doc.id,
                                                'csv_has_header': True,
                                              }
                                   )
        self.assertEqual(200, response.status_code)

        form = response.context['form']
        self.assert_('value="1"' in unicode(form['csv_step']))
        self.assert_('value="True"' in unicode(form['csv_has_header']))

        default_descr = 'A cute pilot'
        response = self.client.post(url, data={
                                                'csv_step':       1,
                                                'csv_document':   doc.id,
                                                'csv_has_header': True,

                                                'user': self.user.id,

                                                'civility_colselect': 0,

                                                'first_name_colselect': 1,
                                                'last_name_colselect':  2,

                                                'description_colselect': 0,
                                                'description_defval':    default_descr,

                                                'skype_colselect':       0,
                                                'landline_colselect':    0,
                                                'mobile_colselect':      0,
                                                'fax_colselect':         0,

                                                'position_colselect': 3,
                                                'position_subfield':  'title',
                                                'position_create':    True,

                                                'sector_colselect': 4,
                                                'sector_subfield':  'title',
                                                #'sector_create':    False,

                                                'email_colselect':       0,
                                                'url_site_colselect':    0,
                                                'birthday_colselect':    0,
                                                'image_colselect':       0,

                                                'property_types':  [ptype.id],
                                                'fixed_relations': '[{"rtype":"%s","ctype":"%s","entity":"%s"}]'  % (
                                                                            loves.id, shinji.entity_type_id, shinji.id
                                                                        ),
                                                'dyn_relations':    '[{"rtype":"%(rtype)s","ctype":"%(ctype)s","column":"%(column)s","searchfield":"%(search)s"}]'  % {
                                                                            'rtype': employed.id,
                                                                            'ctype': ContentType.objects.get_for_model(Organisation).id,
                                                                            'column': 6,
                                                                            'search': 'name',
                                                                        },

                                                'billing_address_colselect':    0,
                                                'billing_po_box_colselect':     0,
                                                'billing_city_colselect':       5,
                                                'billing_state_colselect':      0,
                                                'billing_zipcode_colselect':    0,
                                                'billing_country_colselect':    0,
                                                'billing_department_colselect': 0,

                                                'shipping_address_colselect':    0,
                                                'shipping_po_box_colselect':     0,
                                                'shipping_city_colselect':       0,
                                                'shipping_state_colselect':      0,
                                                'shipping_zipcode_colselect':    0,
                                                'shipping_country_colselect':    0,
                                                'shipping_department_colselect': 0,
                                              }
                                   )
        self.assertEqual(200, response.status_code)

        try:
            form = response.context['form']
        except Exception, e:
            self.fail(str(e))

        count = len(lines) - 1 # '-1' for header
        self.assertEqual(count,     len(form.import_errors)) #sector not found
        self.assertEqual(count,     form.imported_objects_count)
        self.assertEqual(count,     form.lines_count)
        self.assertEqual(count + 1, Contact.objects.count()) #+ 1 : because of shinji

        positions = Position.objects.all()
        self.assertEqual(1, len(positions))

        position = positions[0]
        self.assertEqual(pos_title, position.title)

        self.failIf(Sector.objects.exists())

        for first_name, last_name, pos_title, sector_title, city_name, orga_name in lines[1:]:
            try:
                contact = Contact.objects.get(first_name=first_name, last_name=last_name)
            except Exception, e:
                self.fail(str(e))

            self.assertEqual(default_descr, contact.description)
            self.assertEqual(position.id,   contact.position.id)
            self.assertEqual(1,             CremeProperty.objects.filter(type=ptype, creme_entity=contact.id).count())
            self.assertEqual(1,             Relation.objects.filter(subject_entity=contact, type=loves, object_entity=shinji).count())
            self.assertEqual(1,             Relation.objects.filter(subject_entity=contact, type=employed, object_entity=nerv).count())


        rei = Contact.objects.get(first_name=lines[1][0])
        self.assertEqual(city, rei.billing_address.city)

    def test_import03(self): #create entities to link with them
        self.login()

        self.failIf(Organisation.objects.exists())

        employed, _srt = RelationType.create(('persons-subject_employed_by', 'is an employee of'),
                                             ('persons-object_employed_by',  'employs')
                                            )
        orga_name = 'Nerv'

        doc = self._build_doc([('Ayanami', 'Rei', orga_name)])
        get_ct = ContentType.objects.get_for_model

        response = self.client.post('/creme_core/list_view/import_csv/%s?list_url=%s' % (get_ct(Contact).id, Contact.get_lv_absolute_url()),
                                    data={
                                            'csv_step':       1,
                                            'csv_document':   doc.id,
                                            #'csv_has_header': True,

                                            'user': self.user.id,

                                            'civility_colselect': 0,

                                            'first_name_colselect': 1,
                                            'last_name_colselect':  2,

                                            'description_colselect': 0,
                                            'skype_colselect':       0,
                                            'landline_colselect':    0,
                                            'mobile_colselect':      0,
                                            'fax_colselect':         0,
                                            'position_colselect':    0,
                                            'sector_colselect':      0,
                                            'email_colselect':       0,
                                            'url_site_colselect':    0,
                                            'birthday_colselect':    0,
                                            'image_colselect':       0,

                                            #'property_types':,
                                            #'fixed_relations':,
                                            'dyn_relations':    '[{"rtype":"%(rtype)s","ctype":"%(ctype)s","column":"%(column)s","searchfield":"%(search)s"}]'  % {
                                                                        'rtype': employed.id,
                                                                        'ctype': get_ct(Organisation).id,
                                                                        'column': 3,
                                                                        'search': 'name',
                                                                    },
                                            'dyn_relations_can_create': True,

                                            'billing_address_colselect':    0,
                                            'billing_po_box_colselect':     0,
                                            'billing_city_colselect':       0,
                                            'billing_state_colselect':      0,
                                            'billing_zipcode_colselect':    0,
                                            'billing_country_colselect':    0,
                                            'billing_department_colselect': 0,

                                            'shipping_address_colselect':    0,
                                            'shipping_po_box_colselect':     0,
                                            'shipping_city_colselect':       0,
                                            'shipping_state_colselect':      0,
                                            'shipping_zipcode_colselect':    0,
                                            'shipping_country_colselect':    0,
                                            'shipping_department_colselect': 0,
                                         }
                                   )
        self.assertEqual(200, response.status_code)

        form = response.context['form']
        self.assertEqual(0, len(form.import_errors)) #sector not found
        self.assertEqual(1, form.imported_objects_count)

        contacts = Contact.objects.all()
        self.assertEqual(1, len(contacts))

        rei = contacts[0]
        relations = Relation.objects.filter(subject_entity=rei, type=employed)
        self.assertEqual(1, len(relations))

        employer = relations[0].object_entity.get_real_entity()
        self.assert_(isinstance(employer, Organisation))
        self.assertEqual(orga_name, employer.name)
