# -*- coding: utf-8 -*-

from django.urls import reverse

from creme.creme_config.registry import _AppConfigRegistry
from creme.creme_core.tests.base import CremeTestCase


class PortalTestCase(CremeTestCase):
    def test_portal01(self):
        self.login(is_superuser=False, allowed_apps=['creme_config'])
        response = self.assertGET200(reverse('creme_config__portal'))
        self.assertTemplateUsed(response, 'creme_config/portal.html')

        get = response.context.get
        self.assertEqual(reverse('creme_core__reload_bricks'), get('bricks_reload_url'))

        app_configs = get('app_configs')
        self.assertIsList(app_configs)
        self.assertIsInstance(app_configs[0], _AppConfigRegistry)
        self.assertIn('creme_core', (r.name for r in app_configs))

        self.assertIsList(get('app_bricks'))  # TODO: test better

    def test_portal02(self):
        self.login(is_superuser=False)  # allowed_apps=['creme_config']
        self.assertGET403(reverse('creme_config__portal'))
