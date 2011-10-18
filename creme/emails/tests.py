# -*- coding: utf-8 -*-

try:
    from datetime import datetime, timedelta
    from pickle import loads
    from StringIO import StringIO

    from django.utils.translation import ugettext as _
    from django.contrib.auth.models import User
    from django.contrib.contenttypes.models import ContentType
    from django.conf import settings

    from creme_core.tests.base import CremeTestCase
    from creme_core.models import EntityFilter, EntityFilterCondition, Relation

    from persons.models import Contact, Organisation

    #from documents.models import Document, Folder, FolderCategory

    from emails.models import *
    from emails.models.sending import SENDING_TYPE_IMMEDIATE, SENDING_TYPE_DEFERRED
    from emails.constants import *
except Exception as e:
    print 'Error:', e


class EmailsTestCase(CremeTestCase):
    def test_populate(self):
        self.populate('emails')
        self.get_relationtype_or_fail(REL_SUB_MAIL_RECEIVED, [EntityEmail], [Organisation, Contact])
        self.get_relationtype_or_fail(REL_SUB_MAIL_SENDED,   [EntityEmail], [Organisation, Contact])
        self.get_relationtype_or_fail(REL_SUB_RELATED_TO,    [EntityEmail])

    def test_portal(self):
        self.populate('creme_core', 'creme_config', 'emails')
        self.login()
        self.assertEqual(200, self.client.get('/emails/').status_code)


class CampaignTestCase(CremeTestCase):
    def setUp(self):
        self.populate('creme_core', 'creme_config', 'emails')
        self.login()

    def test_create(self):
        url = '/emails/campaign/add'
        self.assertEqual(200, self.client.get(url).status_code)

        name     = 'my_campaign'
        response = self.client.post(url, follow=True,
                                    data={
                                            'user': self.user.pk,
                                            'name': name,
                                         }
                                   )
        self.assertNoFormError(response)
        self.assertEqual(200, response.status_code)
        self.get_object_or_fail(EmailCampaign, name=name)

    def test_edit(self):
        name = 'my_campaign'
        camp = EmailCampaign.objects.create(user=self.user, name=name)

        url = '/emails/campaign/edit/%s' % camp.id
        self.assertEqual(200, self.client.get(url).status_code)

        name += '_edited'
        response = self.client.post(url, follow=True,
                                    data={
                                            'user': self.user.pk,
                                            'name': name,
                                         }
                                   )
        self.assertNoFormError(response)
        self.assertEqual(200,  response.status_code)
        self.assertEqual(name, EmailCampaign.objects.get(pk=camp.id).name)

    def test_listview(self):
        response = self.client.get('/emails/campaigns')
        self.assertEqual(200, response.status_code)

        try:
            response.context['entities']
        except KeyError as e:
            self.fail(str(e))


