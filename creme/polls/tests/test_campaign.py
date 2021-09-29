# -*- coding: utf-8 -*-

from datetime import date
from functools import partial

from django.urls import reverse
from django.utils.translation import gettext as _

from creme.commercial.models import MarketSegment
from creme.creme_core.auth.entity_credentials import EntityCredentials
from creme.creme_core.models import CremePropertyType, SetCredentials
from creme.creme_core.tests.views.base import BrickTestCaseMixin

from ..bricks import PollCampaignRepliesBrick
from .base import (
    PollCampaign,
    PollForm,
    PollReply,
    _PollsTestCase,
    skipIfCustomPollCampaign,
    skipIfCustomPollForm,
    skipIfCustomPollReply,
)


@skipIfCustomPollCampaign
class PollCampaignsTestCase(_PollsTestCase, BrickTestCaseMixin):
    @staticmethod
    def _create_segment(name, label):  # TODO: inline ?
        ptype = CremePropertyType.objects.smart_update_or_create(
            str_pk=f'polls-prop_{name}', text=f'is from segment "{label}"',
        )
        return MarketSegment.objects.create(name=label, property_type=ptype)

    def test_detailview01(self):
        user = self.login()
        camp = PollCampaign.objects.create(user=user, name='Camp#1')
        response = self.assertGET200(camp.get_absolute_url())
        self.assertTemplateUsed(response, 'polls/view_campaign.html')
        self.assertContains(response, camp.name)
        self.assertTemplateUsed(response, 'polls/bricks/campaign-preplies.html')
        self.get_brick_node(self.get_html_tree(response.content), PollCampaignRepliesBrick.id_)

    def test_createview01(self):
        user = self.login()
        self.assertFalse(PollCampaign.objects.all())

        url = reverse('polls__create_campaign')
        self.assertGET200(url)

        name = 'Campaign#1'
        goal = 'I want to rule the world'
        segment = self._create_segment('customers', 'Customers')
        expected_count = 8
        response = self.client.post(
            url,
            follow=True,
            data={
                'user':           user.id,
                'name':           name,
                'goal':           goal,
                'start':          '26-7-2013',
                'due_date':       '27-8-2013',
                'segment':        segment.id,
                'expected_count': expected_count,
            },
        )
        self.assertNoFormError(response)

        camp = self.get_object_or_fail(PollCampaign, name=name)
        self.assertEqual(user, camp.user)
        self.assertEqual(goal, camp.goal)
        self.assertEqual(date(year=2013, month=7, day=26), camp.start)
        self.assertEqual(date(year=2013, month=8, day=27), camp.due_date)
        self.assertEqual(segment, camp.segment)
        self.assertEqual(expected_count, camp.expected_count)

    def test_editview01(self):
        user = self.login()
        name = 'camp#1'
        camp = PollCampaign.objects.create(user=self.user, name=name)

        url = camp.get_edit_absolute_url()
        self.assertGET200(url)

        name = 'Campaign#1'
        goal = 'I want to rule the world'
        expected_count = 10
        response = self.client.post(
            url,
            follow=True,
            data={
                'user':           user.id,
                'name':           name,
                'goal':           goal,
                'start':          '26-9-2013',
                'due_date':       '27-10-2013',
                'expected_count': expected_count,
            },
        )
        self.assertNoFormError(response)

        camp = self.refresh(camp)
        self.assertEqual(goal, camp.goal)
        self.assertEqual(date(year=2013, month=9,  day=26), camp.start)
        self.assertEqual(date(year=2013, month=10, day=27), camp.due_date)
        self.assertEqual(expected_count, camp.expected_count)

    def test_listview(self):
        user = self.login()
        create_camp = partial(PollCampaign.objects.create, user=user)
        camps = [create_camp(name='Camp#%d' % i) for i in range(3)]

        response = self.assertGET200(PollCampaign.get_lv_absolute_url())

        with self.assertNoException():
            camps_page = response.context['page_obj']

        self.assertEqual(1, camps_page.number)
        self.assertEqual(len(camps), camps_page.paginator.count)
        self.assertSetEqual({*camps}, {*camps_page.object_list})

    def _create_pform_n_campaign(self):
        user  = self.user
        camp  = PollCampaign.objects.create(user=user, name='Camp#1')
        pform = PollForm.objects.create(user=user, name='Form#1')

        create_line = self._get_formline_creator(pform)
        create_line('What is the name of your swallow?')
        create_line('What type of swallow is it?')

        return pform, camp

    @skipIfCustomPollForm
    @skipIfCustomPollReply
    def test_create_preply01(self):
        "Create several replies linked to the campaign"
        user = self.login()
        pform, camp = self._create_pform_n_campaign()

        name = 'Reply'
        reply_number = 2
        response = self.client.post(
            self.ADD_REPLY_URL,
            follow=True,
            data={
                'user':     user.id,
                'name':     name,
                'pform':    pform.id,
                'number':   reply_number,
                'campaign': camp.id,
            },
        )
        self.assertNoFormError(response)

        for i in range(1, reply_number + 1):
            preply = self.get_object_or_fail(PollReply, name=f'{name}#{i}')
            self.assertEqual(camp, preply.campaign)

    @skipIfCustomPollForm
    @skipIfCustomPollReply
    def test_create_preply_from_campaign01(self):
        "Create several replies linked to a given campaign"
        user = self.login()
        pform, camp = self._create_pform_n_campaign()

        url = reverse('polls__create_reply_from_campaign', args=(camp.id,))
        response = self.assertGET200(url)
        self.assertTemplateUsed(response, 'creme_core/generics/blockform/add-popup.html')

        context = response.context
        self.assertEqual(
            _('New replies for «{entity}»').format(entity=camp),
            context.get('title'),
        )
        self.assertEqual(PollReply.multi_save_label, context.get('submit_label'))

        # ---
        name = 'Reply'
        reply_number = 2
        response = self.client.post(
            url,
            follow=True,
            data={
                'user':   user.id,
                'name':   name,
                'pform':  pform.id,
                'number': reply_number,
            },
        )
        self.assertNoFormError(response)

        for i in range(1, reply_number + 1):
            preply = self.get_object_or_fail(PollReply, name=f'{name}#{i}')
            self.assertEqual(camp, preply.campaign)

    @skipIfCustomPollForm
    @skipIfCustomPollReply
    def test_create_preply_from_campaign02(self):
        "Not super user."
        self.login(
            is_superuser=False, allowed_apps=['polls'], creatable_models=[PollReply],
        )
        SetCredentials.objects.create(
            role=self.role,
            value=(
                EntityCredentials.VIEW
                | EntityCredentials.CHANGE
                | EntityCredentials.DELETE
                | EntityCredentials.LINK
                | EntityCredentials.UNLINK
            ),
            set_type=SetCredentials.ESET_ALL,
        )

        pform, camp = self._create_pform_n_campaign()
        self.assertGET200(reverse('polls__create_reply_from_campaign', args=(camp.id,)))

    @skipIfCustomPollForm
    @skipIfCustomPollReply
    def test_create_preply_from_campaign03(self):
        "Creation credentials are needed."
        self.login(
            is_superuser=False, allowed_apps=['polls'],
            # creatable_models=[PollReply],
        )
        SetCredentials.objects.create(
            role=self.role,
            value=(
                EntityCredentials.VIEW
                | EntityCredentials.CHANGE
                | EntityCredentials.DELETE
                | EntityCredentials.LINK
                | EntityCredentials.UNLINK
            ),
            set_type=SetCredentials.ESET_ALL,
        )

        pform, camp = self._create_pform_n_campaign()

        self.assertGET403(reverse('polls__create_reply_from_campaign', args=(camp.id,)))

    @skipIfCustomPollForm
    @skipIfCustomPollReply
    def test_create_preply_from_campaign04(self):
        "LINK credentials are needed."
        self.login(
            is_superuser=False, allowed_apps=['polls'], creatable_models=[PollReply],
        )
        SetCredentials.objects.create(
            role=self.role,
            value=(
                EntityCredentials.VIEW
                | EntityCredentials.CHANGE
                | EntityCredentials.DELETE
                | EntityCredentials.UNLINK
                # | EntityCredentials.LINK
            ),
            set_type=SetCredentials.ESET_ALL,
        )

        pform, camp = self._create_pform_n_campaign()
        self.assertGET403(reverse('polls__create_reply_from_campaign', args=(camp.id,)))
