# -*- coding: utf-8 -*-

try:
    from functools import partial
    from datetime import timedelta # datetime
    from pickle import loads

    from django.contrib.contenttypes.models import ContentType
    from django.utils.timezone import now, make_naive, get_current_timezone
    from django.utils.translation import ugettext as _

    from creme.persons.models import Contact, Organisation

    from .base import _EmailsTestCase
    from ..models import (EmailSending, EmailCampaign, EmailRecipient,
                          EmailTemplate, MailingList, LightWeightEmail)
    from ..models.sending import SENDING_TYPE_IMMEDIATE, SENDING_TYPE_DEFERRED
except Exception as e:
    print 'Error in <%s>: %s' % (__name__, e)


__all__ = ('SendingsTestCase',)


class SendingsTestCase(_EmailsTestCase):
    def setUp(self):
        self.login()

    def _load_or_fail(self, data):
        with self.assertNoException():
            return loads(data.encode('utf-8'))

    def test_create01(self):
        # We create voluntarily duplicates (recipients that have same addresses
        # than Contact/Organisation, MailingList that contain the same addresses)
        # EmailSending should not contain duplicates.
        camp = EmailCampaign.objects.create(user=self.user, name='camp01')

        self.assertFalse(camp.sendings_set.exists())

        create_ml = partial(MailingList.objects.create, user=self.user)
        mlist01 = create_ml(name='ml01')
        mlist02 = create_ml(name='ml02')
        mlist03 = create_ml(name='ml03')
        mlist04 = create_ml(name='ml04', is_deleted=True)
        mlist05 = create_ml(name='ml05')
        mlist06 = create_ml(name='ml06', is_deleted=True)

        mlist01.children.add(mlist02, mlist03, mlist04)
        camp.mailing_lists.add(mlist01, mlist05, mlist06)

        addresses = ['spike.spiegel@bebop.com',  #0
                     'jet.black@bebop.com',      #1
                     'faye.valentine@bebop.com', #2
                     'ed.wong@bebop.com',        #3
                     'ein@bebop.com',            #4
                     'contact@nerv.jp',          #5
                     'contact@seele.jp',         #6
                     'shin@reddragons.mrs',      #7
                    ]

        create_recipient = EmailRecipient.objects.create
        create_recipient(ml=mlist01, address=addresses[0])
        create_recipient(ml=mlist02, address=addresses[2])
        create_recipient(ml=mlist02, address=addresses[3])
        create_recipient(ml=mlist03, address=addresses[3])
        create_recipient(ml=mlist03, address=addresses[4])
        create_recipient(ml=mlist03, address=addresses[6])
        create_recipient(ml=mlist04, address='vicious@reddragons.mrs')
        create_recipient(ml=mlist05, address=addresses[7])
        create_recipient(ml=mlist06, address='jin@reddragons.mrs')

        create_contact = partial(Contact.objects.create, user=self.user)
        contacts = [create_contact(first_name='Spike', last_name='Spiegel', email=addresses[0]),
                    create_contact(first_name='Jet',   last_name='Black',   email=addresses[1]),
                   ]
        deleted_contact = create_contact(first_name='Ed', last_name='Wong',
                                         email='ew@bebop.com', is_deleted=True,
                                        )

        mlist01.contacts.add(contacts[0])
        mlist02.contacts.add(contacts[0])
        mlist02.contacts.add(contacts[1])
        mlist02.contacts.add(deleted_contact)

        create_orga = partial(Organisation.objects.create, user=self.user)
        orgas = [create_orga(name='NERV',  email=addresses[5]),
                 create_orga(name='Seele', email=addresses[6]),
                ]

        mlist02.organisations.add(orgas[0])
        mlist03.organisations.add(orgas[0])
        mlist03.organisations.add(orgas[1])

        subject = 'SUBJECT'
        body    = 'BODYYYYYYYYYYY'
        template = EmailTemplate.objects.create(user=self.user, name='name', subject=subject, body=body)

        url = '/emails/campaign/%s/sending/add' % camp.id
        self.assertGET200(url)

        self.assertNoFormError(self.client.post(url, data={'sender':   'vicious@reddragons.mrs',
                                                           'type':     SENDING_TYPE_IMMEDIATE,
                                                           'template': template.id,
                                                          }
                                               )
                              )

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
        self.assertGET200('/emails/mails_history/%s' % mail.id)

        response = self.assertGET200('/emails/mail/get_body/%s' % mail.id)
        self.assertEqual(u'', response.content)

        #TODO: use the Django fake email framework to test even better

        #popup detail view -----------------------------------------------------
        response = self.assertPOST200('/emails/campaign/sending/%s' % sending.id)
        self.assertContains(response, contacts[0].email)
        self.assertContains(response, orgas[0].email)

        #test delete campaign --------------------------------------------------
        camp.trash()
        response = self.assertPOST(302, '/creme_core/entity/delete/%s' % camp.id)
        self.assertFalse(EmailCampaign.objects.exists())
        self.assertFalse(EmailSending.objects.exists())
        self.assertFalse(LightWeightEmail.objects.exists())

    def test_create02(self):
        "Test template"
        user = self.user
        first_name = 'Spike'
        last_name  = 'Spiegel'

        camp    = EmailCampaign.objects.create(user=user, name='camp01')
        mlist   = MailingList.objects.create(user=user, name='ml01')
        contact = Contact.objects.create(user=user, first_name=first_name,
                                         last_name=last_name, email='spike.spiegel@bebop.com',
                                        )

        camp.mailing_lists.add(mlist)
        mlist.contacts.add(contact)

        subject = 'Hello'
        body    = 'Your first name is: {{first_name}} !'
        body_html = '<p>Your last name is: {{last_name}} !</p>'
        template = EmailTemplate.objects.create(user=user, name='name', subject=subject,
                                                body=body, body_html=body_html,
                                               )
        response = self.client.post('/emails/campaign/%s/sending/add' % camp.id,
                                    data = {'sender':   'vicious@reddragons.mrs',
                                            'type':     SENDING_TYPE_IMMEDIATE,
                                            'template': template.id,
                                           }
                                   )
        self.assertNoFormError(response)

        with self.assertNoException():
            sending = self.refresh(camp).sendings_set.all()[0]

        self.assertEqual(sending.subject, subject)

        with self.assertNoException():
            mail = sending.mails_set.all()[0]

        self.assertEqual('Your first name is: %s !' % first_name, mail.get_body())

        rendered_body = '<p>Your last name is: %s !</p>' % last_name
        self.assertEqual(rendered_body, mail.get_body_html())
        self.assertEqual(rendered_body, self.client.get('/emails/mail/get_body/%s' % mail.id).content)

        #test delete sending ---------------------------------------------------
        ct = ContentType.objects.get_for_model(EmailSending)
        self.assertPOST(302, '/creme_core/entity/delete_related/%s' % ct.id, data={'id': sending.pk})
        self.assertFalse(EmailSending.objects.filter(pk=sending.pk).exists())
        self.assertFalse(LightWeightEmail.objects.filter(pk=mail.pk).exists())

    def test_create03(self):
        "Test deferred"
        user = self.user
        camp     = EmailCampaign.objects.create(user=user, name='camp01')
        template = EmailTemplate.objects.create(user=user, name='name', subject='subject', body='body')

        #now = datetime.now()
        #sending_date = now.replace(year=now.year + 1)
        now_dt = now()
        sending_date = now_dt + timedelta(weeks=1)
        naive_sending_date = make_naive(sending_date, get_current_timezone())
        data = {'sender':   'vicious@reddragons.mrs',
                'type':     SENDING_TYPE_DEFERRED,
                'template': template.id,
               }

        post = partial(self.client.post, '/emails/campaign/%s/sending/add' % camp.id)
        self.assertNoFormError(post(data=dict(data,
                                              #sending_date=sending_date.strftime('%Y-%m-%d'), #future: OK
                                              #hour=sending_date.hour,
                                              #minute=sending_date.minute,
                                              sending_date=naive_sending_date.strftime('%Y-%m-%d'), #future: OK
                                              hour=naive_sending_date.hour,
                                              minute=naive_sending_date.minute,
                                             )
                                   )
                              )

        with self.assertNoException():
            sending = self.refresh(camp).sendings_set.all()[0]

        #fmt = '%d %m %Y %H %M'
        #self.assertEqual(sending_date.strftime(fmt), sending.sending_date.strftime(fmt))
        self.assertLess(abs((sending_date - sending.sending_date).seconds), 60)

        self.assertFormError(post(data=data), 'form', 'sending_date',
                             [_(u"Sending date required for a deferred sending")]
                            )
        self.assertFormError(post(data=dict(data,
                                            sending_date=(now_dt - timedelta(days=1)).strftime('%Y-%m-%d')
                                           )
                                 ),
                             'form', 'sending_date', [_(u"Sending date must be is the future")]
                            )
