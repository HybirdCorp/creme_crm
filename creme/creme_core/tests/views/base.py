# -*- coding: utf-8 -*-

try:
    from creme_core.models import SetCredentials
    from creme_core.tests.base import CremeTestCase
except Exception as e:
    print 'Error in <%s>: %s' % (__name__, e)


__all__ = ('ViewsTestCase', 'MiscViewsTestCase')


class ViewsTestCase(CremeTestCase):
    def login(self, is_superuser=True, *args, **kwargs):
        super(ViewsTestCase, self).login(is_superuser, *args, **kwargs)

        SetCredentials.objects.create(role=self.role,
                                      value=SetCredentials.CRED_VIEW   | \
                                            SetCredentials.CRED_CHANGE | \
                                            SetCredentials.CRED_DELETE | \
                                            SetCredentials.CRED_LINK   | \
                                            SetCredentials.CRED_UNLINK,
                                      set_type=SetCredentials.ESET_OWN
                                     )

    def _set_all_creds_except_one(self, excluded): #TODO: in CremeTestCase ?
        value = SetCredentials.CRED_NONE

        for cred in (SetCredentials.CRED_VIEW, SetCredentials.CRED_CHANGE,
                     SetCredentials.CRED_DELETE, SetCredentials.CRED_LINK,
                     SetCredentials.CRED_UNLINK):
            if cred != excluded:
                value |= cred

        SetCredentials.objects.create(role=self.user.role,
                                      value=value,
                                      set_type=SetCredentials.ESET_ALL)


class MiscViewsTestCase(ViewsTestCase):
    #@classmethod
    #def setUpClass(cls):
        #cls.populate()

    #def setUp(self):
        #self.populate('creme_core', 'creme_config')
        #self.login()

    def test_home(self): #TODO: improve test
        self.populate('creme_core', 'creme_config')
        self.login()
        self.assertEqual(200, self.client.get('/').status_code)

    def test_my_page(self):
        self.populate('creme_core', 'creme_config')
        self.login()
        self.assertEqual(200, self.client.get('/my_page').status_code)

    def test_clean(self):
        self.populate()
        self.login()

        with self.assertNoException():
            response = self.client.get('/creme_core/clean/', follow=True)

        self.assertEqual(200, response.status_code)
        self.assertEqual(2,   len(response.redirect_chain))

        last = response.redirect_chain[-1]
        self.assertTrue(last[0].endswith('/creme_login/'))
        self.assertEqual(302, last[1])
