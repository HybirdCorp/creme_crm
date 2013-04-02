# -*- coding: utf-8 -*-

try:
    from functools import partial
    from StringIO import StringIO

    from django.utils.translation import ugettext as _
    from django.contrib.contenttypes.models import ContentType

    from creme.creme_core.models import EntityFilter, EntityFilterCondition

    from creme.persons.models import Contact, Organisation

    from .base import _EmailsTestCase
    from creme.emails.models import MailingList, EmailCampaign, EmailRecipient
except Exception as e:
    print 'Error in <%s>: %s' % (__name__, e)


__all__ = ('MailingListsTestCase',)


class MailingListsTestCase(_EmailsTestCase):
    def setUp(self):
        self.login()

    def test_create(self):
        url = '/emails/mailing_list/add'
        self.assertGET200(url)

        name     = 'my_mailinglist'
        response = self.client.post(url, follow=True,
                                    data={'user': self.user.pk,
                                          'name': name,
                                         }
                                   )
        self.assertNoFormError(response)
        self.get_object_or_fail(MailingList, name=name)

    def test_edit(self):
        name = 'my_mailinglist'
        mlist = MailingList.objects.create(user=self.user,   name=name)
        url = '/emails/mailing_list/edit/%s' % mlist.id
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
        response = self.assertGET200('/emails/mailing_lists')

        with self.assertNoException():
            response.context['entities']

    def test_ml_and_campaign(self):
        campaign = EmailCampaign.objects.create(user=self.user, name='camp01')
        mlist    = MailingList.objects.create(user=self.user,   name='ml01')
        self.assertFalse(campaign.mailing_lists.exists())

        url = '/emails/campaign/%s/mailing_list/add' % campaign.id
        self.assertGET200(url)

        response = self.client.post(url, follow=True,
                                    data={'mailing_lists': '%s,' % mlist.id, #see MultiCremeEntityField
                                         }
                                   )
        self.assertNoFormError(response)

        with self.assertNoException():
            campaign.mailing_lists.filter(pk=mlist.id)[0]

        self.assertPOST200('/emails/campaign/%s/mailing_list/delete' % campaign.id,
                           follow=True, data={'id': mlist.id}
                          )
        self.assertFalse(campaign.mailing_lists.exists())

    def test_recipients01(self):
        mlist = MailingList.objects.create(user=self.user, name='ml01')
        self.assertFalse(mlist.emailrecipient_set.exists())

        url = '/emails/mailing_list/%s/recipient/add' % mlist.id
        self.assertGET200(url)

        recipients = ['spike.spiegel@bebop.com', 'jet.black@bebop.com']
        self.assertPOST200(url, follow=True, data={'recipients': '\n'.join(recipients)})
        self.assertEqual(set(recipients), set(r.address for r in mlist.emailrecipient_set.all()))

        #################
        response = self.assertPOST200(url, data={'recipients': 'faye.valentine#bebop.com'}) #invalid address
        self.assertFormError(response, 'form', 'recipients', [_(u"Enter a valid e-mail address.")])

        #################
        recipient = mlist.emailrecipient_set.all()[0]
        ct = ContentType.objects.get_for_model(EmailRecipient)
        self.assertPOST200('/creme_core/entity/delete_related/%s' % ct.id, follow=True, data={'id': recipient.id})

        addresses = set(r.address for r in mlist.emailrecipient_set.all())
        self.assertEqual(len(recipients) - 1, len(addresses))
        self.assertNotIn(recipient.address, addresses)

    def test_recipients02(self):
        "From CSV file"
        mlist = MailingList.objects.create(user=self.user, name='ml01')
        url = '/emails/mailing_list/%s/recipient/add_csv' % mlist.id
        self.assertGET200(url)

        recipients = ['spike.spiegel@bebop.com', 'jet.black@bebop.com']

        csvfile = StringIO('\n'.join(recipients))
        csvfile.name = 'recipients.csv' #Django uses this

        self.assertNoFormError(self.client.post(url, data={'recipients': csvfile}))
        self.assertEqual(set(recipients), set(r.address for r in mlist.emailrecipient_set.all()))

        csvfile.close()

    def test_ml_contacts01(self):
        mlist = MailingList.objects.create(user=self.user, name='ml01')
        url = '/emails/mailing_list/%s/contact/add' % mlist.id
        self.assertGET200(url)

        create = partial(Contact.objects.create, user=self.user)
        recipients = [create(first_name='Spike', last_name='Spiegel', email='spike.spiegel@bebop.com'),
                      create(first_name='Jet',   last_name='Black',   email='jet.black@bebop.com'),
                     ]
        response = self.client.post(url, data={'recipients': ','.join(str(c.id) for c in recipients) #see MultiCremeEntityField
                                              }
                                   )
        self.assertNoFormError(response)
        self.assertEqual(set(c.id for c in recipients), set(c.id for c in mlist.contacts.all()))

        ################
        contact_to_del = recipients[0]
        self.client.post('/emails/mailing_list/%s/contact/delete' % mlist.id,
                         data={'id': contact_to_del.id}
                        )

        contacts = set(mlist.contacts.all())
        self.assertEqual(len(recipients) - 1, len(contacts))
        self.assertNotIn(contact_to_del, contacts)

    def test_ml_contacts_filter01(self):
        "'All' filter"
        mlist = MailingList.objects.create(user=self.user, name='ml01')
        url = '/emails/mailing_list/%s/contact/add_from_filter' % mlist.id
        self.assertGET200(url)

        create = partial(Contact.objects.create, user=self.user)
        create(first_name='Spike', last_name='Spiegel', email='spike.spiegel@bebop.com'),
        create(first_name='Jet',   last_name='Black',   email='jet.black@bebop.com'),
        create(first_name='Ed',    last_name='Wong',    email='ed.wong@bebop.com', is_deleted=True),
        self.assertNoFormError(self.client.post(url, data={}))

        contacts = set(Contact.objects.filter(is_deleted=False))
        self.assertGreaterEqual(len(contacts), 2)
        self.assertEqual(contacts, set(mlist.contacts.all()))

    def test_ml_contacts_filter02(self):
        "With a real EntityFilter"
        create = partial(Contact.objects.create, user=self.user)
        recipients = [create(first_name='Ranma', last_name='Saotome'),
                      create(first_name='Genma', last_name='Saotome'),
                      create(first_name='Akane', last_name=u'Tendô'),
                     ]
        expected_ids = set([recipients[0].id, recipients[1].id])

        efilter = EntityFilter.create('test-filter01', 'Saotome', Contact)
        efilter.set_conditions([EntityFilterCondition.build_4_field(model=Contact,
                                                                    operator=EntityFilterCondition.IEQUALS,
                                                                    name='last_name', values=['Saotome']
                                                                   )
                               ])
        self.assertEqual(expected_ids, set(c.id for c in efilter.filter(Contact.objects.all())))

        EntityFilter.create('test-filter02', 'Useless', Organisation) #should not be a valid choice

        mlist = MailingList.objects.create(user=self.user, name='ml01')

        url = '/emails/mailing_list/%s/contact/add_from_filter' % mlist.id
        context = self.client.get(url).context

        with self.assertNoException():
            choices = [ef_id for ef_id, ef_name in context['form'].fields['filters'].choices]

        self.assertEqual(['', efilter.id], choices)

        self.assertNoFormError(self.client.post(url, data={'filters': efilter.id}))
        self.assertEqual(expected_ids, set(c.id for c in mlist.contacts.all()))

    def test_ml_orgas01(self):
        mlist = MailingList.objects.create(user=self.user, name='ml01')
        url = '/emails/mailing_list/%s/organisation/add' % mlist.id
        self.assertGET200(url)

        create = partial(Organisation.objects.create, user=self.user)
        recipients = [create(name='NERV',  email='contact@nerv.jp'),
                      create(name='Seele', email='contact@seele.jp'),
                     ]
        response = self.client.post(url, data={'recipients': ','.join(str(c.id) for c in recipients), #see MultiCremeEntityField
                                              }
                                   )
        self.assertNoFormError(response)
        self.assertEqual(set(c.id for c in recipients), set(c.id for c in mlist.organisations.all()))

        ################
        orga_to_del = recipients[0]
        self.client.post('/emails/mailing_list/%s/organisation/delete' % mlist.id,
                         data={'id': orga_to_del.id}
                        )

        orgas = set(mlist.organisations.all())
        self.assertEqual(len(recipients) - 1, len(orgas))
        self.assertNotIn(orga_to_del, orgas)

    def test_ml_orgas_filter01(self):
        " 'All' filter"
        mlist = MailingList.objects.create(user=self.user, name='ml01')
        url = '/emails/mailing_list/%s/organisation/add_from_filter' % mlist.id
        self.assertGET200(url)

        create_orga = partial(Organisation.objects.create, user=self.user)
        create_orga(name='NERV',  email='contact@nerv.jp'),
        create_orga(name='Seele', email='contact@seele.jp')
        self.assertNoFormError(self.client.post(url, data={}))

        orgas = set(Organisation.objects.all())
        self.assertGreaterEqual(len(orgas), 2)
        self.assertEqual(orgas, set(mlist.organisations.all()))

    def test_ml_orgas_filter02(self):
        "With a real EntityFilter"
        mlist = MailingList.objects.create(user=self.user, name='ml01')

        create = partial(Organisation.objects.create, user=self.user)
        recipients = [create(name='NERV',  email='contact@nerv.jp'),
                      create(name='Seele', email='contact@seele.jp'),
                      create(name='Bebop'),
                     ]
        expected_ids = set([recipients[0].id, recipients[1].id])

        efilter = EntityFilter.create('test-filter01', 'Has email', Organisation)
        efilter.set_conditions([EntityFilterCondition.build_4_field(model=Organisation,
                                                                    operator=EntityFilterCondition.ISEMPTY,
                                                                    name='email', values=[False]
                                                                   )
                               ])
        self.assertEqual(expected_ids, set(c.id for c in efilter.filter(Organisation.objects.all())))

        response = self.client.post('/emails/mailing_list/%s/organisation/add_from_filter' % mlist.id,
                                    data={'filters': efilter.id}
                                   )
        self.assertNoFormError(response)
        self.assertEqual(expected_ids, set(c.id for c in mlist.organisations.all()))

    def test_ml_tree01(self):
        create_ml = partial(MailingList.objects.create, user=self.user)
        mlist01 = create_ml(name='ml01')
        mlist02 = create_ml(name='ml02')

        self.assertFalse(mlist01.children.exists())
        self.assertFalse(mlist02.children.exists())

        url = '/emails/mailing_list/%s/child/add' % mlist01.id
        self.assertGET200(url)
        self.assertPOST200(url, data={'child': mlist02.id})
        self.assertEqual([mlist02.id], [ml.id for ml in mlist01.children.all()])
        self.assertFalse(mlist02.children.exists())

        #########################
        self.assertPOST200('/emails/mailing_list/%s/child/delete' % mlist01.id,
                           data={'id': mlist02.id}, follow=True
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

        post = lambda parent, child: self.client.post('/emails/mailing_list/%s/child/add' % parent.id,
                                                      data={'child': child.id}
                                                     )

        children_error = [_(u'List already in the children')]
        self.assertFormError(post(mlist01, mlist02), 'form', 'child', children_error)
        self.assertFormError(post(mlist01, mlist03), 'form', 'child', children_error)

        parents_error = [_(u'List already in the parents')]
        self.assertFormError(post(mlist02, mlist01), 'form', 'child', parents_error)
        self.assertFormError(post(mlist03, mlist01), 'form', 'child', parents_error)
        self.assertFormError(post(mlist01, mlist01), 'form', 'child', [_(u"A list can't be its own child")])
