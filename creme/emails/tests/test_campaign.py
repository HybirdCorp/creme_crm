# -*- coding: utf-8 -*-

try:
    from django.core.urlresolvers import reverse

    from .base import _EmailsTestCase, skipIfCustomEmailCampaign, EmailCampaign
except Exception as e:
    print('Error in <%s>: %s' % (__name__, e))


@skipIfCustomEmailCampaign
class CampaignTestCase(_EmailsTestCase):
    def setUp(self):
        self.login()

    def test_create(self):
        url = reverse('emails__create_campaign')
        self.assertGET200(url)

        name     = 'my_campaign'
        response = self.client.post(url, follow=True,
                                    data={'user': self.user.pk,
                                          'name': name,
                                         }
                                   )
        self.assertNoFormError(response)
        self.get_object_or_fail(EmailCampaign, name=name)

    def test_edit(self):
        name = 'my_campaign'
        camp = EmailCampaign.objects.create(user=self.user, name=name)

        url = camp.get_edit_absolute_url()
        self.assertGET200(url)

        name += '_edited'
        response = self.client.post(url, follow=True,
                                    data={'user': self.user.pk,
                                          'name': name,
                                         }
                                   )
        self.assertNoFormError(response)
        self.assertEqual(name, self.refresh(camp).name)

    def test_listview(self):
        response = self.assertGET200(EmailCampaign.get_lv_absolute_url())

        with self.assertNoException():
            response.context['entities']
