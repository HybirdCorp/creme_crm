# -*- coding: utf-8 -*-

from datetime import datetime

from creme_core.models.entity import CremeEntity
from creme_core.tests.base import CremeTestCase

from crudity.backends.email.create.base import CreateFromEmailBackend
from crudity.frontends.pop import PopEmail
from crudity.models.actions import WaitingAction


class CreateFromEmailBackendTestCase(CremeTestCase):
    def test_create01(self):#Unallowed user
        backend = CreateFromEmailBackend()
        backend.limit_froms = ('creme@crm.org',)
        backend.in_sandbox = True

        self.assertEqual(0, WaitingAction.objects.count())
        backend.create(PopEmail(body=u"", body_html=u"", senders=('crm@creme.org',)))
        self.assertEqual(0, WaitingAction.objects.count())

    def test_create02(self):#Bad password
        backend = CreateFromEmailBackend()
        backend.password = u"creme"
        backend.in_sandbox = True

        self.assertEqual(0, WaitingAction.objects.count())
        backend.create(PopEmail(body=u"", body_html=u"", senders=('creme@crm.org',)))
        self.assertEqual(0, WaitingAction.objects.count())

    def test_create03(self):#Text mail sandboxed
        self.login()
        user = self.user
        backend = CreateFromEmailBackend()
        backend.password = u"creme"
        backend.in_sandbox = True
        backend.subject = "create_ce"
        backend.model = CremeEntity
        backend.body_map = {
            "user_id": user.id,
            "created": "",
        }

        self.assertEqual(0, WaitingAction.objects.count())
        backend.create(PopEmail(body=u"password=creme\nuser_id=%s\ncreated=01/02/2003\n" % (user.id,), senders=('creme@crm.org',), subject="create_ce"))
        self.assertEqual(1, WaitingAction.objects.count())

        wa = WaitingAction.objects.all()[0]

        expected_data = {u"user_id": u"%s" % user.id, u"created": u"01/02/2003"}

        self.assertEqual(expected_data, wa.get_data())

    def test_create04(self):#Text mail with creation
        self.login()
        user = self.user
        backend = CreateFromEmailBackend()
        backend.password = u"creme"
        backend.in_sandbox = False
        backend.subject = "create_ce"
        backend.model = CremeEntity
        backend.body_map = {
            "user_id": user.id,
            "created": "",
        }

        self.assertEqual(0, WaitingAction.objects.count())
        self.assertEqual(0, CremeEntity.objects.count())
        backend.create(PopEmail(body=u"password=creme\nuser_id=%s\ncreated=01-02-2003\n" % (user.id,), senders=('creme@crm.org',), subject="create_ce"))
        self.assertEqual(0, WaitingAction.objects.count())
        self.assertEqual(1, CremeEntity.objects.count())

        ce = CremeEntity.objects.all()[0]

        self.assertEqual(user, ce.user)
        self.assertEqual(datetime(year=2003, month=02, day=01), ce.created)

    def test_create05(self):#Html mail sandboxed
        self.login()
        user = self.user
        backend = CreateFromEmailBackend()
        backend.password = u"creme"
        backend.in_sandbox = True
        backend.subject = "create_ce"
        backend.model = CremeEntity
        backend.body_map = {
            "user_id": user.id,
            "created": "",
        }

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
        self.login()
        user = self.user
        backend = CreateFromEmailBackend()
        backend.password = u"creme"
        backend.in_sandbox = False
        backend.subject = "create_ce"
        backend.model = CremeEntity
        backend.body_map = {
            "user_id": user.id,
            "created": "",
        }

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

