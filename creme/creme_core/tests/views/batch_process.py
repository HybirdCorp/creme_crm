# -*- coding: utf-8 -*-

try:
    from django.core.exceptions import ValidationError
    from django.core.serializers.json import simplejson
    from django.utils.translation import ugettext as _
    from django.contrib.contenttypes.models import ContentType

    from creme_core.models import EntityFilter, EntityFilterCondition, SetCredentials
    from creme_core.tests.views.base import ViewsTestCase

    from persons.models import Organisation, Contact
except Exception as e:
    print 'Error in <%s>: %s' % (__name__, e)


__all__ = ('BatchProcessViewsTestCase', )


class BatchProcessViewsTestCase(ViewsTestCase):
    format_str1 = '[{"name": "%(name)s", "operator": "%(operator)s", "value": {"type": "%(operator)s", "value": "%(value)s"}}]'
    format_str2 = '[{"name": "%(name01)s", "operator": "%(operator01)s", "value": {"type": "%(operator01)s", "value": "%(value01)s"}},' \
                  ' {"name": "%(name02)s", "operator": "%(operator02)s", "value": {"type": "%(operator02)s", "value": "%(value02)s"}}]'

    @classmethod
    def setUpClass(cls):
        cls.populate('creme_core', 'creme_config')

    def build_url(self, model):
         return '/creme_core/list_view/batch_process/%s?list_url=http://testserver%s' % (
                        ContentType.objects.get_for_model(model).id,
                        model.get_lv_absolute_url(),
                     )

    def test_no_app_perm(self):
        self.login(is_superuser=False)
        self.assertEqual(404, self.client.get(self.build_url(Organisation)).status_code)

    def test_app_perm(self):
        self.login(is_superuser=False, allowed_apps=['persons'])
        self.assertEqual(200, self.client.get(self.build_url(Organisation)).status_code)

    def test_batching_upper01(self):
        self.login()
        url = self.build_url(Organisation)

        response = self.client.get(url)
        self.assertEqual(200, response.status_code)

        with self.assertNoException():
            orga_fields = set(response.context['form'].fields['actions']._fields.iterkeys())

        self.assertIn('name', orga_fields)
        self.assertIn('capital', orga_fields)

        create_orga = Organisation.objects.create
        orga01 = create_orga(user=self.user, name='Genshiken')
        orga02 = create_orga(user=self.user, name='Manga club')

        response = self.client.post(url, follow=True,
                                    data={'actions': self.format_str1 % {
                                                            'operator': 'upper',
                                                            'name':     'name',
                                                            'value':    '',
                                                        },
                                         }
                                   )
        self.assertEqual(200, response.status_code)
        self.assertNoFormError(response)

        self.assertEqual('GENSHIKEN',  self.refresh(orga01).name)
        self.assertEqual('MANGA CLUB', self.refresh(orga02).name)

        with self.assertNoException():
            back_url = response.context['back_url']
            form = response.context['form']

        self.assertEqual(u"http://testserver%s" % Organisation.get_lv_absolute_url(), back_url)

        self.assertIs(Organisation, form.entity_type)

        count = Organisation.objects.count()
        self.assertEqual(count, form.modified_objects_count)
        self.assertEqual(count, form.read_objects_count)
        self.assertEqual(0,     len(form.process_errors))

    def test_batching_lower01(self): # & use ct
        self.login()

        create_contact = Contact.objects.create
        contact01 = create_contact(user=self.user, first_name='Saki',     last_name='Kasukabe')
        contact02 = create_contact(user=self.user, first_name='Harunobu', last_name='Madarame')

        response = self.client.post(self.build_url(Contact), follow=True,
                                    data={'actions': self.format_str1 % {
                                                            'name':     'first_name',
                                                            'operator': 'lower',
                                                            'value':    '',
                                                        },
                                         }
                                   )
        self.assertEqual(200, response.status_code)
        self.assertNoFormError(response)

        self.assertEqual('saki',     self.refresh(contact01).first_name)
        self.assertEqual('harunobu', self.refresh(contact02).first_name)

        with self.assertNoException():
            back_url = response.context['back_url']
            form = response.context['form']

        self.assertEqual(u"http://testserver%s" % Contact.get_lv_absolute_url(), back_url)

        self.assertIs(Contact, form.entity_type)
        self.assertEqual(Contact.objects.count(), form.modified_objects_count)

    def test_validation_error01(self): # invalid field
        self.login()

        response = self.client.post(self.build_url(Contact), follow=True,
                                    data={'actions': self.format_str1 % {
                                                            'name':     'unknown_field', # <============= HERE
                                                            'operator': 'lower',
                                                            'value':    '',
                                                        },
                                         }
                                   )
        self.assertEqual(200, response.status_code)
        self.assertFormError(response, 'form', 'actions', [_(u"This field is invalid with this model.")])

    def test_several_actions(self): # + 'title' operator
        self.login()

        contact = Contact.objects.create(user=self.user, first_name='kanji', last_name='sasahara')
        response = self.client.post(self.build_url(Contact), follow=True,
                                    data={'actions': self.format_str2 % {
                                                            'name01': 'first_name', 'operator01': 'title', 'value01': '',
                                                            'name02': 'last_name',  'operator02': 'upper', 'value02': '',
                                                        },
                                         }
                                   )
        self.assertEqual(200, response.status_code)
        self.assertNoFormError(response)

        contact = self.refresh(contact)
        self.assertEqual('Kanji',    contact.first_name)
        self.assertEqual('SASAHARA', contact.last_name)

    def test_several_actions_error(self): #several times tye same field
        self.login()

        name = 'first_name'
        response = self.client.post(self.build_url(Contact), follow=True,
                                    data={'actions': self.format_str2 % {
                                                            'name01': name, 'operator01': 'title', 'value01': '',
                                                            'name02': name, 'operator02': 'upper', 'value02': '',
                                                        },
                                         }
                                   )
        self.assertEqual(200, response.status_code)
        self.assertFormError(response, 'form', 'actions', [_(u"The field '%s' can not be used twice.") % _('First name')])

    def test_with_filter(self):
        self.login()

        create_orga = Organisation.objects.create
        orga01 = create_orga(user=self.user, name='Genshiken')
        orga02 = create_orga(user=self.user, name='Manga club')
        orga03 = create_orga(user=self.user, name='Anime club')

        efilter = EntityFilter.create('test-filter01', 'Contains "club"', Organisation)
        efilter.set_conditions([EntityFilterCondition.build_4_field(model=Organisation,
                                                                    operator=EntityFilterCondition.CONTAINS,
                                                                    name='name', values=['club']
                                                                   )
                               ])
        self.assertEqual(set([orga02, orga03]), set(efilter.filter(Organisation.objects.all()))) # <== not 'orga01'

        response = self.client.post(self.build_url(Organisation), follow=True,
                                    data={'filter':  efilter.id,
                                          'actions': self.format_str1 % {
                                                            'name':     'name',
                                                            'operator': 'lower',
                                                            'value':    '',
                                                        },
                                         }
                                   )
        self.assertEqual(200, response.status_code)
        self.assertNoFormError(response)

        self.assertEqual('manga club', self.refresh(orga02).name)
        self.assertEqual('anime club', self.refresh(orga03).name)
        self.assertEqual('Genshiken',  self.refresh(orga01).name) # <== not changed

        with self.assertNoException():
            form = response.context['form']

        self.assertEqual(2, form.modified_objects_count)

    def test_use_edit_perm(self):
        self.login(is_superuser=False, allowed_apps=['persons'])

        create_sc = SetCredentials.objects.create
        create_sc(role=self.role,
                  value=SetCredentials.CRED_VIEW | SetCredentials.CRED_DELETE |\
                        SetCredentials.CRED_LINK | SetCredentials.CRED_UNLINK, #no  CRED_CHANGE
                  set_type=SetCredentials.ESET_ALL
                 )
        create_sc(role=self.role,
                  value=SetCredentials.CRED_VIEW | SetCredentials.CRED_CHANGE | SetCredentials.CRED_DELETE |\
                        SetCredentials.CRED_LINK | SetCredentials.CRED_UNLINK,
                  set_type=SetCredentials.ESET_OWN
                 )

        create_orga = Organisation.objects.create
        orga01 = create_orga(user=self.other_user, name='Genshiken')
        orga02 = create_orga(user=self.user,       name='Manga club')

        self.assertFalse(orga01.can_change(self.user)) # <== user cannot change
        self.assertTrue(orga02.can_change(self.user))

        response = self.client.post(self.build_url(Organisation), follow=True,
                                    data={'actions': self.format_str1 % {
                                                            'name':     'name',
                                                            'operator': 'lower',
                                                            'value':    '',
                                                        },
                                         }
                                   )
        self.assertEqual(200, response.status_code)
        self.assertNoFormError(response)

        self.assertEqual('manga club', self.refresh(orga02).name)
        self.assertEqual('Genshiken',  self.refresh(orga01).name) # <== not changed

        self.assertEqual(1, response.context['form'].read_objects_count)

    def test_model_error(self):
        self.login()

        first_name = 'Kanako'
        last_name = 'Ouno'
        contact01 = Contact.objects.create(user=self.user, first_name=first_name,  last_name=last_name)
        contact02 = Contact.objects.create(user=self.user, first_name='Mitsunori', last_name='Kugayama')

        entity_str = unicode(contact01)

        with self.assertRaises(ValidationError) as cm:
            contact01.last_name = ''
            contact01.full_clean()

        response = self.client.post(self.build_url(Contact), follow=True,
                                    data={'actions': self.format_str2 % {
                                                            'name01': 'last_name',  'operator01': 'rm_start', 'value01': 6,
                                                            'name02': 'first_name', 'operator02': 'upper',    'value02': '',
                                                        },
                                         }
                                   )
        self.assertEqual(200, response.status_code)
        self.assertNoFormError(response)

        contact01 = self.refresh(contact01)
        self.assertEqual(last_name,  contact01.last_name) #no change !!
        self.assertEqual(first_name, contact01.first_name) #TODO: make the changes that are possible (u'KANAKO') ??

        form = response.context['form']
        count = Contact.objects.count()
        self.assertLess(form.modified_objects_count, count)
        self.assertEqual(count, form.read_objects_count)

        errors = form.process_errors
        self.assertEqual(1, len(errors))

        error = iter(errors).next()
        self.assertEqual(entity_str, error[0])
        self.assertEqual([u'%s => %s' % (_('Last name'), _(u'This field cannot be blank.'))],
                         error[1]
                        )

    def build_ops_url(self, ct_id, field):
        return '/creme_core/list_view/batch_process/%(ct_id)s/get_ops/%(field)s' % {
                        'ct_id': ct_id,
                        'field': field,
                    }

    def test_get_ops01(self): #unknown CT
        self.login()

        response = self.client.get(self.build_ops_url(ct_id=1216545, field='name'))
        self.assertEqual(404, response.status_code, response.content)

    def test_get_ops02(self):
        self.login()

        ct_id = ContentType.objects.get_for_model(Contact).id
        response = self.client.get(self.build_ops_url(ct_id, 'first_name'))
        self.assertEqual(200, response.status_code, response.content)

        json_data = simplejson.loads(response.content)
        self.assertIsInstance(json_data, list)
        self.assertTrue(json_data)
        self.assertIn(['upper', _('To upper case')], json_data)
        self.assertIn(['lower', _('To lower case')], json_data)
        self.assertNotIn('add_int', (e[0] for e in json_data))

    def test_get_ops03(self): #other CT, other category of operator
        self.login()

        ct_id = ContentType.objects.get_for_model(Organisation).id
        response = self.client.get(self.build_ops_url(ct_id, 'capital'))
        self.assertEqual(200, response.status_code, response.content)

        json_data = simplejson.loads(response.content)
        self.assertIn(['add_int', _('Add')], json_data)
        self.assertIn(['sub_int', _('Subtract')], json_data)
        self.assertNotIn('prefix', (e[0] for e in json_data))

    def test_get_ops04(self): #empty category
        self.login()

        ct_id = ContentType.objects.get_for_model(Contact).id
        response = self.client.get(self.build_ops_url(ct_id, 'image'))
        self.assertEqual(200, response.status_code, response.content)
        self.assertEqual([], simplejson.loads(response.content))

    def test_get_ops05(self): #no app credentials
        self.login(is_superuser=False, allowed_apps=['creme_core']) #not 'persons'

        ct_id = ContentType.objects.get_for_model(Contact).id
        response = self.client.get(self.build_ops_url(ct_id, 'first_name'))
        self.assertEqual(403, response.status_code, response.content)

    def test_get_ops06(self): #unknown field
        self.login()

        ct_id = ContentType.objects.get_for_model(Contact).id
        response = self.client.get(self.build_ops_url(ct_id, 'foobar'))
        self.assertEqual(400, response.status_code, response.content)

    #TODO: custom fields ??
