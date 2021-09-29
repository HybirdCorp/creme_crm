# -*- coding: utf-8 -*-

from functools import partial
from io import StringIO

from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from django.utils.translation import gettext as _
from django.utils.translation import pgettext
from parameterized import parameterized

from creme.creme_core.auth.entity_credentials import EntityCredentials
from creme.creme_core.core.entity_filter import condition_handler, operators
from creme.creme_core.models import (
    EntityFilter,
    FakeOrganisation,
    FieldsConfig,
    SetCredentials,
)
from creme.creme_core.tests.base import CremeTestCase
from creme.persons.tests.base import skipIfCustomContact
from creme.sms.models import Recipient

from .base import Contact, MessagingList, skipIfCustomMessagingList


@skipIfCustomMessagingList
class MessagingListTestCase(CremeTestCase):
    @staticmethod
    def _build_addcontact_url(mlist):
        return reverse('sms__add_contacts_to_mlist', args=(mlist.id,))

    @staticmethod
    def _build_addcontactfilter_url(mlist):
        return reverse('sms__add_contacts_to_mlist_from_filter', args=(mlist.id,))

    def test_createview(self):
        user = self.login()

        url = reverse('sms__create_mlist')
        self.assertGET200(url)

        name = 'My friends'
        response = self.client.post(
            url, follow=True,
            data={
                'user': user.id,
                'name': name,
            },
        )
        self.assertNoFormError(response)

        mlist = self.get_object_or_fail(MessagingList, name=name)
        self.assertEqual(user, mlist.user)

        # ----
        response = self.assertGET200(mlist.get_absolute_url())
        self.assertTemplateUsed(response, 'sms/view_messaginglist.html')

    def test_edit(self):
        user = self.login()

        mlist = MessagingList.objects.create(user=user, name='My family')

        url = mlist.get_edit_absolute_url()
        self.assertGET200(url)

        name = f'{mlist.name}_edited'
        response = self.client.post(
            url, follow=True,
            data={
                'user': user.id,
                'name': name,
            },
        )
        self.assertNoFormError(response)
        self.assertEqual(name, self.refresh(mlist).name)

    def test_listview(self):
        user = self.login()
        camp1 = MessagingList.objects.create(user=user, name='My list #1')
        camp2 = MessagingList.objects.create(user=user, name='My list #2')

        response = self.assertGET200(MessagingList.get_lv_absolute_url())

        with self.assertNoException():
            mlist_page = response.context['page_obj']

        self.assertEqual(2, mlist_page.paginator.count)
        self.assertSetEqual({camp1, camp2}, {*mlist_page.object_list})

    def test_recipients(self):
        user = self.login()

        mlist = MessagingList.objects.create(user=user, name='ml01')
        self.assertFalse(mlist.recipient_set.exists())

        url = reverse('sms__add_recipients', args=(mlist.id,))

        context = self.assertGET200(url).context
        self.assertEqual(
            _('New recipients for «{entity}»').format(entity=mlist),
            context.get('title')
        )
        self.assertEqual(Recipient.multi_save_label, context.get('submit_label'))

        # --------------------
        recipients = ['11223344', '55667788']
        self.assertPOST200(url, follow=True, data={'recipients': '\n'.join(recipients)})
        self.assertSetEqual(
            {*recipients},
            {r.phone for r in mlist.recipient_set.all()}
        )

        # --------------------
        recipient = mlist.recipient_set.all()[0]
        ct = ContentType.objects.get_for_model(Recipient)
        self.assertPOST200(
            reverse('creme_core__delete_related_to_entity', args=(ct.id,)),
            follow=True, data={'id': recipient.id},
        )

        phones = {r.phone for r in mlist.recipient_set.all()}
        self.assertEqual(len(recipients) - 1, len(phones))
        self.assertNotIn(recipient.phone, phones)

    @parameterized.expand([
        ('\n',),    # Unix EOF
        ('\r\n',),  # Windows EOF
        ('\r',),    # Old Mac EOF
    ])
    def test_add_recipients_from_csv(self, end):
        user = self.login()

        mlist = MessagingList.objects.create(user=user, name='ml01')
        url = reverse('sms__add_recipients_from_csv', args=(mlist.id,))
        self.assertGET200(url)

        phone1 = '123456789'
        phone2 = '1122334455'

        csvfile = StringIO(end.join([' ' + phone1, phone2 + ' ', '@{/']) + ' ')
        csvfile.name = 'recipients.csv'  # Django uses this

        self.assertNoFormError(self.client.post(url, data={'recipients': csvfile}))
        self.assertSetEqual(
            {phone1, phone2},
            {r.phone for r in mlist.recipient_set.all()}
        )

        csvfile.close()

    @skipIfCustomContact
    def test_ml_contacts01(self):
        user = self.login(is_superuser=False, allowed_apps=('sms', 'persons'))
        SetCredentials.objects.create(
            role=self.role,
            value=EntityCredentials.VIEW | EntityCredentials.CHANGE | EntityCredentials.LINK,
            set_type=SetCredentials.ESET_ALL,
        )

        mlist = MessagingList.objects.create(user=user, name='ml01')
        url = self._build_addcontact_url(mlist)

        response = self.assertGET200(url)
        self.assertTemplateUsed(response, 'creme_core/generics/blockform/link-popup.html')

        context = response.context
        self.assertEqual(
            _('New contacts for «{entity}»').format(entity=mlist),
            context.get('title')
        )
        self.assertEqual(_('Link the contacts'), context.get('submit_label'))

        create = partial(Contact.objects.create, user=user)
        recipients = [
            create(first_name='Spike', last_name='Spiegel', phone='112255'),
            create(first_name='Jet',   last_name='Black',   phone='789654'),
        ]

        # see MultiCreatorEntityField
        response = self.client.post(
            url,
            data={'recipients': '[{}]'.format(','.join(str(c.id) for c in recipients))},
        )
        self.assertNoFormError(response)
        self.assertSetEqual(
            {c.id for c in recipients},
            {c.id for c in mlist.contacts.all()}
        )

        # --------------------
        contact_to_del = recipients[0]
        self.client.post(
            reverse('sms__remove_contact_from_mlist', args=(mlist.id,)),
            data={'id': contact_to_del.id},
        )

        contacts = {*mlist.contacts.all()}
        self.assertEqual(len(recipients) - 1, len(contacts))
        self.assertNotIn(contact_to_del, contacts)

    def test_ml_contacts03(self):
        "Not a MailingList."
        user = self.login()
        orga = FakeOrganisation.objects.create(user=user, name='Dojo')
        self.assertGET404(self._build_addcontact_url(orga))

    @skipIfCustomContact
    def test_ml_contacts02(self):
        "The field 'mobile' is hidden."
        user = self.login()
        mlist = MessagingList.objects.create(user=user, name='ml01')

        FieldsConfig.objects.create(
            content_type=Contact,
            descriptions=[('mobile', {FieldsConfig.HIDDEN: True})],
        )
        self.assertGET409(self._build_addcontact_url(mlist))

    @skipIfCustomContact
    def test_ml_contacts_filter01(self):
        "'All' filter."
        user = self.login()
        mlist = MessagingList.objects.create(user=user, name='ml01')
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
        create(first_name='Spike', last_name='Spiegel', phone='112233'),
        create(first_name='Jet',   last_name='Black',   phone='45654'),
        create(first_name='Ed',    last_name='Wong',    phone='78998778', is_deleted=True),
        self.assertNoFormError(self.client.post(url, data={}))

        contacts = {*Contact.objects.filter(is_deleted=False)}
        self.assertGreaterEqual(len(contacts), 2)
        self.assertSetEqual(contacts, {*mlist.contacts.all()})

    @skipIfCustomContact
    def test_ml_contacts_filter02(self):
        "With a real EntityFilter."
        user = self.login()
        create_contact = partial(Contact.objects.create, user=user)
        recipients = [
            create_contact(first_name='Ranma', last_name='Saotome'),
            create_contact(first_name='Genma', last_name='Saotome'),
            create_contact(first_name='Akane', last_name='Tendô'),
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
            'test-filter02', 'Useless', FakeOrganisation, is_custom=True,
        )  # Should not be a valid choice

        mlist = MessagingList.objects.create(user=self.user, name='ml01')

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
            choices,
        )

        self.assertNoFormError(self.client.post(url, data={'filters': efilter.id}))
        self.assertSetEqual(expected_ids, {c.id for c in mlist.contacts.all()})

    def test_ml_contacts_filter03(self):
        "Not a MailingList."
        user = self.login()
        orga = FakeOrganisation.objects.create(user=user, name='Dojo')
        self.assertGET404(self._build_addcontactfilter_url(orga))

    @skipIfCustomContact
    def test_ml_contacts_filter04(self):
        "The field 'mobile' is hidden."
        user = self.login()
        mlist = MessagingList.objects.create(user=user, name='ml01')
        FieldsConfig.objects.create(
            content_type=Contact,
            descriptions=[('mobile', {FieldsConfig.HIDDEN: True})],
        )
        self.assertGET409(self._build_addcontactfilter_url(mlist))

    @skipIfCustomContact
    def test_ml_contacts_rm(self):
        "Not allowed to change the list."
        user = self.login(is_superuser=False, allowed_apps=('sms', 'persons'))
        SetCredentials.objects.create(
            role=self.role,
            value=EntityCredentials.VIEW | EntityCredentials.LINK,
            set_type=SetCredentials.ESET_ALL,
        )

        contact = Contact.objects.create(
            user=user, first_name='Spike', last_name='Spiegel',
        )

        mlist = MessagingList.objects.create(user=user, name='ml01')
        mlist.contacts.add(contact)

        self.assertPOST403(
            reverse('sms__remove_contact_from_mlist', args=(mlist.id,)),
            data={'id': contact.id}, follow=True,
        )
