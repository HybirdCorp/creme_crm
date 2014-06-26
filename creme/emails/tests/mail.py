# -*- coding: utf-8 -*-

try:
    from functools import partial
    from os.path import basename
    from tempfile import NamedTemporaryFile

    from django.conf import settings
    from django.core import mail
    from django.utils.translation import ugettext as _

    from creme.creme_core.models import Relation, SetCredentials
    from creme.creme_core.auth.entity_credentials import EntityCredentials

    from creme.persons.models import Contact, Organisation

    from creme.documents.models import Document, Folder, FolderCategory

    from .base import _EmailsTestCase
    from ..constants import (MAIL_STATUS_NOTSENT, MAIL_STATUS_SENT,
            MAIL_STATUS_SENDINGERROR, MAIL_STATUS_SYNCHRONIZED,
            MAIL_STATUS_SYNCHRONIZED_SPAM, MAIL_STATUS_SYNCHRONIZED_WAITING,
            REL_SUB_MAIL_RECEIVED, REL_SUB_MAIL_SENDED)
    from ..management.commands.entity_emails_send import Command as EmailsSendCommand
    from ..models import EntityEmail, EmailSignature, EmailTemplate
except Exception as e:
    print('Error in <%s>: %s' % (__name__, e))


__all__ = ('EntityEmailTestCase',)


