# -*- coding: utf-8 -*-

try:
    from creme_core.tests.base import CremeTestCase
except Exception as e:
    print 'Error in <%s>: %s' % (__name__, e)


__all__ = ('PortalTestCase',)


class PortalTestCase(CremeTestCase):
    def test_portal(self):
        self.populate('creme_core', 'creme_config')
        self.login()
        self.assertGET200('/creme_config/')
