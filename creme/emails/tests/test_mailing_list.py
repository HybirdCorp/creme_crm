from functools import partial
from io import StringIO

from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from django.utils.translation import gettext as _
from django.utils.translation import pgettext
from parameterized import parameterized

from creme.creme_core.core.entity_filter import condition_handler, operators
from creme.creme_core.models import (
    EntityFilter,
    FakeOrganisation,
    FieldsConfig,
)
from creme.creme_core.tests.views.base import BrickTestCaseMixin
from creme.emails.models import EmailRecipient
from creme.persons.tests.base import (
    skipIfCustomContact,
    skipIfCustomOrganisation,
)

from .. import bricks
from .base import (
    Contact,
    EmailCampaign,
    MailingList,
    Organisation,
    _EmailsTestCase,
    skipIfCustomMailingList,
)


@skipIfCustomMailingList
class MailingListsTestCase(BrickTestCaseMixin, _EmailsTestCase):
    @staticmethod
    def _build_addcontact_url(mlist):
        return reverse('emails__add_contacts_to_mlist', args=(mlist.id,))

    @staticmethod
    def _build_addcontactfilter_url(mlist):
        return reverse('emails__add_contacts_to_mlist_from_filter', args=(mlist.id,))

    @staticmethod
    def _build_addorga_url(mlist):
        return reverse('emails__add_orgas_to_mlist', args=(mlist.id,))

    @staticmethod
    def _build_addorgafilter_url(mlist):
        return reverse('emails__add_orgas_to_mlist_from_filter', args=(mlist.id,))

    @staticmethod
    def _build_remove_from_campaign(campaign):
        return reverse('emails__remove_mlist_from_campaign', args=(campaign.id,))

    def test_create(self):
        user = self.login_as_root_and_get()

        url = reverse('emails__create_mlist')
        self.assertGET200(url)

        name = 'my_mailinglist'
        description = 'My friends'
        response2 = self.client.post(
            url, follow=True,
            data={
                'user': user.pk,
                'name': name,
                'description': description,
            },
        )
        self.assertNoFormError(response2)
        ml = self.get_object_or_fail(MailingList, name=name)
        self.assertEqual(description, ml.description)

        # ---
        response3 = self.assertGET200(ml.get_absolute_url())
        self.assertTemplateUsed(response3, 'emails/view_mailing_list.html')

    def test_edit(self):
        user = self.login_as_root_and_get()

        name = 'my_mailinglist'
        mlist = MailingList.objects.create(user=user, name=name)
        url = mlist.get_edit_absolute_url()
        self.assertGET200(url)

        # ---
        name += '_edited'
        response2 = self.client.post(
            url, follow=True,
            data={
                'user': user.pk,
                'name': name,
            },
        )
        self.assertNoFormError(response2)
        self.assertEqual(name, self.refresh(mlist).name)

    def test_listview(self):
        self.login_as_root()
        response = self.assertGET200(MailingList.get_lv_absolute_url())

        with self.assertNoException():
            response.context['page_obj']  # NOQA

    def test_ml_and_campaign01(self):
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

    def test_ml_and_campaign02(self):
        "Remove list from campaign."
        user = self.login_as_emails_user()
        self.add_credentials(user.role, all=['VIEW', 'CHANGE'])

        create_ml = partial(MailingList.objects.create, user=user)
        mlist01 = create_ml(name='Ml01')
        mlist02 = create_ml(name='Ml02')

        campaign = EmailCampaign.objects.create(user=user, name='camp')
        campaign.mailing_lists.set([mlist01, mlist02])

        self.assertPOST200(
            self._build_remove_from_campaign(campaign),
            follow=True, data={'id': mlist01.id},
        )
        self.assertListEqual([mlist02], [*campaign.mailing_lists.all()])

    def test_ml_and_campaign03(self):
        "Not allowed to change the campaign."
        user = self.login_as_emails_user()
        self.add_credentials(user.role, all=['VIEW'])  # Not 'CHANGE'

        mlist = MailingList.objects.create(user=user, name='Ml01')

        campaign = EmailCampaign.objects.create(user=user, name='camp')
        campaign.mailing_lists.add(mlist)

        self.assertPOST403(
            self._build_remove_from_campaign(campaign),
            follow=True, data={'id': mlist.id},
        )

    def test_detect_end_line(self):
        from creme.emails.forms.recipient import _detect_end_line

        class FakeUploadedFile:
            def __init__(self, chunks):
                self._chunks = chunks

            def chunks(self):
                yield from self._chunks

        def detect(chunks):
            return _detect_end_line(FakeUploadedFile(chunks))

        self.assertEqual('\n', detect([]))
        self.assertEqual('\n', detect(['abcde']))

        self.assertEqual('\n',   detect(['abcde\nefgij']))
        self.assertEqual('\r',   detect(['abcde\refgij']))
        self.assertEqual('\r\n', detect(['abcde\r\nefgij']))

        self.assertEqual('\n',   detect(['abcdeefgij', 'ih\nklmonp']))
        self.assertEqual('\r',   detect(['abcdeefgij', 'ih\rklmonp']))
        self.assertEqual('\r\n', detect(['abcdeefgij', 'ih\r\nklmonp']))

        self.assertEqual('\r',   detect(['abcdeefgij\r', 'ih\rklmonp']))
        self.assertEqual('\r\n', detect(['abcdeefgij\r', '\nklmonp']))

        self.assertEqual('\r', detect(['abcdeefgij\r', 'klmo\nnp']))
        self.assertEqual('\r', detect(['abcdeefgij\r', 'klmonp']))

    def test_recipients(self):
        user = self.login_as_root_and_get()

        mlist = MailingList.objects.create(user=user, name='ml01')
        self.assertFalse(mlist.emailrecipient_set.exists())

        url = reverse('emails__add_recipients', args=(mlist.id,))

        context1 = self.assertGET200(url).context
        self.assertEqual(
            _('New recipients for «{entity}»').format(entity=mlist),
            context1.get('title')
        )
        self.assertEqual(EmailRecipient.multi_save_label, context1.get('submit_label'))

        # --------------------
        recipients = ['spike.spiegel@bebop.com', 'jet.black@bebop.com']
        self.assertPOST200(url, follow=True, data={'recipients': '\n'.join(recipients)})
        self.assertCountEqual(
            recipients, [r.address for r in mlist.emailrecipient_set.all()],
        )

        response2 = self.assertGET200(mlist.get_absolute_url())
        brick_node = self.get_brick_node(
            self.get_html_tree(response2.content), brick=bricks.EmailRecipientsBrick,
        )
        self.assertBrickTitleEqual(
            brick_node,
            count=2,
            title='{count} Not linked recipient',
            plural_title='{count} Not linked recipients',
        )

        # --------------------
        # Invalid address
        response3 = self.assertPOST200(url, data={'recipients': 'faye.valentine#bebop.com'})
        self.assertFormError(
            response3.context['form'],
            field='recipients', errors=_('Enter a valid email address.'),
        )

        # --------------------
        recipient = mlist.emailrecipient_set.all()[0]
        ct = ContentType.objects.get_for_model(EmailRecipient)
        self.assertPOST200(
            reverse('creme_core__delete_related_to_entity', args=(ct.id,)),
            follow=True, data={'id': recipient.id},
        )

        addresses = {r.address for r in mlist.emailrecipient_set.all()}
        self.assertEqual(len(recipients) - 1, len(addresses))
        self.assertNotIn(recipient.address, addresses)

    @parameterized.expand([
        '\n',    # Unix EOF
        '\r\n',  # Windows EOF
        '\r',    # Old Mac EOF
    ])
    def test_add_recipients_from_csv(self, end):
        user = self.login_as_root_and_get()

        mlist = MailingList.objects.create(user=user, name='ml01')
        url = reverse('emails__add_recipients_from_csv', args=(mlist.id,))
        self.assertGET200(url)

        # TODO: it seems django validator does not manages address with unicode chars:
        #       is it a problem
        # recipients = ['spike.spiegel@bebop.com', 'jet.bläck@bebop.com']
        recipient1 = 'spike.spiegel@bebop.com'
        recipient2 = 'jet.black@bebop.com'

        csvfile = StringIO(end.join([' ' + recipient1, recipient2 + ' ']) + ' ')
        csvfile.name = 'recipients.csv'  # Django uses this

        self.assertNoFormError(self.client.post(url, data={'recipients': csvfile}))
        self.assertSetEqual(
            {recipient1, recipient2},
            {r.address for r in mlist.emailrecipient_set.all()},
        )

        csvfile.close()

    def test_recipients_error(self):
        "Not a MailingList."
        user = self.login_as_root_and_get()
        orga = FakeOrganisation.objects.create(user=user, name='Dojo')
        self.assertGET404(reverse('emails__add_recipients', args=(orga.id,)))

    @skipIfCustomContact
    def test_ml_contacts01(self):
        user = self.login_as_emails_user(allowed_apps=('persons',))
        self.add_credentials(user.role, all=['VIEW', 'CHANGE', 'LINK'])

        mlist = MailingList.objects.create(user=user, name='ml01')
        url = self._build_addcontact_url(mlist)

        response1 = self.assertGET200(url)
        self.assertTemplateUsed(response1, 'creme_core/generics/blockform/link-popup.html')

        context = response1.context
        self.assertEqual(
            _('New contacts for «{entity}»').format(entity=mlist),
            context.get('title')
        )
        self.assertEqual(_('Link the contacts'), context.get('submit_label'))

        create = partial(Contact.objects.create, user=user)
        recipients = [
            create(first_name='Spike', last_name='Spiegel', email='spike.spiegel@bebop.com'),
            create(first_name='Jet',   last_name='Black',   email='jet.black@bebop.com'),
        ]

        response2 = self.client.post(
            url, data={'recipients': self.formfield_value_multi_creator_entity(*recipients)},
        )
        self.assertNoFormError(response2)
        self.assertCountEqual(recipients, mlist.contacts.all())

        # Brick -----------------
        response3 = self.assertGET200(mlist.get_absolute_url())
        brick_node = self.get_brick_node(
            self.get_html_tree(response3.content), brick=bricks.ContactsBrick,
        )
        self.assertBrickTitleEqual(
            brick_node,
            count=2,
            title='{count} Contact-recipient',
            plural_title='{count} Contact-recipients',
        )

        # --------------------
        contact_to_del = recipients[0]
        self.client.post(
            reverse('emails__remove_contact_from_mlist', args=(mlist.id,)),
            data={'id': contact_to_del.id},
        )

        contacts = {*mlist.contacts.all()}
        self.assertEqual(len(recipients) - 1, len(contacts))
        self.assertNotIn(contact_to_del, contacts)

    @skipIfCustomContact
    def test_ml_contacts02(self):
        "'email' is hidden."
        user = self.login_as_root_and_get()
        mlist = MailingList.objects.create(user=user, name='ml01')

        FieldsConfig.objects.create(
            content_type=Contact,
            descriptions=[('email', {FieldsConfig.HIDDEN: True})],
        )
        self.assertGET409(self._build_addcontact_url(mlist))

    def test_ml_contacts03(self):
        "Not a MailingList."
        user = self.login_as_root_and_get()
        orga = FakeOrganisation.objects.create(user=user, name='Dojo')
        self.assertGET404(self._build_addcontact_url(orga))

    @skipIfCustomContact
    def test_ml_contacts_filter01(self):
        "'All' filter."
        user = self.login_as_root_and_get()
        mlist = MailingList.objects.create(user=user, name='ml01')
        url = self._build_addcontactfilter_url(mlist)

        response = self.assertGET200(url)
        self.assertTemplateUsed(response, 'creme_core/generics/blockform/link-popup.html')

        context = response.context
        self.assertEqual(
            _('New contacts for «{entity}»').format(entity=mlist),
            context.get('title')
        )
        self.assertEqual(_('Link the contacts'), context.get('submit_label'))

        create = partial(Contact.objects.create, user=user)
        create(first_name='Spike', last_name='Spiegel', email='spike.spiegel@bebop.com'),
        create(first_name='Jet', last_name='Black', email='jet.black@bebop.com'),
        create(first_name='Ed', last_name='Wong', email='ed.wong@bebop.com', is_deleted=True),
        self.assertNoFormError(self.client.post(url, data={}))

        contacts = Contact.objects.filter(is_deleted=False)
        self.assertGreaterEqual(len(contacts), 2)
        self.assertCountEqual(contacts, mlist.contacts.all())

    @skipIfCustomContact
    def test_ml_contacts_filter02(self):
        "With a real EntityFilter."
        user = self.login_as_root_and_get()
        create = partial(Contact.objects.create, user=user)
        recipients = [
            create(first_name='Ranma', last_name='Saotome'),
            create(first_name='Genma', last_name='Saotome'),
            create(first_name='Akane', last_name='Tendô'),
        ]
        expected_ids = {recipients[0].id, recipients[1].id}

        efilter = EntityFilter.objects.smart_update_or_create(
            'test-filter01', 'Saotome', Contact, is_custom=True,
            conditions=[
                condition_handler.RegularFieldConditionHandler.build_condition(
                    model=Contact,
                    operator=operators.IEQUALS,
                    field_name='last_name', values=['Saotome'],
                ),
            ],
        )
        self.assertSetEqual(expected_ids, {c.id for c in efilter.filter(Contact.objects.all())})

        EntityFilter.objects.smart_update_or_create(
            'test-filter02', 'Useless', Organisation, is_custom=True,
        )  # Should not be a valid choice

        mlist = MailingList.objects.create(user=user, name='ml01')

        url = self._build_addcontactfilter_url(mlist)
        context = self.client.get(url).context

        with self.assertNoException():
            choices = [*context['form'].fields['filters'].choices]

        self.assertListEqual(
            [
                ('', pgettext('creme_core-filter', 'All')),
                *(
                    (ef.id, ef.name)
                    for ef in EntityFilter.objects.filter(
                        entity_type=ContentType.objects.get_for_model(Contact),
                    )
                ),
            ],
            choices
        )

        self.assertNoFormError(self.client.post(url, data={'filters': efilter.id}))
        self.assertSetEqual(expected_ids, {c.id for c in mlist.contacts.all()})

    @skipIfCustomContact
    def test_ml_contacts_filter03(self):
        "'email' is hidden."
        user = self.login_as_root_and_get()
        mlist = MailingList.objects.create(user=user, name='ml01')
        FieldsConfig.objects.create(
            content_type=Contact,
            descriptions=[('email', {FieldsConfig.HIDDEN: True})],
        )
        self.assertGET409(self._build_addcontactfilter_url(mlist))

    def test_ml_contacts_filter04(self):
        "Not a MailingList."
        user = self.login_as_root_and_get()
        orga = FakeOrganisation.objects.create(user=user, name='Dojo')
        self.assertGET404(self._build_addcontactfilter_url(orga))

    @skipIfCustomContact
    def test_ml_contacts_rm(self):
        "Not allowed to change the list."
        user = self.login_as_emails_user(allowed_apps=('persons',))
        self.add_credentials(user.role, all=['VIEW', 'LINK'])

        contact = Contact.objects.create(
            user=user, first_name='Spike', last_name='Spiegel', email='spike.spiegel@bebop.com',
        )

        mlist = MailingList.objects.create(user=user, name='ml01')
        mlist.contacts.add(contact)

        self.assertPOST403(
            reverse('emails__remove_contact_from_mlist', args=(mlist.id,)),
            data={'id': contact.id}, follow=True,
        )

    @skipIfCustomOrganisation
    def test_ml_orgas01(self):
        user = self.login_as_root_and_get()
        mlist = MailingList.objects.create(user=user, name='ml01')
        url = self._build_addorga_url(mlist)

        response = self.assertGET200(url)
        self.assertTemplateUsed(response, 'creme_core/generics/blockform/link-popup.html')

        context1 = response.context
        self.assertEqual(
            _('New organisations for «{entity}»').format(entity=mlist),
            context1.get('title')
        )
        self.assertEqual(_('Link the organisations'), context1.get('submit_label'))

        # ---
        create = partial(Organisation.objects.create, user=user)
        recipients = [
            create(name='NERV',  email='contact@nerv.jp'),
            create(name='Seele', email='contact@seele.jp'),
        ]
        response2 = self.client.post(
            url,
            data={'recipients': self.formfield_value_multi_creator_entity(*recipients)},
        )
        self.assertNoFormError(response2)
        self.assertCountEqual(recipients, mlist.organisations.all())

        # Brick -----------------
        response3 = self.assertGET200(mlist.get_absolute_url())
        brick_node = self.get_brick_node(
            self.get_html_tree(response3.content), brick=bricks.OrganisationsBrick,
        )
        self.assertBrickTitleEqual(
            brick_node,
            count=2,
            title='{count} Organisation-recipient',
            plural_title='{count} Organisation-recipients',
        )

        # --------------------
        orga_to_del = recipients[0]
        self.client.post(
            reverse('emails__remove_orga_from_mlist', args=(mlist.id,)),
            data={'id': orga_to_del.id}
        )

        orgas = {*mlist.organisations.all()}
        self.assertEqual(len(recipients) - 1, len(orgas))
        self.assertNotIn(orga_to_del, orgas)

    @skipIfCustomOrganisation
    def test_ml_orgas02(self):
        "'email' is hidden."
        user = self.login_as_root_and_get()
        mlist = MailingList.objects.create(user=user, name='ml01')

        FieldsConfig.objects.create(
            content_type=Organisation,
            descriptions=[('email', {FieldsConfig.HIDDEN: True})],
        )
        self.assertGET409(self._build_addorga_url(mlist))

    def test_ml_orgas03(self):
        "Not a MailingList."
        user = self.login_as_root_and_get()
        orga = FakeOrganisation.objects.create(user=user, name='Dojo')
        self.assertGET404(self._build_addorga_url(orga))

    @skipIfCustomOrganisation
    def test_ml_orgas_filter01(self):
        " 'All' filter."
        user = self.login_as_root_and_get()
        mlist = MailingList.objects.create(user=user, name='ml01')
        url = self._build_addorgafilter_url(mlist)

        response = self.assertGET200(url)
        self.assertTemplateUsed(response, 'creme_core/generics/blockform/link-popup.html')

        context = response.context
        self.assertEqual(
            _('New organisations for «{entity}»').format(entity=mlist),
            context.get('title')
        )
        self.assertEqual(_('Link the organisations'), context.get('submit_label'))

        create_orga = partial(Organisation.objects.create, user=user)
        create_orga(name='NERV',  email='contact@nerv.jp'),
        create_orga(name='Seele', email='contact@seele.jp')
        self.assertNoFormError(self.client.post(url, data={}))

        orgas = Organisation.objects.all()
        self.assertGreaterEqual(len(orgas), 2)
        self.assertCountEqual(orgas, mlist.organisations.all())

    @skipIfCustomOrganisation
    def test_ml_orgas_filter02(self):
        "With a real EntityFilter."
        user = self.login_as_root_and_get()
        mlist = MailingList.objects.create(user=user, name='ml01')

        create = partial(Organisation.objects.create, user=user)
        recipients = [
            create(name='NERV',  email='contact@nerv.jp'),
            create(name='Seele', email='contact@seele.jp'),
            create(name='Bebop'),
        ]
        expected_ids = {recipients[0].id, recipients[1].id}

        create_ef = partial(
            EntityFilter.objects.smart_update_or_create,
            name='Has email',
            model=Organisation, is_custom=True,
            conditions=[
                condition_handler.RegularFieldConditionHandler.build_condition(
                    model=Organisation,
                    operator=operators.ISEMPTY,
                    field_name='email', values=[False],
                ),
            ],
        )
        priv_efilter = create_ef(pk='test-filter_priv', is_private=True, user=self.create_user())

        efilter = create_ef(pk='test-filter')
        self.assertSetEqual(
            expected_ids,
            {c.id for c in efilter.filter(Organisation.objects.all())},
        )

        url = self._build_addorgafilter_url(mlist)
        response1 = self.assertPOST200(url, data={'filters': priv_efilter.id})
        self.assertFormError(
            response1.context['form'],
            field='filters',
            errors=_(
                'Select a valid choice. That choice is not one of the available choices.'
            ),
        )

        # ---
        response2 = self.client.post(url, data={'filters': efilter.id})
        self.assertNoFormError(response2)
        self.assertEqual(expected_ids, {c.id for c in mlist.organisations.all()})

    @skipIfCustomOrganisation
    def test_ml_orgas_filter03(self):
        "'email' is hidden."
        user = self.login_as_root_and_get()
        mlist = MailingList.objects.create(user=user, name='ml01')

        FieldsConfig.objects.create(
            content_type=Organisation,
            descriptions=[('email', {FieldsConfig.HIDDEN: True})],
        )
        self.assertGET409(self._build_addorgafilter_url(mlist))

    def test_ml_orgas_filter04(self):
        "Not a MailingList."
        user = self.login_as_root_and_get()
        orga = FakeOrganisation.objects.create(user=user, name='Dojo')
        self.assertGET404(self._build_addorgafilter_url(orga))

    def test_ml_tree01(self):
        user = self.login_as_root_and_get()
        create_ml = partial(MailingList.objects.create, user=user)
        mlist01 = create_ml(name='ml01')
        mlist02 = create_ml(name='ml02')

        self.assertFalse(mlist01.children.exists())
        self.assertFalse(mlist02.children.exists())

        url = reverse('emails__add_child_mlists', args=(mlist01.id,))
        response1 = self.assertGET200(url)
        self.assertTemplateUsed(response1, 'creme_core/generics/blockform/link-popup.html')

        context = response1.context
        self.assertEqual(
            _('New child list for «{entity}»').format(entity=mlist01),
            context.get('title'),
        )
        self.assertEqual(_('Link the mailing list'), context.get('submit_label'))

        # --------------------
        self.assertPOST200(url, data={'child': mlist02.id})
        self.assertListEqual([mlist02.id], [ml.id for ml in mlist01.children.all()])
        self.assertFalse(mlist02.children.exists())

        # Children Brick -----------------
        response3 = self.assertGET200(mlist01.get_absolute_url())
        children_brick_node = self.get_brick_node(
            self.get_html_tree(response3.content), brick=bricks.ChildListsBrick,
        )
        self.assertBrickTitleEqual(
            children_brick_node,
            count=1,
            title='{count} Child List',
            plural_title='{count} Child Lists',
        )
        self.assertInstanceLink(children_brick_node, mlist02)

        # Parents Brick -----------------
        response4 = self.assertGET200(mlist02.get_absolute_url())
        parents_brick_node = self.get_brick_node(
            self.get_html_tree(response4.content), brick=bricks.ParentListsBrick,
        )
        self.assertBrickTitleEqual(
            parents_brick_node,
            count=1,
            title='{count} Parent List',
            plural_title='{count} Parent Lists',
        )
        self.assertInstanceLink(parents_brick_node, mlist01)

        # --------------------
        self.assertPOST200(
            reverse('emails__remove_child_mlist', args=(mlist01.id,)),
            data={'id': mlist02.id}, follow=True,
        )
        self.assertFalse(mlist01.children.exists())
        self.assertFalse(mlist02.children.exists())

    def test_ml_tree02(self):
        user = self.login_as_root_and_get()
        create_ml = partial(MailingList.objects.create, user=user)
        mlist01 = create_ml(name='ml01')
        mlist02 = create_ml(name='ml02')
        mlist03 = create_ml(name='ml03')

        mlist01.children.add(mlist02)
        mlist02.children.add(mlist03)

        def post(parent, child):
            response = self.client.post(
                reverse('emails__add_child_mlists', args=(parent.id,)),
                data={'child': child.id},
            )
            return self.get_form_or_fail(response)

        children_error = _('List already in the children')
        self.assertFormError(post(mlist01, mlist02), field='child', errors=children_error)
        self.assertFormError(post(mlist01, mlist03), field='child', errors=children_error)

        parents_error = _('List already in the parents')
        self.assertFormError(post(mlist02, mlist01), field='child', errors=parents_error)
        self.assertFormError(post(mlist03, mlist01), field='child', errors=parents_error)
        self.assertFormError(
            post(mlist01, mlist01), field='child', errors=_("A list can't be its own child")
        )

    def test_ml_tree03(self):
        "Not a MailingList."
        user = self.login_as_root_and_get()
        orga = FakeOrganisation.objects.create(user=user, name='Dojo')
        self.assertGET404(reverse('emails__add_child_mlists', args=(orga.id,)))

    def test_clone(self):
        user = self.login_as_root_and_get()
        create_ml = partial(MailingList.objects.create, user=user)
        mlist = create_ml(name='ml01')
        child = create_ml(name='ml02')

        mlist.children.add(child)

        contact = Contact.objects.create(
            user=user, first_name='Spike', last_name='Spiegel',
        )
        mlist.contacts.add(contact)

        orga = Organisation.objects.create(user=user, name='Bepop')
        mlist.organisations.add(orga)

        email = 'faye@bebop.mrs'
        EmailRecipient.objects.create(ml=mlist, address=email)

        cloned_mlist = self.clone(mlist)
        self.assertIsInstance(cloned_mlist, MailingList)
        self.assertNotEqual(mlist.pk, cloned_mlist.pk)
        self.assertEqual(mlist.name, cloned_mlist.name)
        self.assertCountEqual([child],   cloned_mlist.children.all())
        self.assertCountEqual([contact], cloned_mlist.contacts.all())
        self.assertCountEqual([orga],    cloned_mlist.organisations.all())
        self.assertCountEqual(
            [email], cloned_mlist.emailrecipient_set.values_list('address', flat=True),
        )

    # def test_clone__method(self):  # DEPRECATED
    #     user = self.get_root_user()
    #     create_ml = partial(MailingList.objects.create, user=user)
    #     mlist = create_ml(name='ml01')
    #     child = create_ml(name='ml02')
    #
    #     mlist.children.add(child)
    #
    #     contact = Contact.objects.create(
    #         user=user, first_name='Spike', last_name='Spiegel',
    #     )
    #     mlist.contacts.add(contact)
    #
    #     orga = Organisation.objects.create(user=user, name='Bepop')
    #     mlist.organisations.add(orga)
    #
    #     email = 'faye@bebop.mrs'
    #     EmailRecipient.objects.create(ml=mlist, address=email)
    #
    #     cloned_mlist = mlist.clone()
    #     self.assertIsInstance(cloned_mlist, MailingList)
    #     self.assertNotEqual(mlist.pk, cloned_mlist.pk)
    #     self.assertEqual(mlist.name, cloned_mlist.name)
    #     self.assertCountEqual([child],   cloned_mlist.children.all())
    #     self.assertCountEqual([contact], cloned_mlist.contacts.all())
    #     self.assertCountEqual([orga],    cloned_mlist.organisations.all())
    #     self.assertCountEqual(
    #         [email], cloned_mlist.emailrecipient_set.values_list('address', flat=True),
    #     )
