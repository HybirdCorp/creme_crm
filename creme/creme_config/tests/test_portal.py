from django.urls import reverse

from creme.creme_config.registry import _AppConfigRegistry
from creme.creme_core.tests.base import CremeTestCase
from creme.creme_core.tests.fake_bricks import FakePortalBrick


class PortalTestCase(CremeTestCase):
    def test_portal01(self):
        self.login_as_standard(allowed_apps=['creme_config'])
        response = self.assertGET200(reverse('creme_config__portal'))
        self.assertTemplateUsed(response, 'creme_config/portal.html')

        get = response.context.get
        self.assertEqual(
            reverse('creme_config__reload_portal_bricks'),
            get('bricks_reload_url'),
        )

        app_configs = get('app_configs')
        self.assertIsList(app_configs)
        self.assertIsInstance(app_configs[0], _AppConfigRegistry)
        self.assertIn('creme_core', (r.name for r in app_configs))

        bricks = get('bricks')
        # self.assertIsList(bricks)
        # self.assertIn(FakePortalBrick, [type(brick) for brick in bricks])
        self.assertIsDict(bricks, length=1)
        main_bricks = bricks.get('main')
        self.assertIsList(main_bricks)
        self.assertIn(FakePortalBrick, [type(brick) for brick in main_bricks])

    def test_portal02(self):
        self.login_as_standard()  # allowed_apps=['creme_config']
        self.assertGET403(reverse('creme_config__portal'))

    def test_reload_portal_bricks01(self):
        self.login_as_standard(allowed_apps=['creme_config'])

        brick = FakePortalBrick()
        url = reverse('creme_config__reload_portal_bricks')
        response = self.assertGET200(url, data={'brick_id': brick.id})
        self.assertListEqual(
            [[brick.id, brick.detailview_display({})]],
            response.json(),
        )

        # ---
        self.assertGET404(url, data={'brick_id': 'invalid'})

    def test_reload_portal_bricks02(self):
        self.login_as_standard()  # allowed_apps=['creme_config']

        self.assertGET403(
            reverse('creme_config__reload_portal_bricks'),
            data={'brick_id': FakePortalBrick.id},
        )
