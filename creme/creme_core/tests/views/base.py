# -*- coding: utf-8 -*-

try:
    from django.conf import settings

    from creme_core.tests.base import CremeTestCase
    from creme_core.auth.entity_credentials import EntityCredentials
    from creme_core.models import SetCredentials, Language, Currency

    from persons.models import Contact
except Exception as e:
    print 'Error in <%s>: %s' % (__name__, e)


__all__ = ('ViewsTestCase', 'MiscViewsTestCase', 'LanguageTestCase', 'CurrencyTestCase')


class ViewsTestCase(CremeTestCase):
    def login(self, is_superuser=True, *args, **kwargs):
        super(ViewsTestCase, self).login(is_superuser, *args, **kwargs)

        SetCredentials.objects.create(role=self.role,
                                      value=EntityCredentials.VIEW   | \
                                            EntityCredentials.CHANGE | \
                                            EntityCredentials.DELETE | \
                                            EntityCredentials.LINK   | \
                                            EntityCredentials.UNLINK,
                                      set_type=SetCredentials.ESET_OWN
                                     )

    def _set_all_creds_except_one(self, excluded): #TODO: in CremeTestCase ?
        value = EntityCredentials.NONE

        for cred in (EntityCredentials.VIEW, EntityCredentials.CHANGE,
                     EntityCredentials.DELETE, EntityCredentials.LINK,
                     EntityCredentials.UNLINK):
            if cred != excluded:
                value |= cred

        SetCredentials.objects.create(role=self.user.role, value=value,
                                      set_type=SetCredentials.ESET_ALL
                                     )


class MiscViewsTestCase(ViewsTestCase):
    @classmethod
    def setUpClass(cls):
        cls.populate()

    def setUp(self):
        #self.populate('creme_core', 'creme_config')
        self.login()
        
        self.FORCE_JS_TESTVIEW = settings.FORCE_JS_TESTVIEW
        settings.FORCE_JS_TESTVIEW = False

        user = self.user
        Contact.objects.create(user=user, is_user=user,
                               first_name='Fulbert', last_name='Creme'
                              ) #TODO: move into login()

    def tearDown(self):
        settings.FORCE_JS_TESTVIEW = self.FORCE_JS_TESTVIEW

    def test_home(self): #TODO: improve test
        #self.populate('creme_core', 'creme_config')
        #self.login()
        self.assertEqual(200, self.client.get('/').status_code)

    def test_my_page(self):
        #self.populate('creme_core', 'creme_config')
        #self.login()
        self.assertEqual(200, self.client.get('/my_page').status_code)

    def test_clean(self):
        #self.populate()
        #self.login()

        with self.assertNoException():
            response = self.client.get('/creme_core/clean/', follow=True)

        self.assertEqual(200, response.status_code)
        self.assertEqual(2,   len(response.redirect_chain))

        last = response.redirect_chain[-1]
        self.assertTrue(last[0].endswith('/creme_login/'))
        self.assertEqual(302, last[1])

    def test_js_view(self):
        self.assertFalse(settings.FORCE_JS_TESTVIEW)
        self.assertEqual(200, self.client.get('/test_js').status_code)


class LanguageTestCase(ViewsTestCase):
    @classmethod
    def setUpClass(cls):
        cls.populate('creme_core', 'creme_config')

    def setUp(self):
        self.login()

    def test_portal(self):
        self.assertEqual(200, self.client.get('/creme_config/creme_core/language/portal/').status_code)

    def test_create(self):
        url = '/creme_config/creme_core/language/add/'
        self.assertEqual(200, self.client.get(url).status_code)

        name = 'Klingon'
        code = 'KLN'
        response = self.client.post(url, data={'name': name, 'code': code})
        self.assertEqual(200, response.status_code)
        self.assertNoFormError(response)

        self.get_object_or_fail(Language, name=name, code=code)

    def test_edit(self):
        name = 'klingon'
        code = 'KLGN'
        language = Language.objects.create(name=name, code=code)

        url = '/creme_config/creme_core/language/edit/%s' % language.id
        self.assertEqual(200, self.client.get(url).status_code)

        name = name.title()
        code = 'KLN'
        response = self.client.post(url, data={'name': name, 'code': code})
        self.assertEqual(200, response.status_code)
        self.assertNoFormError(response)

        language = self.refresh(language)
        self.assertEqual(name, language.name)
        self.assertEqual(code, language.code)

    def test_delete(self):
        language = Language.objects.create(name='Klingon', code='KLN')

        response = self.client.post('/creme_config/creme_core/language/delete',
                                    data={'id': language.id}
                                   )
        self.assertEqual(200, response.status_code)
        self.assertFalse(Language.objects.filter(pk=language.pk).exists())


class CurrencyTestCase(ViewsTestCase):
    @classmethod
    def setUpClass(cls):
        cls.populate('creme_core', 'creme_config')

    def setUp(self):
        self.login()

    def test_portal(self):
        self.assertGET200('/creme_config/creme_core/currency/portal/')

    def test_create(self):
        url = '/creme_config/creme_core/currency/add/'
        self.assertGET200(url)

        name = 'Berry'
        local_symbol = 'B'
        international_symbol = 'BRY'
        response = self.client.post(url,
                                    data={'name':                 name,
                                          'local_symbol':         local_symbol,
                                          'international_symbol': international_symbol,
                                         }
                                   )
        self.assertNoFormError(response)

        self.get_object_or_fail(Currency, name=name, local_symbol=local_symbol,
                                international_symbol=international_symbol
                               )

    def test_edit(self):
        name = 'berry'
        local_symbol = 'b'
        international_symbol = 'bry'
        currency = Currency.objects.create(name=name, local_symbol=local_symbol,
                                           international_symbol=international_symbol
                                          )

        url = '/creme_config/creme_core/currency/edit/%s' % currency.id
        self.assertGET200(url)

        name = name.title()
        local_symbol = local_symbol.upper()
        international_symbol = international_symbol.upper()
        response = self.client.post(url,
                                    data={'name':                 name,
                                          'local_symbol':         local_symbol,
                                          'international_symbol': international_symbol,
                                         }
                                   )
        self.assertNoFormError(response)

        currency = self.refresh(currency)
        self.assertEqual(name,                 currency.name)
        self.assertEqual(local_symbol,         currency.local_symbol)
        self.assertEqual(international_symbol, currency.international_symbol)

    def test_delete(self):
        currency = Currency.objects.create(name='Berry', local_symbol='B',
                                           international_symbol='BRY'
                                          )

        self.assertPOST200('/creme_config/creme_core/currency/delete',
                           data={'id': currency.id}
                          )
        self.assertFalse(Currency.objects.filter(pk=currency.pk).exists())
