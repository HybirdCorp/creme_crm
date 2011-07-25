# -*- coding: utf-8 -*-

from datetime import datetime
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db.models.query_utils import Q

from creme_core.models.entity import CremeEntity

from creme_config.models.setting import SettingValue
from creme_core.models.i18n import Language
from crudity.utils import decode_b64binary
from documents.crudity_email_register import CreateDocumentFromEmailInfopath
from documents.models.document import Document
from documents.models.folder import Folder
from persons.models.contact import Contact

from crudity import CREATE
from crudity.models import History, WaitingAction
from crudity.constants import SETTING_CRUDITY_SANDBOX_BY_USER
from crudity.fetchers.pop import PopEmail
from crudity.backends.email.create.infopath import InfopathCreateFromEmail
from crudity.backends.registry import from_email_crud_registry
from crudity.tests.base import CrudityTestCase


class CreateFromEmailBackendTestCase(CrudityTestCase):
    def test_create01(self):#Unallowed user
        backend = self._get_create_from_email_backend(limit_froms = ('creme@crm.org',), )

        self.assertEqual(0, WaitingAction.objects.count())
        backend.create(PopEmail(body=u"", body_html=u"", senders=('crm@creme.org',)))
        self.assertEqual(0, WaitingAction.objects.count())

    def test_create02(self):#Bad password
        backend = self._get_create_from_email_backend(password = u"creme")

        self.assertEqual(0, WaitingAction.objects.count())
        backend.create(PopEmail(body=u"", body_html=u"", senders=('creme@crm.org',)))
        self.assertEqual(0, WaitingAction.objects.count())

    def test_create03(self):#Text mail sandboxed
        user = self.user
        backend = self._get_create_from_email_backend(password = u"creme", subject = "create_ce",
                                                      body_map = {
                                                            "user_id": user.id,
                                                            "created": "",
                                                        })

        self.assertEqual(0, WaitingAction.objects.count())
        backend.create(PopEmail(body=u"password=creme\nuser_id=%s\ncreated=01/02/2003\n" % (user.id,), senders=('creme@crm.org',), subject="create_ce"))
        self.assertEqual(1, WaitingAction.objects.count())

        wa = WaitingAction.objects.all()[0]

        expected_data = {u"user_id": u"%s" % user.id, u"created": u"01/02/2003"}

        self.assertEqual(expected_data, wa.get_data())

    def test_create04(self):#Text mail with creation
        user = self.user

        backend = self._get_create_from_email_backend(password = u"creme", in_sandbox = False,
                                                      subject = "create_ce",
                                                      body_map = {
                                                            "user_id": user.id,
                                                            "created": "",
                                                      })

        self.assertEqual(0, WaitingAction.objects.count())
        self.assertEqual(0, CremeEntity.objects.count())
        backend.create(PopEmail(body=u"password=creme\nuser_id=%s\ncreated=01-02-2003\n" % (user.id,), senders=('creme@crm.org',), subject="create_ce"))
        self.assertEqual(0, WaitingAction.objects.count())
        self.assertEqual(1, CremeEntity.objects.count())

        ce = CremeEntity.objects.all()[0]

        self.assertEqual(user, ce.user)
        self.assertEqual(datetime(year=2003, month=02, day=01), ce.created)

    def test_create05(self):#Html mail sandboxed
        user = self.user
        backend = self._get_create_from_email_backend(password = u"creme",
                                                      subject = "create_ce",
                                                      body_map = {
                                                            "user_id": user.id,
                                                            "created": "",
                                                      })

        self.assertEqual(0, WaitingAction.objects.count())
        self.assertEqual(0, CremeEntity.objects.count())
        backend.create(PopEmail(body_html=u"""<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN">
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
        self.assertEqual(1, WaitingAction.objects.count())
        self.assertEqual(0, CremeEntity.objects.count())

        wa = WaitingAction.objects.all()[0]

        expected_data = {u"user_id": u"%s" % user.id, u"created": u"01-02-2003"}

        self.assertEqual(expected_data, wa.get_data())

    def test_create06(self):#Html mail with creation
        user = self.user
        backend = self._get_create_from_email_backend(password = u"creme",
                                                      subject = "create_ce",
                                                      in_sandbox = False,
                                                      body_map = {
                                                            "user_id": user.id,
                                                            "created": "",
                                                      })

        self.assertEqual(0, WaitingAction.objects.count())
        self.assertEqual(0, CremeEntity.objects.count())
        backend.create(PopEmail(body_html=u"""<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN">
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
        self.assertEqual(1, CremeEntity.objects.count())

        ce = CremeEntity.objects.all()[0]

        self.assertEqual(user, ce.user)
        self.assertEqual(datetime(year=2003, month=02, day=01), ce.created)

    def test_create07(self):#Text mail sandboxed with one multiline
        user = self.user
        backend = self._get_create_from_email_backend(password = u"creme",
                                                      subject = "create_ce",
                                                      body_map = {
                                                        "user_id": user.id,
                                                        "created": "",
                                                        "description": "",
                                                    })

        self.assertEqual(0, WaitingAction.objects.count())
        backend.create(PopEmail(body=u"password=creme\nuser_id=%s\ncreated=01/02/2003\ndescription=[[I\n want to\n create a    \ncreme entity\n]]\n" % (user.id,), senders=('creme@crm.org',), subject="create_ce"))
        self.assertEqual(1, WaitingAction.objects.count())

        wa = WaitingAction.objects.all()[0]

        expected_data = {u"user_id": u"%s" % user.id, u"created": u"01/02/2003", "description": "I\n want to\n create a    \ncreme entity\n"}

        self.assertEqual(expected_data, wa.get_data())

    def test_create08(self):#Text mail sandboxed with more than one multiline
        user = self.user
        backend = self._get_create_from_email_backend(password = u"creme",
                                                      subject = "create_ce",
                                                      body_map = {
                                                            "user_id": user.id,
                                                            "created": "",
                                                            "description": "",
                                                            "description2": "",
                                                            "description3": "",
                                                            "description4": "",
                                                      })

        self.assertEqual(0, WaitingAction.objects.count())

        body = """
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
        description2=[[I'am the
        second description]]
        created=01/02/2003

        description3=[[


        Not empty


        ]]

        """ % user.id

        backend.create(PopEmail(body=body, senders=('creme@crm.org',), subject="create_ce"))
        self.assertEqual(1, WaitingAction.objects.count())

        wa = WaitingAction.objects.all()[0]

        expected_data = {u"user_id": u"%s" % user.id, u"created": u"01/02/2003",
                         "description": "I\n\n        want\n\n        to\n                    create\n                a\ncreme\nentity\n\n        ",
                         "description2":"I'am the\n        second description",
                         "description3":"\n\n\n        Not empty\n\n\n        ",
                         "description4": "",
        }

        self.assertEqual(expected_data, wa.get_data())


    def test_create09(self):#Text mail sandboxed with more than one multiline and malformed multilines
        user = self.user

        backend = self._get_create_from_email_backend(password = u"creme", in_sandbox = True, subject = "create_ce",
                                                      body_map = {
                                                            "user_id": user.id,
                                                            "created": "",
                                                            "description": "",
                                                            "description2": "",
                                                            "description3": "",
                                                            "description4": "",
                                                        })

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

        backend.create(PopEmail(body=body, senders=('creme@crm.org',), subject="create_ce"))
        self.assertEqual(1, WaitingAction.objects.count())

        wa = WaitingAction.objects.all()[0]

        expected_data = {u"user_id": u"%s" % user.id, u"created": u"01/02/2003",
                         "description": "I",
                         "description2":"I'am the",
                         "description3":"\n\n\n        Not empty\n\n\n        ",
                         "description4": "",
        }

        self.assertEqual(expected_data, wa.get_data())

    def test_create10(self):#Html mail sandboxed with one multiline
        user = self.user
        backend = self._get_create_from_email_backend(password = u"creme",
                                                      subject = "create_ce",
                                                      body_map = {
                                                        "user_id": user.id,
                                                        "created": "",
                                                        "description": "",
                                                    })

        body_html=u"""<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN">
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
        backend.create(PopEmail(body_html=body_html, senders=('creme@crm.org',), subject="create_ce"))
        self.assertEqual(1, WaitingAction.objects.count())

        wa = WaitingAction.objects.all()[0]

        expected_data = {u"user_id": u"%s" % user.id, u"created": u"01-02-2003", "description": "I\n want to\n create a    \ncreme entity\n"}

        self.assertEqual(expected_data, wa.get_data())

    def test_create11(self):#Html mail sandboxed with more than one multiline
        user = self.user
        backend = self._get_create_from_email_backend(password = u"creme",
                                                      subject = "create_ce",
                                                      body_map = {
                                                        "user_id": user.id,
                                                        "created": "",
                                                        "description": "",
                                                        "description2": "",
                                                        "description3": "",
                                                        "description4": "",
                                                    })

        body_html=u"""<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN">
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
        backend.create(PopEmail(body_html=body_html, senders=('creme@crm.org',), subject="create_ce"))
        self.assertEqual(1, WaitingAction.objects.count())

        wa = WaitingAction.objects.all()[0]

        expected_data = {u"user_id": u"%s" % user.id, u"created": u"01-02-2003", "description": "I\n want to\n create a    \ncreme entity\n",
                         u"description2": "        \n Second description  \n \n",
                         u"description3": "\n",
                         u"description4": "                         \nNot empty    \n         ",
                        }

        self.assertEqual(expected_data, wa.get_data())

    def test_create12(self):#Html mail sandboxed with more than one multiline but malformed
        user = self.user
        backend = self._get_create_from_email_backend(password = u"creme",
                                                      subject = "create_ce",
                                                      body_map = {
                                                        "user_id": user.id,
                                                        "created": "",
                                                        "description": "",
                                                        "description2": "",
                                                        "description3": "",
                                                        "description4": "",
                                                    })

        body_html=u"""<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN">
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
        backend.create(PopEmail(body_html=body_html, senders=('creme@crm.org',), subject="create_ce"))
        self.assertEqual(1, WaitingAction.objects.count())

        wa = WaitingAction.objects.all()[0]

        expected_data = {u"user_id": u"%s" % user.id, u"created": u"01-02-2003", "description": "I",
                         u"description2": "        ",
                         u"description3": "\n",
                         u"description4": "                         ",
                        }

        self.assertEqual(expected_data, wa.get_data())

    def test_create13(self):#Text mail sandboxed by user
        user = self.user
        other_user = self.other_user

        contact_user = Contact.objects.create(is_user=user, user=user, email="user@cremecrm.com")
        contact_other_user = Contact.objects.create(is_user=other_user, user=other_user, email="other_user@cremecrm.com")

        self._set_sandbox_by_user()

        backend = self._get_create_from_email_backend(password = u"creme", subject = "create_ce",
                                                      body_map = {
                                                            "user_id": user.id,
                                                            "created": "",
                                                        })

        self.assertEqual(0, WaitingAction.objects.count())
        backend.create(PopEmail(body=u"password=creme\nuser_id=%s\ncreated=01/02/2003\n" % (user.id,), senders=('user@cremecrm.com',), subject="create_ce"))
        self.assertEqual(1, WaitingAction.objects.filter(user=user).count())
        self.assertEqual(0, WaitingAction.objects.filter(user=None).count())

        wa = WaitingAction.objects.all()[0]

        expected_data = {u"user_id": u"%s" % user.id, u"created": u"01/02/2003"}

        self.assertEqual(expected_data, wa.get_data())
        self.assertEqual(user, wa.user)

    def test_create14(self):#Text mail un-sandboxed but by user
        user = self.user
        other_user = self.other_user

        contact_user = Contact.objects.create(is_user=user, user=user, email="user@cremecrm.com")
        contact_other_user = Contact.objects.create(is_user=other_user, user=other_user, email="other_user@cremecrm.com")

        self._set_sandbox_by_user()

        backend = self._get_create_from_email_backend(password = u"creme", subject = "create_ce",
                                                      body_map = {
                                                            "user_id": user.id,
                                                            "created": "",
                                                        }, in_sandbox=False)

        ce_count = CremeEntity.objects.count()
        existing_ce = list(CremeEntity.objects.all().values_list('pk', flat=True))

        self.assertEqual(0, WaitingAction.objects.count())
        self.assertEqual(0, History.objects.count())
        backend.create(PopEmail(body=u"password=creme\nuser_id=%s\ncreated=01/02/2003\n" % (user.id,), senders=('other_user@cremecrm.com',), subject="create_ce"))
        self.assertEqual(0, WaitingAction.objects.count())
        self.assertEqual(ce_count + 1, CremeEntity.objects.count())
        self.assertEqual(1, History.objects.filter(user=contact_other_user).count())
        self.assertEqual(0, History.objects.filter(user=None).count())

        try:
            ce = CremeEntity.objects.filter(~Q(pk__in=existing_ce))[0]
        except IndexError, e:
            self.fail(e)

        self.assertEqual(other_user, History.objects.all()[0].user)
        self.assertEqual(user, ce.user)#Sandbox by user doesn't have to change the assignation set in the mail

    def test_create15(self):#Text mail sandboxed by user and created later
        user = self.user
        other_user = self.other_user
        contact_user = Contact.objects.create(is_user=user, user=user, email="user@cremecrm.com")
        contact_other_user = Contact.objects.create(is_user=other_user, user=other_user, email="other_user@cremecrm.com")
        self._set_sandbox_by_user()
        backend = self._get_create_from_email_backend(password = u"creme", subject = "create_ce",
                                                      body_map = {
                                                            "user_id": user.id,
                                                            "created": "",
                                                        })
        ce_count = CremeEntity.objects.count()
        existing_ce = list(CremeEntity.objects.all().values_list('pk', flat=True))
        self.assertEqual(0, WaitingAction.objects.count())
        self.assertEqual(0, History.objects.count())
        backend.create(PopEmail(body=u"password=creme\nuser_id=%s\ncreated=01/02/2003\n" % (user.id,), senders=('other_user@cremecrm.com',), subject="create_ce"))
        self.assertEqual(1, WaitingAction.objects.count())
        self.assertEqual(0, History.objects.count())
        self.assertEqual(ce_count, CremeEntity.objects.count())

        wa = WaitingAction.objects.all()[0]
        self.assertEqual(other_user, wa.user)

        backend.create_from_waiting_action_n_history(wa)
        self.assertEqual(ce_count + 1, CremeEntity.objects.count())
        self.assertEqual(1, History.objects.count())

        self.assertEqual(user, CremeEntity.objects.get(~Q(pk__in=existing_ce)).user)
        self.assertEqual(other_user, History.objects.all()[0].user)

    def test_create16(self):#Text mail with creation
        user = self.user

        backend = self._get_create_from_email_backend(password = u"creme", in_sandbox = False,
                                                      subject = "create_contact",
                                                      body_map = {
                                                            "user_id": user.id,
                                                            "created": "",
                                                            "is_actived": "",
                                                            "url_site":"",
                                                      },
                                                      model=Contact)
        contact_count = Contact.objects.count()
        self.assertEqual(0, WaitingAction.objects.count())
        self.assertEqual(contact_count, Contact.objects.count())
        backend.create(PopEmail(body=u"password=creme\nuser_id=%s\ncreated=01-02-2003\nis_actived=false\nurl_site=plop" % (user.id,), senders=('creme@crm.org',), subject="create_contact"))
        self.assertEqual(0, WaitingAction.objects.count())
        self.assertEqual(contact_count+1, Contact.objects.count())

        ce = Contact.objects.all()[contact_count]

        self.assertEqual(user, ce.user)
        self.assertEqual(datetime(year=2003, month=02, day=01), ce.created)
        self.assertEqual(False, ce.is_actived)
        self.assertEqual("plop", ce.url_site)

    def test_is_sandbox_by_user_property01(self):
        self._set_sandbox_by_user()

        for backend in from_email_crud_registry.iter_creates_values():
            self.assert_(backend.is_sandbox_by_user)

        sv = SettingValue.objects.get(key=SETTING_CRUDITY_SANDBOX_BY_USER, user=None)
        sv.value = "False"
        sv.save()

        for backend in from_email_crud_registry.iter_creates_values():
            self.assertFalse(backend.is_sandbox_by_user)

    def test_get_owner01(self):#The sandbox is not by user
        user = self.user
        contact_user = Contact.objects.create(is_user=user, user=user, email="user@cremecrm.com")
        backend = self._get_create_from_email_backend(password = u"creme", subject = "create_ce",
                                              body_map = {
                                                    "user_id": user.id,
                                                })
        self.assertEqual(None, backend.get_owner(sender="user@cremecrm.com"))

    def test_get_owner02(self):#The user matches
        self._set_sandbox_by_user()
        user = self.user
        other_user = self.other_user

        contact_user = Contact.objects.create(is_user=user, user=user, email="user@cremecrm.com")
        contact_other_user = Contact.objects.create(is_user=other_user, user=other_user, email="other_user@cremecrm.com")

        backend = self._get_create_from_email_backend(password = u"creme", subject = "create_ce",
                                                      body_map = {
                                                            "user_id": user.id,
                                                            "created": "",
                                                        })
        self.assertEqual(other_user, backend.get_owner(sender="other_user@cremecrm.com"))

    def test_get_owner03(self):#The user doesn't match
        self._set_sandbox_by_user()
        user = self.user
        other_user = self.other_user

        contact_user = Contact.objects.create(is_user=user, user=user, email="user@cremecrm.com")
        contact_other_user = Contact.objects.create(is_user=other_user, user=other_user, email="other_user@cremecrm.com")

        backend = self._get_create_from_email_backend(password = u"creme", subject = "create_ce",
                                                      body_map = {
                                                            "user_id": user.id,
                                                            "created": "",
                                                        })
        self.assertEqual(user, backend.get_owner(sender="another_user@cremecrm.com"))

    def test_get_owner04(self):#The user doesn't match and multiple superuser exists
        self._set_sandbox_by_user()
        superuser1 = self.user

        superuser2 = User.objects.create(username='Kirika2')
        superuser2.set_password("Kirika2")
        superuser2.is_superuser = True
        superuser2.save()

        self.assert_(superuser2.pk > superuser1.pk)

        backend = self._get_create_from_email_backend(password = u"creme", subject = "create_ce",
                                                      body_map = {
                                                            "user_id": superuser1.id,
                                                            "created": "",
                                                        })
        self.assertEqual(superuser2, backend.get_owner(sender="another_user@cremecrm.com"))

    def test_is_configured01(self):
        backend = self._get_create_from_email_backend(password = u"creme", subject = "", body_map = {})
        self.assertFalse(backend.is_configured)

        backend2 = self._get_create_from_email_backend(password = u"creme", subject = "", body_map = {"created": ""})
        self.assertFalse(backend2.is_configured)

        backend3 = self._get_create_from_email_backend(password = u"creme", subject = "create_ce", body_map = {"created": ""})
        self.assert_(backend3.is_configured)

    def test_create_contact01(self):#Text mail sandboxed
        user = self.user
        count = Contact.objects.count()

        backend = self._get_create_from_email_backend(password = u"creme", subject = "create_contact",
                                                      body_map = {
                                                                    'user_id': user.id, 'is_actived': True,
                                                                    "first_name":"", "last_name":"",
                                                                    "email": "none@none.com", "description": "",
                                                                    "birthday":"", "created":"", 'url_site': "",},
                                                      model=Contact)

        body = [u"password=creme", "user_id=%s"  % (user.id,),
                "created=01/02/2003", "last_name=Bros",
                "first_name=Mario", "email=mario@bros.com",
                "url_site=http://mario.com", "birthday=02/08/1987",
                u"description=[[A plumber]]",
        ]

        self.assertEqual(0, WaitingAction.objects.count())
        backend.create(PopEmail(body="\n".join(body), senders=('creme@crm.org',), subject="create_contact"))
        self.assertEqual(1, WaitingAction.objects.count())

        wa = WaitingAction.objects.all()[0]

        expected_data = {u"user_id": u"%s"  % (user.id,), u"created": u"01/02/2003", u"last_name": u"Bros",
                        u"first_name": u"Mario", u"email": u"mario@bros.com", u"url_site": u"http://mario.com",
                        u"is_actived": u"True", u"birthday": u"02/08/1987", u"description": u"A plumber",
                        }
        self.assertEqual(expected_data, wa.get_data())

        backend.create_from_waiting_action_n_history(wa)
        contact = Contact.objects.all()[count]
        self.assertEqual(user.id, contact.user_id)
        self.assertEqual(datetime(year=2003, month=02, day=01), contact.created)
        self.assertEqual("Bros", contact.last_name)
        self.assertEqual("Mario", contact.first_name)
        self.assertEqual("mario@bros.com", contact.email)
        self.assertEqual("http://mario.com", contact.url_site)
        self.assertEqual(True, contact.is_actived)
        self.assertEqual(datetime(year=1987, month=8, day=02).date(), contact.birthday)
        self.assertEqual("A plumber", contact.description)


class WaitingActionTestCase(CrudityTestCase):
    def test_can_validate_or_delete01(self):#Sandbox for everyone
        action = WaitingAction.objects.create(user=None, be_name="", type=CREATE, ct=ContentType.objects.get_for_model(CremeEntity))
        self.assert_(action.can_validate_or_delete(self.user)[0])
        self.assert_(action.can_validate_or_delete(self.other_user)[0])

    def test_can_validate_or_delete02(self):#Sandbox by user
        self._set_sandbox_by_user()
        action  = WaitingAction.objects.create(user=self.user,       be_name="", type=CREATE, ct=ContentType.objects.get_for_model(CremeEntity))
        self.assert_(action.can_validate_or_delete(self.user)[0])
        self.assertFalse(action.can_validate_or_delete(self.other_user)[0])

        action2 = WaitingAction.objects.create(user=self.other_user, be_name="", type=CREATE, ct=ContentType.objects.get_for_model(CremeEntity))
        self.assert_(action2.can_validate_or_delete(self.user)[0])
        self.assert_(action2.can_validate_or_delete(self.other_user)[0])

    def test_auto_assignation01(self):
        """If the sandbox was not by user, but now it is all WaitingAction has to be assigned to someone"""
        #Sandbox for everyone
        action  = WaitingAction.objects.create(be_name="", type=CREATE, ct=ContentType.objects.get_for_model(CremeEntity))

        self.assertEqual(None, action.user)

        #Sandbox will be by user
        self._set_sandbox_by_user()

        self.assertEqual(0, WaitingAction.objects.filter(user=None).count())
        self.assertEqual(self.user, WaitingAction.objects.filter(user__isnull=False)[0].user)

    def test_auto_assignation02(self):
        action  = WaitingAction.objects.create(be_name="", type=CREATE, ct=ContentType.objects.get_for_model(CremeEntity))
        self.assertEqual(None, action.user)

        superuser1 = self.user

        superuser2 = User.objects.create(username='Kirika2')
        superuser2.set_password("Kirika2")
        superuser2.is_superuser = True
        superuser2.save()

        self._set_sandbox_by_user()
        self.assertEqual(0, WaitingAction.objects.filter(user=None).count())
        self.assertEqual(superuser2, WaitingAction.objects.filter(user__isnull=False)[0].user)


class InfopathCreateFromEmailBackendTestCase(CrudityTestCase):
    def _get_create_from_email_backend(self, backend_klass=InfopathCreateFromEmail, *args, **kwargs):
        return super(InfopathCreateFromEmailBackendTestCase, self)._get_create_from_email_backend(backend_klass=backend_klass, *args, **kwargs)

    def _build_attachment(self, filename="", content_type='application/x-microsoft-infopathform', content=""):
        return (filename, SimpleUploadedFile(filename, content, content_type=content_type))

    def test_create01(self):#Unallowed user
        backend = self._get_create_from_email_backend(limit_froms = ('creme@cremecrm.com',))

        self.assertEqual(0, WaitingAction.objects.count())
        backend.create(PopEmail(body=u"", body_html=u"", senders=('crm@cremecrm.com',), attachments=[self._build_attachment()]))
        self.assertEqual(0, WaitingAction.objects.count())

    def test_create02(self):#Bad password
        backend = self._get_create_from_email_backend(password = u"creme")

        self.assertEqual(0, WaitingAction.objects.count())
        backend.create(PopEmail(body=u"", body_html=u"", senders=('creme@cremecrm.com',), attachments=[self._build_attachment()]))
        self.assertEqual(0, WaitingAction.objects.count())

    def test_create03(self):#Allowed password, subject but attachment content_type is unallowed
        user = self.user

        backend = self._get_create_from_email_backend(password = u"creme", in_sandbox = False,
                                                      subject = "create_ce_infopath",
                                                      body_map = {
                                                            "user_id": user.id,
                                                            "created": "",
                                                      })

        self.assertEqual(0, WaitingAction.objects.count())
        backend.create(PopEmail(body=u"password=creme", senders=('creme@cremecrm.com',), subject="create_ce_infopath", attachments=[self._build_attachment(content_type='text/invalid')]))
        self.assertEqual(0, WaitingAction.objects.count())

    def test_create04(self):#Allowed but empty xml
        user = self.user

        backend = self._get_create_from_email_backend(password = u"creme", in_sandbox = False,
                                                      subject = "create_ce_infopath",
                                                      body_map = {
                                                            "user_id": user.id,
                                                            "created": "",
                                                      })

        self.assertEqual(0, WaitingAction.objects.count())
        backend.create(PopEmail(body=u"password=creme", senders=('creme@cremecrm.com',), subject="create_ce_infopath", attachments=[self._build_attachment()]))
        self.assertEqual(0, WaitingAction.objects.count())

    def test_create05(self):#Allowed but bad xml
        user = self.user

        backend = self._get_create_from_email_backend(password = u"creme", in_sandbox = False,
                                                      subject = "create_ce_infopath",
                                                      body_map = {
                                                            "user_id": user.id,
                                                            "created": "",
                                                      })

        self.assertEqual(0, WaitingAction.objects.count())
        backend.create(PopEmail(body=u"password=creme", senders=('creme@cremecrm.com',), subject="create_ce_infopath", attachments=[self._build_attachment(content="invalid")]))
        self.assertEqual(0, WaitingAction.objects.count())

    def test_create06(self):#Allowed with valid xml
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

        backend = self._get_create_from_email_backend(password = u"creme",
                                                      subject = "create_ce_infopath",
                                                      body_map = {
                                                            "user_id": user.id,
                                                            "created": "",
                                                            "description": "",
                                                      })

        self.assertEqual(0, WaitingAction.objects.count())
        backend.create(PopEmail(body=u"password=creme", senders=('creme@cremecrm.com',), subject="create_ce_infopath", attachments=[self._build_attachment(content=xml_content)]))
        self.assertEqual(1, WaitingAction.objects.count())

        wa = WaitingAction.objects.all()[0]

        expected_data = {u"user_id": u"%s" % other_user.id, u"created": u"2003-02-01", u"description": u"My creme entity\n\ndescription"}

        self.assertEqual(expected_data, wa.get_data())
        self.assertEqual(None, wa.user)#Sandbox is not by user

    def test_create07(self):#Allowed with valid but weird xml
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

        backend = self._get_create_from_email_backend(password = u"creme",
                                                      subject = "create_ce_infopath",
                                                      body_map = {
                                                            "user_id": user.id,
                                                            "created": "",
                                                            "description": "",
                                                      })

        self.assertEqual(0, WaitingAction.objects.count())
        backend.create(PopEmail(body=u"password=creme", senders=('creme@cremecrm.com',), subject="create_ce_infopath", attachments=[self._build_attachment(content=xml_content)]))
        self.assertEqual(1, WaitingAction.objects.count())

        wa = WaitingAction.objects.all()[0]

        expected_data = {u"user_id": u"%s" % other_user.id, u"created": u"2003-02-01", u"description": u"My creme entity\n\ndescription"}

        self.assertEqual(expected_data, wa.get_data())

    def test_create08(self):#Allowed with valid xml with sandbox by user
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

        backend = self._get_create_from_email_backend(password = u"creme",
                                                      subject = "create_ce_infopath",
                                                      body_map = {
                                                            "user_id": user.id,
                                                            "created": "",
                                                            "description": "",
                                                      })

        self.assertEqual(0, WaitingAction.objects.count())
        backend.create(PopEmail(body=u"password=creme", senders=('creme@cremecrm.com',), subject="create_ce_infopath", attachments=[self._build_attachment(content=xml_content)]))
        self.assertEqual(1, WaitingAction.objects.count())

        wa = WaitingAction.objects.all()[0]

        expected_data = {u"user_id": u"%s" % other_user.id, u"created": u"2003-02-01", u"description": u"My creme entity\n\ndescription"}

        self.assertEqual(expected_data, wa.get_data())
        self.assertEqual(user, wa.user)

    def test_create09(self):#Allowed with valid xml with sandbox by user with real match on email
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

        backend = self._get_create_from_email_backend(password = u"creme",
                                                      subject = "create_ce_infopath",
                                                      body_map = {
                                                            "user_id": user.id,
                                                            "created": "",
                                                            "description": "",
                                                      })

        self.assertEqual(0, WaitingAction.objects.count())
        backend.create(PopEmail(body=u"password=creme", senders=('other_user@cremecrm.com',), subject="create_ce_infopath", attachments=[self._build_attachment(content=xml_content)]))
        self.assertEqual(1, WaitingAction.objects.count())

        wa = WaitingAction.objects.all()[0]

        expected_data = {u"user_id": u"%s" % other_user.id, u"created": u"2003-02-01", u"description": u"My creme entity\n\ndescription"}

        self.assertEqual(expected_data, wa.get_data())
        self.assertEqual(other_user, wa.user)

    def test_create10(self):#Allowed with valid xml with no sandbox with default values
        user = self.user

        xml_content = """
        <?xml version="1.0" encoding="UTF-8"?><?mso-infoPathSolution solutionVersion="1.0.0.14" productVersion="12.0.0" PIVersion="1.0.0.0" href="file:///C:\Users\Raph\Desktop\Infopath\create_contact.xsn" name="urn:schemas-microsoft-com:office:infopath:create-contact:-myXSD-2011-07-04T07-44-13" ?><?mso-application progid="InfoPath.Document" versionProgid="InfoPath.Document.2"?><my:CremeCRMCrudity xmlns:my="http://schemas.microsoft.com/office/infopath/2003/myXSD/2011-07-04T07:44:13" xml:lang="fr">
        </my:CremeCRMCrudity>"""

        backend = self._get_create_from_email_backend(password = u"creme",
                                                      in_sandbox=False,
                                                      subject = "create_ce_infopath",
                                                      body_map = {
                                                            "user_id": user.id,
                                                            "created": "2011-10-09",
                                                            "description": "default",
                                                      })

        ce_count = CremeEntity.objects.count()
        q_ce_existing_ids = ~Q(pk__in=list(CremeEntity.objects.all().values_list('pk', flat=True)))

        self.assertEqual(0, WaitingAction.objects.count())
        backend.create(PopEmail(body=u"password=creme", senders=('other_user@cremecrm.com',), subject="create_ce_infopath", attachments=[self._build_attachment(content=xml_content)]))
        self.assertEqual(0, WaitingAction.objects.count())
        self.assertEqual(ce_count + 1, CremeEntity.objects.count())

        ce = CremeEntity.objects.filter(q_ce_existing_ids)[0]
        self.assertEqual(user, ce.user)
        self.assertEqual(9, ce.created.day)
        self.assertEqual(10, ce.created.month)
        self.assertEqual(2011, ce.created.year)

    def test_create11(self):#Allowed with valid xml with no sandbox but by user with real match on email
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

        backend = self._get_create_from_email_backend(password = u"creme",
                                                      in_sandbox=False,
                                                      subject = "create_ce_infopath",
                                                      body_map = {
                                                            "user_id": user.id,
                                                            "created": "",
                                                      })

        ce_count = CremeEntity.objects.count()
        q_ce_existing_ids = ~Q(pk__in=list(CremeEntity.objects.all().values_list('pk', flat=True)))

        self.assertEqual(0, WaitingAction.objects.count())
        backend.create(PopEmail(body=u"password=creme", senders=('other_user@cremecrm.com',), subject="create_ce_infopath", attachments=[self._build_attachment(content=xml_content)]))
        self.assertEqual(0, WaitingAction.objects.count())
        self.assertEqual(ce_count + 1, CremeEntity.objects.count())

        ce = CremeEntity.objects.filter(q_ce_existing_ids)[0]

        self.assertEqual(other_user, ce.user)
        self.assertEqual(1, ce.created.day)
        self.assertEqual(2, ce.created.month)
        self.assertEqual(2003, ce.created.year)

    def test_create_contact01(self):#sandboxed with image
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

        backend = self._get_create_from_email_backend(password = u"creme", subject = "create_ce_infopath",
                                                      body_map = {
                                                                    'user_id': user.id, 'is_actived': True,
                                                                    "first_name":"", "last_name":"",
                                                                    "email": "none@none.com", "description": "",
                                                                    "birthday":"", "created":"", 'url_site': "",
                                                                    "image": ""},
                                                      model=Contact)

        q_contact_existing_ids = ~Q(pk__in=list(Contact.objects.all().values_list('pk', flat=True)))
        self.assertEqual(0, WaitingAction.objects.count())
        backend.create(PopEmail(body=u"password=creme", senders=('user@cremecrm.com',), subject="create_ce_infopath", attachments=[self._build_attachment(content=xml_content)]))
        self.assertEqual(1, WaitingAction.objects.count())

        wa = WaitingAction.objects.all()[0]

        img_content = "x0lGQRQAAAABAAAAAAAAAHwCAAAGAAAAYgAuAHAAbgBnAAAAiVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAABHNCSVQICAgIfAhkiAAAAAlwSFlzAAABuwAAAbsBOuzj4gAAABl0RVh0U29mdHdhcmUAd3d3Lmlua3NjYXBlLm9yZ5vuPBoAAAH5SURBVDiNpZM9a1RBFIbfd87M3N3szW6iYoIYlYBgY6FNwMafIOJPsLCwEm3UQoKFYhk7/4lYGqxtRPAr6kIS3KjZTbIfc+/MsfAjyV5FwYFTnAPnmfc9Z4aqiv85drzQeJQ9YENOmpaZEsPm7OEZdtvb7dWL6xf+CuAtnjp6eebaKAVLA5SD1Hu9/LYJYvZPCsy+LCErY1QKYK2AgHACgEf6NwsZGmKo4j2gChKCBoAhRO7zOhRFAp7oTX35S7Wqor5UP39oYfohatoyM2aOJMtQoAgFhl+Hq0URi9AtyI4eSz08j1f1zD4FNPGcn3eni1GAs4KYdjdjGnLEJ4KK9uhDAAWxMoOiG9eNIXzdQ2xlMfC1DMYI2ATwOwAccpc5ZJmvNnuPeq0GI3QI30sVgCpf9VcG7wadsAYF8MOBEQPnLayxSIU67WMT23izF8C9L5G3efbElbmnqOlEMQhIUbXz7PNHBmXc0sdpA/f0rq5ULexmXVWNACBOYBKC7qTj0alPm7gx3rwPQJKObkKHSUFArACKEgIYwRCrGFQGtNcCQU4uTh7s2/4l15IFmZZ5Nak1Wgvvbc8vWbFfKIwkyxhir4/+J72jJcd/Ixdpc+QHoo1OS3XipIkIjt8cGXv5Vr5RAVQkLtLnyKcUan4GLGhKU+y82Ol8A49h31zz9A1IAAAAAElFTkSuQmCC"

        expected_data = {u"user_id": u"%s"  % (user.id,), u"created": u"2003-02-01", u"last_name": u"Bros",
                        u"first_name": u"Mario", u"email": u"mario@bros.com", u"url_site": u"http://mario.com",
                        u"is_actived": u"True", u"birthday": u"02/08/1987", u"description": u"A plumber",
                        u"image": img_content,
                        }

        self.assertEqual(expected_data, wa.get_data())

        backend.create_from_waiting_action_n_history(wa)
        contact = Contact.objects.filter(q_contact_existing_ids)[0]

        self.assertEqual(user.id, contact.user_id)
        self.assertEqual(datetime(year=2003, month=02, day=01), contact.created)
        self.assertEqual("Bros", contact.last_name)
        self.assertEqual("Mario", contact.first_name)
        self.assertEqual("mario@bros.com", contact.email)
        self.assertEqual("http://mario.com", contact.url_site)
        self.assertEqual(True, contact.is_actived)
        self.assertEqual(datetime(year=1987, month=8, day=02).date(), contact.birthday)
        self.assertEqual("A plumber", contact.description)
        self.assert_(contact.image)

        filename, blob = decode_b64binary(img_content)

        self.assertEqual(blob, contact.image.image.read())

    def test_create_contact02(self):#sandboxed with m2m
        user = self.user

        languages = Language.objects.all()
        if not languages or len(languages) < 2:
            Language.objects.all().delete()
            languages = [Language.objects.create(code=u'en', name=u'English'),
                         Language.objects.create(code=u'fr', name=u'French'),
                         Language.objects.create(code=u'es', name=u'Spanish')]

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

        backend = self._get_create_from_email_backend(password = u"creme", subject = "create_ce_infopath",
                                                      body_map = {
                                                                    'user_id': user.id, 'is_actived': True,
                                                                    "first_name":"", "last_name":"",
                                                                    "email": "none@none.com", "description": "",
                                                                    "birthday":"", "created":"", 'url_site': "",
                                                                    "language": ""},
                                                      model=Contact)

        q_contact_existing_ids = ~Q(pk__in=list(Contact.objects.all().values_list('pk', flat=True)))
        self.assertEqual(0, WaitingAction.objects.count())
        backend.create(PopEmail(body=u"password=creme", senders=('user@cremecrm.com',), subject="create_ce_infopath", attachments=[self._build_attachment(content=xml_content)]))
        self.assertEqual(1, WaitingAction.objects.count())

        wa = WaitingAction.objects.all()[0]

        expected_data = {u"user_id": u"%s"  % (user.id,), u"created": u"2003-02-01", u"last_name": u"Bros",
                        u"first_name": u"Mario", u"email": u"mario@bros.com", u"url_site": u"http://mario.com",
                        u"is_actived": u"True", u"birthday": u"02/08/1987", u"description": u"A plumber",
                        u"language": u"\n%s\n%s" % (languages[0].id, languages[1].id),
                        }

        self.assertEqual(expected_data, wa.get_data())

        backend.create_from_waiting_action_n_history(wa)
        contact = Contact.objects.filter(q_contact_existing_ids)[0]

        self.assertEqual(user.id, contact.user_id)
        self.assertEqual(datetime(year=2003, month=02, day=01), contact.created)
        self.assertEqual("Bros", contact.last_name)
        self.assertEqual("Mario", contact.first_name)
        self.assertEqual("mario@bros.com", contact.email)
        self.assertEqual("http://mario.com", contact.url_site)
        self.assertEqual(True, contact.is_actived)
        self.assertEqual(datetime(year=1987, month=8, day=02).date(), contact.birthday)
        self.assertEqual("A plumber", contact.description)
        self.assertEqual(set(languages[:2]), set(contact.language.all()))

    def test_create_contact03(self):#unsandboxed with m2m
        user = self.user

        languages = Language.objects.all()
        if not languages or len(languages) < 2:
            Language.objects.all().delete()
            languages = [Language.objects.create(code=u'en', name=u'English'),
                         Language.objects.create(code=u'fr', name=u'French'),
                         Language.objects.create(code=u'es', name=u'Spanish')]

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

        backend = self._get_create_from_email_backend(password = u"creme", subject = "create_ce_infopath",
                                                      body_map = {
                                                                    'user_id': user.id, 'is_actived': True,
                                                                    "first_name":"", "last_name":"",
                                                                    "email": "none@none.com", "description": "",
                                                                    "birthday":"", "created":"", 'url_site': "",
                                                                    "language": ""},
                                                      model=Contact,
                                                      in_sandbox=False,)

        q_contact_existing_ids = ~Q(pk__in=list(Contact.objects.all().values_list('pk', flat=True)))
        self.assertEqual(0, WaitingAction.objects.count())
        backend.create(PopEmail(body=u"password=creme", senders=('user@cremecrm.com',), subject="create_ce_infopath", attachments=[self._build_attachment(content=xml_content)]))
        self.assertEqual(0, WaitingAction.objects.count())
        self.assertEqual(1, Contact.objects.filter(q_contact_existing_ids).count())

        contact = Contact.objects.filter(q_contact_existing_ids)[0]

        self.assertEqual(user.id, contact.user_id)
        self.assertEqual(datetime(year=2003, month=02, day=01), contact.created)
        self.assertEqual("Bros", contact.last_name)
        self.assertEqual("Mario", contact.first_name)
        self.assertEqual("mario@bros.com", contact.email)
        self.assertEqual("http://mario.com", contact.url_site)
        self.assertEqual(True, contact.is_actived)
        self.assertEqual(datetime(year=1987, month=8, day=02).date(), contact.birthday)
        self.assertEqual("A plumber", contact.description)
        self.assertEqual(set(languages[:2]), set(contact.language.all()))

    def test_create_document01(self):#sandboxed with image
        user = self.user

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


        backend = self._get_create_from_email_backend(password = u"creme", subject = "create_ce_infopath",
                                                      body_map = {'user_id': user.id, "filedata":"", "title":"", "description": "", "folder_id": ""},
                                                      model=Document,
                                                      backend_klass=CreateDocumentFromEmailInfopath)

        q_document_existing_ids = ~Q(pk__in=list(Document.objects.all().values_list('pk', flat=True)))
        self.assertEqual(0, WaitingAction.objects.count())
        backend.create(PopEmail(body=u"password=creme", senders=('user@cremecrm.com',), subject="create_ce_infopath", attachments=[self._build_attachment(content=xml_content)]))
        self.assertEqual(1, WaitingAction.objects.count())

        wa = WaitingAction.objects.all()[0]

        img_content = "x0lGQRQAAAABAAAAAAAAAHwCAAAGAAAAYgAuAHAAbgBnAAAAiVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAABHNCSVQICAgIfAhkiAAAAAlwSFlzAAABuwAAAbsBOuzj4gAAABl0RVh0U29mdHdhcmUAd3d3Lmlua3NjYXBlLm9yZ5vuPBoAAAH5SURBVDiNpZM9a1RBFIbfd87M3N3szW6iYoIYlYBgY6FNwMafIOJPsLCwEm3UQoKFYhk7/4lYGqxtRPAr6kIS3KjZTbIfc+/MsfAjyV5FwYFTnAPnmfc9Z4aqiv85drzQeJQ9YENOmpaZEsPm7OEZdtvb7dWL6xf+CuAtnjp6eebaKAVLA5SD1Hu9/LYJYvZPCsy+LCErY1QKYK2AgHACgEf6NwsZGmKo4j2gChKCBoAhRO7zOhRFAp7oTX35S7Wqor5UP39oYfohatoyM2aOJMtQoAgFhl+Hq0URi9AtyI4eSz08j1f1zD4FNPGcn3eni1GAs4KYdjdjGnLEJ4KK9uhDAAWxMoOiG9eNIXzdQ2xlMfC1DMYI2ATwOwAccpc5ZJmvNnuPeq0GI3QI30sVgCpf9VcG7wadsAYF8MOBEQPnLayxSIU67WMT23izF8C9L5G3efbElbmnqOlEMQhIUbXz7PNHBmXc0sdpA/f0rq5ULexmXVWNACBOYBKC7qTj0alPm7gx3rwPQJKObkKHSUFArACKEgIYwRCrGFQGtNcCQU4uTh7s2/4l15IFmZZ5Nak1Wgvvbc8vWbFfKIwkyxhir4/+J72jJcd/Ixdpc+QHoo1OS3XipIkIjt8cGXv5Vr5RAVQkLtLnyKcUan4GLGhKU+y82Ol8A49h31zz9A1IAAAAAElFTkSuQmCC"

        expected_data = {u"user_id": u"%s"  % (user.id,), u"title": u"My doc",
                         u"folder_id": u"%s" % (folder.id,), u"description": u"A document",
                        u"filedata": img_content,
                        }

        self.assertEqual(expected_data, wa.get_data())

        backend.create_from_waiting_action_n_history(wa)
        document = Document.objects.filter(q_document_existing_ids)[0]

        self.assertEqual(user.id, document.user_id)
        self.assertEqual(folder.id, document.folder_id)
        self.assertEqual(u"My doc", document.title)
        self.assertEqual(u"A document", document.description)
        self.assert_(document.filedata)

        filename, blob = decode_b64binary(img_content)

        self.assertEqual(blob, document.filedata.read())
