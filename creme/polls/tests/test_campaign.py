# -*- coding: utf-8 -*-

try:
    from functools import partial
    from datetime import date

    from django.urls import reverse

    from creme.creme_core.models import CremePropertyType
    from creme.creme_core.tests.views.base import BrickTestCaseMixin

    from creme.commercial.models import MarketSegment

    from .base import (_PollsTestCase, skipIfCustomPollCampaign,
            skipIfCustomPollForm, skipIfCustomPollReply,
            PollCampaign, PollForm, PollReply)
    from ..bricks import PollCampaignRepliesBrick
except Exception as e:
    print('Error in <{}>: {}'.format(__name__, e))


@skipIfCustomPollCampaign
class PollCampaignsTestCase(_PollsTestCase, BrickTestCaseMixin):
    def setUp(self):
        self.login()

    def _create_segment(self, name, label):  # TODO: inline ?
        ptype = CremePropertyType.create('polls-prop_{}'.format(name), u'is from segment "{}"'.format(label))
        return MarketSegment.objects.create(name=label, property_type=ptype)

    def test_detailview01(self):
        camp = PollCampaign.objects.create(user=self.user, name='Camp#1')
        response = self.assertGET200(camp.get_absolute_url())
        self.assertContains(response, camp.name)
        self.assertTemplateUsed(response, 'polls/bricks/campaign-preplies.html')
        self.get_brick_node(self.get_html_tree(response.content), PollCampaignRepliesBrick.id_)

    def test_createview01(self):
        user = self.user
        self.assertFalse(PollCampaign.objects.all())

        url = reverse('polls__create_campaign')
        self.assertGET200(url)

        name = 'Campaign#1'
        goal = 'I want to rule the world'
        segment = self._create_segment('customers', 'Customers')
        expected_count = 8
        response = self.client.post(url, follow=True,
                                    data={'user':           user.id,
                                          'name':           name,
                                          'goal':           goal,
                                          'start':          '26-7-2013',
                                          'due_date':       '27-8-2013',
                                          'segment':        segment.id,
                                          'expected_count': expected_count,
                                         }
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
        user = self.user
        name = 'camp#1'
        camp = PollCampaign.objects.create(user=self.user, name=name)

        url = camp.get_edit_absolute_url()
        self.assertGET200(url)

        name = 'Campaign#1'
        goal = 'I want to rule the world'
        expected_count = 10
        response = self.client.post(url, follow=True,
                                    data={'user':           user.id,
                                          'name':           name,
                                          'goal':           goal,
                                          'start':          '26-9-2013',
                                          'due_date':       '27-10-2013',
                                          'expected_count': expected_count,
                                         }
                                   )
        self.assertNoFormError(response)

        camp = self.refresh(camp)
        self.assertEqual(goal, camp.goal)
        self.assertEqual(date(year=2013, month=9,  day=26), camp.start)
        self.assertEqual(date(year=2013, month=10, day=27), camp.due_date)
        self.assertEqual(expected_count, camp.expected_count)

    def test_listview(self):
        create_camp = partial(PollCampaign.objects.create, user=self.user)
        camps = [create_camp(name='Camp#%d' % i) for i in range(3)]

        response = self.assertGET200(PollCampaign.get_lv_absolute_url())

        with self.assertNoException():
            camps_page = response.context['entities']

        self.assertEqual(1, camps_page.number)
        self.assertEqual(len(camps), camps_page.paginator.count)
        self.assertEqual(set(camps), set(camps_page.object_list))

    def _create_pform_n_campaign(self):
        user  = self.user
        camp  = PollCampaign.objects.create(user=user, name='Camp#1')
        pform = PollForm.objects.create(user=user, name='Form#1')

        create_line = self._get_formline_creator(pform)
        create_line('What is the name of your swallow ?')
        create_line('What type of swallow is it ?')

        return pform, camp

    @skipIfCustomPollForm
    @skipIfCustomPollReply
    def test_create_preply01(self):
        "Create several replies linked to the campaign"
        pform, camp = self._create_pform_n_campaign()

        name = 'Reply'
        reply_number = 2
        response = self.client.post(self.ADD_REPLY_URL, follow=True,
                                    data={'user':     self.user.id,
                                          'name':     name,
                                          'pform':    pform.id,
                                          'number':   reply_number,
                                          'campaign': camp.id,
                                         }
                                   )
        self.assertNoFormError(response)

        for i in range(1, reply_number + 1):
            preply = self.get_object_or_fail(PollReply, name='{}#{}'.format(name, i))
            self.assertEqual(camp, preply.campaign)

    @skipIfCustomPollForm
    @skipIfCustomPollReply
    def test_create_preply02(self):
        "Create several replies linked to a given campaign"
        pform, camp = self._create_pform_n_campaign()

        url = reverse('polls__create_reply_from_campaign', args=(camp.id,))
        self.assertGET200(url)

        name = 'Reply'
        reply_number = 2
        response = self.client.post(url, follow=True,
                                    data={'user':   self.user.id,
                                          'name':   name,
                                          'pform':  pform.id,
                                          'number': reply_number,
                                         }
                                   )
        self.assertNoFormError(response)

        for i in range(1, reply_number + 1):
            preply = self.get_object_or_fail(PollReply, name='{}#{}'.format(name, i))
            self.assertEqual(camp, preply.campaign)
