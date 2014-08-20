# -*- coding: utf-8 -*-

try:
    from django.utils.translation import ugettext as _

    from creme.creme_core.tests.base import CremeTestCase

    from creme.creme_config.models import SettingValue, SettingKey

    from ..blocks import mobile_sync_config_block
    from ..constants import *
    from ..utils import is_user_sync_calendars, is_user_sync_contacts
except Exception as e:
    print('Error in <%s>: %s' % (__name__, e))


class GlobalSettingsTestCase(CremeTestCase):
    @classmethod
    def setUpClass(cls):
        cls.populate('creme_core', 'creme_config', 'activesync')

    def test_editview(self):
        self.login()
        url = '/activesync/mobile_synchronization/edit'
        self.assertGET200(url)

        sv_url    = self.get_object_or_fail(SettingValue, key=MAPI_SERVER_URL)
        sv_domain = self.get_object_or_fail(SettingValue, key=MAPI_DOMAIN)
        sv_ssl    = self.get_object_or_fail(SettingValue, key=MAPI_SERVER_SSL)

        server_url = 'http://cremecrm.com/as'
        server_domain = 'creme'
        response = self.client.post(url, data={'url':    server_url,
                                               'domain': server_domain,
                                               'ssl':    'on',
                                              }
                                   )
        self.assertNoFormError(response)

        with self.assertNoException():
            sv_url    = self.refresh(sv_url)
            sv_domain = self.refresh(sv_domain)
            sv_ssl    = self.refresh(sv_ssl)

        self.assertEqual(server_url,    sv_url.value)
        self.assertEqual(server_domain, sv_domain.value)
        self.assertIs(sv_ssl.value, True)

        response = self.assertGET200(url)

        with self.assertNoException():
            form = response.context['form']

        self.assertEqual({'url': server_url, 'domain': server_domain, 'ssl': True},
                         form.initial
                        )

    def test_config_page(self):
        self.login()
        response = self.assertGET200('/creme_config/activesync/portal/')
        self.assertContains(response, ' id="%s"' % mobile_sync_config_block.id_)


