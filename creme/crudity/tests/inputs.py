# -*- coding: utf-8 -*-

try:
    from datetime import datetime, date

    from django.contrib.auth.models import User
    from django.core.files.uploadedfile import SimpleUploadedFile
    from django.db.models.query_utils import Q

    from creme_core.models import CremeEntity, Language

    from documents.models import Document, Folder

    from crudity.backends.models import CrudityBackend
    from crudity.fetchers.pop import PopEmail
    from crudity.inputs.email import CreateEmailInput, CreateInfopathInput
    from crudity.models.actions import WaitingAction
    from crudity.models.history import History
    from crudity.tests.base import CrudityTestCase, ContactFakeBackend, DocumentFakeBackend
    from crudity.utils import decode_b64binary

    from persons.models import Contact
except Exception as e:
    print 'Error:', e


class InputsBaseTestCase(CrudityTestCase):
    def _get_pop_email(self, body=u"", body_html=u"", senders=(), tos=(), ccs=(), subject=None, dates=(), attachments=()):
        return PopEmail(body=body, body_html=body_html, senders=senders, tos=tos, ccs=ccs,
                        subject=subject, dates=dates, attachments=attachments
                       )

    def _get_input(self, input_klass, backend_klass, **backend_cfg):
        input = input_klass()
        input.add_backend(backend_klass(config=backend_cfg))
        return input

    def _get_existing_q(self, model):
        return ~Q(pk__in=list(model.objects.values_list('pk', flat=True)))