class EntityEmailTestCase(_EmailsTestCase):
    clean_files_in_teardown = True #see CremeTestCase

    def login(self, is_superuser=True):
        super(EntityEmailTestCase, self).login(is_superuser,
                                               allowed_apps=['persons', 'emails'],
                                               creatable_models=[Contact, Organisation, EntityEmail],
                                              )

        user = self.user
        ###self.user_contact = Contact.objects.create(user=user, is_user=user,
                                                   ###first_name='Re-l',
                                                   ###last_name='Mayer',
                                                   ###email='re-l.mayer@rpd.rmd',
                                                  ###)
        ##self.user_contact = self.get_object_or_fail(Contact, is_user=user)
        #self.user_contact = user.linked_contact

        return user

    def _build_send_url(self, entity):
        return '/emails/mail/add/%s' % entity.id

    def _build_send_from_template_url(self, entity):
        return '/emails/mail/add_from_template/%s' % entity.id

    def test_createview01(self):
        self.login()
        user = self.user

        recipient = 'vincent.law@immigrates.rmd'
        contact = Contact.objects.create(user=user, first_name='Vincent', last_name='Law', email=recipient)
        url = self._build_send_url(contact)

        response = self.assertGET200(url)

        with self.assertNoException():
            c_recipients = response.context['form'].fields['c_recipients']

        self.assertEqual([contact.id], c_recipients.initial)

        #sender = self.user_contact.email
        sender = user.linked_contact.email
        body = 'Freeze !'
        body_html = '<p>Freeze !</p>'
        subject = 'Under arrest'
        response = self.client.post(url, data={'user':         user.id,
                                               'sender':       sender,
                                               'c_recipients': '[%d]' % contact.id,
                                               'subject':      subject,
                                               'body':         body,
                                               'body_html':    body_html,
                                              }
                                   )
        self.assertNoFormError(response)

        email = self.get_object_or_fail(EntityEmail, sender=sender, recipient=recipient)
        self.assertEqual(user,             email.user)
        self.assertEqual(subject,          email.subject)
        self.assertEqual(body,             email.body)
        self.assertEqual(body_html,        email.body_html)
        self.assertEqual(MAIL_STATUS_SENT, email.status)

        #self.get_object_or_fail(Relation, subject_entity=email, type=REL_SUB_MAIL_SENDED,   object_entity=self.user_contact)
        self.get_object_or_fail(Relation, subject_entity=email, type=REL_SUB_MAIL_SENDED,   object_entity=user.linked_contact)
        self.get_object_or_fail(Relation, subject_entity=email, type=REL_SUB_MAIL_RECEIVED, object_entity=contact)

        self.assertGET200('/emails/mail/%s' % email.id)
        self.assertGET200('/emails/mail/%s/popup' % email.id)

        messages = mail.outbox
        self.assertEqual(1, len(messages))

        message = messages[0]
        self.assertEqual(subject,                    message.subject)
        self.assertEqual(body,                       message.body)
        self.assertEqual([recipient],                message.recipients())
        self.assertEqual(sender,                     message.from_email)
        self.assertEqual([(body_html, 'text/html')], message.alternatives)
        self.assertFalse(message.attachments)

    def test_createview02(self):
        "Attachments"
        self.login()
        user = self.user

        recipient = 'contact@venusgate.jp'
        orga = Organisation.objects.create(user=user, name='Venus gate', email=recipient)
        url = self._build_send_url(orga)

        response = self.assertGET200(url)

        with self.assertNoException():
            o_recipients = response.context['form'].fields['o_recipients']

        self.assertEqual([orga.id], o_recipients.initial)

        folder = Folder.objects.create(user=user, title=u'Test folder', parent_folder=None,
                                        category=FolderCategory.objects.create(name=u'Test category'),
                                        )


        def create_doc(title, content):
            tmpfile = NamedTemporaryFile(suffix=".txt")
            tmpfile.write(content)
            tmpfile.flush()
            tmpfile.file.seek(0)

            response = self.client.post('/documents/document/add', follow=True,
                                        data={'user':        user.id,
                                              'title':       title,
                                              'description': 'Attachment file',
                                              'filedata':    tmpfile,
                                              'folder':      folder.id,
                                             }
                                       )
            self.assertNoFormError(response)

            return self.get_object_or_fail(Document, title=title)

        content1 = "Hey I'm the content"
        content2 = "Another content"
        doc1 = create_doc('Doc01', content1)
        doc2 = create_doc('Doc02', content2)

        sender = 're-l.mayer@rpd.rmd'
        signature = EmailSignature.objects.create(user=self.user, name="Re-l's signature", body='I love you... not')
        response = self.client.post(url, data={'user':         user.id,
                                               'sender':       sender,
                                               'o_recipients': '[%d]' % orga.id,
                                               'subject':      'Cryogenisation',
                                               'body':         'I want to be freezed !',
                                               'body_html':    '<p>I want to be freezed !</p>',
                                               'signature':    signature.id,
                                               'attachments':  '[%s,%s]' % (doc1.id, doc2.id),
                                               'send_me':      True,
                                              }
                                   )
        self.assertNoFormError(response)

        email = self.get_object_or_fail(EntityEmail, sender=sender, recipient=recipient)
        self.assertEqual(signature, email.signature)

        email = self.get_object_or_fail(EntityEmail, sender=sender, recipient=sender)
        self.assertEqual(signature, email.signature)

        messages = mail.outbox
        self.assertEqual(2, len(messages))
        self.assertEqual([sender], messages[0].recipients())

        message = messages[1]
        self.assertEqual([recipient], message.recipients())
        self.assertEqual([(basename(doc1.filedata.name), content1, None),
                          (basename(doc2.filedata.name), content2, None),
                         ],
                         message.attachments
                        )

    def test_createview03(self):
        "Invalid email adress"
        self.login()
        user = self.user

        create_contact = partial(Contact.objects.create, user=user)
        contact01 = create_contact(first_name='Vincent', last_name='Law',
                                   email='vincent.law@immigrates', #invalid
                                  )
        contact02 = create_contact(first_name='Pino', last_name='AutoReiv',
                                   email='pino@autoreivs.rmd', #ok
                                  )

        create_orga = partial(Organisation.objects.create, user=user)
        orga01 = create_orga(name='Venus gate', email='contact/venusgate.jp') #invalid 
        orga02 = create_orga(name='Nerv',       email='contact@nerv.jp') #ok

        response = self.assertPOST200(self._build_send_url(contact01),
                                      data={'user':         user.id,
                                            #'sender':       self.user_contact.email,
                                            'sender':       user.linked_contact.email,
                                            'c_recipients': '[%d,%d]' % (contact01.id, contact02.id),
                                            'o_recipients': '[%d,%d]' % (orga01.id, orga02.id),
                                            'subject':      'Under arrest',
                                            'body':         'Freeze !',
                                            'body_html':    '<p>Freeze !</p>',
                                           }
                                     )
        self.assertFormError(response, 'form', 'c_recipients',
                             _(u"The email address for %s is invalid") % contact01
                            )
        self.assertFormError(response, 'form', 'o_recipients',
                             _(u"The email address for %s is invalid") % orga01
                            )

    def test_createview04(self):
        "Related contact has no emails address"
        self.login()

        contact = Contact.objects.create(user=self.user, first_name='Vincent', last_name='Law')
        response = self.assertGET200(self._build_send_url(contact))

        with self.assertNoException():
            c_recipients = response.context['form'].fields['c_recipients']

        self.assertIsNone(c_recipients.initial)
        self.assertEqual(_(u'Beware: the contact «%s» has no email address!') % contact, c_recipients.help_text)

    def test_createview05(self):
        "Related organisation has no email address"
        self.login()

        orga = Organisation.objects.create(user=self.user, name='Venus gate')
        response = self.assertGET200(self._build_send_url(orga))

        with self.assertNoException():
            o_recipients = response.context['form'].fields['o_recipients']

        self.assertIsNone(o_recipients.initial)
        self.assertEqual(_(u'Beware: the organisation «%s» has no email address!') % orga, o_recipients.help_text)

    def test_createview06(self):
        "Credentials problem"
        user = self.login(is_superuser=False)

        create_sc = partial(SetCredentials.objects.create, role=user.role)
        create_sc(value=(EntityCredentials.VIEW   | EntityCredentials.CHANGE |
                         EntityCredentials.LINK   |
                         EntityCredentials.DELETE | EntityCredentials.UNLINK
                        ),
                  set_type=SetCredentials.ESET_OWN
                 )
        create_sc(value=(EntityCredentials.VIEW   | EntityCredentials.CHANGE |
                         EntityCredentials.DELETE | EntityCredentials.UNLINK
                        ), #no LINK
                  set_type=SetCredentials.ESET_ALL
                 )

        create_contact = Contact.objects.create
        contact01 = create_contact(user=self.other_user, first_name='Vincent', 
                                   last_name='Law', email='vincent.law@immigrates.rmd',
                                  )
        contact02 = create_contact(user=user, first_name='Pino', last_name='AutoReiv',
                                   email='pino@autoreivs.rmd',
                                  )

        create_orga = Organisation.objects.create
        orga01 = create_orga(user=self.other_user, name='Venus gate', email='contact@venusgate.jp')
        orga02 = create_orga(user=user, name='Nerv', email='contact@nerv.jp')

        self.assertTrue(user.has_perm_to_view(contact01))
        self.assertFalse(user.has_perm_to_link(contact01))
        self.assertTrue(user.has_perm_to_view(contact02))
        self.assertTrue(user.has_perm_to_link(contact02))

        def post(contact):
            return self.client.post(self._build_send_url(contact),
                                    data={'user':         user.id,
                                          #'sender':       self.user_contact.email,
                                          'sender':       user.linked_contact.email,
                                          'c_recipients': '[%d,%d]' % (contact01.id, contact02.id),
                                          'o_recipients': '[%d,%d]' % (orga01.id, orga02.id),
                                          'subject':      'Under arrest',
                                          'body':         'Freeze !',
                                          'body_html':    '<p>Freeze !</p>',
                                         }
                                   )

        self.assertEqual(403, post(contact01).status_code)

        response = post(contact02)
        self.assertEqual(200, response.status_code)

        self.assertFormError(response, 'form', 'c_recipients',
                             [_(u"Some entities are not linkable: %s") % contact01]
                            )
        self.assertFormError(response, 'form', 'o_recipients',
                             [_(u"Some entities are not linkable: %s") % orga01]
                            )

    def test_create_from_template01(self):
        self.login()
        user = self.user

        body_format      = 'Hi %s %s, nice to meet you !'
        body_html_format = 'Hi <strong>%s %s</strong>, nice to meet you !'

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

        url = self._build_send_from_template_url(contact)
        self.assertGET200(url)

        response = self.client.post(url, data={'step':     1,
                                               'template': template.id,
                                              }
                                   )
        self.assertNoFormError(response)

        with self.assertNoException():
            form = response.context['form']
            fields = form.fields
            fields['subject']
            fields['body']
            fields['body_html']
            fields['signature']
            fields['attachments']

        self.assertEqual(2, fields['step'].initial)

        ini_get = form.initial.get
        self.assertEqual(subject, ini_get('subject'))
        self.assertEqual(body_format % (contact.first_name, contact.last_name),      ini_get('body'))
        self.assertEqual(body_html_format % (contact.first_name, contact.last_name), ini_get('body_html'))
        self.assertEqual(signature.id, ini_get('signature'))
        #self.assertEqual(attachments,  ini_get('attachments')) #TODO

        response = self.client.post(url, data={'step':         2,
                                               'user':         user.id,
                                               #'sender':       self.user_contact.email,
                                               'sender':       user.linked_contact.email,
                                               'c_recipients': '[%d]' % contact.id,
                                               'subject':      subject,
                                               'body':         ini_get('body'),
                                               'body_html':    ini_get('body_html'),
                                               'signature':    signature.id,
                                              }
                                   )
        self.assertNoFormError(response)
        self.get_object_or_fail(EntityEmail, recipient=recipient)

    def test_create_from_template02(self): #TODO: test better (credentials....)
        self.login()
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

        response = self.assertPOST200(self._build_send_from_template_url(contact),
                                      data={'step':         2,
                                            'user':         user.id,
                                            #'sender':       self.user_contact.email,
                                            'sender':       user.linked_contact.email,
                                            'c_recipients': '[%d]' % contact.id,
                                            'subject':      template.subject,
                                            'body':         template.body,
                                            'body_html':    template.body_html,
                                            }
                                     )
        self.assertFormError(response, 'form', 'body_html',
                             _(u"The image «%s» no longer exists or isn't valid.") % image_filename
                            )

    def _create_emails(self):
        user = self.user

        create_c = partial(Contact.objects.create, user=user)
        contacts = [create_c(first_name='Vincent',  last_name='Law', email='vincent.law@immigrates.rmd'),
                    create_c(first_name='Daedalus', last_name='??',  email='daedalus@research.rmd'),
                   ]

        create_o = partial(Organisation.objects.create, user=user)
        orgas = [create_o(name='Venus gate', email='contact@venusgate.jp'),
                 create_o(name='Nerv',       email='contact@nerv.jp'),
                ]

        url = self._build_send_url(contacts[0])
        self.assertGET200(url)

        response = self.client.post(url, data={'user':         user.id,
                                               'sender':       're-l.mayer@rpd.rmd',
                                               'c_recipients': '[%d,%d]' % (contacts[0].id, contacts[1].id),
                                               'o_recipients': '[%d,%d]' % (orgas[0].id, orgas[1].id),
                                               'subject':      'Under arrest',
                                               'body':         'Freeze',
                                               'body_html':    '<p>Freeze !</p>',
                                              }
                                   )
        self.assertNoFormError(response)

        emails = EntityEmail.objects.all()
        self.assertEqual(4, len(emails))

        return emails

    def test_listview01(self):
        self.login()
        self._create_emails()

        response = self.assertGET200('/emails/mails')

        with self.assertNoException():
            emails = response.context['entities']

        self.assertEqual(4, emails.object_list.count())

    def test_spam(self):
        self.login()
        emails = self._create_emails()

        self.assertEqual([MAIL_STATUS_SENT] * 4, [e.status for e in emails])

        url = '/emails/mail/spam'
        self.assertPOST200(url)
        self.assertPOST200(url, data={'ids': [e.id for e in emails]})

        refresh = self.refresh
        self.assertEqual([MAIL_STATUS_SYNCHRONIZED_SPAM] * 4,
                         [refresh(e).status for e in emails]
                        )

    def test_validated(self):
        self.login()
        emails = self._create_emails()

        self.assertPOST200('/emails/mail/validated', data={'ids': [e.id for e in emails]})

        refresh = self.refresh
        self.assertEqual([MAIL_STATUS_SYNCHRONIZED] * 4,
                         [refresh(e).status for e in emails]
                        )

    def test_waiting(self):
        self.login()
        emails = self._create_emails()

        self.assertPOST200('/emails/mail/waiting', data={'ids': [e.id for e in emails]})

        refresh = self.refresh
        self.assertEqual([MAIL_STATUS_SYNCHRONIZED_WAITING] * 4,
                         [refresh(e).status for e in emails]
                        )

    def _create_email(self, status):
        user = self.user
        return EntityEmail.objects.create(user=user,
                                          sender=user.linked_contact.email,
                                          recipient='vincent.law@immigrates.rmd',
                                          subject='Under arrest',
                                          body='Freeze !',
                                          status=status,
                                         )

    def test_command01(self):
        self.login()
        email = self._create_email(MAIL_STATUS_NOTSENT)

        EmailsSendCommand().handle(verbosity=0)

        messages = mail.outbox
        self.assertEqual(1, len(messages))

        message = messages[0]
        self.assertEqual(email.subject, message.subject)
        self.assertEqual(email.body,    message.body)

    def test_command02(self):
        self.login()
        email = self._create_email(MAIL_STATUS_SENDINGERROR)

        EmailsSendCommand().handle(verbosity=0)

        messages = mail.outbox
        self.assertEqual(1, len(messages))

        message = messages[0]
        self.assertEqual(email.subject, message.subject)
        self.assertEqual(email.body,    message.body)

    def test_command03(self):
        self.login()
        self._create_email(MAIL_STATUS_SENT)
        EmailsSendCommand().handle(verbosity=0)

        self.assertFalse(mail.outbox)

    #TODO: test other views
