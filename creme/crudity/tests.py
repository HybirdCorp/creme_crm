# -*- coding: utf-8 -*-

from datetime import datetime

from creme_core.models.entity import CremeEntity
from creme_core.tests.base import CremeTestCase

from crudity.backends.email.create.base import CreateFromEmailBackend
from crudity.frontends.pop import PopEmail
from crudity.models.actions import WaitingAction


class CreateFromEmailBackendTestCase(CremeTestCase):
    def setUp(self):
        self.login()

    def _get_create_from_email_backend(self, password="", in_sandbox=True, subject="", model=CremeEntity, body_map={}, limit_froms=()):
        backend = CreateFromEmailBackend()
        backend.password = password
        backend.in_sandbox = in_sandbox
        backend.subject = subject
        backend.model = model
        backend.body_map = body_map
        backend.limit_froms = limit_froms
        return backend

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
