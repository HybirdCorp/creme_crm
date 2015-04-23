# -*- coding: utf-8 -*-

try:
    from creme.creme_core.tests.base import CremeTestCase
except Exception as e:
    print('Error in <%s>: %s' % (__name__, e))


class PortalTestCase(CremeTestCase):
    def test_portal(self):
#        self.populate('creme_core', 'creme_config')
        self.populate('creme_core')
        self.login()
        self.assertGET200('/creme_config/')
