# -*- coding: utf-8 -*-

try:
    from django.urls import reverse

    from creme.creme_core.tests.base import CremeTestCase
except Exception as e:
    print('Error in <{}>: {}'.format(__name__, e))


class PortalTestCase(CremeTestCase):
    def test_portal(self):
        self.login()
        self.assertGET200(reverse('creme_config__portal'))
