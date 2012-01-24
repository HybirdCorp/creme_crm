# -*- coding: utf-8 -*-

try:
    from django.utils.translation import ugettext as _
    from django.contrib.contenttypes.models import ContentType

    from creme_core.models import EntityFilter, EntityFilterCondition, SetCredentials
    from creme_core.tests.views.base import ViewsTestCase

    from persons.models import Organisation, Contact
except Exception as e:
    print 'Error:', e


__all__ = ('BatchProcessViewsTestCase', )


class BatchProcessViewsTestCase(ViewsTestCase):
    format_str1 = '[{"name": "%(name)s", "operator": "%(operator)s", "value": {"type": "%(operator)s", "value": "%(value)s"}}]'
    format_str2 = '[{"name": "%(name01)s", "operator": "%(operator01)s", "value": {"type": "%(operator01)s", "value": "%(value01)s"}},' \
                  ' {"name": "%(name02)s", "operator": "%(operator02)s", "value": {"type": "%(operator02)s", "value": "%(value02)s"}}]'

    @classmethod
    def setUpClass(cls):
        cls.populate('creme_core', 'creme_config')

    def build_url(self, model):
         return '/creme_core/list_view/batch_process/%s' % ContentType.objects.get_for_model(model).id

    def test_no_app_perm(self):
        self.login(is_superuser=False)
        self.assertEqual(404, self.client.get(self.build_url(Organisation)).status_code)

    def test_app_perm(self):
        self.login(is_superuser=False, allowed_apps=['persons'])
        self.assertEqual(200, self.client.get(self.build_url(Organisation)).status_code)

    def test_batching_upper01(self):
        self.login()
        url = self.build_url(Organisation)
        self.assertEqual(200, self.client.get(url).status_code)

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
        self.assertTrue(response.redirect_chain)
        self.assertEqual(u"http://testserver%s" % Organisation.get_lv_absolute_url(), response.redirect_chain[-1][0])

        self.assertEqual('GENSHIKEN',  self.refresh(orga01).name)
        self.assertEqual('MANGA CLUB', self.refresh(orga02).name)

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
        self.assertTrue(response.redirect_chain)
        self.assertEqual(u"http://testserver%s" % Contact.get_lv_absolute_url(), response.redirect_chain[-1][0])

        self.assertEqual('saki',     self.refresh(contact01).first_name)
        self.assertEqual('harunobu', self.refresh(contact02).first_name)

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

    #TODO: custom fields ??

#Saki Kasukabe
#Harunobu Madarame
#Kanji Sasahara
#Kanako Ōno
#Chika Ogiue
#Mitsunori Kugayama
#Sōichirō Tanaka
#Makoto Kōsaka
#Manabu Kuchiki
