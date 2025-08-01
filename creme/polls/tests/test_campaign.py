from datetime import date
from functools import partial

from django.urls import reverse
from django.utils.translation import gettext as _

from creme.commercial.models import MarketSegment
from creme.creme_core.models import CremePropertyType
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
class PollCampaignsTestCase(BrickTestCaseMixin, _PollsTestCase):
    @staticmethod
    def _create_segment(name, label):  # TODO: inline ?
        ptype = CremePropertyType.objects.create(text=f'is from segment "{label}"')
        return MarketSegment.objects.create(name=label, property_type=ptype)

    def test_detailview01(self):
        user = self.login_as_root_and_get()
        camp = PollCampaign.objects.create(user=user, name='Camp#1')
        response = self.assertGET200(camp.get_absolute_url())
        self.assertTemplateUsed(response, 'polls/view_campaign.html')
        self.assertContains(response, camp.name)
        self.assertTemplateUsed(response, 'polls/bricks/campaign-preplies.html')

        brick_node = self.get_brick_node(
            self.get_html_tree(response.content), brick=PollCampaignRepliesBrick,
        )
        self.assertEqual(
            _('Filled form replies'), self.get_brick_title(brick_node),
        )

    def test_detailview02(self):
        user = self.login_as_root_and_get()
        camp = PollCampaign.objects.create(user=user, name='Camp', expected_count=2)
        pform = PollForm.objects.create(user=user, name='Form')

        create_reply = partial(PollReply.objects.create, user=user, pform=pform, campaign=camp)
        create_reply(name='Reply#1')

        response1 = self.assertGET200(camp.get_absolute_url())
        brick_node1 = self.get_brick_node(
            self.get_html_tree(response1.content), brick=PollCampaignRepliesBrick,
        )
        self.assertBrickTitleEqual(
            brick_node1,
            count=1,
            title='{count} Filled form reply',
            plural_title='{count} Filled form replies',
        )
        self.get_html_node_or_fail(brick_node1, './/td[@class="brick-table-data-error"]')

        # ----
        create_reply(name='Reply#2')
        response2 = self.assertGET200(camp.get_absolute_url())
        brick_node2 = self.get_brick_node(
            self.get_html_tree(response2.content), brick=PollCampaignRepliesBrick,
        )
        self.assertBrickTitleEqual(
            brick_node2,
            count=2,
            title='{count} Filled form reply',
            plural_title='{count} Filled form replies',
        )
        self.get_html_node_or_fail(brick_node2, './/td[@class="brick-table-data-valid"]')

    def test_createview01(self):
        user = self.login_as_root_and_get()
        self.assertFalse(PollCampaign.objects.all())

        url = reverse('polls__create_campaign')
        self.assertGET200(url)

        name = 'Campaign#1'
        goal = 'I want to rule the world'
        segment = self._create_segment('customers', 'Customers')
        expected_count = 8
        start = date(year=2013, month=7, day=26)
        due_date = date(year=2013, month=8, day=27)
        self.assertNoFormError(self.client.post(
            url,
            follow=True,
            data={
                'user':           user.id,
                'name':           name,
                'goal':           goal,
                'start':          start,
                'due_date':       due_date,
                'segment':        segment.id,
                'expected_count': expected_count,
            },
        ))

        camp = self.get_object_or_fail(PollCampaign, name=name)
        self.assertEqual(user, camp.user)
        self.assertEqual(goal, camp.goal)
        self.assertEqual(start, camp.start)
        self.assertEqual(due_date, camp.due_date)
        self.assertEqual(segment, camp.segment)
        self.assertEqual(expected_count, camp.expected_count)

    def test_editview01(self):
        user = self.login_as_root_and_get()
        name = 'camp#1'
        camp = PollCampaign.objects.create(user=user, name=name)

        url = camp.get_edit_absolute_url()
        self.assertGET200(url)

        name = 'Campaign#1'
        goal = 'I want to rule the world'
        expected_count = 10
        start = date(year=2013, month=9,  day=26)
        due_date = date(year=2013, month=10, day=27)
        self.assertNoFormError(self.client.post(
            url,
            follow=True,
            data={
                'user':           user.id,
                'name':           name,
                'goal':           goal,
                'start':          start,
                'due_date':       due_date,
                'expected_count': expected_count,
            },
        ))

        camp = self.refresh(camp)
        self.assertEqual(goal, camp.goal)
        self.assertEqual(start, camp.start)
        self.assertEqual(due_date, camp.due_date)
        self.assertEqual(expected_count, camp.expected_count)

    def test_listview(self):
        user = self.login_as_root_and_get()
        create_camp = partial(PollCampaign.objects.create, user=user)
        camps = [create_camp(name='Camp#%d' % i) for i in range(3)]

        response = self.assertGET200(PollCampaign.get_lv_absolute_url())

        with self.assertNoException():
            camps_page = response.context['page_obj']

        self.assertEqual(1, camps_page.number)
        self.assertEqual(len(camps), camps_page.paginator.count)
        self.assertCountEqual(camps, camps_page.object_list)

    def _create_pform_n_campaign(self, user):
        camp  = PollCampaign.objects.create(user=user, name='Camp#1')
        pform = PollForm.objects.create(user=user, name='Form#1')

        create_line = self._get_formline_creator(pform)
        create_line('What is the name of your swallow?')
        create_line('What type of swallow is it?')

        return pform, camp

    @skipIfCustomPollForm
    @skipIfCustomPollReply
    def test_create_preply01(self):
        "Create several replies linked to the campaign."
        user = self.login_as_root_and_get()
        pform, camp = self._create_pform_n_campaign(user=user)

        name = 'Reply'
        reply_number = 2
        self.assertNoFormError(self.client.post(
            self.ADD_REPLIES_URL,
            follow=True,
            data={
                'user':     user.id,
                'name':     name,
                'pform':    pform.id,
                'number':   reply_number,
                'campaign': camp.id,
            },
        ))

        for i in range(1, reply_number + 1):
            preply = self.get_object_or_fail(PollReply, name=f'{name}#{i}')
            self.assertEqual(camp, preply.campaign)

    @skipIfCustomPollForm
    @skipIfCustomPollReply
    def test_create_preplies_from_campaign(self):
        "Create several replies linked to a given campaign."
        user = self.login_as_root_and_get()
        pform, camp = self._create_pform_n_campaign(user=user)

        url = reverse('polls__create_replies_from_campaign', args=(camp.id,))
        response1 = self.assertGET200(url)
        self.assertTemplateUsed(response1, 'creme_core/generics/blockform/add-popup.html')

        get_ctxt1 = response1.context.get
        self.assertEqual(
            _('New replies for «{entity}»').format(entity=camp),
            get_ctxt1('title'),
        )
        self.assertEqual(PollReply.multi_save_label, get_ctxt1('submit_label'))

        # ---
        name = 'Reply'
        reply_number = 2
        self.assertNoFormError(self.client.post(
            url,
            follow=True,
            data={
                'user':   user.id,
                'name':   name,
                'pform':  pform.id,
                'number': reply_number,
            },
        ))

        for i in range(1, reply_number + 1):
            preply = self.get_object_or_fail(PollReply, name=f'{name}#{i}')
            self.assertEqual(camp, preply.campaign)

    @skipIfCustomPollForm
    @skipIfCustomPollReply
    def test_create_preplies_from_campaign__not_super_user(self):
        user = self.login_as_polls_user(creatable_models=[PollReply])
        self.add_credentials(user.role, all='*')

        pform, camp = self._create_pform_n_campaign(user=user)
        self.assertGET200(reverse('polls__create_replies_from_campaign', args=(camp.id,)))

    @skipIfCustomPollForm
    @skipIfCustomPollReply
    def test_create_preplies_from_campaign__creation_perms(self):
        "Creation credentials are needed."
        user = self.login_as_polls_user()  # creatable_models=[PollReply]
        self.add_credentials(user.role, all='*')

        pform, camp = self._create_pform_n_campaign(user=user)
        self.assertGET403(reverse('polls__create_replies_from_campaign', args=(camp.id,)))

    @skipIfCustomPollForm
    @skipIfCustomPollReply
    def test_create_preply_from_campaign__link_perms(self):
        "LINK credentials are needed."
        user = self.login_as_polls_user(creatable_models=[PollReply])
        self.add_credentials(user.role, all='!LINK')

        pform, camp = self._create_pform_n_campaign(user=user)
        self.assertGET403(reverse('polls__create_replies_from_campaign', args=(camp.id,)))
