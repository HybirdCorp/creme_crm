# -*- coding: utf-8 -*-

from datetime import datetime, timedelta
from StringIO import StringIO

from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType

from creme_core.tests.base import CremeTestCase

from persons.models import Contact, Organisation

from emails.models import *
from emails.models.sending import SENDING_TYPE_IMMEDIATE, SENDING_TYPE_DEFERRED


class EmailsTestCase(CremeTestCase):
    def setUp(self):
        self.populate('creme_core', 'emails')
        self.login()

    def test_campaign_createview01(self):
        response = self.client.get('/emails/campaign/add')
        self.assertEqual(response.status_code, 200)

        name     = 'my_campaign'
        response = self.client.post('/emails/campaign/add',
                                    follow=True,
                                    data={
                                            'user': self.user.pk,
                                            'name': name,
                                         }
                                   )
        self.assertEqual(response.status_code, 200)

        try:
            EmailCampaign.objects.get(name=name)
        except Exception, e:
            self.fail(str(e))

    def test_ml_createview01(self):
        response = self.client.get('/emails/mailing_list/add')
        self.assertEqual(response.status_code, 200)

        name     = 'my_mailinglist'
        response = self.client.post('/emails/mailing_list/add',
                                    follow=True,
                                    data={
                                            'user': self.user.pk,
                                            'name': name,
                                         }
                                   )
        self.assertEqual(response.status_code, 200)

        try:
            MailingList.objects.get(name=name)
        except Exception, e:
            self.fail(str(e))

    def test_ml_and_campaign(self):
        campaign = EmailCampaign.objects.create(user=self.user, name='camp01')
        mlist    = MailingList.objects.create(user=self.user,   name='ml01')

        self.failIf(campaign.mailing_lists.all())

        response = self.client.get('/emails/campaign/%s/mailing_list/add' % campaign.id)
        self.assertEqual(response.status_code, 200)

        response = self.client.post('/emails/campaign/%s/mailing_list/add' % campaign.id,
                                    follow=True,
                                    data={
                                            'mailing_lists': '%s,' % mlist.id, #see MultiCremeEntityField
                                         }
                                   )
        self.assertEqual(response.status_code, 200)

        try:
            campaign.mailing_lists.filter(pk=mlist.id)[0]
        except Exception, e:
            self.fail(str(e))

        response = self.client.post('/emails/campaign/%s/mailing_list/delete' % campaign.id,
                                    follow=True, data={'id': mlist.id}
                                   )
        self.assertEqual(response.status_code, 200)
        self.failIf(campaign.mailing_lists.all())

    def test_recipients01(self):
        mlist = MailingList.objects.create(user=self.user, name='ml01')
        self.failIf(mlist.emailrecipient_set.all())

        response = self.client.get('/emails/mailing_list/%s/recipient/add' % mlist.id)
        self.assertEqual(response.status_code, 200)

        recipients = ['spike.spiegel@bebop.com', 'jet.black@bebop.com']
        response = self.client.post('/emails/mailing_list/%s/recipient/add' % mlist.id,
                                    follow=True, data={'recipients': '\n'.join(recipients)}
                                   )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(set(recipients), set(r.address for r in mlist.emailrecipient_set.all()))

        #################
        response = self.client.post('/emails/mailing_list/%s/recipient/add' % mlist.id, follow=True,
                                    data={'recipients': 'faye.valentine#bebop.com'} #invalid address
                                   )
        self.assertEqual(response.status_code, 200)
        try:
            response.context['form'].errors
        except Exception, e:
            self.fail('There should be a ValidationError')

        #################
        recipient = mlist.emailrecipient_set.all()[0]
        ct = ContentType.objects.get_for_model(EmailRecipient)
        response = self.client.post('/creme_core/entity/delete_related/%s' % ct.id, follow=True, data={'id': recipient.id})
        self.assertEqual(response.status_code, 200)

        addresses = set(r.address for r in mlist.emailrecipient_set.all())
        self.assertEqual(len(recipients) - 1, len(addresses))
        self.assert_(recipient.address not in addresses)

    def test_recipients02(self):
        mlist = MailingList.objects.create(user=self.user, name='ml01')

        response = self.client.get('/emails/mailing_list/%s/recipient/add_csv' % mlist.id)
        self.assertEqual(response.status_code, 200)

        recipients = ['spike.spiegel@bebop.com', 'jet.black@bebop.com']

        csvfile = StringIO('\n'.join(recipients))
        csvfile.name = 'recipients.csv' #Django uses this

        response = self.client.post('/emails/mailing_list/%s/recipient/add_csv' % mlist.id,
                                    data={'recipients': csvfile}
                                   )
        self.failIf(response.context['form'].errors)
        self.assertEqual(set(recipients), set(r.address for r in mlist.emailrecipient_set.all()))

        csvfile.close()

    def test_ml_contacts01(self):
        mlist = MailingList.objects.create(user=self.user, name='ml01')

        response = self.client.get('/emails/mailing_list/%s/contact/add' % mlist.id)
        self.assertEqual(response.status_code, 200)

        create = Contact.objects.create
        recipients = [
                        create(user=self.user, first_name='Spike', last_name='Spiegel', email='spike.spiegel@bebop.com'),
                        create(user=self.user, first_name='Jet',   last_name='Black',   email='jet.black@bebop.com')
                     ]
        response = self.client.post('/emails/mailing_list/%s/contact/add' % mlist.id,
                                    data={
                                            'recipients': ','.join(str(c.id) for c in recipients) #see MultiCremeEntityField
                                         }
                                   )
        self.failIf(response.context['form'].errors)
        self.assertEqual(set(c.id for c in recipients), set(c.id for c in mlist.contacts.all()))

        ################
        contact_to_del = recipients[0]
        response = self.client.post('/emails/mailing_list/%s/contact/delete' % mlist.id,
                                    data={'id': contact_to_del.id}
                                   )

        contacts = set(mlist.contacts.all())
        self.assertEqual(len(recipients) -1, len(contacts))
        self.assert_(contact_to_del not in contacts)

    def test_ml_contacts02(self): #TODO test with a True filter too
        mlist = MailingList.objects.create(user=self.user, name='ml01')

        response = self.client.get('/emails/mailing_list/%s/contact/add_from_filter' % mlist.id)
        self.assertEqual(response.status_code, 200)

        create = Contact.objects.create
        recipients = [
                        create(user=self.user, first_name='Spike', last_name='Spiegel', email='spike.spiegel@bebop.com'),
                        create(user=self.user, first_name='Jet',   last_name='Black',   email='jet.black@bebop.com')
                     ]
        response = self.client.post('/emails/mailing_list/%s/contact/add_from_filter' % mlist.id,
                                    data={
                                            'filters': 0, #means 'All'
                                         }
                                   )
        self.failIf(response.context['form'].errors)
        self.assertEqual(set(c.id for c in recipients), set(c.id for c in mlist.contacts.all()))

    def test_ml_orgas01(self):
        mlist = MailingList.objects.create(user=self.user, name='ml01')

        response = self.client.get('/emails/mailing_list/%s/organisation/add' % mlist.id)
        self.assertEqual(response.status_code, 200)

        create = Organisation.objects.create
        recipients = [
                        create(user=self.user, name='NERV',  email='contact@nerv.jp'),
                        create(user=self.user, name='Seele', email='contact@seele.jp')
                     ]
        response = self.client.post('/emails/mailing_list/%s/organisation/add' % mlist.id,
                                    data={
                                            'recipients': ','.join(str(c.id) for c in recipients) #see MultiCremeEntityField
                                         }
                                   )
        self.failIf(response.context['form'].errors)
        self.assertEqual(set(c.id for c in recipients), set(c.id for c in mlist.organisations.all()))

        ################
        orga_to_del = recipients[0]
        response = self.client.post('/emails/mailing_list/%s/organisation/delete' % mlist.id,
                                    data={'id': orga_to_del.id}
                                   )

        orgas = set(mlist.organisations.all())
        self.assertEqual(len(recipients) -1, len(orgas))
        self.assert_(orga_to_del not in orgas)

    def test_ml_orgas02(self): #TODO test with a True filter too
        mlist = MailingList.objects.create(user=self.user, name='ml01')

        response = self.client.get('/emails/mailing_list/%s/organisation/add_from_filter' % mlist.id)
        self.assertEqual(response.status_code, 200)

        create = Organisation.objects.create
        recipients = [
                        create(user=self.user, name='NERV',  email='contact@nerv.jp'),
                        create(user=self.user, name='Seele', email='contact@seele.jp')
                     ]
        response = self.client.post('/emails/mailing_list/%s/organisation/add_from_filter' % mlist.id,
                                    data={
                                            'filters': 0, #means 'All'
                                         }
                                   )
        self.failIf(response.context['form'].errors)
        self.assertEqual(set(c.id for c in recipients), set(c.id for c in mlist.organisations.all()))

    def test_ml_tree01(self):
        create_ml = MailingList.objects.create
        mlist01 = create_ml(user=self.user, name='ml01')
        mlist02 = create_ml(user=self.user, name='ml02')

        self.failIf(mlist01.children.all())
        self.failIf(mlist02.children.all())

        response = self.client.get('/emails/mailing_list/%s/child/add' % mlist01.id)
        self.assertEqual(response.status_code, 200)

        response = self.client.post('/emails/mailing_list/%s/child/add' % mlist01.id,
                                    data={'child': mlist02.id}
                                   )
        self.assertEqual([mlist02.id], [ml.id for ml in mlist01.children.all()])
        self.failIf(mlist02.children.all())

        #########################
        response = self.client.post('/emails/mailing_list/%s/child/delete' % mlist01.id,
                                    data={'id': mlist02.id}, follow=True
                                   )
        self.assertEqual(response.status_code, 200)
        self.failIf(mlist01.children.all())
        self.failIf(mlist02.children.all())

    def test_ml_tree02(self):
        create_ml = MailingList.objects.create
        mlist01 = create_ml(user=self.user, name='ml01')
        mlist02 = create_ml(user=self.user, name='ml02')
        mlist03 = create_ml(user=self.user, name='ml03')

        mlist01.children.add(mlist02)
        mlist02.children.add(mlist03)

        response = self.client.post('/emails/mailing_list/%s/child/add' % mlist01.id,
                                    data={'child': mlist02.id}
                                   )
        self.assert_(response.context['form'].errors)

        response = self.client.post('/emails/mailing_list/%s/child/add' % mlist01.id,
                                    data={'child': mlist03.id}
                                   )
        self.assert_(response.context['form'].errors)

        response = self.client.post('/emails/mailing_list/%s/child/add' % mlist03.id,
                                    data={'child': mlist01.id}
                                   )
        self.assert_(response.context['form'].errors)

        response = self.client.post('/emails/mailing_list/%s/child/add' % mlist03.id,
                                    data={'child': mlist02.id}
                                   )
        self.assert_(response.context['form'].errors)

    def test_template_createview01(self): #TODO: test attachments too
        response = self.client.get('/emails/template/add')
        self.assertEqual(response.status_code, 200)

        name    = 'my_template'
        subject = 'Insert a joke *here*'
        body    = 'blablabla'
        response = self.client.post('/emails/template/add', follow=True,
                                    data={
                                            'user':    self.user.pk,
                                            'name':    name,
                                            'subject': subject,
                                            'body':    body,
                                         }
                                   )
        self.assertEqual(response.status_code, 200)

        try:
            template = EmailTemplate.objects.get(name=name)
        except Exception, e:
            self.fail(str(e))

        self.assertEqual(subject, template.subject)
        self.assertEqual(body,    template.body)

    def test_sending01(self):
        # We create voluntarily duplicates (recipients taht have same addresses
        # than Contact/Organisation, MailingList that contain the same addresses)
        # EmailSending should not contain duplicates.
        camp = EmailCampaign.objects.create(user=self.user, name='camp01')

        self.failIf(camp.sendings_set.all())

        create_ml = MailingList.objects.create
        mlist01 = create_ml(user=self.user, name='ml01')
        mlist02 = create_ml(user=self.user, name='ml02')
        mlist03 = create_ml(user=self.user, name='ml03')

        mlist01.children.add(mlist02, mlist03)
        camp.mailing_lists.add(mlist01)

        addresses = [
                    'spike.spiegel@bebop.com',  #0
                    'jet.black@bebop.com',      #1
                    'faye.valentine@bebop.com', #2
                    'ed.wong@bebop.com',        #3
                    'ein@bebop.com',            #4
                    'contact@nerv.jp',          #5
                    'contact@seele.jp',         #6
                  ]

        create_recipient = EmailRecipient.objects.create
        create_recipient(ml=mlist01, address=addresses[0])
        create_recipient(ml=mlist02, address=addresses[2])
        create_recipient(ml=mlist02, address=addresses[3])
        create_recipient(ml=mlist03, address=addresses[3])
        create_recipient(ml=mlist03, address=addresses[4])
        create_recipient(ml=mlist03, address=addresses[6])

        create_contact = Contact.objects.create
        contacts = [
                    create_contact(user=self.user, first_name='Spike', last_name='Spiegel', email=addresses[0]),
                    create_contact(user=self.user, first_name='Jet',   last_name='Black',   email=addresses[1])
                   ]

        mlist01.contacts.add(contacts[0])
        mlist02.contacts.add(contacts[0])
        mlist02.contacts.add(contacts[1])

        create_orga = Organisation.objects.create
        orgas = [
                        create_orga(user=self.user, name='NERV',  email=addresses[5]),
                        create_orga(user=self.user, name='Seele', email=addresses[6])
                     ]

        mlist02.organisations.add(orgas[0])
        mlist03.organisations.add(orgas[0])
        mlist03.organisations.add(orgas[1])

        subject = 'SUBJECT'
        body    = 'BODYYYYYYYYYYY'
        template = EmailTemplate.objects.create(user=self.user, name='name', subject=subject, body=body)

        response = self.client.get('/emails/campaign/%s/sending/add' % camp.id)
        self.assertEqual(response.status_code, 200)

        response = self.client.post('/emails/campaign/%s/sending/add' % camp.id,
                                    data = {
                                            'sender':   'vicious@reddragons.mrs',
                                            'type':     SENDING_TYPE_IMMEDIATE,
                                            'template': template.id,
                                    }
                                   )
        self.failIf(response.context['form'].errors)
        self.assertEqual(response.status_code, 200)

        sendings = EmailCampaign.objects.get(pk=camp.id).sendings_set.all()
        self.assertEqual(1, len(sendings))

        sending = sendings[0]
        self.assertEqual(sending.type,    SENDING_TYPE_IMMEDIATE)
        self.assertEqual(sending.subject, subject)
        self.assertEqual(sending.body,    body)

        mails = sending.mails_set.all()
        self.assertEqual(len(addresses), len(mails))

        addr_set = set(mail.recipient for mail in mails)
        self.assert_(all(address in addr_set for address in addresses))

        related_set = set(mail.recipient_entity_id for mail in mails)
        self.assert_(all(c.id in related_set for c in contacts))
        self.assert_(all(o.id in related_set for o in orgas))

        #TODO: use the Django fake email framework to test even better

    def test_sending02(self): #test template
        first_name = 'Spike'
        last_name  = 'Spiegel'

        camp    = EmailCampaign.objects.create(user=self.user, name='camp01')
        mlist   = MailingList.objects.create(user=self.user, name='ml01')
        contact = Contact.objects.create(user=self.user, first_name=first_name, last_name=last_name, email='spike.spiegel@bebop.com')

        camp.mailing_lists.add(mlist)
        mlist.contacts.add(contact)

        subject = 'Hello'
        body    = 'Your name is: {{first_name}} {{last_name}} !'
        template = EmailTemplate.objects.create(user=self.user, name='name', subject=subject, body=body)

        response = self.client.post('/emails/campaign/%s/sending/add' % camp.id,
                                    data = {
                                            'sender':   'vicious@reddragons.mrs',
                                            'type':     SENDING_TYPE_IMMEDIATE,
                                            'template': template.id,
                                    }
                                   )
        self.failIf(response.context['form'].errors)
        self.assertEqual(response.status_code, 200)

        try:
            sending = EmailCampaign.objects.get(pk=camp.id).sendings_set.all()[0]
        except Exception, e:
            self.fail(str(e))

        self.assertEqual(sending.subject, subject)

        try:
            mail = sending.mails_set.all()[0]
        except Exception, e:
            self.fail(str(e))

        self.assertEqual('Your name is: %s %s !' % (first_name, last_name), mail.get_body())

    def test_sending03(self): #test deferred
        camp     = EmailCampaign.objects.create(user=self.user, name='camp01')
        template = EmailTemplate.objects.create(user=self.user, name='name', subject='subject', body='body')

        now  = datetime.now()
        sending_date = now.replace(year=now.year + 1)

        response = self.client.post('/emails/campaign/%s/sending/add' % camp.id,
                                    data = {
                                            'sender':   'vicious@reddragons.mrs',
                                            'type':     SENDING_TYPE_DEFERRED,
                                            'template': template.id,
                                            'sending_date': sending_date.strftime('%Y-%m-%d'), #future: OK
                                            'hour':         sending_date.hour,
                                            'minute':       sending_date.minute,
                                    }
                                   )
        self.failIf(response.context['form'].errors)
        self.assertEqual(response.status_code, 200)

        try:
            sending = EmailCampaign.objects.get(pk=camp.id).sendings_set.all()[0]
        except Exception, e:
            self.fail(str(e))

        format = '%d %m %Y %H %M'
        self.assertEqual(sending_date.strftime(format), sending.sending_date.strftime(format))

        response = self.client.post('/emails/campaign/%s/sending/add' % camp.id,
                                    data = {
                                            'sender':   'vicious@reddragons.mrs',
                                            'type':     SENDING_TYPE_DEFERRED,
                                            'template': template.id,
                                    }
                                   )
        self.assert_(response.context['form'].errors, "'sending_date' should be required !?")

        response = self.client.post('/emails/campaign/%s/sending/add' % camp.id,
                                    data = {
                                            'sender':       'vicious@reddragons.mrs',
                                            'type':         SENDING_TYPE_DEFERRED,
                                            'template':     template.id,
                                            'sending_date': (now - timedelta(days=1)).strftime('%Y-%m-%d'), #past: KO
                                    }
                                   )
        self.assert_(response.context['form'].errors)
