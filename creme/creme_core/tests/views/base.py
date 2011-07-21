# -*- coding: utf-8 -*-

from django.contrib.contenttypes.models import ContentType

from creme_core.models import SetCredentials
from creme_core.models.header_filter import HeaderFilter, HeaderFilterItem, HFI_FIELD
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

    def test_csv_export(self): #TODO: test other hfi type...
        self.login()

        ct = ContentType.objects.get_for_model(Contact)
        hf = HeaderFilter.objects.create(id='test-hf_contact', name='Contact view', entity_type=ct)
        create_hfi = HeaderFilterItem.objects.create
        create_hfi(id='test-hfi_lastname',  order=1, name='last_name',  title='Last name',  type=HFI_FIELD, header_filter=hf, has_a_filter=True, editable=True, filter_string="last_name__icontains")
        create_hfi(id='test-hfi_firstname', order=2, name='first_name', title='First name', type=HFI_FIELD, header_filter=hf, has_a_filter=True, editable=True, filter_string="first_name__icontains")

        for first_name, last_name in [('Spike', 'Spiegel'), ('Jet', 'Black'), ('Faye', 'Valentine'), ('Edward', 'Wong')]:
            Contact.objects.create(user=self.user, first_name=first_name, last_name=last_name)

        lv_url = Contact.get_lv_absolute_url()
        self.assertEqual(200, self.client.get(lv_url).status_code) #set the current list view state...

        response = self.client.get('/creme_core/list_view/dl_csv/%s' % ct.id, data={'list_url': lv_url})
        self.assertEqual(200, response.status_code)
        self.assertEqual(['"Last name","First name"', '"Black","Jet"', '"Spiegel","Spike"', '"Valentine","Faye"', '"Wong","Edward"'],
                         response.content.splitlines()
                        )
