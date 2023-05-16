from io import BytesIO

from django.conf import settings
from django.http import Http404
from django.test.client import RequestFactory
from django.test.utils import override_settings
from django.urls import reverse
from django.utils.translation import gettext as _
from parameterized import parameterized
from PIL import Image

from creme.creme_core.bricks import HistoryBrick, StatisticsBrick
from creme.creme_core.gui.bricks import Brick
from creme.creme_core.models import (
    BrickHomeLocation,
    Currency,
    FakeContact,
    FakeImage,
    FakeOrganisation,
    Language,
)
from creme.creme_core.utils.media import get_creme_media_url
from creme.creme_core.views.testjs import js_testview_or_404

from .base import ViewsTestCase


class MiscViewsTestCase(ViewsTestCase):
    def setUp(self):
        super().setUp()
        self.FORCE_JS_TESTVIEW = settings.FORCE_JS_TESTVIEW
        settings.FORCE_JS_TESTVIEW = False

    def tearDown(self):
        super().tearDown()
        settings.FORCE_JS_TESTVIEW = self.FORCE_JS_TESTVIEW

    def test_static_media(self):
        response = self.assertGET200(
            get_creme_media_url('chantilly', 'images/add_16.png')
        )

        f = BytesIO(b''.join(response.streaming_content))
        img = Image.open(f)
        self.assertEqual('PNG', img.format)

    @override_settings(SOFTWARE_LABEL='Creme')
    def test_home01(self):
        # self.login()
        self.login_as_root()
        response = self.assertGET200(reverse('creme_core__home'))
        self.assertTemplateUsed(response, 'creme_core/home.html')

        context = response.context
        self.assertEqual(
            reverse('creme_core__reload_home_bricks'),
            context.get('bricks_reload_url'),
        )

        bricks = context.get('bricks')
        self.assertIsList(bricks, min_length=2)
        self.assertIsInstance(bricks[0], Brick)

        # brick_ids = [b.id_ for b in bricks]
        brick_ids = [b.id for b in bricks]
        # i1 = self.assertIndex(StatisticsBrick.id_, brick_ids)
        i1 = self.assertIndex(StatisticsBrick.id, brick_ids)
        # i2 = self.assertIndex(HistoryBrick.id_,    brick_ids)
        i2 = self.assertIndex(HistoryBrick.id,    brick_ids)
        self.assertLess(i1, i2)

        self.assertContains(response, _('Home') + ' - Creme', html=True)

    @override_settings(SOFTWARE_LABEL='My CRM')
    def test_home02(self):
        "Superuser bricks configuration."
        # self.login()
        self.login_as_root()

        # brick_id = StatisticsBrick.id_
        brick_id = StatisticsBrick.id
        BrickHomeLocation.objects.create(brick_id=brick_id, superuser=True, order=1)

        # Should not be used
        # BrickHomeLocation.objects.create(brick_id=HistoryBrick.id_, role=self.role, order=1)
        BrickHomeLocation.objects.create(
            brick_id=HistoryBrick.id, role=self.create_role(), order=1,
        )

        response = self.assertGET200(reverse('creme_core__home'))
        bricks = response.context.get('bricks')
        self.assertEqual(len(bricks), 1)

        brick = bricks[0]
        self.assertIsInstance(brick, StatisticsBrick)
        # self.assertEqual(brick_id, brick.id_)
        self.assertEqual(brick_id, brick.id)

        self.assertContains(response, _('Home') + ' - My CRM', html=True)

    def test_home03(self):
        "Superuser bricks configuration"
        # self.login(is_superuser=False)
        user = self.login_as_standard()
        role2 = self.create_role(name='Viewer')

        # brick_id = StatisticsBrick.id_
        brick_id = StatisticsBrick.id
        create_hbl = BrickHomeLocation.objects.create
        create_hbl(brick_id=brick_id, role=user.role, order=1)

        # Should not be used
        # create_hbl(brick_id=HistoryBrick.id_, superuser=True, order=1)
        create_hbl(brick_id=HistoryBrick.id, superuser=True, order=1)
        # create_hbl(brick_id=HistoryBrick.id_, role=role2,     order=1)
        create_hbl(brick_id=HistoryBrick.id, role=role2,     order=1)

        response = self.assertGET200(reverse('creme_core__home'))
        bricks = response.context.get('bricks')
        self.assertEqual(len(bricks), 1)

        brick = bricks[0]
        self.assertIsInstance(brick, StatisticsBrick)
        # self.assertEqual(brick_id, brick.id_)
        self.assertEqual(brick_id, brick.id)

    def test_my_page(self):
        # self.login()
        self.login_as_root()
        response = self.assertGET200('/my_page')
        self.assertTemplateUsed(response, 'creme_core/my_page.html')

        context = response.context
        self.assertEqual(
            reverse('creme_core__reload_home_bricks'),
            context.get('bricks_reload_url'),
        )

        bricks = context.get('bricks')
        self.assertIsList(bricks)
        self.assertIn(HistoryBrick, {b.__class__ for b in bricks})

    def test_about(self):
        # self.login()
        self.login_as_root()
        response = self.assertGET200('/creme_about')
        self.assertTemplateUsed(response, 'about/about.html')

    def test_logout(self):
        # self.login()
        self.login_as_root()

        self.assertIn('_auth_user_id', self.client.session)
        # response = self.assertGET200(reverse('creme_logout'), follow=True)
        # TODO: with django5.0, test GET does not work
        response = self.assertPOST200(reverse('creme_logout'), follow=True)
        self.assertNotIn('_auth_user_id', self.client.session)

        self.assertRedirects(response, reverse(settings.LOGIN_URL))

    def test_js_view(self):
        # self.login()
        self.login_as_root()
        factory = RequestFactory()

        request = factory.get('/test_js')
        self.assertFalse(settings.FORCE_JS_TESTVIEW)

        with self.assertRaises(Http404):
            js_testview_or_404('', '')

        settings.FORCE_JS_TESTVIEW = True
        self.assertTrue(settings.FORCE_JS_TESTVIEW)

        request.META['SERVER_NAME'] = 'otherserver'
        self.assertTrue(settings.FORCE_JS_TESTVIEW)

    def test_js_widget_view_home__disabled(self):
        # self.login()
        self.login_as_root()

        response = self.assertGET404(reverse('creme_core__test_widget_home'))

        self.assertContains(
            response,
            "This is view is only reachable during javascript debug.",
            status_code=404
        )

    @override_settings(FORCE_JS_TESTVIEW=True, TESTS_ON=False)
    def test_js_widget_view_home(self):
        # self.login()
        self.login_as_root()
        self.assertGET200(reverse('creme_core__test_widget_home'))

    @parameterized.expand([
        'actions',
        'blocklist',
        'checklistselect',
        'select2',
        'combobox',
        'editor',
        'entityselector',
        'filterselector',
        'frame',
        'jqplot',
        'layout',
        'listview',
        'model',
        'plotselector',
        'polymorphicselector',
        'popover',
        'scrollactivator',
        'toggle',
    ])
    @override_settings(FORCE_JS_TESTVIEW=True, TESTS_ON=False)
    def test_js_widget_views(self, widget):
        # self.login()
        self.login_as_root()
        self.assertGET200(reverse('creme_core__test_widget', args=(widget,)))

    def test_400_middleware(self):
        # self.login()
        self.login_as_root()
        response = self.assertGET(400, '/test_http_response?status=400')
        self.assertEqual(response.content, b'<p>Http Response 400</p>')

        response = self.assertGET(
            # 400, '/test_http_response?status=400', HTTP_X_REQUESTED_WITH='XMLHttpRequest',
            400, '/test_http_response?status=400', headers={'X-Requested-With': 'XMLHttpRequest'},
        )
        self.assertEqual(response.content, b'XML Http Response 400')

    def test_403_middleware(self):
        # self.login()
        self.login_as_root()
        response = self.assertGET403('/test_http_response?status=403')
        self.assertContains(response, 'Tests: operation is not allowed', status_code=403)

        response = self.assertGET403(
            # '/test_http_response?status=403', HTTP_X_REQUESTED_WITH='XMLHttpRequest',
            '/test_http_response?status=403', headers={'X-Requested-With': 'XMLHttpRequest'},
        )
        self.assertContains(response, 'Tests: operation is not allowed', status_code=403)

    def test_404_middleware(self):
        # self.login()
        self.login_as_root()
        response = self.assertGET404('/test_http_response?status=404')
        self.assertContains(
            response,
            _('The page you have requested is not found.'),
            status_code=404,
        )

        response = self.assertGET404(
            # '/test_http_response?status=404', HTTP_X_REQUESTED_WITH='XMLHttpRequest',
            '/test_http_response?status=404', headers={'X-Requested-With': 'XMLHttpRequest'},
        )
        self.assertContains(response, 'Tests: no such result or unknown url', status_code=404)

    def test_409_middleware(self):
        # self.login()
        self.login_as_root()
        response = self.assertGET409('/test_http_response?status=409')
        self.assertContains(response, 'Tests: conflicting operation', status_code=409)

        response = self.assertGET(
            # 409, '/test_http_response?status=409', HTTP_X_REQUESTED_WITH='XMLHttpRequest',
            409, '/test_http_response?status=409', headers={'X-Requested-With': 'XMLHttpRequest'},
        )
        self.assertEqual(response.content, b'Tests: conflicting operation')

    def test_500_middleware(self):
        # self.login()
        self.login_as_root()

        with self.assertRaises(Exception):
            self.client.get('/test_http_response?status=500')

        response = self.assertGET(
            # 500, '/test_http_response?status=500', HTTP_X_REQUESTED_WITH='XMLHttpRequest',
            500, '/test_http_response?status=500', headers={'X-Requested-With': 'XMLHttpRequest'},
        )
        self.assertEqual(response.content, b'Tests: server internal error')

    def test_auth_decorators01(self):
        # self.login(
        self.login_as_standard(
            # is_superuser=False,
            allowed_apps=['documents'],  # Not 'creme_core'
            creatable_models=[FakeContact],
        )
        self.assertGET403('/tests/contact/add')

    def test_auth_decorators02(self):
        # self.login(
        self.login_as_standard(
            # is_superuser=False,
            allowed_apps=['creme_core'],
            creatable_models=[FakeImage],  # Not FakeContact
        )
        self.assertGET403('/tests/contact/add')

    def test_auth_decorators03(self):
        # self.login(
        self.login_as_standard(
            # is_superuser=False,
            allowed_apps=['creme_core'],
            creatable_models=[FakeContact],
        )
        self.assertGET200('/tests/contact/add')

    def test_auth_decorators_multiperm01(self):
        # self.login(
        self.login_as_standard(
            # is_superuser=False,
            allowed_apps=['documents'],  # Not 'creme_core'
            creatable_models=[FakeOrganisation],
        )
        self.assertGET403('/tests/organisation/add')

    def test_auth_decorators_multiperm02(self):
        # self.login(
        self.login_as_standard(
            # is_superuser=False,
            allowed_apps=['creme_core'],
            creatable_models=[FakeImage],  # Not FakeOrganisation
        )
        self.assertGET403('/tests/organisation/add')

    def test_auth_decorators_multiperm03(self):
        # self.login(
        self.login_as_standard(
            # is_superuser=False,
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
    def setUp(self):
        super().setUp()
        # self.login()
        self.login_as_root()

    def test_portal(self):
        self.assertGET200(
            reverse('creme_config__model_portal', args=('creme_core', 'language'))
        )

    def test_create(self):
        url = reverse('creme_config__create_instance', args=('creme_core', 'language'))
        self.assertGET200(url)

        name = 'Klingon'
        # code = 'KLN'
        response = self.assertPOST200(url, data={'name': name})  # 'code': code
        self.assertNoFormError(response)

        self.get_object_or_fail(Language, name=name)  # code=code

    def test_edit(self):
        name = 'klingon'
        # code = 'KLGN'
        language = Language.objects.create(name=name)  # code=code

        url = reverse(
            'creme_config__edit_instance',
            args=('creme_core', 'language', language.id),
        )
        self.assertGET200(url)

        name = name.title()
        self.assertNoFormError(self.client.post(url, data={'name': name}))
        self.assertEqual(name, self.refresh(language).name)

    def test_delete(self):
        language = Language.objects.create(name='Klingon')

        response = self.client.post(
            reverse(
                'creme_config__delete_instance',
                args=('creme_core', 'language', language.id),
            ),
        )
        self.assertNoFormError(response)

        job = self.get_deletion_command_or_fail(Language).job
        job.type.execute(job)
        self.assertDoesNotExist(language)


class CurrencyTestCase(ViewsTestCase):
    def setUp(self):
        super().setUp()
        # self.login()
        self.login_as_root()

    def test_portal(self):
        self.assertGET200(
            reverse('creme_config__model_portal', args=('creme_core', 'currency'))
        )

    def test_create(self):
        url = reverse('creme_config__create_instance', args=('creme_core', 'currency'))
        self.assertGET200(url)

        name = 'Berry'
        local_symbol = 'B'
        international_symbol = 'BRY'
        response = self.client.post(
            url,
            data={
                'name':                 name,
                'local_symbol':         local_symbol,
                'international_symbol': international_symbol,
            },
        )
        self.assertNoFormError(response)
        self.get_object_or_fail(
            Currency,
            name=name,
            local_symbol=local_symbol,
            international_symbol=international_symbol,
        )

    def test_edit(self):
        name = 'berry'
        local_symbol = 'b'
        international_symbol = 'bry'
        currency = Currency.objects.create(
            name=name, local_symbol=local_symbol,
            international_symbol=international_symbol,
        )

        url = reverse(
            'creme_config__edit_instance',
            args=('creme_core', 'currency', currency.id),
        )
        self.assertGET200(url)

        name = name.title()
        local_symbol = local_symbol.upper()
        international_symbol = international_symbol.upper()
        response = self.client.post(
            url,
            data={
                'name':                 name,
                'local_symbol':         local_symbol,
                'international_symbol': international_symbol,
            },
        )
        self.assertNoFormError(response)

        currency = self.refresh(currency)
        self.assertEqual(name,                 currency.name)
        self.assertEqual(local_symbol,         currency.local_symbol)
        self.assertEqual(international_symbol, currency.international_symbol)

    def test_delete(self):
        currency = Currency.objects.create(
            name='Berry', local_symbol='B', international_symbol='BRY',
        )
        response = self.client.post(
            reverse(
                'creme_config__delete_instance',
                args=('creme_core', 'currency', currency.id),
            ),
        )
        self.assertNoFormError(response)

        job = self.get_deletion_command_or_fail(Currency).job
        job.type.execute(job)
        self.assertDoesNotExist(currency)
