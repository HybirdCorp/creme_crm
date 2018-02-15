# -*- coding: utf-8 -*-

try:
    from functools import partial
    from StringIO import StringIO

    from django.contrib.contenttypes.models import ContentType
    from django.core.urlresolvers import reverse
    from django.utils.translation import ugettext as _

    from creme.creme_core.models import EntityFilter, EntityFilterCondition, FieldsConfig

    from creme.persons.tests.base import skipIfCustomContact, skipIfCustomOrganisation

    from .base import (_EmailsTestCase, skipIfCustomMailingList,
            Contact, Organisation, MailingList, EmailCampaign)
    from creme.emails.models import EmailRecipient
except Exception as e:
    print('Error in <%s>: %s' % (__name__, e))


@skipIfCustomMailingList
class MailingListsTestCase(_EmailsTestCase):
    def setUp(self):
        super(MailingListsTestCase, self).setUp()
        self.login()

    def _build_addcontact_url(self, mlist):
        return reverse('emails__add_contacts_to_mlist', args=(mlist.id,))

    def _build_addcontactfilter_url(self, mlist):
        return reverse('emails__add_contacts_to_mlist_from_filter', args=(mlist.id,))

    def _build_addorga_url(self, mlist):
        return reverse('emails__add_orgas_to_mlist', args=(mlist.id,))

    def _build_addorgafilter_url(self, mlist):
        return reverse('emails__add_orgas_to_mlist_from_filter', args=(mlist.id,))

    def test_create(self):
        url = reverse('emails__create_mlist')
        self.assertGET200(url)

        name = 'my_mailinglist'
        response = self.client.post(url, follow=True,
                                    data={'user': self.user.pk,
                                          'name': name,
                                         }
                                   )
        self.assertNoFormError(response)
        self.get_object_or_fail(MailingList, name=name)

    def test_edit(self):
        name = 'my_mailinglist'
        mlist = MailingList.objects.create(user=self.user, name=name)
        url = mlist.get_edit_absolute_url()
        self.assertGET200(url)

        name += '_edited'
        response = self.client.post(url, follow=True,
                                    data={'user': self.user.pk,
                                          'name': name,
                                         }
                                   )
        self.assertNoFormError(response)
        self.assertEqual(name, self.refresh(mlist).name)

    def test_listview(self):
        response = self.assertGET200(MailingList.get_lv_absolute_url())

        with self.assertNoException():
            response.context['entities']

    def test_ml_and_campaign(self):
        user = self.user
        campaign = EmailCampaign.objects.create(user=user, name='camp01')

        create_ml = partial(MailingList.objects.create, user=user)
        mlist01 = create_ml(name='Ml01')
        mlist02 = create_ml(name='Ml02')
        self.assertFalse(campaign.mailing_lists.exists())

        url = reverse('emails__add_mlists_to_campaign', args=(campaign.id,))
        self.assertGET200(url)

        def post(*mlists):
            return self.client.post(url, follow=True,
                                    # See MultiCreatorEntityField
                                    data={'mailing_lists': '[%s]' % ','.join(str(ml.id) for ml in mlists)}
                                   )

        response = post(mlist01, mlist02)
        self.assertNoFormError(response)
        self.assertEqual({mlist01, mlist02}, set(campaign.mailing_lists.all()))

        # Duplicates ---------------------
        mlist03 = create_ml(name='Ml03')
        response = post(mlist01, mlist03)
        self.assertEqual(200, response.status_code)
        self.assertFormError(response, 'form', 'mailing_lists', _('This entity does not exist.'))

        # Delete ----------------------
        self.assertPOST200(reverse('emails__remove_mlist_from_campaign', args=(campaign.id,)),
                           follow=True, data={'id': mlist01.id}
                          )
        self.assertEqual([mlist02], list(campaign.mailing_lists.all()))

    def test_detect_end_line(self):
        from creme.emails.forms.recipient import _detect_end_line

        class FakeUploadedFile:
            def __init__(self, chunks):
                self._chunks = chunks

            def chunks(self):
                for chunk in self._chunks:
                    yield chunk

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

    def test_recipients01(self):
        mlist = MailingList.objects.create(user=self.user, name='ml01')
        self.assertFalse(mlist.emailrecipient_set.exists())

        url = reverse('emails__add_recipients', args=(mlist.id,))
        self.assertGET200(url)

        recipients = ['spike.spiegel@bebop.com', 'jet.black@bebop.com']
        self.assertPOST200(url, follow=True, data={'recipients': '\n'.join(recipients)})
        self.assertEqual(set(recipients), {r.address for r in mlist.emailrecipient_set.all()})

        # --------------------
        response = self.assertPOST200(url, data={'recipients': 'faye.valentine#bebop.com'})  # Invalid address
        self.assertFormError(response, 'form', 'recipients', _(u'Enter a valid email address.'))

        # --------------------
        recipient = mlist.emailrecipient_set.all()[0]
        ct = ContentType.objects.get_for_model(EmailRecipient)
        self.assertPOST200(reverse('creme_core__delete_related_to_entity', args=(ct.id,)),
                           follow=True, data={'id': recipient.id},
                          )

        addresses = {r.address for r in mlist.emailrecipient_set.all()}
        self.assertEqual(len(recipients) - 1, len(addresses))
        self.assertNotIn(recipient.address, addresses)

    def _aux_test_add_recipients_csv(self, end='\n'):
        mlist = MailingList.objects.create(user=self.user, name='ml01')
        url = reverse('emails__add_recipients_from_csv', args=(mlist.id,))
        self.assertGET200(url)

        # TODO: it seems django validator does manages address with unicode chars:
        #       is it a problem
        # recipients = ['spike.spiegel@bebop.com', u'jet.bläck@bebop.com']
        recipients = ['spike.spiegel@bebop.com', u'jet.black@bebop.com']

        csvfile = StringIO(end.join(recipients) + ' ')
        csvfile.name = 'recipients.csv'  # Django uses this

        self.assertNoFormError(self.client.post(url, data={'recipients': csvfile}))
        self.assertEqual(set(recipients), {r.address for r in mlist.emailrecipient_set.all()})

        csvfile.close()

    def test_recipients02(self):
        "From CSV file (Unix EOF)"
        self._aux_test_add_recipients_csv(end=u'\n')

    def test_recipients03(self):
        "From CSV file (Windows EOF)"
        self._aux_test_add_recipients_csv(end=u'\r\n')

    def test_recipients04(self):
        "From CSV file (old Mac EOF)"
        self._aux_test_add_recipients_csv(end=u'\r')

    @skipIfCustomContact
    def test_ml_contacts01(self):
        mlist = MailingList.objects.create(user=self.user, name='ml01')
        url = self._build_addcontact_url(mlist)
        self.assertGET200(url)

        create = partial(Contact.objects.create, user=self.user)
        recipients = [create(first_name='Spike', last_name='Spiegel', email='spike.spiegel@bebop.com'),
                      create(first_name='Jet',   last_name='Black',   email='jet.black@bebop.com'),
                     ]

        # see MultiCreatorEntityField
        response = self.client.post(url, data={'recipients': '[%s]' % ','.join(str(c.id) for c in recipients)})
        self.assertNoFormError(response)
        self.assertEqual({c.id for c in recipients}, {c.id for c in mlist.contacts.all()})

        # --------------------
        contact_to_del = recipients[0]
        self.client.post(reverse('emails__remove_contact_from_mlist', args=(mlist.id,)),
                         data={'id': contact_to_del.id}
                        )

        contacts = set(mlist.contacts.all())
        self.assertEqual(len(recipients) - 1, len(contacts))
        self.assertNotIn(contact_to_del, contacts)

    @skipIfCustomContact
    def test_ml_contacts02(self):
        "'email' is hidden"
        mlist = MailingList.objects.create(user=self.user, name='ml01')

        FieldsConfig.create(Contact,
                            descriptions=[('email', {FieldsConfig.HIDDEN: True})],
                           )
        self.assertGET409(self._build_addcontact_url(mlist))

    @skipIfCustomContact
    def test_ml_contacts_filter01(self):
        "'All' filter"
        mlist = MailingList.objects.create(user=self.user, name='ml01')
        url = self._build_addcontactfilter_url(mlist)
        self.assertGET200(url)

        create = partial(Contact.objects.create, user=self.user)
        create(first_name='Spike', last_name='Spiegel', email='spike.spiegel@bebop.com'),
        create(first_name='Jet',   last_name='Black',   email='jet.black@bebop.com'),
        create(first_name='Ed',    last_name='Wong',    email='ed.wong@bebop.com', is_deleted=True),
        self.assertNoFormError(self.client.post(url, data={}))

        contacts = set(Contact.objects.filter(is_deleted=False))
        self.assertGreaterEqual(len(contacts), 2)
        self.assertEqual(contacts, set(mlist.contacts.all()))

    @skipIfCustomContact
    def test_ml_contacts_filter02(self):
        "With a real EntityFilter"
        create = partial(Contact.objects.create, user=self.user)
        recipients = [create(first_name='Ranma', last_name='Saotome'),
                      create(first_name='Genma', last_name='Saotome'),
                      create(first_name='Akane', last_name=u'Tendô'),
                     ]
        expected_ids = {recipients[0].id, recipients[1].id}

        efilter = EntityFilter.create('test-filter01', 'Saotome', Contact, is_custom=True,
                                      conditions=[EntityFilterCondition.build_4_field(model=Contact,
                                                        operator=EntityFilterCondition.IEQUALS,
                                                        name='last_name', values=['Saotome'],
                                                    )
                                                 ],
                                     )
        self.assertEqual(expected_ids, {c.id for c in efilter.filter(Contact.objects.all())})

        EntityFilter.create('test-filter02', 'Useless', Organisation, is_custom=True)  # Should not be a valid choice

        mlist = MailingList.objects.create(user=self.user, name='ml01')

        url = self._build_addcontactfilter_url(mlist)
        context = self.client.get(url).context

        with self.assertNoException():
            choices = list(context['form'].fields['filters'].choices)

        self.assertEqual([('', _('All'))] +
                         [(ef.id, ef.name)
                            for ef in EntityFilter.objects.filter(entity_type=ContentType.objects.get_for_model(Contact))
                         ],
                         choices
                        )

        self.assertNoFormError(self.client.post(url, data={'filters': efilter.id}))
        self.assertEqual(expected_ids, {c.id for c in mlist.contacts.all()})

    @skipIfCustomContact
    def test_ml_contacts_filter03(self):
        "'email' is hidden"
        mlist = MailingList.objects.create(user=self.user, name='ml01')
        FieldsConfig.create(Contact,
                            descriptions=[('email', {FieldsConfig.HIDDEN: True})],
                           )
        self.assertGET409(self._build_addcontactfilter_url(mlist))

    @skipIfCustomOrganisation
    def test_ml_orgas01(self):
        mlist = MailingList.objects.create(user=self.user, name='ml01')
        url = self._build_addorga_url(mlist)
        self.assertGET200(url)

        create = partial(Organisation.objects.create, user=self.user)
        recipients = [create(name='NERV',  email='contact@nerv.jp'),
                      create(name='Seele', email='contact@seele.jp'),
                     ]
        response = self.client.post(url, data={'recipients': '[%s]' % ','.join(str(c.id) for c in recipients)})
        self.assertNoFormError(response)
        self.assertEqual({c.id for c in recipients}, {c.id for c in mlist.organisations.all()})

        # --------------------
        orga_to_del = recipients[0]
        self.client.post(reverse('emails__remove_orga_from_mlist', args=(mlist.id,)),
                         data={'id': orga_to_del.id}
                        )

        orgas = set(mlist.organisations.all())
        self.assertEqual(len(recipients) - 1, len(orgas))
        self.assertNotIn(orga_to_del, orgas)

    @skipIfCustomOrganisation
    def test_ml_orgas02(self):
        "'email' is hidden"
        mlist = MailingList.objects.create(user=self.user, name='ml01')

        FieldsConfig.create(Organisation,
                            descriptions=[('email', {FieldsConfig.HIDDEN: True})],
                           )
        self.assertGET409(self._build_addorga_url(mlist))

    @skipIfCustomOrganisation
    def test_ml_orgas_filter01(self):
        " 'All' filter"
        mlist = MailingList.objects.create(user=self.user, name='ml01')
        url = self._build_addorgafilter_url(mlist)
        self.assertGET200(url)

        create_orga = partial(Organisation.objects.create, user=self.user)
        create_orga(name='NERV',  email='contact@nerv.jp'),
        create_orga(name='Seele', email='contact@seele.jp')
        self.assertNoFormError(self.client.post(url, data={}))

        orgas = set(Organisation.objects.all())
        self.assertGreaterEqual(len(orgas), 2)
        self.assertEqual(orgas, set(mlist.organisations.all()))

    @skipIfCustomOrganisation
    def test_ml_orgas_filter02(self):
        "With a real EntityFilter"
        mlist = MailingList.objects.create(user=self.user, name='ml01')

        create = partial(Organisation.objects.create, user=self.user)
        recipients = [create(name='NERV',  email='contact@nerv.jp'),
                      create(name='Seele', email='contact@seele.jp'),
                      create(name='Bebop'),
                     ]
        expected_ids = {recipients[0].id, recipients[1].id}

        create_ef = partial(EntityFilter.create, name='Has email',
                            model=Organisation, is_custom=True,
                            conditions=[EntityFilterCondition.build_4_field(
                                            model=Organisation,
                                            operator=EntityFilterCondition.ISEMPTY,
                                            name='email', values=[False],
                                        ),
                                       ]
                            )
        priv_efilter = create_ef(pk='test-filter_priv', is_private=True, user=self.other_user)

        efilter = create_ef(pk='test-filter')
        self.assertEqual(expected_ids, {c.id for c in efilter.filter(Organisation.objects.all())})

        url = self._build_addorgafilter_url(mlist)
        response = self.assertPOST200(url, data={'filters': priv_efilter.id})
        self.assertFormError(response, 'form', 'filters',
                             _(u'Select a valid choice. That choice is not one of the available choices.')
                            )

        response = self.client.post(url, data={'filters': efilter.id})
        self.assertNoFormError(response)
        self.assertEqual(expected_ids, {c.id for c in mlist.organisations.all()})

    @skipIfCustomOrganisation
    def test_ml_orgas_filter03(self):
        "'email' is hidden"
        mlist = MailingList.objects.create(user=self.user, name='ml01')

        FieldsConfig.create(Organisation,
                            descriptions=[('email', {FieldsConfig.HIDDEN: True})],
                           )
        self.assertGET409(self._build_addorgafilter_url(mlist))

    def test_ml_tree01(self):
        create_ml = partial(MailingList.objects.create, user=self.user)
        mlist01 = create_ml(name='ml01')
        mlist02 = create_ml(name='ml02')

        self.assertFalse(mlist01.children.exists())
        self.assertFalse(mlist02.children.exists())

        url = reverse('emails__add_child_mlists', args=(mlist01.id,))
        self.assertGET200(url)
        self.assertPOST200(url, data={'child': mlist02.id})
        self.assertEqual([mlist02.id], [ml.id for ml in mlist01.children.all()])
        self.assertFalse(mlist02.children.exists())

        # --------------------
        self.assertPOST200(reverse('emails__remove_child_mlist', args=(mlist01.id,)),
                           data={'id': mlist02.id}, follow=True,
                          )
        self.assertFalse(mlist01.children.exists())
        self.assertFalse(mlist02.children.exists())

    def test_ml_tree02(self):
        create_ml = partial(MailingList.objects.create, user=self.user)
        mlist01 = create_ml(name='ml01')
        mlist02 = create_ml(name='ml02')
        mlist03 = create_ml(name='ml03')

        mlist01.children.add(mlist02)
        mlist02.children.add(mlist03)

        post = lambda parent, child: self.client.post(reverse('emails__add_child_mlists', args=(parent.id,)),
                                                      data={'child': child.id},
                                                     )

        children_error = _(u'List already in the children')
        self.assertFormError(post(mlist01, mlist02), 'form', 'child', children_error)
        self.assertFormError(post(mlist01, mlist03), 'form', 'child', children_error)

        parents_error = _(u'List already in the parents')
        self.assertFormError(post(mlist02, mlist01), 'form', 'child', parents_error)
        self.assertFormError(post(mlist03, mlist01), 'form', 'child', parents_error)
        self.assertFormError(post(mlist01, mlist01), 'form', 'child', _(u"A list can't be its own child"))