class InputsTestCase(InputsBaseTestCase):
    def _get_email_input(self, backend, **backend_cfg):
        return self._get_input(CreateEmailInput, backend, **backend_cfg)

    def test_create_email_input01(self):
        """Unallowed user"""
        email_input = self._get_email_input(ContactFakeBackend, limit_froms=('creme@crm.org',))

        self.assertEqual(0, WaitingAction.objects.count())
        email_input.create(self._get_pop_email(senders=('crm@creme.org',)))
        self.assertEqual(0, WaitingAction.objects.count())

    def test_create_email_input02(self):
        """Bad password"""
        email_input = self._get_email_input(ContactFakeBackend, password=u"creme")

        self.assertEqual(0, WaitingAction.objects.count())
        email_input.create(self._get_pop_email(senders=('fulbert@cremecrm.org',)))
        self.assertEqual(0, WaitingAction.objects.count())

    def test_create_email_input03(self):
        """Text mail sandboxed"""
        user = self.user
        email_input = self._get_email_input(ContactFakeBackend, password = u"creme", subject="create_ce",
                                            body_map={"user_id": user.id, "created": ""}
                                           )
        self.assertEqual(0, WaitingAction.objects.count())
        email_input.create(self._get_pop_email(body=u"password=creme\nuser_id=%s\ncreated=01/02/2003\n" % user.id,
                                               senders=('creme@crm.org',),
                                               subject="create_ce"
                                              )
                          )
        self.assertEqual(1, WaitingAction.objects.count())
        self.assertEqual({u"user_id": unicode(user.id), u"created": u"01/02/2003"},
                         WaitingAction.objects.all()[0].get_data()
                        )

    def test_create_email_input04(self):
        """Text mail with creation (unsandboxed)"""
        user = self.user
        email_input = self._get_email_input(ContactFakeBackend, password=u"creme",
                                            in_sandbox=False, subject="create_ce",
                                            body_map={"user_id":    user.id,
                                                      "created":    "",
                                                      "first_name": "",
                                                     }
                                           )

        c_count = Contact.objects.count()
        q_contact_existing_ids = self._get_existing_q(Contact)

        self.assertEqual(0, WaitingAction.objects.count())
        email_input.create(self._get_pop_email(body=u"password=creme\nuser_id=%s\ncreated=01-02-2003\nfirst_name=é" % user.id,
                                               senders=('creme@crm.org',),
                                               subject="create_ce"
                                              )
                          )
        self.assertEqual(0, WaitingAction.objects.count())
        self.assertEqual(c_count + 1, Contact.objects.count())

        ce = Contact.objects.filter(q_contact_existing_ids)[0]
        self.assertEqual(user, ce.user)
        self.assertEqual(datetime(year=2003, month=02, day=01), ce.created)

    def test_create_email_input05(self):
        """Html mail sandboxed"""
        user = self.user
        email_input = self._get_email_input(ContactFakeBackend, password=u"creme",
                                            subject="create_ce",
                                            body_map={"user_id": user.id,
                                                      "created": "",
                                                     }
                                           )

        c_count = Contact.objects.count()
        q_contact_existing_ids = self._get_existing_q(Contact)

        self.assertEqual(0, WaitingAction.objects.count())
        email_input.create(self._get_pop_email(body_html=u"""<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN">
<html>
  <head>
    <meta http-equiv="content-type" content="text/html;
      charset=ISO-8859-1">
  </head>
  <body text="#3366ff" bgcolor="#ffffff">
    <font face="Calibri">
      password=creme<br>
      created=01-02-2003<br>
    </font>
  </body>
</html>""", senders=('creme@crm.org',), subject="create_ce"))
        self.assertEqual(1, WaitingAction.objects.count())
        self.assertEqual(c_count, Contact.objects.count())
        self.assertEqual({u"user_id": user.id, u"created": u"01-02-2003"},
                         WaitingAction.objects.all()[0].get_data()
                        )

    def test_create_email_input06(self):
        """Html mail with creation"""
        user = self.user
        email_input = self._get_email_input(ContactFakeBackend, password=u"creme",
                                            subject="create_ce", in_sandbox=False,
                                            body_map={"user_id": user.id,
                                                      "created": "",
                                                     }
                                           )
        c_count = Contact.objects.count()
        q_contact_existing_ids = self._get_existing_q(Contact)

        self.assertEqual(0, WaitingAction.objects.count())
        email_input.create(self._get_pop_email(body_html=u"""<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN">
<html>
  <head>
    <meta http-equiv="content-type" content="text/html;
      charset=ISO-8859-1">
  </head>
  <body text="#3366ff" bgcolor="#ffffff">
    <font face="Calibri">password=contact<br>
      password=creme<br>
      created=01-02-2003<br>
    </font>
  </body>
</html>""", senders=('creme@crm.org',), subject="create_ce"))
        self.assertEqual(0, WaitingAction.objects.count())
        self.assertEqual(1 + c_count, Contact.objects.count())

        ce = Contact.objects.filter(q_contact_existing_ids)[0]
        self.assertEqual(user, ce.user)
        self.assertEqual(datetime(year=2003, month=02, day=01), ce.created)

    def test_create_email_input07(self):
        """Text mail sandboxed with one multiline"""
        user = self.user
        email_input = self._get_email_input(ContactFakeBackend, password=u"creme",
                                            subject="create_ce",
                                            body_map={"user_id": user.id,
                                                      "created": "",
                                                      "description": "",
                                                     }
                                           )

        self.assertEqual(0, WaitingAction.objects.count())
        email_input.create(self._get_pop_email(body=u"password=creme\nuser_id=%s\ncreated=01/02/2003\ndescription=[[I\n want to\n create a    \ncreme entity\n]]\n" % user.id,
                                               senders=('creme@crm.org',), subject="create_ce"
                                              )
                          )
        self.assertEqual(1, WaitingAction.objects.count())
        self.assertEqual({u"user_id": unicode(user.id), u"created": u"01/02/2003",
                          "description": "I\n want to\n create a    \ncreme entity\n"
                         },
                         WaitingAction.objects.all()[0].get_data()
                        )

    def test_create_email_input08(self):
        """Text mail sandboxed with a weird multiline and some almost same field names"""
        user = self.user
        email_input = self._get_email_input(ContactFakeBackend, password=u"creme",
                                            subject="create_ce",
                                            body_map={"user_id":     user.id,
                                                      "created":     "",
                                                      "description": "",
                                                     }
                                           )

        self.assertEqual(0, WaitingAction.objects.count())

        body = """
        description2=[[I'am the
        second description]]
        description=[[I

        want

        to
                    create
                a
creme
entity

        ]]
        password=creme
        user_id=%s
        created=01/02/2003

        description3=[[


        Not empty


        ]]

        """ % user.id

        email_input.create(self._get_pop_email(body=body, senders=('creme@crm.org',), subject="create_ce"))
        self.assertEqual(1, WaitingAction.objects.count())

        expected_data = {u"user_id": unicode(user.id), u"created": u"01/02/2003",
                         u"description": u"I\n\n        want\n\n        to\n                    create\n                a\ncreme\nentity\n\n        ",
                        }
        self.assertEqual(expected_data, WaitingAction.objects.all()[0].get_data())

    def test_create_email_input09(self):#Text mail sandboxed with malformed multilines
        user = self.user
        email_input = self._get_email_input(ContactFakeBackend, password=u"creme",
                                            in_sandbox=True, subject="create_ce",
                                            body_map={"user_id":     user.id,
                                                      "created":     "",
                                                      "description": "",
                                                     }
                                           )
        self.assertEqual(0, WaitingAction.objects.count())

        body = """
        description=I

        want

        to
                    create
                a
creme
entity

        ]]
        password=creme
        user_id=%s
        description2=[[I'am the
        second description
        created=01/02/2003

        description3=[[


        Not empty


        ]]

        """ % user.id

        email_input.create(self._get_pop_email(body=body, senders=('creme@crm.org',), subject="create_ce"))
        self.assertEqual(1, WaitingAction.objects.count())

        expected_data = {u"user_id": unicode(user.id), u"created": u"01/02/2003",
                         u"description": u"I",
                        }
        self.assertEqual(expected_data, WaitingAction.objects.all()[0].get_data())

    def test_create_email_input10(self):
        """Html mail sandboxed with one multiline"""
        user = self.user
        email_input = self._get_email_input(ContactFakeBackend, password = u"creme",
                                                      subject = "create_ce",
                                                      body_map = {
                                                        "user_id": user.id,
                                                        "created": "",
                                                        "description": "",
                                                    })

        body_html = u"""<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN">
                        <html>
                          <head>
                            <meta http-equiv="content-type" content="text/html;
                              charset=ISO-8859-1">
                          </head>
                          <body text="#3366ff" bgcolor="#ffffff">
                            <font face="Calibri">password=contact<br>
                              password=creme<br>
                              created=01-02-2003<br>
                              description=[[I<br> want to<br> create a    <br>creme entity<br>]]
                            </font>
                          </body>
                        </html>"""

        self.assertEqual(0, WaitingAction.objects.count())
        email_input.create(self._get_pop_email(body_html=body_html, senders=('creme@crm.org',), subject="create_ce"))
        self.assertEqual(1, WaitingAction.objects.count())

        self.assertEqual({u"user_id": user.id, u"created": u"01-02-2003", "description": "I\n want to\n create a    \ncreme entity\n"},
                         WaitingAction.objects.all()[0].get_data()
                        )

    def test_create_email_input11(self):
        """Html mail sandboxed with more than one multiline and some almost same field names"""
        user = self.user
        email_input = self._get_email_input(ContactFakeBackend, password=u"creme",
                                            subject="create_ce",
                                            body_map={"user_id": user.id,
                                                      "created": "",
                                                      "description": "",
                                                     }
                                           )

        body_html = u"""<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN">
                        <html>
                          <head>
                            <meta http-equiv="content-type" content="text/html;
                              charset=ISO-8859-1">
                          </head>
                          <body text="#3366ff" bgcolor="#ffffff">
                            <font face="Calibri">password=contact<br>
                                description2=[[        <br> Second description  <br> <br>]]
                              password=creme<br>
                description3=[[<br>]]
                              created=01-02-2003<br>
                              description=[[I<br> want to<br> create a    <br>creme entity<br>]]
                              description4=[[                         <br>Not empty    <br>         ]]
                            </font>
                          </body>
                        </html>"""

        self.assertEqual(0, WaitingAction.objects.count())
        email_input.create(PopEmail(body_html=body_html, senders=('creme@crm.org',), subject="create_ce"))
        self.assertEqual(1, WaitingAction.objects.count())
        self.assertEqual({u"user_id": user.id, u"created": u"01-02-2003", "description": "I\n want to\n create a    \ncreme entity\n" },
                         WaitingAction.objects.all()[0].get_data()
                        )

    def test_create_email_input12(self):
        """Html mail sandboxed with more than one multiline but malformed"""
        user = self.user
        email_input = self._get_email_input(ContactFakeBackend, password=u"creme",
                                            subject="create_ce",
                                            body_map={"user_id":     user.id,
                                                      "created":     "",
                                                      "description": "",
                                                     }
                                           )

        body_html = u"""<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN">
                        <html>
                          <head>
                            <meta http-equiv="content-type" content="text/html;
                              charset=ISO-8859-1">
                          </head>
                          <body text="#3366ff" bgcolor="#ffffff">
                            <font face="Calibri">password=contact<br>
                                description2=[[        <br> Second description  <br> <br>
                              password=creme<br>
                description3=[[<br>]]
                              created=01-02-2003<br>
                              description=I<br> want to<br> create a    <br>creme entity<br>]]
                              description4=                         <br>Not empty    <br>
                            </font>
                          </body>
                        </html>"""

        self.assertEqual(0, WaitingAction.objects.count())
        email_input.create(self._get_pop_email(body_html=body_html, senders=('creme@crm.org',), subject="create_ce"))
        self.assertEqual(1, WaitingAction.objects.count())
        self.assertEqual({u"user_id": user.id, u"created": u"01-02-2003", "description": "I"},
                         WaitingAction.objects.all()[0].get_data()
                        )

    def test_create_email_input13(self):
        """Text mail sandboxed by user"""
        user = self.user
        other_user = self.other_user

        contact_user = Contact.objects.create(is_user=user, user=user, email="user@cremecrm.com")
        contact_other_user = Contact.objects.create(is_user=other_user, user=other_user, email="other_user@cremecrm.com")
        self._set_sandbox_by_user()

        email_input = self._get_email_input(ContactFakeBackend, password=u"creme", subject="create_ce",
                                            body_map={"user_id": user.id, "created": ""}
                                           )
        self.assertEqual(0, WaitingAction.objects.count())

        email_input.create(self._get_pop_email(body=u"password=creme\nuser_id=%s\ncreated=01/02/2003\n" % user.id,
                                               senders=('user@cremecrm.com',), subject="create_ce"
                                              )
                          )
        self.assertEqual(1, WaitingAction.objects.filter(user=user).count())
        self.assertEqual(0, WaitingAction.objects.filter(user=None).count())

        wa = WaitingAction.objects.all()[0]
        self.assertEqual({u"user_id": u"%s" % user.id, u"created": u"01/02/2003"}, wa.get_data())
        self.assertEqual(user, wa.user)

    def test_create_email_input14(self):
        """Text mail un-sandboxed but by user"""
        user = self.user
        other_user = self.other_user

        contact_user = Contact.objects.create(is_user=user, user=user, email="user@cremecrm.com")
        contact_other_user = Contact.objects.create(is_user=other_user, user=other_user, email="other_user@cremecrm.com")

        self._set_sandbox_by_user()

        email_input = self._get_email_input(ContactFakeBackend,
                                            password=u"creme", subject="create_ce",
                                            body_map={"user_id": user.id,
                                                      "created": "",
                                                     },
                                            in_sandbox=False
                                           )

        c_count = Contact.objects.count()
        existing_c = list(Contact.objects.values_list('pk', flat=True))

        self.assertEqual(0, WaitingAction.objects.count())
        self.assertEqual(0, History.objects.count())

        email_input.create(self._get_pop_email(body=u"password=creme\nuser_id=%s\ncreated=01/02/2003\n" % user.id,
                                               senders=('other_user@cremecrm.com',), subject="create_ce"
                                              )
                          )
        self.assertEqual(0, WaitingAction.objects.count())
        self.assertEqual(c_count + 1, Contact.objects.count())
        self.assertEqual(1, History.objects.filter(user=other_user).count())
        self.assertEqual(0, History.objects.filter(user=None).count())

        try:
            ce = Contact.objects.exclude(pk__in=existing_c)[0]
        except IndexError, e:
            self.fail(e)

        self.assertEqual(other_user, History.objects.all()[0].user)
        self.assertEqual(user, ce.user)#Sandbox by user doesn't have to change the assignation set in the mail

    def test_create_email_input15(self):
        """Text mail sandboxed by user and created later"""
        user = self.user
        other_user = self.other_user
        contact_user = Contact.objects.create(is_user=user, user=user, email="user@cremecrm.com")
        contact_other_user = Contact.objects.create(is_user=other_user, user=other_user, email="other_user@cremecrm.com")
        self._set_sandbox_by_user()
        email_input = self._get_email_input(ContactFakeBackend, password=u"creme", subject="create_ce",
                                            body_map={"user_id": user.id,
                                                      "created": "",
                                                     }
                                           )
        c_count = Contact.objects.count()
        existing_c = list(Contact.objects.all().values_list('pk', flat=True))
        self.assertEqual(0, WaitingAction.objects.count())
        self.assertEqual(0, History.objects.count())

        email_input.create(self._get_pop_email(body=u"password=creme\nuser_id=%s\ncreated=01/02/2003\n" % user.id,
                                               senders=('other_user@cremecrm.com',),
                                               subject="create_ce"
                                              )
                          )
        self.assertEqual(1, WaitingAction.objects.count())
        self.assertEqual(0, History.objects.count())
        self.assertEqual(c_count, Contact.objects.count())

        wa = WaitingAction.objects.all()[0]
        self.assertEqual(other_user, wa.user)

        email_input.get_backend(CrudityBackend.normalize_subject("create_ce")).create(wa)
        self.assertEqual(c_count + 1, Contact.objects.count())
        self.assertEqual(1, History.objects.count())

        self.assertEqual(user, Contact.objects.get(~Q(pk__in=existing_c)).user)
        self.assertEqual(other_user, History.objects.all()[0].user)

    def test_create_email_input16(self):
        """Text mail with creation"""
        user = self.user

        email_input = self._get_email_input(ContactFakeBackend, password=u"creme",
                                            in_sandbox=False,
                                            subject="create_contact",
                                            body_map={"user_id":    user.id,
                                                      "created":    "",
                                                      "is_actived": "",
                                                      "url_site":   "",
                                                     },
                                            model=Contact
                                           )
        contact_count = Contact.objects.count()
        self.assertEqual(0, WaitingAction.objects.count())
        #self.assertEqual(contact_count, Contact.objects.count())

        email_input.create(PopEmail(body=u"password=creme\nuser_id=%s\ncreated=01-02-2003\nis_actived=false\nurl_site=plop" % user.id,
                                    senders=('creme@crm.org',), subject="create_contact"
                                   )
                          )
        self.assertEqual(0, WaitingAction.objects.count())
        self.assertEqual(contact_count + 1, Contact.objects.count())

        contact = self.get_object_or_fail(Contact, url_site='plop')
        self.assertEqual(user, contact.user)
        self.assertEqual(datetime(year=2003, month=02, day=01), contact.created)
        self.assertIs(contact.is_actived, False)

    def test_get_owner01(self):
        """The sandbox is not by user"""
        user = self.user
        contact_user = Contact.objects.create(is_user=user, user=user, email="user@cremecrm.com")
        email_input = self._get_email_input(ContactFakeBackend, password=u"creme", subject="create_ce",
                                            body_map={"user_id": user.id}
                                           )
        self.assertIsNone(email_input.get_owner(False, sender="user@cremecrm.com"))

    def test_get_owner02(self):
        """The user matches"""
        self._set_sandbox_by_user()
        user = self.user
        other_user = self.other_user

        contact_user       = Contact.objects.create(is_user=user, user=user, email="user@cremecrm.com")
        contact_other_user = Contact.objects.create(is_user=other_user, user=other_user, email="other_user@cremecrm.com")

        email_input = self._get_email_input(ContactFakeBackend, password=u"creme", subject="create_ce",
                                            body_map={"user_id": user.id,
                                                      "created": "",
                                                     }
                                           )
        self.assertEqual(other_user, email_input.get_owner(True, sender="other_user@cremecrm.com"))

    def test_get_owner03(self):
        """The user doesn't match"""
        self._set_sandbox_by_user()
        user = self.user
        other_user = self.other_user

        create_contact = Contact.objects.create
        contact_user       = create_contact(is_user=user,       user=user,       email="user@cremecrm.com")
        contact_other_user = create_contact(is_user=other_user, user=other_user, email="other_user@cremecrm.com")

        email_input = self._get_email_input(ContactFakeBackend, password=u"creme", subject="create_ce",
                                            body_map={"user_id": user.id,
                                                      "created": "",
                                                     }
                                           )
        self.assertEqual(user, email_input.get_owner(True, sender="another_user@cremecrm.com"))

    def test_get_owner04(self):
        """The user doesn't match and multiple superuser exists"""
        self._set_sandbox_by_user()
        superuser1 = self.user

        superuser2 = User.objects.create(username='Kirika2')
        superuser2.set_password("Kirika2")
        superuser2.is_superuser = True
        superuser2.save()

        self.assertGreater(superuser2.pk, superuser1.pk)

        email_input = self._get_email_input(ContactFakeBackend, password=u"creme", subject="create_ce",
                                            body_map={"user_id": superuser1.id,
                                                      "created": "",
                                                     }
                                           )
        self.assertEqual(superuser2, email_input.get_owner(True, sender="another_user@cremecrm.com"))

    def test_create_contact01(self):
        """Text mail sandboxed"""
        user = self.user
        email_input = self._get_email_input(ContactFakeBackend, password=u"creme", subject="create_contact",
                                            body_map={'user_id':     user.id,
                                                      'is_actived':  True,
                                                      'first_name':  '',
                                                      'last_name':   '',
                                                      'email':       "none@none.com",
                                                      'description': '',
                                                      'birthday':    '',
                                                      'created':     '',
                                                      'url_site':    '',
                                                     },
                                            model=Contact
                                           )

        body = [u"password=creme",           "user_id=%s"  % user.id,
                "created=01/02/2003",        "last_name=Bros",
                "first_name=Mario",          "email=mario@bros.com",
                "url_site=http://mario.com", "birthday=02/08/1987",
                u"description=[[A plumber]]",
               ]

        self.assertEqual(0, WaitingAction.objects.count())
        email_input.create(self._get_pop_email(body="\n".join(body), senders=('creme@crm.org',), subject="create_contact"))
        self.assertEqual(1, WaitingAction.objects.count())

        wa = WaitingAction.objects.all()[0]
        expected_data = {u"user_id": unicode(user.id), u"created": u"01/02/2003", u"last_name": u"Bros",
                         u"first_name": u"Mario", u"email": u"mario@bros.com", u"url_site": u"http://mario.com",
                         u"is_actived": True, u"birthday": u"02/08/1987", u"description": u"A plumber",
                        }
        self.assertEqual(expected_data, wa.get_data())

        email_input.get_backend(CrudityBackend.normalize_subject("create_contact")).create(wa)

        contact = self.get_object_or_fail(Contact, first_name='Mario', last_name='Bros')
        self.assertEqual(user, contact.user)
        self.assertEqual(datetime(year=2003, month=02, day=01), contact.created)
        self.assertEqual("mario@bros.com", contact.email)
        self.assertEqual("http://mario.com", contact.url_site)
        self.assertIs(contact.is_actived, True)
        self.assertEqual(datetime(year=1987, month=8, day=02).date(), contact.birthday)
        self.assertEqual("A plumber", contact.description)


