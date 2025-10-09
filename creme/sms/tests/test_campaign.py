from functools import partial

from django.test.utils import override_settings
from django.urls import reverse
from django.utils.translation import gettext as _

from creme.creme_core.tests.base import CremeTestCase

from .base import (
    MessagingList,
    SMSCampaign,
    skipIfCustomMessagingList,
    skipIfCustomSMSCampaign,
)


@skipIfCustomSMSCampaign
class SMSCampaignTestCase(CremeTestCase):
    @staticmethod
    def _build_remove_list(campaign):
        return reverse('sms__remove_mlist_from_campaign', args=(campaign.id,))

    def test_createview01(self):
        user = self.login_as_root_and_get()

        url = reverse('sms__create_campaign')
        self.assertGET200(url)

        name = 'Camp#1'
        response = self.client.post(
            url, follow=True,
            data={
                'user': user.pk,
                'name': name,
            },
        )
        self.assertNoFormError(response)

        camp = self.get_object_or_fail(SMSCampaign, name=name)
        self.assertEqual(user, camp.user)

        # ----
        response = self.assertGET200(camp.get_absolute_url())
        self.assertTemplateUsed(response, 'sms/view_campaign.html')

    @skipIfCustomMessagingList
    def test_createview02(self):
        "With list."
        user = self.login_as_root_and_get()

        create_ml = partial(MessagingList.objects.create, user=user)
        mlists = [
            create_ml(name='Ml01'),
            create_ml(name='Ml02'),
        ]

        name = 'My Camp'
        response = self.client.post(
            reverse('sms__create_campaign'),
            follow=True,
            data={
                'user': user.id,
                'name': name,
                'lists': self.formfield_value_multi_creator_entity(*mlists),
            },
        )
        self.assertNoFormError(response)

        camp = self.get_object_or_fail(SMSCampaign, name=name)
        self.assertCountEqual(mlists, [*camp.lists.all()])

    @skipIfCustomMessagingList
    def test_edit(self):
        user = self.login_as_root_and_get()
        mlist = MessagingList.objects.create(user=user, name='Ml01')
        camp = SMSCampaign.objects.create(user=user, name='My campaign')

        url = camp.get_edit_absolute_url()
        self.assertGET200(url)

        name = f'{camp.name}_edited'
        response = self.client.post(
            url, follow=True,
            data={
                'user': user.id,
                'name': name,

                # Should be ignored
                'lists': self.formfield_value_multi_creator_entity(mlist),
            },
        )
        self.assertNoFormError(response)

        camp = self.refresh(camp)
        self.assertEqual(name, camp.name)
        self.assertFalse([*camp.lists.all()])

    def test_listview(self):
        user = self.login_as_root_and_get()
        camp1 = SMSCampaign.objects.create(user=user, name='My campaign #1')
        camp2 = SMSCampaign.objects.create(user=user, name='My campaign #2')

        response = self.assertGET200(SMSCampaign.get_lv_absolute_url())

        with self.assertNoException():
            camp_page = response.context['page_obj']

        self.assertEqual(2, camp_page.paginator.count)
        self.assertCountEqual([camp1, camp2], camp_page.object_list)

    @skipIfCustomMessagingList
    def test_messaging_list01(self):
        user = self.login_as_root_and_get()
        campaign = SMSCampaign.objects.create(user=user, name='camp01')

        create_ml = partial(MessagingList.objects.create, user=user)
        mlist01 = create_ml(name='Ml01')
        mlist02 = create_ml(name='Ml02')
        self.assertFalse(campaign.lists.exists())

        url = reverse('sms__add_mlists_to_campaign', args=(campaign.id,))
        response1 = self.assertGET200(url)
        self.assertTemplateUsed(response1, 'creme_core/generics/blockform/link-popup.html')

        get_ctxt1 = response1.context.get
        self.assertEqual(
            _('New messaging lists for «{entity}»').format(entity=campaign),
            get_ctxt1('title'),
        )
        self.assertEqual(_('Link the messaging lists'), get_ctxt1('submit_label'))

        # ----
        def post(*mlists):
            return self.client.post(
                url, follow=True,
                data={'messaging_lists': self.formfield_value_multi_creator_entity(*mlists)},
            )

        response2 = post(mlist01, mlist02)
        self.assertNoFormError(response2)
        self.assertCountEqual([mlist01, mlist02], campaign.lists.all())

        # Duplicates ---------------------
        mlist03 = create_ml(name='Ml03')
        response3 = post(mlist01, mlist03)
        self.assertEqual(200, response3.status_code)
        self.assertFormError(
            response3.context['form'],
            field='messaging_lists',
            errors=_('«%(entity)s» violates the constraints.') % {'entity': mlist01},
        )

    @skipIfCustomMessagingList
    def test_messaging_list02(self):
        "Remove list from campaign."
        user = self.login_as_standard(allowed_apps=('sms',))
        self.add_credentials(user.role, all=['VIEW', 'CHANGE'])

        create_ml = partial(MessagingList.objects.create, user=user)
        mlist01 = create_ml(name='Ml01')
        mlist02 = create_ml(name='Ml02')

        campaign = SMSCampaign.objects.create(user=user, name='camp')
        campaign.lists.set([mlist01, mlist02])

        self.assertPOST200(
            self._build_remove_list(campaign),
            follow=True, data={'id': mlist01.id},
        )
        self.assertListEqual([mlist02], [*campaign.lists.all()])

    @skipIfCustomMessagingList
    def test_ml_and_campaign03(self):
        "Not allowed to change the campaign."
        user = self.login_as_standard(allowed_apps=('sms',))
        self.add_credentials(user.role, all=['VIEW'])  # 'CHANGE'

        mlist = MessagingList.objects.create(user=user, name='Ml01')

        campaign = SMSCampaign.objects.create(user=user, name='camp')
        campaign.lists.add(mlist)

        self.assertPOST403(
            self._build_remove_list(campaign),
            follow=True, data={'id': mlist.id},
        )

    @skipIfCustomMessagingList
    def test_clone(self):
        user = self.login_as_root_and_get()

        mlist = MessagingList.objects.create(user=user, name='Ml01')

        campaign = SMSCampaign.objects.create(user=user, name='camp')
        campaign.lists.add(mlist)

        cloned_camp = self.clone(campaign)
        self.assertIsInstance(cloned_camp, SMSCampaign)
        self.assertNotEqual(campaign.pk, cloned_camp.pk)
        self.assertEqual(campaign.name, cloned_camp.name)
        self.assertCountEqual([mlist], campaign.lists.all())

    # @skipIfCustomMessagingList
    # def test_clone__method(self):  # DEPRECATED
    #     user = self.get_root_user()
    #
    #     mlist = MessagingList.objects.create(user=user, name='Ml01')
    #
    #     campaign = SMSCampaign.objects.create(user=user, name='camp')
    #     campaign.lists.add(mlist)
    #
    #     cloned_camp = campaign.clone()
    #     self.assertIsInstance(cloned_camp, SMSCampaign)
    #     self.assertNotEqual(campaign.pk, cloned_camp.pk)
    #     self.assertEqual(campaign.name, cloned_camp.name)
    #     self.assertCountEqual([mlist], campaign.lists.all())

    @override_settings(ENTITIES_DELETION_ALLOWED=True)
    def test_delete(self):
        user = self.login_as_root_and_get()
        campaign = SMSCampaign.objects.create(user=user, name='camp')

        url = campaign.get_delete_absolute_url()
        self.assertPOST200(url, follow=True)

        with self.assertNoException():
            campaign = self.refresh(campaign)

        self.assertIs(campaign.is_deleted, True)

        self.assertPOST200(url, follow=True)
        self.assertDoesNotExist(campaign)
