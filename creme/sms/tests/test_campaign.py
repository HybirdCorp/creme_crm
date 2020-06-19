# -*- coding: utf-8 -*-

from django.urls import reverse

from creme.creme_core.tests.base import CremeTestCase

from .base import SMSCampaign, skipIfCustomSMSCampaign

__all__ = ('SMSCampaignTestCase',)


@skipIfCustomSMSCampaign
class SMSCampaignTestCase(CremeTestCase):
    def test_createview(self):
        user = self.login()

        url = reverse('sms__create_campaign')
        self.assertGET200(url)

        name = 'Camp#1'
        response = self.client.post(url, follow=True,
                                    data={'user': user.pk,
                                          'name': name,
                                         }
                                    )
        self.assertNoFormError(response)
        self.get_object_or_fail(SMSCampaign, name=name)

    # TODO: complete
