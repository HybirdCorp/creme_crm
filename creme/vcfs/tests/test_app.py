# -*- coding: utf-8 -*-

try:
    from creme.creme_core.tests.base import CremeTestCase
except Exception as e:
    print('Error in <%s>: %s' % (__name__, e))


class VcfsTestCase(CremeTestCase):
    def test_config(self):
        "Should not ne available when creating UserRoles"
        self.login()

        response = self.assertGET200('/creme_config/role/add/')

        with self.assertNoException():
            fields = response.context['form'].fields
            apps_choices  = set(c[0] for c in fields['allowed_apps'].choices)
            admin_choices = set(c[0] for c in fields['admin_4_apps'].choices)

        self.assertIn('creme_core', apps_choices)
        self.assertIn('persons',    apps_choices)
        self.assertNotIn('vcfs',    apps_choices) #<==

        self.assertIn('creme_core', admin_choices)
        self.assertIn('persons',    admin_choices)
        self.assertNotIn('vcfs',    admin_choices) #<==
