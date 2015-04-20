# -*- coding: utf-8 -*-

try:
    from creme.creme_core.tests.base import CremeTestCase

    from ..models import SMSCampaign
except Exception as e:
    print('Error in <%s>: %s' % (__name__, e))


__all__ = ('SMSCampaignTestCase',)


class SMSCampaignTestCase(CremeTestCase):
    def test_createview(self):
        user = self.login()

        url = '/sms/campaign/add'
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