class InfopathInputEmailTestCase(InputsBaseTestCase):
    def _build_attachment(self, filename="", content_type='application/x-microsoft-infopathform', content=""):
        return (filename, SimpleUploadedFile(filename, content, content_type=content_type))

    def _get_infopath_input(self, backend, **backend_cfg):
        return self._get_input(CreateInfopathInput, backend, **backend_cfg)

    def test_create01(self):
        """Unallowed user"""
        infopath_input = self._get_infopath_input(ContactFakeBackend, limit_froms=('creme@cremecrm.com',))

        self.assertEqual(0, WaitingAction.objects.count())
        infopath_input.create(self._get_pop_email(body=u"", body_html=u"", senders=('crm@cremecrm.com',),
                              attachments=[self._build_attachment()])
                             )
        self.assertEqual(0, WaitingAction.objects.count())

    def test_create02(self):
        """Bad password"""
        infopath_input = self._get_infopath_input(ContactFakeBackend, password = u"creme")

        self.assertEqual(0, WaitingAction.objects.count())
        infopath_input.create(self._get_pop_email(body=u"", body_html=u"", senders=('creme@cremecrm.com',),
                              attachments=[self._build_attachment()])
                             )
        self.assertEqual(0, WaitingAction.objects.count())

    def test_create03(self):
        """Allowed password, subject but attachment content_type is unallowed"""
        user = self.user
        infopath_input = self._get_infopath_input(ContactFakeBackend, password=u"creme", in_sandbox=False,
                                                  subject="create_ce_infopath",
                                                  body_map={"user_id": user.id,
                                                            "created": "",
                                                           }
                                                 )

        self.assertEqual(0, WaitingAction.objects.count())
        infopath_input.create(self._get_pop_email(body=u"password=creme", senders=('creme@cremecrm.com',),
                              subject="create_ce_infopath", attachments=[self._build_attachment(content_type='text/invalid')])
                             )
        self.assertEqual(0, WaitingAction.objects.count())

    def test_create04(self):
        """Allowed but empty xml"""
        user = self.user
        infopath_input = self._get_infopath_input(ContactFakeBackend, password=u"creme", in_sandbox=False,
                                                  subject = "create_ce_infopath",
                                                  body_map={"user_id": user.id,
                                                            "created": "",
                                                           }
                                                 )

        self.assertEqual(0, WaitingAction.objects.count())
        infopath_input.create(self._get_pop_email(body=u"password=creme", senders=('creme@cremecrm.com',),
                              subject="create_ce_infopath", attachments=[self._build_attachment()])
                             )
        self.assertEqual(0, WaitingAction.objects.count())

    def test_create05(self):
        """Allowed but bad xml"""
        user = self.user
        infopath_input = self._get_infopath_input(ContactFakeBackend, password = u"creme",
                                                  in_sandbox=False,
                                                  subject="create_ce_infopath",
                                                  body_map={"user_id": user.id,
                                                            "created": "",
                                                           }
                                                 )

        self.assertEqual(0, WaitingAction.objects.count())
        infopath_input.create(self._get_pop_email(body=u"password=creme", senders=('creme@cremecrm.com',),
                              subject="create_ce_infopath", attachments=[self._build_attachment(content="invalid")])
                             )
        self.assertEqual(0, WaitingAction.objects.count())

    def test_create06(self):
        """Allowed with valid xml"""
        user = self.user
        other_user = self.other_user
        xml_content = """
        <?xml version="1.0" encoding="UTF-8"?><?mso-infoPathSolution solutionVersion="1.0.0.14" productVersion="12.0.0" PIVersion="1.0.0.0" href="file:///C:\Users\Raph\Desktop\Infopath\create_contact.xsn" name="urn:schemas-microsoft-com:office:infopath:create-contact:-myXSD-2011-07-04T07-44-13" ?><?mso-application progid="InfoPath.Document" versionProgid="InfoPath.Document.2"?><my:CremeCRMCrudity xmlns:my="http://schemas.microsoft.com/office/infopath/2003/myXSD/2011-07-04T07:44:13" xml:lang="fr">
            <my:user_id>%s</my:user_id>
            <my:created xsi:nil="true" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">2003-02-01</my:created>
            <my:description>
                <div xmlns="http://www.w3.org/1999/xhtml">My creme entity</div>
                <div xmlns="http://www.w3.org/1999/xhtml"> </div>
                <div xmlns="http://www.w3.org/1999/xhtml">description</div>
            </my:description>
        </my:CremeCRMCrudity>""" % (other_user.id, )

        infopath_input = self._get_infopath_input(ContactFakeBackend, password=u"creme",
                                                  subject="create_ce_infopath",
                                                  body_map={"user_id":     user.id,
                                                            "created":     "",
                                                            "description": "",
                                                           }
                                                 )

        self.assertEqual(0, WaitingAction.objects.count())
        infopath_input.create(PopEmail(body=u"password=creme", senders=('creme@cremecrm.com',),
                              subject="create_ce_infopath", attachments=[self._build_attachment(content=xml_content)])
                             )
        self.assertEqual(1, WaitingAction.objects.count())

        wa = WaitingAction.objects.all()[0]
        self.assertEqual({u"user_id": u"%s" % other_user.id, u"created": u"2003-02-01", u"description": u"My creme entity\n\ndescription"},
                         wa.get_data()
                        )
        self.assertIsNone(wa.user)#Sandbox is not by user

    def test_create07(self):
        """Allowed with valid but weird xml"""
        user = self.user
        other_user = self.other_user
        xml_content = """

        <?xml version="1.0" encoding="UTF-8"?>
<?mso-infoPathSolution solutionVersion="1.0.0.14" productVersion="12.0.0" PIVersion="1.0.0.0" href="file:///C:\Users\Raph\Desktop\Infopath\create_contact.xsn" name="urn:schemas-microsoft-com:office:infopath:create-contact:-myXSD-2011-07-04T07-44-13" ?><?mso-application progid="InfoPath.Document" versionProgid="InfoPath.Document.2"?><my:CremeCRMCrudity xmlns:my="http://schemas.microsoft.com/office/infopath/2003/myXSD/2011-07-04T07:44:13" xml:lang="fr">



            <my:user_id>%s</my:user_id>
                                                    <my:created xsi:nil="true" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">2003-02-01</my:created>
        <my:description>
                    <div xmlns="http://www.w3.org/1999/xhtml">My creme entity</div>

                <div xmlns="http://www.w3.org/1999/xhtml"> </div>
        <div xmlns="http://www.w3.org/1999/xhtml">description</div>



            </my:description> </my:CremeCRMCrudity>""" % (other_user.id, )

        infopath_input = self._get_infopath_input(ContactFakeBackend, password = u"creme",
                                                  subject="create_ce_infopath",
                                                  body_map={"user_id": user.id,
                                                            "created": "",
                                                            "description": "",
                                                           }
                                                 )

        self.assertEqual(0, WaitingAction.objects.count())
        infopath_input.create(self._get_pop_email(body=u"password=creme", senders=('creme@cremecrm.com',),
                              subject="create_ce_infopath", attachments=[self._build_attachment(content=xml_content)])
                             )
        self.assertEqual(1, WaitingAction.objects.count())
        self.assertEqual({u"user_id": u"%s" % other_user.id, u"created": u"2003-02-01", u"description": u"My creme entity\n\ndescription"},
                         WaitingAction.objects.all()[0].get_data()
                        )

    def test_create08(self):
        """Allowed with valid xml with sandbox by user"""
        user = self.user
        other_user = self.other_user
        self._set_sandbox_by_user()

        xml_content = """
        <?xml version="1.0" encoding="UTF-8"?><?mso-infoPathSolution solutionVersion="1.0.0.14" productVersion="12.0.0" PIVersion="1.0.0.0" href="file:///C:\Users\Raph\Desktop\Infopath\create_contact.xsn" name="urn:schemas-microsoft-com:office:infopath:create-contact:-myXSD-2011-07-04T07-44-13" ?><?mso-application progid="InfoPath.Document" versionProgid="InfoPath.Document.2"?><my:CremeCRMCrudity xmlns:my="http://schemas.microsoft.com/office/infopath/2003/myXSD/2011-07-04T07:44:13" xml:lang="fr">
            <my:user_id>%s</my:user_id>
            <my:created xsi:nil="true" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">2003-02-01</my:created>
            <my:description>
                <div xmlns="http://www.w3.org/1999/xhtml">My creme entity</div>
                <div xmlns="http://www.w3.org/1999/xhtml"> </div>
                <div xmlns="http://www.w3.org/1999/xhtml">description</div>
            </my:description>
        </my:CremeCRMCrudity>""" % (other_user.id, )

        infopath_input = self._get_infopath_input(ContactFakeBackend, password=u"creme",
                                                  subject="create_ce_infopath",
                                                  body_map={"user_id":     user.id,
                                                            "created":     "",
                                                            "description": "",
                                                           }
                                                 )

        self.assertEqual(0, WaitingAction.objects.count())
        infopath_input.create(self._get_pop_email(body=u"password=creme", senders=('creme@cremecrm.com',),
                              subject="create_ce_infopath", attachments=[self._build_attachment(content=xml_content)])
                             )
        self.assertEqual(1, WaitingAction.objects.count())

        wa = WaitingAction.objects.all()[0]
        self.assertEqual({u"user_id": u"%s" % other_user.id, u"created": u"2003-02-01", u"description": u"My creme entity\n\ndescription"},
                         wa.get_data()
                        )
        self.assertEqual(user, wa.user)

    def test_create09(self):
        """Allowed with valid xml with sandbox by user with real match on email"""
        user = self.user
        other_user = self.other_user
        self._set_sandbox_by_user()

        contact_other_user = Contact.objects.create(is_user=other_user, user=other_user, email="other_user@cremecrm.com")

        xml_content = """
        <?xml version="1.0" encoding="UTF-8"?><?mso-infoPathSolution solutionVersion="1.0.0.14" productVersion="12.0.0" PIVersion="1.0.0.0" href="file:///C:\Users\Raph\Desktop\Infopath\create_contact.xsn" name="urn:schemas-microsoft-com:office:infopath:create-contact:-myXSD-2011-07-04T07-44-13" ?><?mso-application progid="InfoPath.Document" versionProgid="InfoPath.Document.2"?><my:CremeCRMCrudity xmlns:my="http://schemas.microsoft.com/office/infopath/2003/myXSD/2011-07-04T07:44:13" xml:lang="fr">
            <my:user_id>%s</my:user_id>
            <my:created xsi:nil="true" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">2003-02-01</my:created>
            <my:description>
                <div xmlns="http://www.w3.org/1999/xhtml">My creme entity</div>
                <div xmlns="http://www.w3.org/1999/xhtml"> </div>
                <div xmlns="http://www.w3.org/1999/xhtml">description</div>
            </my:description>
        </my:CremeCRMCrudity>""" % (other_user.id, )

        infopath_input = self._get_infopath_input(ContactFakeBackend, password=u"creme",
                                                  subject="create_ce_infopath",
                                                  body_map={"user_id": user.id,
                                                            "created": "",
                                                            "description": "",
                                                           }
                                                 )

        self.assertEqual(0, WaitingAction.objects.count())
        infopath_input.create(self._get_pop_email(body=u"password=creme", senders=('other_user@cremecrm.com',),
                              subject="create_ce_infopath", attachments=[self._build_attachment(content=xml_content)])
                             )
        self.assertEqual(1, WaitingAction.objects.count())

        wa = WaitingAction.objects.all()[0]
        self.assertEqual({u"user_id": u"%s" % other_user.id, u"created": u"2003-02-01", u"description": u"My creme entity\n\ndescription"},
                         wa.get_data()
                        )
        self.assertEqual(other_user, wa.user)

    def test_create10(self):
        """Allowed with valid xml with no sandbox with default values"""
        user = self.user

        xml_content = """
        <?xml version="1.0" encoding="UTF-8"?><?mso-infoPathSolution solutionVersion="1.0.0.14" productVersion="12.0.0" PIVersion="1.0.0.0" href="file:///C:\Users\Raph\Desktop\Infopath\create_contact.xsn" name="urn:schemas-microsoft-com:office:infopath:create-contact:-myXSD-2011-07-04T07-44-13" ?><?mso-application progid="InfoPath.Document" versionProgid="InfoPath.Document.2"?><my:CremeCRMCrudity xmlns:my="http://schemas.microsoft.com/office/infopath/2003/myXSD/2011-07-04T07:44:13" xml:lang="fr">
        </my:CremeCRMCrudity>"""

        infopath_input = self._get_infopath_input(ContactFakeBackend, password=u"creme",
                                                  in_sandbox=False,
                                                  subject="create_ce_infopath",
                                                  body_map={"user_id": user.id,
                                                            "created": "2011-10-09",
                                                            "description": "default",
                                                           }
                                                 )

        c_count = Contact.objects.count()
        q_c_existing_ids = self._get_existing_q(Contact)

        self.assertEqual(0, WaitingAction.objects.count())
        infopath_input.create(self._get_pop_email(body=u"password=creme", senders=('other_user@cremecrm.com',),
                              subject="create_ce_infopath", attachments=[self._build_attachment(content=xml_content)])
                             )
        self.assertEqual(0, WaitingAction.objects.count())
        self.assertEqual(c_count + 1, Contact.objects.count())

        ce = Contact.objects.filter(q_c_existing_ids)[0]
        self.assertEqual(user, ce.user)
        self.assertEqual(date(year=2011, month=10, day=9), ce.created.date())

    def test_create11(self):
        """Allowed with valid xml with no sandbox but by user with real match on email"""
        user = self.user
        other_user = self.other_user
        self._set_sandbox_by_user()
        contact_other_user = Contact.objects.create(is_user=other_user, user=other_user, email="other_user@cremecrm.com")

        xml_content = """
        <?xml version="1.0" encoding="UTF-8"?><?mso-infoPathSolution solutionVersion="1.0.0.14" productVersion="12.0.0" PIVersion="1.0.0.0" href="file:///C:\Users\Raph\Desktop\Infopath\create_contact.xsn" name="urn:schemas-microsoft-com:office:infopath:create-contact:-myXSD-2011-07-04T07-44-13" ?><?mso-application progid="InfoPath.Document" versionProgid="InfoPath.Document.2"?><my:CremeCRMCrudity xmlns:my="http://schemas.microsoft.com/office/infopath/2003/myXSD/2011-07-04T07:44:13" xml:lang="fr">
            <my:user_id>%s</my:user_id>
            <my:created xsi:nil="true" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">2003-02-01</my:created>
            <my:description>
                <div xmlns="http://www.w3.org/1999/xhtml">My creme entity</div>
                <div xmlns="http://www.w3.org/1999/xhtml"> </div>
                <div xmlns="http://www.w3.org/1999/xhtml">description</div>
            </my:description>
        </my:CremeCRMCrudity>""" % (other_user.id, )

        infopath_input = self._get_infopath_input(ContactFakeBackend, password=u"creme",
                                                  in_sandbox=False,
                                                  subject="create_ce_infopath",
                                                  body_map={"user_id": user.id,
                                                            "created": "",
                                                           }
                                                 )

        c_count = Contact.objects.count()
        q_c_existing_ids = self._get_existing_q(Contact)

        self.assertEqual(0, WaitingAction.objects.count())
        infopath_input.create(PopEmail(body=u"password=creme", senders=('other_user@cremecrm.com',),
                                       subject="create_ce_infopath",
                                       attachments=[self._build_attachment(content=xml_content)]
                                      )
                             )
        self.assertEqual(0, WaitingAction.objects.count())
        self.assertEqual(c_count + 1, Contact.objects.count())

        contact = Contact.objects.filter(q_c_existing_ids)[0]
        self.assertEqual(other_user, contact.user)
        self.assertEqual(date(year=2003, month=2, day=1), contact.created.date())

    def test_create_contact01(self):
        """sandboxed with image"""
        user = self.user
        xml_content = """
        <?xml version="1.0" encoding="UTF-8"?><?mso-infoPathSolution solutionVersion="1.0.0.14" productVersion="12.0.0" PIVersion="1.0.0.0" href="file:///C:\Users\User\Desktop\Infopath\create_contact.xsn" name="urn:schemas-microsoft-com:office:infopath:create-contact:-myXSD-2011-07-04T07-44-13" ?><?mso-application progid="InfoPath.Document" versionProgid="InfoPath.Document.2"?><my:CremeCRMCrudity xmlns:my="http://schemas.microsoft.com/office/infopath/2003/myXSD/2011-07-04T07:44:13" xml:lang="fr">
            <my:user_id>%s</my:user_id>
            <my:created xsi:nil="true" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">2003-02-01</my:created>
            <my:first_name>Mario</my:first_name>
            <my:last_name>Bros</my:last_name>
            <my:url_site>http://mario.com</my:url_site>
            <my:email>mario@bros.com</my:email>
            <my:birthday xsi:nil="true" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">02/08/1987</my:birthday>
            <my:image>x0lGQRQAAAABAAAAAAAAAHwCAAAGAAAAYgAuAHAAbgBnAAAAiVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAABHNCSVQICAgIfAhkiAAAAAlwSFlzAAABuwAAAbsBOuzj4gAAABl0RVh0U29mdHdhcmUAd3d3Lmlua3NjYXBlLm9yZ5vuPBoAAAH5SURBVDiNpZM9a1RBFIbfd87M3N3szW6iYoIYlYBgY6FNwMafIOJPsLCwEm3UQoKFYhk7/4lYGqxtRPAr6kIS3KjZTbIfc+/MsfAjyV5FwYFTnAPnmfc9Z4aqiv85drzQeJQ9YENOmpaZEsPm7OEZdtvb7dWL6xf+CuAtnjp6eebaKAVLA5SD1Hu9/LYJYvZPCsy+LCErY1QKYK2AgHACgEf6NwsZGmKo4j2gChKCBoAhRO7zOhRFAp7oTX35S7Wqor5UP39oYfohatoyM2aOJMtQoAgFhl+Hq0URi9AtyI4eSz08j1f1zD4FNPGcn3eni1GAs4KYdjdjGnLEJ4KK9uhDAAWxMoOiG9eNIXzdQ2xlMfC1DMYI2ATwOwAccpc5ZJmvNnuPeq0GI3QI30sVgCpf9VcG7wadsAYF8MOBEQPnLayxSIU67WMT23izF8C9L5G3efbElbmnqOlEMQhIUbXz7PNHBmXc0sdpA/f0rq5ULexmXVWNACBOYBKC7qTj0alPm7gx3rwPQJKObkKHSUFArACKEgIYwRCrGFQGtNcCQU4uTh7s2/4l15IFmZZ5Nak1Wgvvbc8vWbFfKIwkyxhir4/+J72jJcd/Ixdpc+QHoo1OS3XipIkIjt8cGXv5Vr5RAVQkLtLnyKcUan4GLGhKU+y82Ol8A49h31zz9A1IAAAAAElFTkSuQmCC</my:image>
            <my:description>
                <div xmlns="http://www.w3.org/1999/xhtml">A plumber</div>
            </my:description>
        </my:CremeCRMCrudity>""" % user.id

        infopath_input = self._get_infopath_input(ContactFakeBackend, password=u"creme", subject="create_ce_infopath",
                                                  body_map = {'user_id':     user.id,
                                                              'is_actived':  True,
                                                              "first_name":  "",
                                                              "last_name":   "",
                                                              "email":       "none@none.com",
                                                              "description": "",
                                                              "birthday":    "",
                                                              "created":     "",
                                                              'url_site':    "",
                                                              "image":       "",
                                                      },
                                                      model=Contact
                                                 )

        q_contact_existing_ids = ~Q(pk__in=list(Contact.objects.all().values_list('pk', flat=True)))
        self.assertEqual(0, WaitingAction.objects.count())
        infopath_input.create(self._get_pop_email(body=u"password=creme", senders=('user@cremecrm.com',),
                                                  subject="create_ce_infopath",
                                                  attachments=[self._build_attachment(content=xml_content)]
                                                 )
                             )
        self.assertEqual(1, WaitingAction.objects.count())

        wa = WaitingAction.objects.all()[0]
        img_content = "x0lGQRQAAAABAAAAAAAAAHwCAAAGAAAAYgAuAHAAbgBnAAAAiVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAABHNCSVQICAgIfAhkiAAAAAlwSFlzAAABuwAAAbsBOuzj4gAAABl0RVh0U29mdHdhcmUAd3d3Lmlua3NjYXBlLm9yZ5vuPBoAAAH5SURBVDiNpZM9a1RBFIbfd87M3N3szW6iYoIYlYBgY6FNwMafIOJPsLCwEm3UQoKFYhk7/4lYGqxtRPAr6kIS3KjZTbIfc+/MsfAjyV5FwYFTnAPnmfc9Z4aqiv85drzQeJQ9YENOmpaZEsPm7OEZdtvb7dWL6xf+CuAtnjp6eebaKAVLA5SD1Hu9/LYJYvZPCsy+LCErY1QKYK2AgHACgEf6NwsZGmKo4j2gChKCBoAhRO7zOhRFAp7oTX35S7Wqor5UP39oYfohatoyM2aOJMtQoAgFhl+Hq0URi9AtyI4eSz08j1f1zD4FNPGcn3eni1GAs4KYdjdjGnLEJ4KK9uhDAAWxMoOiG9eNIXzdQ2xlMfC1DMYI2ATwOwAccpc5ZJmvNnuPeq0GI3QI30sVgCpf9VcG7wadsAYF8MOBEQPnLayxSIU67WMT23izF8C9L5G3efbElbmnqOlEMQhIUbXz7PNHBmXc0sdpA/f0rq5ULexmXVWNACBOYBKC7qTj0alPm7gx3rwPQJKObkKHSUFArACKEgIYwRCrGFQGtNcCQU4uTh7s2/4l15IFmZZ5Nak1Wgvvbc8vWbFfKIwkyxhir4/+J72jJcd/Ixdpc+QHoo1OS3XipIkIjt8cGXv5Vr5RAVQkLtLnyKcUan4GLGhKU+y82Ol8A49h31zz9A1IAAAAAElFTkSuQmCC"
        filename, blob = decode_b64binary(img_content)
        expected_data = {"user_id": "%s"  % (user.id,), "created": "2003-02-01", "last_name": "Bros",
                        "first_name": "Mario", "email": "mario@bros.com", "url_site": "http://mario.com",
                        "is_actived": True, "birthday": "02/08/1987", "description": "A plumber",
#                        "image": img_content,
                        "image": (filename, blob),
                        }
        self.maxDiff = None
        self.assertEqual(expected_data, wa.get_data())

        infopath_input.get_backend(CrudityBackend.normalize_subject("create_ce_infopath")).create(wa)
        contact = Contact.objects.filter(q_contact_existing_ids)[0]

        self.assertEqual(user, contact.user)
        self.assertEqual(datetime(year=2003, month=02, day=01), contact.created)
        self.assertEqual("Bros", contact.last_name)
        self.assertEqual("Mario", contact.first_name)
        self.assertEqual("mario@bros.com", contact.email)
        self.assertEqual("http://mario.com", contact.url_site)
        self.assertEqual(True, contact.is_actived)
        self.assertEqual(datetime(year=1987, month=8, day=02).date(), contact.birthday)
        self.assertEqual("A plumber", contact.description)
        self.assertTrue(contact.image)

