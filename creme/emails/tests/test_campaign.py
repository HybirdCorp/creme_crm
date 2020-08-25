# -*- coding: utf-8 -*-

from django.urls import reverse

from .base import EmailCampaign, _EmailsTestCase, skipIfCustomEmailCampaign


@skipIfCustomEmailCampaign
class CampaignTestCase(_EmailsTestCase):
    def setUp(self):
        super().setUp()
        self.login()

    def test_create(self):
        url = reverse('emails__create_campaign')
        self.assertGET200(url)

        name = 'my_campaign'
        response = self.client.post(
            url, follow=True,
            data={
                'user': self.user.pk,
                'name': name,
            },
        )
        self.assertNoFormError(response)
        self.get_object_or_fail(EmailCampaign, name=name)

    def test_edit(self):
        name = 'my_campaign'
        camp = EmailCampaign.objects.create(user=self.user, name=name)

        url = camp.get_edit_absolute_url()
        self.assertGET200(url)

        name += '_edited'
        response = self.client.post(
            url,
            follow=True,
            data={
                'user': self.user.pk,
                'name': name,
            },
        )
        self.assertNoFormError(response)
        self.assertEqual(name, self.refresh(camp).name)

    def test_listview(self):
        response = self.assertGET200(EmailCampaign.get_lv_absolute_url())

        with self.assertNoException():
            response.context['page_obj']
