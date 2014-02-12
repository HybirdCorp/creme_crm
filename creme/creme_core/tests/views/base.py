# -*- coding: utf-8 -*-

try:
    from django.conf import settings

    from django.http import Http404
    from django.utils.translation import ugettext as _
    from django.test.client import RequestFactory

    from ..base import CremeTestCase
    from creme.creme_core.auth.entity_credentials import EntityCredentials
    from creme.creme_core.models import SetCredentials, Language, Currency
    from creme.creme_core.utils import is_testenvironment

    from creme.creme_core.views.testjs import js_testview_or_404

    from creme.persons.models import Contact
except Exception as e:
    print 'Error in <%s>: %s' % (__name__, e)


__all__ = ('ViewsTestCase', 'MiscViewsTestCase', 'LanguageTestCase', 'CurrencyTestCase')


class ViewsTestCase(CremeTestCase):
    def login(self, is_superuser=True, *args, **kwargs):
        super(ViewsTestCase, self).login(is_superuser, *args, **kwargs)

        SetCredentials.objects.create(role=self.role,
                                      value=EntityCredentials.VIEW   |
                                            EntityCredentials.CHANGE |
                                            EntityCredentials.DELETE |
                                            EntityCredentials.LINK   |
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
        response = self.assertGET200('/')
        self.assertTemplateUsed(response, 'creme_core/home.html')

    def test_my_page(self):
        response = self.assertGET200('/my_page')
        self.assertTemplateUsed(response, 'creme_core/my_page.html')

    def test_clean(self):
        #with self.assertNoException():
            #response = self.client.get('/creme_core/clean/', follow=True)

        #self.assertEqual(200, response.status_code)
        #self.assertRedirects(response, '/creme_login/')

        #reverse() forces all views to load & can detect some errors
        #will be useless when test covers all code
        #Problem: it 'artificially' increases coverage rate
        from django.core.urlresolvers import reverse
        with self.assertNoException():
            reverse('creme_logout')

    def test_logout(self):
        self.assertIn('_auth_user_id', self.client.session)
        response = self.assertGET200('/creme_logout/', follow=True)
        self.assertNotIn('_auth_user_id', self.client.session)

        self.assertRedirects(response, '/creme_login/')

    def test_js_view(self):
        factory = RequestFactory()

        request = factory.get('/test_js');
        self.assertFalse(settings.FORCE_JS_TESTVIEW)
        self.assertTrue(is_testenvironment(request));

        with self.assertRaises(Http404):
            js_testview_or_404(request, '', '')

        settings.FORCE_JS_TESTVIEW = True
        self.assertTrue(settings.FORCE_JS_TESTVIEW)
        self.assertTrue(is_testenvironment(request));

        with self.assertRaises(Http404):
            js_testview_or_404(request, '', '')

        request.META['SERVER_NAME'] = 'otherserver'
        self.assertTrue(settings.FORCE_JS_TESTVIEW)
        self.assertFalse(is_testenvironment(request));

        with self.assertNoException():
            js_testview_or_404(request, '', '')

    def test_400_middleware(self):
        response = self.assertGET(400, '/test_http_response?status=400')
        self.assertEqual(response.content, u'<p>Http Response 400</p>')

        response = self.assertGET(400, '/test_http_response?status=400', HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.content, u'XML Http Response 400')

    def test_403_middleware(self):
        response = self.assertGET403('/test_http_response?status=403')
        self.assertContains(response, 'Operation is not allowed', status_code=403)

        response = self.assertGET403('/test_http_response?status=403', HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertContains(response, 'Operation is not allowed', status_code=403)

    def test_404_middleware(self):
        response = self.assertGET404('/test_http_response?status=404')
        self.assertContains(response, _('The page you have requested is unfoundable.'), status_code=404)

        response = self.assertGET404('/test_http_response?status=404', HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertContains(response, 'No such result or unknown url', status_code=404)

    def test_409_middleware(self):
        response = self.assertGET409('/test_http_response?status=409')
        self.assertContains(response, 'Conflicting operation', status_code=409)

        response = self.assertGET(409, '/test_http_response?status=409', HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.content, 'Conflicting operation')

    def test_500_middleware(self):
        with self.assertRaises(Exception):
            self.client.get('/test_http_response?status=500')

        response = self.assertGET(500, '/test_http_response?status=500', HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.content, 'Server internal error')


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


class ExceptionMiddlewareTestCase(ViewsTestCase):
    @classmethod
    def setUpClass(cls):
        cls.populate('creme_core', 'creme_config')

    def setUp(self):
        self.login()