#        filename, blob = decode_b64binary(img_content)

        self.assertEqual(blob, contact.image.image.read())

    def test_create_contact02(self):
        """sandboxed with m2m"""
        user = self.user

        languages = Language.objects.all()
        if not languages or len(languages) < 2:
            Language.objects.all().delete()
            languages = [Language.objects.create(code=u'en', name=u'English'),
                         Language.objects.create(code=u'fr', name=u'French'),
                         Language.objects.create(code=u'es', name=u'Spanish'),
                        ]

        xml_content = """
        <?xml version="1.0" encoding="UTF-8"?><?mso-infoPathSolution solutionVersion="1.0.0.14" productVersion="12.0.0" PIVersion="1.0.0.0" href="file:///C:\Users\User\Desktop\Infopath\create_contact.xsn" name="urn:schemas-microsoft-com:office:infopath:create-contact:-myXSD-2011-07-04T07-44-13" ?><?mso-application progid="InfoPath.Document" versionProgid="InfoPath.Document.2"?><my:CremeCRMCrudity xmlns:my="http://schemas.microsoft.com/office/infopath/2003/myXSD/2011-07-04T07:44:13" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xml:lang="fr">
            <my:user_id>%s</my:user_id>
            <my:created xsi:nil="true" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">2003-02-01</my:created>
            <my:first_name>Mario</my:first_name>
            <my:last_name>Bros</my:last_name>
            <my:url_site>http://mario.com</my:url_site>
            <my:email>mario@bros.com</my:email>
            <my:birthday xsi:nil="true" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">02/08/1987</my:birthday>
            <my:language>
                <my:language_value xsi:nil="true"></my:language_value>
                <my:language_value>%s</my:language_value>
                <my:language_value>%s</my:language_value>
            </my:language>
            <my:description>
                <div xmlns="http://www.w3.org/1999/xhtml">A plumber</div>
            </my:description>
        </my:CremeCRMCrudity>""" % (user.id, languages[0].id, languages[1].id)

        infopath_input = self._get_infopath_input(ContactFakeBackend, password=u"creme", subject="create_ce_infopath",
                                                  body_map={'user_id':     user.id,
                                                            'is_actived':  True,
                                                            "first_name":  "",
                                                            "last_name":   "",
                                                            "email":       "none@none.com",
                                                            "description": "",
                                                            "birthday":    "",
                                                            "created":     "",
                                                            'url_site':    "",
                                                            "language":    ""
                                                           },
                                                   model=Contact
                                                  )

        q_contact_existing_ids = self._get_existing_q(Contact)
        self.assertEqual(0, WaitingAction.objects.count())
        infopath_input.create(self._get_pop_email(body=u"password=creme", senders=('user@cremecrm.com',),
                                                  subject="create_ce_infopath",
                                                  attachments=[self._build_attachment(content=xml_content)])
                                                 )
        self.assertEqual(1, WaitingAction.objects.count())

        wa = WaitingAction.objects.all()[0]
        expected_data = {"user_id": "%s"  % user.id, "created": "2003-02-01", "last_name": "Bros",
                         "first_name": "Mario", "email": "mario@bros.com", "url_site": "http://mario.com",
                         "is_actived": True, "birthday": "02/08/1987", "description": "A plumber",
                         "language": "\n%s\n%s" % (languages[0].id, languages[1].id),
                        }
        self.assertEqual(expected_data, wa.get_data())

        infopath_input.get_backend(CrudityBackend.normalize_subject("create_ce_infopath")).create(wa)
        contact = Contact.objects.filter(q_contact_existing_ids)[0]

        self.assertEqual(user, contact.user)
        self.assertEqual(datetime(year=2003, month=02, day=01), contact.created)
        self.assertEqual("Bros", contact.last_name)
        self.assertEqual("Mario", contact.first_name)
        self.assertEqual("mario@bros.com", contact.email)
        self.assertEqual("http://mario.com", contact.url_site)
        self.assertIs(contact.is_actived, True)
        self.assertEqual(datetime(year=1987, month=8, day=02).date(), contact.birthday)
        self.assertEqual("A plumber", contact.description)
        self.assertEqual(set(languages[:2]), set(contact.language.all()))

    def test_create_contact03(self):
        """unsandboxed with m2m"""
        user = self.user

        languages = Language.objects.all()
        if not languages or len(languages) < 2:
            Language.objects.all().delete()
            languages = [Language.objects.create(code=u'en', name=u'English'),
                         Language.objects.create(code=u'fr', name=u'French'),
                         Language.objects.create(code=u'es', name=u'Spanish'),
                        ]

        xml_content = """
        <?xml version="1.0" encoding="UTF-8"?><?mso-infoPathSolution solutionVersion="1.0.0.14" productVersion="12.0.0" PIVersion="1.0.0.0" href="file:///C:\Users\User\Desktop\Infopath\create_contact.xsn" name="urn:schemas-microsoft-com:office:infopath:create-contact:-myXSD-2011-07-04T07-44-13" ?><?mso-application progid="InfoPath.Document" versionProgid="InfoPath.Document.2"?><my:CremeCRMCrudity xmlns:my="http://schemas.microsoft.com/office/infopath/2003/myXSD/2011-07-04T07:44:13" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xml:lang="fr">
            <my:user_id>%s</my:user_id>
            <my:created xsi:nil="true" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">2003-02-01</my:created>
            <my:first_name>Mario</my:first_name>
            <my:last_name>Bros</my:last_name>
            <my:url_site>http://mario.com</my:url_site>
            <my:email>mario@bros.com</my:email>
            <my:birthday xsi:nil="true" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">02/08/1987</my:birthday>
            <my:language>
                <my:language_value xsi:nil="true"></my:language_value>
                <my:language_value>%s</my:language_value>
                <my:language_value>%s</my:language_value>
            </my:language>
            <my:description>
                <div xmlns="http://www.w3.org/1999/xhtml">A plumber</div>
            </my:description>
        </my:CremeCRMCrudity>""" % (user.id, languages[0].id, languages[1].id)

        infopath_input = self._get_infopath_input(ContactFakeBackend, password=u"creme",
                                                  subject="create_ce_infopath",
                                                  body_map={'user_id':     user.id,
                                                            'is_actived':  True,
                                                            "first_name":  "",
                                                            "last_name":   "",
                                                            "email":       "none@none.com",
                                                            "description": "",
                                                            "birthday":    "",
                                                            "created":     "",
                                                            'url_site':    "",
                                                            "language":    ""
                                                           },
                                                  model=Contact,
                                                  in_sandbox=False,
                                                 )

        q_contact_existing_ids = self._get_existing_q(Contact)
        self.assertEqual(0, WaitingAction.objects.count())
        infopath_input.create(self._get_pop_email(body=u"password=creme", senders=('user@cremecrm.com',),
                                                  subject="create_ce_infopath",
                                                  attachments=[self._build_attachment(content=xml_content)]
                                                 )
                             )
        self.assertEqual(0, WaitingAction.objects.count())
        self.assertEqual(1, Contact.objects.filter(q_contact_existing_ids).count())

        contact = Contact.objects.filter(q_contact_existing_ids)[0]
        self.assertEqual(user, contact.user)
        self.assertEqual(datetime(year=2003, month=02, day=01), contact.created)
        self.assertEqual("Bros", contact.last_name)
        self.assertEqual("Mario", contact.first_name)
        self.assertEqual("mario@bros.com", contact.email)
        self.assertEqual("http://mario.com", contact.url_site)
        self.assertIs(contact.is_actived, True)
        self.assertEqual(datetime(year=1987, month=8, day=02).date(), contact.birthday)
        self.assertEqual("A plumber", contact.description)
        self.assertEqual(set(languages[:2]), set(contact.language.all()))

    def test_create_document01(self):
        """sandboxed with image"""
        user = self.user
        self.maxDiff = None
        folder = Folder.objects.create(user=user, title="test_create_document01")

        xml_content = """
        <?xml version="1.0" encoding="UTF-8"?><?mso-infoPathSolution solutionVersion="1.0.0.14" productVersion="12.0.0" PIVersion="1.0.0.0" href="file:///C:\Users\User\Desktop\Infopath\create_document.xsn" name="urn:schemas-microsoft-com:office:infopath:create-document:-myXSD-2011-07-04T07-44-13" ?><?mso-application progid="InfoPath.Document" versionProgid="InfoPath.Document.2"?><my:CremeCRMCrudity xmlns:my="http://schemas.microsoft.com/office/infopath/2003/myXSD/2011-07-04T07:44:13" xml:lang="fr">
            <my:user_id>%s</my:user_id>
            <my:title>My doc</my:title>
            <my:folder_id>%s</my:folder_id>
            <my:filedata>x0lGQRQAAAABAAAAAAAAAHwCAAAGAAAAYgAuAHAAbgBnAAAAiVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAABHNCSVQICAgIfAhkiAAAAAlwSFlzAAABuwAAAbsBOuzj4gAAABl0RVh0U29mdHdhcmUAd3d3Lmlua3NjYXBlLm9yZ5vuPBoAAAH5SURBVDiNpZM9a1RBFIbfd87M3N3szW6iYoIYlYBgY6FNwMafIOJPsLCwEm3UQoKFYhk7/4lYGqxtRPAr6kIS3KjZTbIfc+/MsfAjyV5FwYFTnAPnmfc9Z4aqiv85drzQeJQ9YENOmpaZEsPm7OEZdtvb7dWL6xf+CuAtnjp6eebaKAVLA5SD1Hu9/LYJYvZPCsy+LCErY1QKYK2AgHACgEf6NwsZGmKo4j2gChKCBoAhRO7zOhRFAp7oTX35S7Wqor5UP39oYfohatoyM2aOJMtQoAgFhl+Hq0URi9AtyI4eSz08j1f1zD4FNPGcn3eni1GAs4KYdjdjGnLEJ4KK9uhDAAWxMoOiG9eNIXzdQ2xlMfC1DMYI2ATwOwAccpc5ZJmvNnuPeq0GI3QI30sVgCpf9VcG7wadsAYF8MOBEQPnLayxSIU67WMT23izF8C9L5G3efbElbmnqOlEMQhIUbXz7PNHBmXc0sdpA/f0rq5ULexmXVWNACBOYBKC7qTj0alPm7gx3rwPQJKObkKHSUFArACKEgIYwRCrGFQGtNcCQU4uTh7s2/4l15IFmZZ5Nak1Wgvvbc8vWbFfKIwkyxhir4/+J72jJcd/Ixdpc+QHoo1OS3XipIkIjt8cGXv5Vr5RAVQkLtLnyKcUan4GLGhKU+y82Ol8A49h31zz9A1IAAAAAElFTkSuQmCC</my:filedata>
            <my:description>
                <div xmlns="http://www.w3.org/1999/xhtml">A document</div>
            </my:description>
        </my:CremeCRMCrudity>""" % (user.id, folder.id)


        infopath_input = self._get_infopath_input(DocumentFakeBackend, password=u"creme", subject="create_ce_infopath",
                                                  body_map={'user_id':     user.id,
                                                            "filedata":    "",
                                                            "title":       "",
                                                            "description": "",
                                                            "folder_id":   ""
                                                           }
                                                 )

        q_document_existing_ids = self._get_existing_q(Document)
        self.assertEqual(0, WaitingAction.objects.count())
        infopath_input.create(self._get_pop_email(body=u"password=creme", senders=('user@cremecrm.com',),
                              subject="create_ce_infopath",
                              attachments=[self._build_attachment(content=xml_content)])
                             )
        self.assertEqual(1, WaitingAction.objects.count())

        wa = WaitingAction.objects.all()[0]

        img_content = "x0lGQRQAAAABAAAAAAAAAHwCAAAGAAAAYgAuAHAAbgBnAAAAiVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAABHNCSVQICAgIfAhkiAAAAAlwSFlzAAABuwAAAbsBOuzj4gAAABl0RVh0U29mdHdhcmUAd3d3Lmlua3NjYXBlLm9yZ5vuPBoAAAH5SURBVDiNpZM9a1RBFIbfd87M3N3szW6iYoIYlYBgY6FNwMafIOJPsLCwEm3UQoKFYhk7/4lYGqxtRPAr6kIS3KjZTbIfc+/MsfAjyV5FwYFTnAPnmfc9Z4aqiv85drzQeJQ9YENOmpaZEsPm7OEZdtvb7dWL6xf+CuAtnjp6eebaKAVLA5SD1Hu9/LYJYvZPCsy+LCErY1QKYK2AgHACgEf6NwsZGmKo4j2gChKCBoAhRO7zOhRFAp7oTX35S7Wqor5UP39oYfohatoyM2aOJMtQoAgFhl+Hq0URi9AtyI4eSz08j1f1zD4FNPGcn3eni1GAs4KYdjdjGnLEJ4KK9uhDAAWxMoOiG9eNIXzdQ2xlMfC1DMYI2ATwOwAccpc5ZJmvNnuPeq0GI3QI30sVgCpf9VcG7wadsAYF8MOBEQPnLayxSIU67WMT23izF8C9L5G3efbElbmnqOlEMQhIUbXz7PNHBmXc0sdpA/f0rq5ULexmXVWNACBOYBKC7qTj0alPm7gx3rwPQJKObkKHSUFArACKEgIYwRCrGFQGtNcCQU4uTh7s2/4l15IFmZZ5Nak1Wgvvbc8vWbFfKIwkyxhir4/+J72jJcd/Ixdpc+QHoo1OS3XipIkIjt8cGXv5Vr5RAVQkLtLnyKcUan4GLGhKU+y82Ol8A49h31zz9A1IAAAAAElFTkSuQmCC"
        filename, blob = decode_b64binary(img_content)

        self.assertEqual({u"user_id":     unicode(user.id),
                          u"title":       u"My doc",
                          u"folder_id":   unicode(folder.id),
                          u"description": u"A document",
                          #u"filedata": img_content,
                          u"filedata": (filename, blob),
                        },
                        wa.get_data()
                       )

        infopath_input.get_backend(CrudityBackend.normalize_subject("create_ce_infopath")).create(wa)

        document = Document.objects.filter(q_document_existing_ids)[0]
        self.assertEqual(user, document.user)
        self.assertEqual(folder, document.folder)
        self.assertEqual(u"My doc", document.title)
        self.assertEqual(u"A document", document.description)
        self.assertTrue(document.filedata)

        filename, blob = decode_b64binary(img_content)
        self.assertEqual(blob, document.filedata.read())
