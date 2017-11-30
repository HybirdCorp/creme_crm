# -*- coding: utf-8 -*-

try:
    from django.conf import settings
    from django.core.urlresolvers import reverse
    from django.http import Http404
    from django.utils.translation import ugettext as _
    from django.test.client import RequestFactory

    from ..fake_models import FakeContact, FakeImage, FakeOrganisation
    from creme.creme_core.models import Language, Currency
    from creme.creme_core.utils import is_testenvironment

    from creme.creme_core.views.testjs import js_testview_or_404
    from .base import ViewsTestCase
except Exception as e:
    print('Error in <%s>: %s' % (__name__, e))


class MiscViewsTestCase(ViewsTestCase):
    # @classmethod
    # def setUpClass(cls):
    #     ViewsTestCase.setUpClass()
    #     cls.populate()

    def setUp(self):
        super(MiscViewsTestCase, self).setUp()

        self.FORCE_JS_TESTVIEW = settings.FORCE_JS_TESTVIEW
        settings.FORCE_JS_TESTVIEW = False

    def tearDown(self):
        super(MiscViewsTestCase, self).tearDown()
        settings.FORCE_JS_TESTVIEW = self.FORCE_JS_TESTVIEW

    def test_home(self):  # TODO: improve test
        self.login()
        response = self.assertGET200('/')
        self.assertTemplateUsed(response, 'creme_core/home.html')

    def test_my_page(self):
        self.login()
        response = self.assertGET200('/my_page')
        self.assertTemplateUsed(response, 'creme_core/my_page.html')

    def test_logout(self):
        self.login()

        self.assertIn('_auth_user_id', self.client.session)
        response = self.assertGET200('/creme_logout/', follow=True)
        self.assertNotIn('_auth_user_id', self.client.session)

        self.assertRedirects(response, '/creme_login/')

    def test_js_view(self):
        self.login()
        factory = RequestFactory()

        request = factory.get('/test_js')
        self.assertFalse(settings.FORCE_JS_TESTVIEW)
        self.assertTrue(is_testenvironment(request))

        with self.assertRaises(Http404):
        #     js_testview_or_404(request, '', '')
            js_testview_or_404('', '')

        settings.FORCE_JS_TESTVIEW = True
        self.assertTrue(settings.FORCE_JS_TESTVIEW)
        self.assertTrue(is_testenvironment(request))

        # with self.assertRaises(Http404):
        #     js_testview_or_404(request, '', '')

        request.META['SERVER_NAME'] = 'otherserver'
        self.assertTrue(settings.FORCE_JS_TESTVIEW)
        self.assertFalse(is_testenvironment(request))

        # with self.assertNoException():
        #     js_testview_or_404(request, '', '')

    def test_400_middleware(self):
        self.login()
        response = self.assertGET(400, '/test_http_response?status=400')
        self.assertEqual(response.content, u'<p>Http Response 400</p>')

        response = self.assertGET(400, '/test_http_response?status=400', HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.content, u'XML Http Response 400')

    def test_403_middleware(self):
        self.login()
        response = self.assertGET403('/test_http_response?status=403')
        self.assertContains(response, 'Tests: operation is not allowed', status_code=403)

        response = self.assertGET403('/test_http_response?status=403', HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertContains(response, 'Tests: operation is not allowed', status_code=403)

    def test_404_middleware(self):
        self.login()
        response = self.assertGET404('/test_http_response?status=404')
        self.assertContains(response, _(u'The page you have requested is not found.'), status_code=404)

        response = self.assertGET404('/test_http_response?status=404', HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertContains(response, 'Tests: no such result or unknown url', status_code=404)

    def test_409_middleware(self):
        self.login()
        response = self.assertGET409('/test_http_response?status=409')
        self.assertContains(response, 'Tests: conflicting operation', status_code=409)

        response = self.assertGET(409, '/test_http_response?status=409', HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.content, 'Tests: conflicting operation')

    def test_500_middleware(self):
        self.login()

        with self.assertRaises(Exception):
            self.client.get('/test_http_response?status=500')

        response = self.assertGET(500, '/test_http_response?status=500', HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.content, 'Tests: server internal error')

    def test_auth_decorators01(self):
        self.login(is_superuser=False,
                   allowed_apps=['documents'],  # Not 'creme_core'
                   creatable_models=[FakeContact],
                  )
        self.assertGET403('/tests/contact/add')

    def test_auth_decorators02(self):
        self.login(is_superuser=False,
                   allowed_apps=['creme_core'],
                   creatable_models=[FakeImage],  # Not FakeContact
                  )
        self.assertGET403('/tests/contact/add')

    def test_auth_decorators03(self):
        self.login(is_superuser=False,
                   allowed_apps=['creme_core'],
                   creatable_models=[FakeContact],
                  )
        self.assertGET200('/tests/contact/add')

    def test_auth_decorators_multiperm01(self):
        self.login(is_superuser=False,
                   allowed_apps=['documents'],  # Not 'creme_core'
                   creatable_models=[FakeOrganisation],
                  )
        self.assertGET403('/tests/organisation/add')

    def test_auth_decorators_multiperm02(self):
        self.login(is_superuser=False,
                   allowed_apps=['creme_core'],
                   creatable_models=[FakeImage],  # Not FakeOrganisation
                  )
        self.assertGET403('/tests/organisation/add')

    def test_auth_decorators_multiperm03(self):
        self.login(is_superuser=False,
                   allowed_apps=['creme_core'],
                   creatable_models=[FakeOrganisation],
                  )
        self.assertGET200('/tests/organisation/add')

    def test_utils_build_cancel_path(self):
        from creme.creme_core.views.utils import build_cancel_path

        factory = RequestFactory()
        path = '/foobar'

        # -------------------------
        request = factory.get('/')
        self.assertIsNone(build_cancel_path(request))

        # -------------------------
        request = factory.get('/')
        request.META['HTTP_REFERER'] = 'http://testserver' + path
        self.assertEqual(path, build_cancel_path(request))

        # -------------------------
        request.META['HTTP_REFERER'] = 'http://otherserver' + path
        self.assertIsNone(build_cancel_path(request))

        # -------------------------
        request.META['HTTP_REFERER'] = 'http://testserver:8005' + path
        self.assertIsNone(build_cancel_path(request))

        # -------------------------
        request.META['HTTP_REFERER'] = 'http://testserver:80' + path
        self.assertEqual(path, build_cancel_path(request))

        # -------------------------
        request.META['HTTP_REFERER'] = 'https://testserver' + path
        self.assertIsNone(build_cancel_path(request))

        # -------------------------
        request.get_host = lambda: 'testserver:8005'
        request.META['HTTP_REFERER'] = 'http://testserver:8005' + path
        self.assertEqual(path, build_cancel_path(request))


class LanguageTestCase(ViewsTestCase):
    # @classmethod
    # def setUpClass(cls):
    #     ViewsTestCase.setUpClass()
    #     cls.populate('creme_core')

    def setUp(self):
        self.login()

    def test_portal(self):
        # self.assertGET200('/creme_config/creme_core/language/portal/')
        self.assertGET200(reverse('creme_config__model_portal', args=('creme_core', 'language')))

    def test_create(self):
        # url = '/creme_config/creme_core/language/add/'
        url = reverse('creme_config__create_instance', args=('creme_core', 'language'))
        self.assertGET200(url)

        name = 'Klingon'
        code = 'KLN'
        response = self.assertPOST200(url, data={'name': name, 'code': code})
        self.assertNoFormError(response)

        self.get_object_or_fail(Language, name=name, code=code)

    def test_edit(self):
        name = 'klingon'
        code = 'KLGN'
        language = Language.objects.create(name=name, code=code)

        # url = '/creme_config/creme_core/language/edit/%s' % language.id
        url = reverse('creme_config__edit_instance', args=('creme_core', 'language', language.id))
        self.assertGET200(url)

        name = name.title()
        code = 'KLN'
        response = self.assertPOST200(url, data={'name': name, 'code': code})
        self.assertNoFormError(response)

        language = self.refresh(language)
        self.assertEqual(name, language.name)
        self.assertEqual(code, language.code)

    def test_delete(self):
        language = Language.objects.create(name='Klingon', code='KLN')

        # self.assertPOST200('/creme_config/creme_core/language/delete',
        self.assertPOST200(reverse('creme_config__delete_instance', args=('creme_core', 'language')),
                           data={'id': language.id}
                          )
        self.assertDoesNotExist(language)


class CurrencyTestCase(ViewsTestCase):
    # @classmethod
    # def setUpClass(cls):
    #     ViewsTestCase.setUpClass()
    #     cls.populate('creme_core')

    def setUp(self):
        self.login()

    def test_portal(self):
        # self.assertGET200('/creme_config/creme_core/currency/portal/')
        self.assertGET200(reverse('creme_config__model_portal', args=('creme_core', 'currency')))

    def test_create(self):
        # url = '/creme_config/creme_core/currency/add/'
        url = reverse('creme_config__create_instance', args=('creme_core', 'currency'))
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

        # url = '/creme_config/creme_core/currency/edit/%s' % currency.id
        url = reverse('creme_config__edit_instance', args=('creme_core', 'currency', currency.id))
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
        # self.assertPOST200('/creme_config/creme_core/currency/delete',
        self.assertPOST200(reverse('creme_config__delete_instance', args=('creme_core', 'currency')),
                           data={'id': currency.id}
                          )
        self.assertDoesNotExist(currency)
