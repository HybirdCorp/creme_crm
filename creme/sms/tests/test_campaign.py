# -*- coding: utf-8 -*-

from functools import partial

from django.urls import reverse
from django.utils.translation import gettext as _

from creme.creme_core.auth.entity_credentials import EntityCredentials
from creme.creme_core.models import SetCredentials
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
        user = self.login()

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
        user = self.login()

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
        user = self.login()

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
        user = self.login()
        camp1 = SMSCampaign.objects.create(user=user, name='My campaign #1')
        camp2 = SMSCampaign.objects.create(user=user, name='My campaign #2')

        response = self.assertGET200(SMSCampaign.get_lv_absolute_url())

        with self.assertNoException():
            camp_page = response.context['page_obj']

        self.assertEqual(2, camp_page.paginator.count)
        self.assertSetEqual({camp1, camp2}, {*camp_page.object_list})

    @skipIfCustomMessagingList
    def test_messaging_list01(self):
        user = self.login()
        campaign = SMSCampaign.objects.create(user=user, name='camp01')

        create_ml = partial(MessagingList.objects.create, user=user)
        mlist01 = create_ml(name='Ml01')
        mlist02 = create_ml(name='Ml02')
        self.assertFalse(campaign.lists.exists())

        url = reverse('sms__add_mlists_to_campaign', args=(campaign.id,))
        response = self.assertGET200(url)
        self.assertTemplateUsed(response, 'creme_core/generics/blockform/link-popup.html')

        context = response.context
        self.assertEqual(
            _('New messaging lists for «{entity}»').format(entity=campaign),
            context.get('title')
        )
        self.assertEqual(_('Link the messaging lists'), context.get('submit_label'))

        # ----
        def post(*mlists):
            return self.client.post(
                url, follow=True,
                data={'messaging_lists': self.formfield_value_multi_creator_entity(*mlists)},
            )

        response = post(mlist01, mlist02)
        self.assertNoFormError(response)
        self.assertSetEqual({mlist01, mlist02}, {*campaign.lists.all()})

        # Duplicates ---------------------
        mlist03 = create_ml(name='Ml03')
        response = post(mlist01, mlist03)
        self.assertEqual(200, response.status_code)
        self.assertFormError(
            # response, 'form', 'messaging_lists', _('This entity does not exist.')
            response, 'form', 'messaging_lists',
            _('«%(entity)s» violates the constraints.') % {'entity': mlist01},
        )

    @skipIfCustomMessagingList
    def test_messaging_list02(self):
        "Remove list from campaign."
        user = self.login(is_superuser=False, allowed_apps=('sms',))
        SetCredentials.objects.create(
            role=self.role,
            value=EntityCredentials.VIEW | EntityCredentials.CHANGE,
            set_type=SetCredentials.ESET_ALL,
        )

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
        user = self.login(is_superuser=False, allowed_apps=('sms',))
        SetCredentials.objects.create(
            role=self.role,
            value=EntityCredentials.VIEW,  # Not CHANGE
            set_type=SetCredentials.ESET_ALL,
        )

        mlist = MessagingList.objects.create(user=user, name='Ml01')

        campaign = SMSCampaign.objects.create(user=user, name='camp')
        campaign.lists.add(mlist)

        self.assertPOST403(
            self._build_remove_list(campaign),
            follow=True, data={'id': mlist.id},
        )