class UserSettingsTestCase(CremeTestCase):
    @classmethod
    def setUpClass(cls):
        cls.populate('creme_core', 'creme_config', 'activesync')

    def _assertNoSValue(self, skeys, user):
        self.assertFalse(SettingValue.objects.filter(key__in=skeys, user=user))

    def _build_values_map(self, skeys, user):
        svalues = SettingValue.objects.filter(key__in=skeys, user=user)
        self.assertEqual(len(skeys), len(svalues))

        return {svalue.key_id: svalue.value for svalue in svalues}

    def test_is_user_sync_calendars(self):
        self.login()
        user = self.user

        skey = self.get_object_or_fail(SettingKey, pk=USER_MOBILE_SYNC_ACTIVITIES)
        self.assertEqual(0, SettingValue.objects.filter(key=skey).count())
        self.assertIs(False, is_user_sync_calendars(user))

        SettingValue.objects.create(key=skey, value=True, user=user)
        self.assertTrue(is_user_sync_calendars(user))

    def test_is_user_sync_contacts(self):
        self.login()
        user = self.user

        skey = self.get_object_or_fail(SettingKey, pk=USER_MOBILE_SYNC_CONTACTS)
        self.assertEqual(0, SettingValue.objects.filter(key=skey).count())
        self.assertIs(False, is_user_sync_contacts(user))

        SettingValue.objects.create(key=skey, value=True, user=user)
        self.assertTrue(is_user_sync_contacts(user))

    def test_view(self):
        self.login()
        user = self.user

        skeys = [USER_MOBILE_SYNC_SERVER_URL, USER_MOBILE_SYNC_SERVER_DOMAIN, USER_MOBILE_SYNC_SERVER_SSL,
                 USER_MOBILE_SYNC_SERVER_LOGIN, USER_MOBILE_SYNC_SERVER_PWD,
                 USER_MOBILE_SYNC_ACTIVITIES, USER_MOBILE_SYNC_CONTACTS,
                ]
        self.assertEqual(len(skeys), SettingKey.objects.filter(pk__in=skeys).count())

        url = '/activesync/user_settings'
        response = self.assertGET200(url)

        with self.assertNoException():
            fields = response.context['form'].fields
            url_f    = fields['url']
            domain_f = fields['domain']
            ssl_f    = fields['ssl']
            login_f  = fields['login']
            pwd_f    = fields['password']
            sync_calendars_f = fields['sync_calendars']
            sync_contacts_f  = fields['sync_contacts']

        self.assertIsNone(url_f.initial)
        self.assertIsNone(domain_f.initial)
        self.assertIsNone(ssl_f.initial)
        self.assertIsNone(login_f.initial)
        self.assertIsNone(pwd_f.initial)
        self.assertIsNone(sync_calendars_f.initial)
        self.assertIsNone(sync_contacts_f.initial)

        self._assertNoSValue(skeys, user)
        self._assertNoSValue(skeys, self.other_user)

        server_url = 'http://cremecrm.com/as'
        server_domain = 'creme'
        login = 'fulbert'
        pwd = 'fulbert_pwd'
        response = self.client.post(url, data={'url':            server_url,
                                               'domain':         server_domain,
                                               'ssl':            '1',
                                               'login':          login,
                                               'password':       pwd,
                                               'sync_calendars': '1',
                                               'sync_contacts':  '0',
                                              }
                                   )
        self.assertNoFormError(response)
        self._assertNoSValue(skeys, self.other_user)

        values = self._build_values_map(skeys, user)
        get_val = values.get
        self.assertEqual(server_url,    get_val(USER_MOBILE_SYNC_SERVER_URL))
        self.assertEqual(server_domain, get_val(USER_MOBILE_SYNC_SERVER_DOMAIN))
        self.assertEqual(login,         get_val(USER_MOBILE_SYNC_SERVER_LOGIN))
        self.assertIs(get_val(USER_MOBILE_SYNC_SERVER_SSL), True)
        self.assertIs(get_val(USER_MOBILE_SYNC_ACTIVITIES), True)
        self.assertIs(get_val(USER_MOBILE_SYNC_CONTACTS),   False)

        # Other values --------------------------------------------------------
        response = self.assertGET200(url)

        with self.assertNoException():
            fields = response.context['form'].fields
            url_f    = fields['url']
            domain_f = fields['domain']
            ssl_f    = fields['ssl']
            login_f  = fields['login']
            pwd_f    = fields['password']
            sync_calendars_f = fields['sync_calendars']
            sync_contacts_f  = fields['sync_contacts']

        self.assertEqual(server_url, url_f.initial)
        self.assertEqual(_(u"Let empty to get the default configuration (currently '%s').") % '',
                         url_f.help_text
                        )

        self.assertEqual(server_domain, domain_f.initial)
        self.assertEqual(_(u"Let empty to get the default configuration (currently '%s').") % '',
                         domain_f.help_text
                        )


        self.assertEqual(1, ssl_f.initial)
        self.assertEqual(_(u"Let 'Default' to get the default configuration (currently '%s').") % _('No'),
                         ssl_f.help_text
                        )

        self.assertEqual(login, login_f.initial)
        self.assertEqual(pwd,   pwd_f.initial)
        self.assertEqual(1,     sync_calendars_f.initial)
        self.assertEqual(0,     sync_contacts_f.initial)

        server_url = 'http://cremecrm.fr/as'
        server_domain = 'cremecrm'
        login = 'kirika'
        response = self.client.post(url, data={'url':            server_url,
                                               'domain':         server_domain,
                                               'ssl':            '0',
                                               'login':          login,
                                               'password':       'fulbert_pwd',
                                               'sync_calendars': '0',
                                               'sync_contacts':  '1',
                                              }
                                   )
        self.assertNoFormError(response)

        values = self._build_values_map(skeys, user)
        get_val = values.get
        self.assertEqual(server_url,    get_val(USER_MOBILE_SYNC_SERVER_URL))
        self.assertEqual(server_domain, get_val(USER_MOBILE_SYNC_SERVER_DOMAIN))
        self.assertEqual(login,         get_val(USER_MOBILE_SYNC_SERVER_LOGIN))
        self.assertIs(get_val(USER_MOBILE_SYNC_SERVER_SSL), False)
        self.assertIs(get_val(USER_MOBILE_SYNC_ACTIVITIES), False)
        self.assertIs(get_val(USER_MOBILE_SYNC_CONTACTS),   True)

        # Empty values --------------------------------------------------------
        response = self.client.post(url, data={'ssl':            '',
                                               'sync_calendars': '0',
                                               'sync_contacts':  '0',
                                              }
                                   )
        self.assertNoFormError(response)

        self._assertNoSValue([USER_MOBILE_SYNC_SERVER_URL, USER_MOBILE_SYNC_SERVER_DOMAIN,
                              USER_MOBILE_SYNC_SERVER_LOGIN, USER_MOBILE_SYNC_SERVER_PWD,
                              USER_MOBILE_SYNC_SERVER_SSL,
                             ],
                             user
                            )
        self._build_values_map([USER_MOBILE_SYNC_ACTIVITIES, USER_MOBILE_SYNC_CONTACTS], user)

    def _aux_test_sync_view_error(self, url):
        self.login()

        response = self.client.post('/activesync/user_settings',
                                    data={'url':            url,
                                          'ssl':            '1',
                                          'login':          'fulbert',
                                          'password':       'fulbert',
                                          'sync_calendars': '1',
                                          'sync_contacts':  '1',
                                         }
                                   )

        self.assertGET200('/activesync/sync')
        #TODO: test errors

    def test_sync_view_error01(self):
        self._aux_test_sync_view_error('http://toto.com')

    def test_sync_view_error02(self):
        self._aux_test_sync_view_error('http://invalid.com')