class MailingListsTestCase(CremeTestCase):
    def setUp(self):
        self.populate('creme_core', 'creme_config', 'emails')
        self.login()

    def test_create01(self):
        url = '/emails/mailing_list/add'
        self.assertEqual(200, self.client.get(url).status_code)

        name     = 'my_mailinglist'
        response = self.client.post(url, follow=True,
                                    data={
                                            'user': self.user.pk,
                                            'name': name,
                                         }
                                   )
        self.assertNoFormError(response)
        self.assertEqual(200, response.status_code)
        self.get_object_or_fail(MailingList, name=name)

    def test_edit(self):
        name = 'my_mailinglist'
        mlist = MailingList.objects.create(user=self.user,   name=name)
        url = '/emails/mailing_list/edit/%s' % mlist.id
        self.assertEqual(200, self.client.get(url).status_code)

        name += '_edited'
        response = self.client.post(url, follow=True,
                                    data={
                                            'user': self.user.pk,
                                            'name': name,
                                         }
                                   )
        self.assertNoFormError(response)
        self.assertEqual(200,  response.status_code)
        self.assertEqual(name, self.refresh(mlist).name)

    def test_listview(self):
        response = self.client.get('/emails/mailing_lists')
        self.assertEqual(200, response.status_code)

        try:
            response.context['entities']
        except KeyError, e:
            self.fail(str(e))

    def test_ml_and_campaign(self):
        campaign = EmailCampaign.objects.create(user=self.user, name='camp01')
        mlist    = MailingList.objects.create(user=self.user,   name='ml01')
        self.assertFalse(campaign.mailing_lists.all())

        url = '/emails/campaign/%s/mailing_list/add' % campaign.id
        self.assertEqual(200, self.client.get(url).status_code)

        response = self.client.post(url, follow=True,
                                    data={
                                            'mailing_lists': '%s,' % mlist.id, #see MultiCremeEntityField
                                         }
                                   )
        self.assertNoFormError(response)
        self.assertEqual(200, response.status_code)

        try:
            campaign.mailing_lists.filter(pk=mlist.id)[0]
        except Exception as e:
            self.fail(str(e))

        response = self.client.post('/emails/campaign/%s/mailing_list/delete' % campaign.id,
                                    follow=True, data={'id': mlist.id}
                                   )
        self.assertEqual(200, response.status_code)
        self.assertFalse(campaign.mailing_lists.all())

    def test_recipients01(self):
        mlist = MailingList.objects.create(user=self.user, name='ml01')
        self.assertFalse(mlist.emailrecipient_set.all())

        url = '/emails/mailing_list/%s/recipient/add' % mlist.id
        self.assertEqual(200, self.client.get(url).status_code)

        recipients = ['spike.spiegel@bebop.com', 'jet.black@bebop.com']
        response = self.client.post(url, follow=True, data={'recipients': '\n'.join(recipients)})
        self.assertEqual(200, response.status_code)
        self.assertEqual(set(recipients), set(r.address for r in mlist.emailrecipient_set.all()))

        #################
        response = self.client.post('/emails/mailing_list/%s/recipient/add' % mlist.id, follow=True,
                                    data={'recipients': 'faye.valentine#bebop.com'} #invalid address
                                   )
        self.assertEqual(response.status_code, 200)
        try:
            response.context['form'].errors
        except Exception as e:
            self.fail('There should be a ValidationError')

        #################
        recipient = mlist.emailrecipient_set.all()[0]
        ct = ContentType.objects.get_for_model(EmailRecipient)
        response = self.client.post('/creme_core/entity/delete_related/%s' % ct.id, follow=True, data={'id': recipient.id})
        self.assertEqual(200, response.status_code)

        addresses = set(r.address for r in mlist.emailrecipient_set.all())
        self.assertEqual(len(recipients) - 1, len(addresses))
        self.assertNotIn(recipient.address, addresses)

    def test_recipients02(self):
        mlist = MailingList.objects.create(user=self.user, name='ml01')
        url = '/emails/mailing_list/%s/recipient/add_csv' % mlist.id
        self.assertEqual(200, self.client.get(url).status_code)

        recipients = ['spike.spiegel@bebop.com', 'jet.black@bebop.com']

        csvfile = StringIO('\n'.join(recipients))
        csvfile.name = 'recipients.csv' #Django uses this

        response = self.client.post(url, data={'recipients': csvfile})
        self.assertNoFormError(response)
        self.assertEqual(set(recipients), set(r.address for r in mlist.emailrecipient_set.all()))

        csvfile.close()

    def test_ml_contacts01(self):
        mlist = MailingList.objects.create(user=self.user, name='ml01')
        url = '/emails/mailing_list/%s/contact/add' % mlist.id
        self.assertEqual(200, self.client.get(url).status_code)

        create = Contact.objects.create
        recipients = [create(user=self.user, first_name='Spike', last_name='Spiegel', email='spike.spiegel@bebop.com'),
                      create(user=self.user, first_name='Jet',   last_name='Black',   email='jet.black@bebop.com'),
                     ]
        response = self.client.post(url, data={
                                                'recipients': ','.join(str(c.id) for c in recipients) #see MultiCremeEntityField
                                              }
                                   )
        self.assertNoFormError(response)
        self.assertEqual(set(c.id for c in recipients), set(c.id for c in mlist.contacts.all()))

        ################
        contact_to_del = recipients[0]
        response = self.client.post('/emails/mailing_list/%s/contact/delete' % mlist.id,
                                    data={'id': contact_to_del.id}
                                   )

        contacts = set(mlist.contacts.all())
        self.assertEqual(len(recipients) - 1, len(contacts))
        self.assertNotIn(contact_to_del, contacts)

    def test_ml_contacts_filter01(self): #'All' filter
        mlist = MailingList.objects.create(user=self.user, name='ml01')
        url = '/emails/mailing_list/%s/contact/add_from_filter' % mlist.id
        self.assertEqual(200, self.client.get(url).status_code)

        create = Contact.objects.create
        recipients = [create(user=self.user, first_name='Spike', last_name='Spiegel', email='spike.spiegel@bebop.com'),
                      create(user=self.user, first_name='Jet',   last_name='Black',   email='jet.black@bebop.com'),
                     ]
        response = self.client.post(url, data={})
        self.assertNoFormError(response)
        self.assertEqual(set(c.id for c in recipients), set(c.id for c in mlist.contacts.all()))

    def test_ml_contacts_filter02(self): #A true filter
        create = Contact.objects.create
        recipients = [create(user=self.user, first_name='Ranma', last_name='Saotome'),
                      create(user=self.user, first_name='Genma', last_name='Saotome'),
                      create(user=self.user, first_name='Akane', last_name=u'Tendô'),
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
        try:
            choices = [ef_id for ef_id, ef_name in context['form'].fields['filters'].choices]
        except Exception as e:
            self.fail(str(e))

        self.assertEqual(['', efilter.id], choices)

        response = self.client.post(url, data={'filters': efilter.id})
        self.assertNoFormError(response)
        self.assertEqual(expected_ids, set(c.id for c in mlist.contacts.all()))

    def test_ml_orgas01(self):
        mlist = MailingList.objects.create(user=self.user, name='ml01')
        url = '/emails/mailing_list/%s/organisation/add' % mlist.id
        self.assertEqual(200, self.client.get(url).status_code)

        create = Organisation.objects.create
        recipients = [create(user=self.user, name='NERV',  email='contact@nerv.jp'),
                      create(user=self.user, name='Seele', email='contact@seele.jp'),
                     ]
        response = self.client.post(url,
                                    data={'recipients': ','.join(str(c.id) for c in recipients), #see MultiCremeEntityField
                                         }
                                   )
        self.assertNoFormError(response)
        self.assertEqual(set(c.id for c in recipients), set(c.id for c in mlist.organisations.all()))

        ################
        orga_to_del = recipients[0]
        response = self.client.post('/emails/mailing_list/%s/organisation/delete' % mlist.id,
                                    data={'id': orga_to_del.id}
                                   )

        orgas = set(mlist.organisations.all())
        self.assertEqual(len(recipients) - 1, len(orgas))
        self.assertNotIn(orga_to_del, orgas)

    def test_ml_orgas_filter01(self): # 'All' filter
        mlist = MailingList.objects.create(user=self.user, name='ml01')

        url = '/emails/mailing_list/%s/organisation/add_from_filter' % mlist.id
        self.assertEqual(200, self.client.get(url).status_code)

        create = Organisation.objects.create
        recipients = [create(user=self.user, name='NERV',  email='contact@nerv.jp'),
                      create(user=self.user, name='Seele', email='contact@seele.jp')
                     ]
        response = self.client.post(url, data={})
        self.assertNoFormError(response)
        self.assertEqual(set(c.id for c in recipients), set(c.id for c in mlist.organisations.all()))

    def test_ml_orgas_filter02(self): #"true" Filter
        mlist = MailingList.objects.create(user=self.user, name='ml01')

        create = Organisation.objects.create
        recipients = [create(user=self.user, name='NERV',  email='contact@nerv.jp'),
                      create(user=self.user, name='Seele', email='contact@seele.jp'),
                      create(user=self.user, name='Bebop'),
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
        create_ml = MailingList.objects.create
        mlist01 = create_ml(user=self.user, name='ml01')
        mlist02 = create_ml(user=self.user, name='ml02')

        self.assertFalse(mlist01.children.all())
        self.assertFalse(mlist02.children.all())

        url = '/emails/mailing_list/%s/child/add' % mlist01.id
        self.assertEqual(200, self.client.get(url).status_code)

        self.assertEqual(200, self.client.post(url, data={'child': mlist02.id}).status_code)
        self.assertEqual([mlist02.id], [ml.id for ml in mlist01.children.all()])
        self.assertFalse(mlist02.children.all())

        #########################
        response = self.client.post('/emails/mailing_list/%s/child/delete' % mlist01.id,
                                    data={'id': mlist02.id}, follow=True
                                   )
        self.assertEqual(200, response.status_code)
        self.assertFalse(mlist01.children.all())
        self.assertFalse(mlist02.children.all())

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
        self.assertTrue(response.context['form'].errors)

        response = self.client.post('/emails/mailing_list/%s/child/add' % mlist01.id,
                                    data={'child': mlist03.id}
                                   )
        self.assertTrue(response.context['form'].errors)

        response = self.client.post('/emails/mailing_list/%s/child/add' % mlist03.id,
                                    data={'child': mlist01.id}
                                   )
        self.assertTrue(response.context['form'].errors)

        response = self.client.post('/emails/mailing_list/%s/child/add' % mlist03.id,
                                    data={'child': mlist02.id}
                                   )
        self.assertTrue(response.context['form'].errors)


class TemplatesTestCase(CremeTestCase):
    def setUp(self):
        self.populate('creme_core', 'creme_config', 'emails')
        self.login()

    def test_createview01(self): #TODO: test attachments & images
        url = '/emails/template/add'
        self.assertEqual(200, self.client.get(url).status_code)

        name      = 'my_template'
        subject   = 'Insert a joke *here*'
        body      = 'blablabla {{first_name}}'
        body_html = '<p>blablabla {{last_name}}</p>'
        response = self.client.post(url, follow=True,
                                    data={
                                            'user':      self.user.pk,
                                            'name':      name,
                                            'subject':   subject,
                                            'body':      body,
                                            'body_html': body_html,
                                         }
                                   )
        self.assertNoFormError(response)
        self.assertEqual(200, response.status_code)

        template = self.get_object_or_fail(EmailTemplate, name=name)
        self.assertEqual(subject,   template.subject)
        self.assertEqual(body,      template.body)
        self.assertEqual(body_html, template.body_html)

    def test_createview02(self): # variable errors
        response = self.client.post('/emails/template/add', follow=True,
                                    data={
                                            'user':      self.user.pk,
                                            'name':      'my_template',
                                            'subject':   'Insert a joke *here*',
                                            'body':      'blablabla {{unexisting_var}}',
                                            'body_html': '<p>blablabla</p> {{foobar_var}}',
                                         }
                                   )
        self.assertEqual(200, response.status_code)

        error_msg = _(u'The following variables are invalid: %s')
        self.assertFormError(response, 'form', 'body',      [error_msg % [u'unexisting_var']])
        self.assertFormError(response, 'form', 'body_html', [error_msg % [u'foobar_var']])

    def test_editview01(self):
        name    = 'my template'
        subject = 'Insert a joke *here*'
        body    = 'blablabla'
        template = EmailTemplate.objects.create(user=self.user, name=name, subject=subject, body=body)

        url = '/emails/template/edit/%s' % template.id
        self.assertEqual(200, self.client.get(url).status_code)

        name    = name.title()
        subject = subject.title()
        body    += ' edited'
        response = self.client.post(url, follow=True,
                                    data={
                                            'user':    self.user.pk,
                                            'name':    name,
                                            'subject': subject,
                                            'body':    body,
                                         }
                                   )
        self.assertNoFormError(response)
        self.assertEqual(200, response.status_code)

        template = self.refresh(template)
        self.assertEqual(name,    template.name)
        self.assertEqual(subject, template.subject)
        self.assertEqual(body,    template.body)
        self.assertEqual('',      template.body_html)

    def test_listview(self):
        response = self.client.get('/emails/templates')
        self.assertEqual(200, response.status_code)

        try:
            response.context['entities']
        except KeyError as e:
            self.fail(str(e))


class SendingsTestCase(CremeTestCase):
    def setUp(self):
        self.populate('creme_config')
        self.login()

    def _load_or_fail(self, data):
        try:
            return loads(data.encode('utf-8'))
        except Exception as e:
            self.fail(str(e))

    def test_create01(self):
        # We create voluntarily duplicates (recipients that have same addresses
        # than Contact/Organisation, MailingList that contain the same addresses)
        # EmailSending should not contain duplicates.
        camp = EmailCampaign.objects.create(user=self.user, name='camp01')

        self.assertFalse(camp.sendings_set.exists())

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
        contacts = [create_contact(user=self.user, first_name='Spike', last_name='Spiegel', email=addresses[0]),
                    create_contact(user=self.user, first_name='Jet',   last_name='Black',   email=addresses[1]),
                   ]

        mlist01.contacts.add(contacts[0])
        mlist02.contacts.add(contacts[0])
        mlist02.contacts.add(contacts[1])

        create_orga = Organisation.objects.create
        orgas = [create_orga(user=self.user, name='NERV',  email=addresses[5]),
                 create_orga(user=self.user, name='Seele', email=addresses[6]),
                ]

        mlist02.organisations.add(orgas[0])
        mlist03.organisations.add(orgas[0])
        mlist03.organisations.add(orgas[1])

        subject = 'SUBJECT'
        body    = 'BODYYYYYYYYYYY'
        template = EmailTemplate.objects.create(user=self.user, name='name', subject=subject, body=body)

        url = '/emails/campaign/%s/sending/add' % camp.id
        self.assertEqual(self.client.get(url).status_code, 200)

        response = self.client.post(url, data={
                                                'sender':   'vicious@reddragons.mrs',
                                                'type':     SENDING_TYPE_IMMEDIATE,
                                                'template': template.id,
                                              }
                                   )
        self.assertFalse(response.context['form'].errors)
        self.assertEqual(200, response.status_code)

        sendings = EmailCampaign.objects.get(pk=camp.id).sendings_set.all()
        self.assertEqual(1, len(sendings))

        sending = sendings[0]
        self.assertEqual(SENDING_TYPE_IMMEDIATE, sending.type)
        self.assertEqual(subject,                sending.subject)
        self.assertEqual(body,                   sending.body)
        self.assertEqual('',                     sending.body_html)

        mails = sending.mails_set.all()
        self.assertEqual(len(addresses), len(mails))

        addr_set = set(mail.recipient for mail in mails)
        self.assertTrue(all(address in addr_set for address in addresses))

        related_set = set(mail.recipient_entity_id for mail in mails)
        self.assertTrue(all(c.id in related_set for c in contacts))
        self.assertTrue(all(o.id in related_set for o in orgas))

        self.assertEqual('', sending.mails_set.filter(recipient_entity=None)[0].body)
        self.assertEqual('', sending.mails_set.get(recipient_entity=contacts[0].id).body)
        self.assertEqual('', sending.mails_set.get(recipient_entity=orgas[0].id).body)

        mail = mails[0]
        self.assertEqual(200, self.client.get('/emails/mails_history/%s' % mail.id).status_code)

        response = self.client.get('/emails/mail/get_body/%s' % mail.id)
        self.assertEqual(200, response.status_code)
        self.assertEqual(u'', response.content)

        #TODO: use the Django fake email framework to test even better

        #test delete campaign --------------------------------------------------
        response = self.client.post('/creme_core/entity/delete/%s' % camp.id)
        self.assertEqual(302, response.status_code)
        self.assertFalse(EmailCampaign.objects.exists())
        self.assertFalse(EmailSending.objects.exists())
        self.assertFalse(LightWeightEmail.objects.exists())

    def test_create02(self): #test template
        first_name = 'Spike'
        last_name  = 'Spiegel'

        camp    = EmailCampaign.objects.create(user=self.user, name='camp01')
        mlist   = MailingList.objects.create(user=self.user, name='ml01')
        contact = Contact.objects.create(user=self.user, first_name=first_name, last_name=last_name, email='spike.spiegel@bebop.com')

        camp.mailing_lists.add(mlist)
        mlist.contacts.add(contact)

        subject = 'Hello'
        body    = 'Your first name is: {{first_name}} !'
        body_html    = '<p>Your last name is: {{last_name}} !</p>'
        template = EmailTemplate.objects.create(user=self.user, name='name', subject=subject, body=body, body_html=body_html)
        response = self.client.post('/emails/campaign/%s/sending/add' % camp.id,
                                    data = {
                                            'sender':   'vicious@reddragons.mrs',
                                            'type':     SENDING_TYPE_IMMEDIATE,
                                            'template': template.id,
                                           }
                                   )
        self.assertNoFormError(response)
        self.assertEqual(200, response.status_code)

        try:
            sending = self.refresh(camp).sendings_set.all()[0]
        except Exception as e:
            self.fail(str(e))

        self.assertEqual(sending.subject, subject)

        try:
            mail = sending.mails_set.all()[0]
        except Exception as e:
            self.fail(str(e))

        self.assertEqual('Your first name is: %s !' % first_name, mail.get_body())

        rendered_body = '<p>Your last name is: %s !</p>' % last_name
        self.assertEqual(rendered_body, mail.get_body_html())
        self.assertEqual(rendered_body, self.client.get('/emails/mail/get_body/%s' % mail.id).content)

        #test delete sending ---------------------------------------------------
        ct = ContentType.objects.get_for_model(EmailSending)
        response = self.client.post('/creme_core/entity/delete_related/%s' % ct.id, data={'id': sending.pk})
        self.assertEqual(302, response.status_code)
        self.assertFalse(EmailSending.objects.filter(pk=sending.pk).exists())
        self.assertFalse(LightWeightEmail.objects.filter(pk=mail.pk).exists())

    def test_create03(self): #test deferred
        camp     = EmailCampaign.objects.create(user=self.user, name='camp01')
        template = EmailTemplate.objects.create(user=self.user, name='name', subject='subject', body='body')
        url = '/emails/campaign/%s/sending/add' % camp.id

        now  = datetime.now()
        sending_date = now.replace(year=now.year + 1)
        response = self.client.post(url, data={
                                                'sender':       'vicious@reddragons.mrs',
                                                'type':         SENDING_TYPE_DEFERRED,
                                                'template':     template.id,
                                                'sending_date': sending_date.strftime('%Y-%m-%d'), #future: OK
                                                'hour':         sending_date.hour,
                                                'minute':       sending_date.minute,
                                              }
                                   )
        self.assertNoFormError(response)
        self.assertEqual(200, response.status_code)

        try:
            sending = self.refresh(camp).sendings_set.all()[0]
        except Exception as e:
            self.fail(str(e))

        format = '%d %m %Y %H %M'
        self.assertEqual(sending_date.strftime(format), sending.sending_date.strftime(format))

        response = self.client.post(url, data={
                                                'sender':   'vicious@reddragons.mrs',
                                                'type':     SENDING_TYPE_DEFERRED,
                                                'template': template.id,
                                              }
                                   )
        self.assertTrue(response.context['form'].errors, "'sending_date' should be required !?")

        response = self.client.post(url, data={
                                                'sender':       'vicious@reddragons.mrs',
                                                'type':         SENDING_TYPE_DEFERRED,
                                                'template':     template.id,
                                                'sending_date': (now - timedelta(days=1)).strftime('%Y-%m-%d'), #past: KO
                                              }
                                   )
        self.assertTrue(response.context['form'].errors)


class SignaturesTestCase(CremeTestCase):
    def setUp(self):
        self.populate('creme_core', 'creme_config', )

    def login(self, is_superuser=True):
        super(SignaturesTestCase, self).login(is_superuser, allowed_apps=['emails'])

    def test_create01(self):
        self.login()
        self.assertFalse(EmailSignature.objects.count())

        url = '/emails/signature/add'
        self.assertEqual(200, self.client.get(url).status_code)

        name = 'Polite signature'
        body = 'I love you'
        response = self.client.post(url, data={
                                                'name': name,
                                                'body': body,
                                              }
                                   )
        self.assertNoFormError(response)
        self.assertEqual(200, response.status_code)

        signature = self.get_object_or_fail(EmailSignature, name=name)
        self.assertEqual(body,      signature.body)
        self.assertEqual(self.user, signature.user)
        self.assertEqual(0,         signature.images.count())

    #TODO: create with images....

    def test_edit01(self):
        self.login()

        name = 'Funny signature'
        body = 'I love you... not'
        signature = EmailSignature.objects.create(user=self.user, name=name, body=body)

        url = '/emails/signature/edit/%s' % signature.id
        self.assertEqual(200, self.client.get(url).status_code)

        name += '_edited'
        body += '_edited'
        response = self.client.post(url, data={
                                                'name': name,
                                                'body': body,
                                              }
                                   )
        self.assertNoFormError(response)
        self.assertEqual(200, response.status_code)

        signature = self.refresh(signature)
        self.assertEqual(name,      signature.name)
        self.assertEqual(body,      signature.body)
        self.assertEqual(self.user, signature.user)
        self.assertFalse(signature.images.exists())

    #TODO: edit with images....

    def test_edit02(self): #'perm' error
        self.login(is_superuser=False)

        signature = EmailSignature.objects.create(user=self.other_user, name='Funny signature', body='I love you... not')
        self.assertEqual(403, self.client.get('/emails/signature/edit/%s' % signature.id).status_code)

    def test_edit03(self): #superuser can delete all signatures
        self.login()

        signature = EmailSignature.objects.create(user=self.other_user, name='Funny signature', body='I love you... not')
        self.assertEqual(200, self.client.get('/emails/signature/edit/%s' % signature.id).status_code)

    def test_delete01(self):
        self.login()

        signature = EmailSignature.objects.create(user=self.user, name="Spike's one", body='See U space cowboy')
        self.assertEqual(200, self.client.post('/emails/signature/delete', data={'id': signature.id}, follow=True).status_code)
        self.assertFalse(EmailSignature.objects.filter(pk=signature.id).exists())

    def test_delete02(self): #'perm' error
        self.login(is_superuser=False)

        signature = EmailSignature.objects.create(user=self.other_user, name="Spike's one", body='See U space cowboy')
        self.assertEqual(403, self.client.post('/emails/signature/delete', data={'id': signature.id}, follow=True).status_code)
        self.assertEqual(1, EmailSignature.objects.filter(pk=signature.id).count())

    def test_delete03(self): #deps
        self.login()

        signature = EmailSignature.objects.create(user=self.user, name="Spike's one", body='See U space cowboy')
        template  = EmailTemplate.objects.create(user=self.user, name='name', signature=signature,
                                                 subject='Hello', body='Do you know the real folk blues ?'
                                                )

        self.assertEqual(200, self.client.post('/emails/signature/delete', data={'id': signature.id}, follow=True).status_code)
        self.assertFalse(EmailSignature.objects.filter(pk=signature.id).exists())

        template = self.get_object_or_fail(EmailTemplate, pk=template.id)
        self.assertIsNone(template.signature)


class EntityEmailTestCase(CremeTestCase):
    def setUp(self):
        self.populate('creme_core', 'creme_config', 'emails')
        self.login()

        user = self.user
        self.user_contact = Contact.objects.create(user=user, is_user=user,
                                                   first_name='Re-l',
                                                   last_name='Mayer',
                                                   email='re-l.mayer@rpd.rmd',
                                                  )

    def test_createview01(self):
        user = self.user

        recipient = 'vincent.law@immigrates.rmd'
        contact = Contact.objects.create(user=user, first_name='Vincent', last_name='Law', email=recipient)
        url = '/emails/mail/add/%s' % contact.id

        response = self.client.get(url)
        self.assertEqual(200, response.status_code)

        try:
            c_recipients = response.context['form'].fields['c_recipients']
        except Exception as e:
            self.fail(str(e))

        self.assertEqual([contact.id], c_recipients.initial)

        sender = self.user_contact.email
        body = 'Freeze !'
        body_html = '<p>Freeze !</p>'
        subject = 'Under arrest'
        response = self.client.post(url, data={
                                                'user':         user.id,
                                                'sender':       sender,
                                                'c_recipients': contact.id,
                                                'subject':      subject,
                                                'body':         body,
                                                'body_html':    body_html,
                                              }
                                   )
        self.assertNoFormError(response)
        self.assertEqual(200, response.status_code)

        email = self.get_object_or_fail(EntityEmail, sender=sender, recipient=recipient)
        self.assertEqual(user,             email.user)
        self.assertEqual(subject,          email.subject)
        self.assertEqual(body,             email.body)
        self.assertEqual(body_html,        email.body_html)
        self.assertEqual(MAIL_STATUS_SENT, email.status)

        self.get_object_or_fail(Relation, subject_entity=email, type=REL_SUB_MAIL_SENDED,   object_entity=self.user_contact)
        self.get_object_or_fail(Relation, subject_entity=email, type=REL_SUB_MAIL_RECEIVED, object_entity=contact)

        self.assertEqual(200, self.client.get('/emails/mail/%s' % email.id).status_code)
        self.assertEqual(200, self.client.get('/emails/mail/%s/popup' % email.id).status_code)

    def test_createview02(self): #TODO: attachments
        user = self.user

        recipient = 'contact@venusgate.jp'
        orga = Organisation.objects.create(user=user, name='Venus gate', email=recipient)
        url = '/emails/mail/add/%s' % orga.id

        response = self.client.get(url)
        self.assertEqual(200, response.status_code)

        try:
            o_recipients = response.context['form'].fields['o_recipients']
        except Exception as e:
            self.fail(str(e))

        self.assertEqual([orga.id], o_recipients.initial)

        #TODO
        #folder = Folder.objects.create(user=self.user, title=u'Test folder', parent_folder=None,
                                       #category=FolderCategory.objects.create(name=u'Test category'),
                                      #)
        #docs = [Document.objects.create(user=self.user, title='Doc01', folder=folder),
                #Document.objects.create(user=self.user, title='Doc02', folder=folder),
               #]

        sender = 're-l.mayer@rpd.rmd'
        signature = EmailSignature.objects.create(user=self.user, name="Re-l's signature", body='I love you... not')
        response = self.client.post(url, data={
                                                'user':         user.id,
                                                'sender':       sender,
                                                'o_recipients': orga.id,
                                                'subject':      'Cryogenisation',
                                                'body':         'I want to be freezed !',
                                                'body_html':    '<p>I want to be freezed !</p>',
                                                'signature':    signature.id,
                                                #'attachments':  ','.join(str(doc.id) for doc in docs),
                                                'send_me':      True,
                                              }
                                   )
        self.assertNoFormError(response)
        self.assertEqual(200, response.status_code)

        email = self.get_object_or_fail(EntityEmail, sender=sender, recipient=recipient)
        self.assertEqual(signature, email.signature)

        email = self.get_object_or_fail(EntityEmail, sender=sender, recipient=sender)
        self.assertEqual(signature, email.signature)

    def test_create_from_template01(self):
        user = self.user

        body_format       = 'Hi %s %s, nice to meet you !'
        body_html_format  = 'Hi <strong>%s %s</strong>, nice to meet you !'

        subject   = 'I am da subject'
        signature = EmailSignature.objects.create(user=user, name="Re-l's signature", body='I love you... not')
        template = EmailTemplate.objects.create(user=user, name='My template',
                                                subject=subject,
                                                body=body_format % ('{{first_name}}', '{{last_name}}'),
                                                body_html=body_html_format % ('{{first_name}}', '{{last_name}}'),
                                                signature=signature,
                                               )

        recipient = 'vincent.law@city.mosk'
        first_name = 'Vincent'
        last_name = 'Law'
        contact = Contact.objects.create(user=user, first_name=first_name, last_name=last_name, email=recipient)

        url = '/emails/mail/add_from_template/%s' % contact.id
        self.assertEqual(200, self.client.get(url).status_code)

        response = self.client.post(url, data={
                                                'step':     1,
                                                'template': template.id,
                                              }
                                   )
        self.assertNoFormError(response)
        self.assertEqual(200, response.status_code)

        try:
            form = response.context['form']
            fields = form.fields
            fields['subject']
            fields['body']
            fields['body_html']
            fields['signature']
            fields['attachments']
        except KeyError as e:
            self.fail(str(e))

        self.assertEqual(2, fields['step'].initial)

        ini_get = form.initial.get
        self.assertEqual(subject, ini_get('subject'))
        self.assertEqual(body_format % (contact.first_name, contact.last_name),      ini_get('body'))
        self.assertEqual(body_html_format % (contact.first_name, contact.last_name), ini_get('body_html'))
        self.assertEqual(signature.id, ini_get('signature'))
        #self.assertEqual(attachments,  ini_get('attachments')) #TODO

        response = self.client.post(url, data={
                                                'step':         2,
                                                'user':         user.id,
                                                'sender':       self.user_contact.email,
                                                'c_recipients': contact.id,
                                                'subject':      subject,
                                                'body':         ini_get('body'),
                                                'body_html':    ini_get('body_html'),
                                                'signature':    signature.id,
                                              }
                                   )
        self.assertNoFormError(response)
        self.assertEqual(200, response.status_code)

        self.get_object_or_fail(EntityEmail, recipient=recipient)

    def test_create_from_template02(self): #TODO: test better (credentials....)
        user = self.user
        body = 'Hi , nice to meet you !'

        image_filename = '13_myimg.png'
        body_html = 'Hi <img src="%(media_url)supload/images/%(name)s">, nice to meet you !' % {
                            'media_url': settings.MEDIA_URL,
                            'name':      image_filename,
                        }

        template = EmailTemplate.objects.create(user=user, name='My template',
                                                subject='I am da subject',
                                                body=body, body_html=body_html,
                                               )
        contact = Contact.objects.create(user=user, first_name='Vincent', last_name='Law',
                                         email='vincent.law@city.mosk'
                                        )

        response = self.client.post('/emails/mail/add_from_template/%s' % contact.id,
                                    data={
                                            'step':         2,
                                            'user':         user.id,
                                            'sender':       self.user_contact.email,
                                            'c_recipients': contact.id,
                                            'subject':      template.subject,
                                            'body':         template.body,
                                            'body_html':    template.body_html,
                                         }
                                   )
        self.assertEqual(200, response.status_code)
        self.assertFormError(response, 'form', 'body_html',
                             [_(u"The image «%s» no longer exists or isn't valid.") % image_filename]
                            )

    def _create_emails(self):
        user = self.user

        contacts = [Contact.objects.create(user=user, first_name='Vincent',  last_name='Law', email='vincent.law@immigrates.rmd'),
                    Contact.objects.create(user=user, first_name='Daedalus', last_name='??',  email='daedalus@research.rmd'),
                   ]

        orgas = [Organisation.objects.create(user=user, name='Venus gate', email='contact@venusgate.jp'),
                 Organisation.objects.create(user=user, name='Nerv',       email='contact@nerv.jp'),
                ]

        url = '/emails/mail/add/%s' % contacts[0].id
        self.assertEqual(200, self.client.get(url).status_code)

        response = self.client.post(url, data={
                                                'user':         user.id,
                                                'sender':       're-l.mayer@rpd.rmd',
                                                'c_recipients': '%s,%s' % (contacts[0].id, contacts[1].id),
                                                'o_recipients': '%s,%s' % (orgas[0].id, orgas[1].id),
                                                'subject':      'Under arrest',
                                                'body':         'Freeze',
                                                'body_html':    '<p>Freeze !</p>',
                                              }
                                   )
        self.assertNoFormError(response)
        self.assertEqual(200, response.status_code)

        emails = EntityEmail.objects.all()
        self.assertEqual(4, len(emails))

        return emails

    def test_listview01(self):
        emails = self._create_emails()

        response = self.client.get('/emails/mails')
        self.assertEqual(200, response.status_code)

        try:
            emails = response.context['entities']
        except KeyError as e:
            self.fail(str(e))

        self.assertEqual(4, emails.object_list.count())

    def test_spam(self):
        emails = self._create_emails()

        self.assertEqual([MAIL_STATUS_SENT] * 4, [e.status for e in emails])

        self.assertEqual(200, self.client.post('/emails/mail/spam').status_code)
        self.assertEqual(200, self.client.post('/emails/mail/spam', data={'ids': [e.id for e in emails]}).status_code)

        refresh = self.refresh
        self.assertEqual([MAIL_STATUS_SYNCHRONIZED_SPAM] * 4, [refresh(e).status for e in emails])

    def test_validated(self):
        emails = self._create_emails()

        self.assertEqual(200, self.client.post('/emails/mail/validated', data={'ids': [e.id for e in emails]}).status_code)

        refresh = self.refresh
        self.assertEqual([MAIL_STATUS_SYNCHRONIZED] * 4, [refresh(e).status for e in emails])

    def test_waiting(self):
        emails = self._create_emails()

        self.assertEqual(200, self.client.post('/emails/mail/waiting', data={'ids': [e.id for e in emails]}).status_code)

        refresh = self.refresh
        self.assertEqual([MAIL_STATUS_SYNCHRONIZED_WAITING] * 4, [refresh(e).status for e in emails])

    #TODO: test other views
