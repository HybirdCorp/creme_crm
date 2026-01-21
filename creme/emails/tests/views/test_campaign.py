from functools import partial

from django.urls import reverse
from django.utils.translation import gettext as _

from creme.creme_core.tests.views.base import BrickTestCaseMixin
from creme.emails import bricks

from ..base import (
    EmailCampaign,
    MailingList,
    _EmailsTestCase,
    skipIfCustomEmailCampaign,
    skipIfCustomMailingList,
)


@skipIfCustomEmailCampaign
class CampaignViewsTestCase(BrickTestCaseMixin, _EmailsTestCase):
    @staticmethod
    def _build_remove_mlist_url(campaign):
        return reverse('emails__remove_mlist_from_campaign', args=(campaign.id,))

    def test_detail_view(self):
        user = self.login_as_emails_user()
        self.add_credentials(user.role, own=['VIEW'])

        campaign = EmailCampaign.objects.create(user=user, name='Camp001')

        response = self.assertGET200(campaign.get_absolute_url())
        self.assertTemplateUsed(response, 'emails/view_campaign.html')

        sending_brick_node = self.get_brick_node(
            self.get_html_tree(response.content), brick=bricks.SendingsBrick,
        )
        self.assertEqual(_('Emails sending'), self.get_brick_title(sending_brick_node))

        ml_brick_node = self.get_brick_node(
            self.get_html_tree(response.content), brick=bricks.MailingListsBrick,
        )
        self.assertEqual(_('Mailing lists'), self.get_brick_title(ml_brick_node))

    def test_creation(self):
        user = self.login_as_emails_user(creatable_models=[EmailCampaign])
        self.add_credentials(user.role, own=['VIEW'])

        url = reverse('emails__create_campaign')
        self.assertGET200(url)

        # ---
        name = 'My campaign'
        self.assertNoFormError(self.client.post(
            url, follow=True, data={'user': user.pk, 'name': name},
        ))
        self.get_object_or_fail(EmailCampaign, user=user, name=name)

    def test_edition(self):
        user = self.login_as_emails_user()
        self.add_credentials(user.role, own=['VIEW', 'CHANGE'])

        name = 'my_campaign'
        camp = EmailCampaign.objects.create(user=user, name=name)

        url = camp.get_edit_absolute_url()
        self.assertGET200(url)

        name += '_edited'
        response = self.client.post(
            url,
            follow=True,
            data={'user': user.pk, 'name': name},
        )
        self.assertNoFormError(response)
        self.assertEqual(name, self.refresh(camp).name)

    def test_list_view(self):
        user = self.login_as_emails_user(listable_models=[EmailCampaign])
        self.add_credentials(user.role, own=['VIEW'])

        camp = EmailCampaign.objects.create(user=user, name='my_campaign')
        response = self.assertGET200(EmailCampaign.get_lv_absolute_url())

        with self.assertNoException():
            camp_page = response.context['page_obj']

        self.assertEqual(1, camp_page.number)
        self.assertCountEqual([camp], camp_page.object_list)

    @skipIfCustomMailingList
    def test_add_list(self):
        user = self.login_as_root_and_get()
        campaign = EmailCampaign.objects.create(user=user, name='camp01')

        create_ml = partial(MailingList.objects.create, user=user)
        mlist01 = create_ml(name='Ml01')
        mlist02 = create_ml(name='Ml02')
        self.assertFalse(campaign.mailing_lists.exists())

        url = reverse('emails__add_mlists_to_campaign', args=(campaign.id,))
        response1 = self.assertGET200(url)
        self.assertTemplateUsed(response1, 'creme_core/generics/blockform/link-popup.html')

        context = response1.context
        self.assertEqual(
            _('New mailing lists for «{entity}»').format(entity=campaign),
            context.get('title')
        )
        self.assertEqual(_('Link the mailing lists'), context.get('submit_label'))

        # ----
        def post(*mlists):
            return self.client.post(
                url, follow=True,
                data={'mailing_lists': self.formfield_value_multi_creator_entity(*mlists)},
            )

        response2 = post(mlist01, mlist02)
        self.assertNoFormError(response2)
        self.assertCountEqual([mlist01, mlist02], campaign.mailing_lists.all())

        response3 = self.assertGET200(campaign.get_absolute_url())
        brick_node = self.get_brick_node(
            self.get_html_tree(response3.content), brick=bricks.MailingListsBrick,
        )
        self.assertBrickTitleEqual(
            brick_node,
            count=2,
            title='{count} Related mailing list',
            plural_title='{count} Related mailing lists',
        )
        self.assertInstanceLink(brick_node, mlist01)
        self.assertInstanceLink(brick_node, mlist02)

        # Duplicates ---------------------
        mlist03 = create_ml(name='Ml03')
        response4 = post(mlist01, mlist03)
        self.assertEqual(200, response4.status_code)
        self.assertFormError(
            response4.context['form'],
            field='mailing_lists',
            errors=_('«%(entity)s» violates the constraints.') % {'entity': mlist01},
        )

    @skipIfCustomMailingList
    def test_remove_list(self):
        user = self.login_as_emails_user()
        self.add_credentials(user.role, all=['VIEW', 'CHANGE'])

        create_ml = partial(MailingList.objects.create, user=user)
        mlist01 = create_ml(name='Ml01')
        mlist02 = create_ml(name='Ml02')

        campaign = EmailCampaign.objects.create(user=user, name='camp')
        campaign.mailing_lists.set([mlist01, mlist02])

        self.assertPOST200(
            self._build_remove_mlist_url(campaign),
            follow=True, data={'id': mlist01.id},
        )
        self.assertListEqual([mlist02], [*campaign.mailing_lists.all()])

    @skipIfCustomMailingList
    def test_remove_list__forbidden(self):
        "Not allowed to change the campaign."
        user = self.login_as_emails_user()
        self.add_credentials(user.role, all=['VIEW'])  # Not 'CHANGE'

        mlist = MailingList.objects.create(user=user, name='Ml01')

        campaign = EmailCampaign.objects.create(user=user, name='camp')
        campaign.mailing_lists.add(mlist)

        self.assertPOST403(
            self._build_remove_mlist_url(campaign),
            follow=True, data={'id': mlist.id},
        )
