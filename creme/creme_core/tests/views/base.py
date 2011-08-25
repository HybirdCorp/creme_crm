# -*- coding: utf-8 -*-

from django.utils.translation import ugettext as _
from django.utils.encoding import smart_str, force_unicode
from django.contrib.contenttypes.models import ContentType

from creme_core.models import SetCredentials, HeaderFilter, HeaderFilterItem
from creme_core.tests.base import CremeTestCase

from persons.models import Contact


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
    def setUp(self):
        self.populate('creme_core', 'creme_config', 'persons')

    def test_home(self): #TODO: improve test
        self.login()
        self.assertEqual(200, self.client.get('/').status_code)

    def test_my_page(self):
        self.login()
        self.assertEqual(200, self.client.get('/my_page').status_code)

    def test_clean(self):
        self.login()

        try:
            response = self.client.get('/creme_core/clean/', follow=True)
        except Exception, e:
            self.fail(str(e))

        self.assertEqual(200, response.status_code)
        self.assertEqual(2,   len(response.redirect_chain))

        last = response.redirect_chain[-1]
        self.assert_(last[0].endswith('/creme_login/'))
        self.assertEqual(302, last[1])

    def _build_hf_n_contacts(self):
        hf = HeaderFilter.create(pk='test-hf_contact', name='Contact view', model=Contact)
        hfi1 = HeaderFilterItem.build_4_field(model=Contact, name='last_name')
        hfi2 = HeaderFilterItem.build_4_field(model=Contact, name='first_name')
        hf.set_items([hfi1, hfi2])

        for first_name, last_name in [('Spike', 'Spiegel'), ('Jet', 'Black'), ('Faye', 'Valentine'), ('Edward', 'Wong')]:
            Contact.objects.create(user=self.user, first_name=first_name, last_name=last_name)

        return (hfi1, hfi2)

    def test_csv_export01(self): #TODO: test other hfi type...
        self.login()

        ct = ContentType.objects.get_for_model(Contact)
        hfi1, hfi2 = self._build_hf_n_contacts()

        lv_url = Contact.get_lv_absolute_url()
        self.assertEqual(200, self.client.get(lv_url).status_code) #set the current list view state...

        response = self.client.get('/creme_core/list_view/dl_csv/%s' % ct.id, data={'list_url': lv_url})
        self.assertEqual(200, response.status_code)
        self.assertEqual([u'"%s","%s"' % (hfi1.title, hfi2.title), '"Black","Jet"', '"Creme","Fulbert"', '"Spiegel","Spike"', '"Valentine","Faye"', '"Wong","Edward"'],
                         map(force_unicode, response.content.splitlines())
                        )

    def test_csv_export02(self): #export credential
        self.login(is_superuser=False, allowed_apps=['creme_core', 'persons'])
        ct = ContentType.objects.get_for_model(Contact)

        self._build_hf_n_contacts()

        lv_url = Contact.get_lv_absolute_url()
        self.assertEqual(200, self.client.get(lv_url).status_code) #set the current list view state...

        url = '/creme_core/list_view/dl_csv/%s' % ct.id
        data = {'list_url': lv_url}
        self.assertEqual(403, self.client.get(url, data=data).status_code)

        self.role.exportable_ctypes = [ct] # set the export creddential
        self.assertEqual(200, self.client.get(url, data=data).status_code)
