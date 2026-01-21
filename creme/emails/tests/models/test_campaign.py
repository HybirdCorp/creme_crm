from functools import partial

from ..base import (
    EmailCampaign,
    MailingList,
    _EmailsTestCase,
    skipIfCustomEmailCampaign,
)


@skipIfCustomEmailCampaign
class CampaignTestCase(_EmailsTestCase):
    def test_clone(self):
        user = self.login_as_root_and_get()
        camp = EmailCampaign.objects.create(user=user, name='My campaign')

        create_ml = partial(MailingList.objects.create, user=user)
        ml1 = create_ml(name='List 01')
        ml2 = create_ml(name='List 02')
        camp.mailing_lists.set([ml1, ml2])

        cloned_camp = self.clone(camp)
        self.assertIsInstance(cloned_camp, EmailCampaign)
        self.assertNotEqual(camp.pk, cloned_camp.pk)
        self.assertEqual(camp.name, cloned_camp.name)
        self.assertCountEqual([ml1, ml2], cloned_camp.mailing_lists.all())

    # def test_clone__method(self):  # DEPRECATED
    #     user = self.get_root_user()
    #     camp = EmailCampaign.objects.create(user=user, name='My campaign')
    #
    #     create_ml = partial(MailingList.objects.create, user=user)
    #     ml1 = create_ml(name='List 01')
    #     ml2 = create_ml(name='List 02')
    #     camp.mailing_lists.set([ml1, ml2])
    #
    #     cloned_camp = camp.clone()
    #     self.assertIsInstance(cloned_camp, EmailCampaign)
    #     self.assertNotEqual(camp.pk, cloned_camp.pk)
    #     self.assertEqual(camp.name, cloned_camp.name)
    #     self.assertCountEqual([ml1, ml2], cloned_camp.mailing_lists.all())
