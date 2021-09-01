# -*- coding: utf-8 -*-

from datetime import date
from os.path import dirname, exists, join
from shutil import copy, rmtree
from tempfile import NamedTemporaryFile, mkdtemp

from django.apps import apps
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db.models.query_utils import Q

from creme.activities.constants import (
    ACTIVITYSUBTYPE_MEETING_MEETING,
    ACTIVITYTYPE_MEETING,
)
from creme.creme_core.models import FakeContact, Language
from creme.documents.tests.base import skipIfCustomDocument, skipIfCustomFolder
from creme.persons.tests.base import skipIfCustomContact

from ..backends.models import CrudityBackend
from ..fetchers.pop import PopEmail
from ..inputs.email import CreateEmailInput, CreateInfopathInput
from ..inputs.filesystem import IniFileInput
from ..models import History, WaitingAction
from ..utils import decode_b64binary
# from .base import Activity, ActivityFakeBackend
from .base import (
    Contact,
    ContactFakeBackend,
    CrudityTestCase,
    Document,
    DocumentFakeBackend,
    Folder,
)

if apps.is_installed('creme.activities'):
    from creme.activities.tests.base import skipIfCustomActivity
else:
    from unittest import SkipTest

    def skipIfCustomActivity(test_func):
        def _aux(*args, **kwargs):
            raise SkipTest('The app "activities" is not installed.')

        return _aux


class InputsBaseTestCase(CrudityTestCase):  # TODO: rename EmailInputBaseTestCase ?
    def setUp(self):
        super().setUp()
        self.login()

    def _get_pop_email(
            self,
            body='', body_html='',
            senders=(), tos=(), ccs=(), subject=None, dates=(), attachments=()):
        return PopEmail(
            body=body, body_html=body_html,
            senders=senders,
            tos=tos, ccs=ccs,
            subject=subject,
            dates=dates,
            attachments=attachments,
        )

    def _get_input(self, input_klass, backend_klass, **backend_cfg):
        input = input_klass()
        input.add_backend(backend_klass(config=backend_cfg))
        return input

    def _get_existing_q(self, model):
        return ~Q(pk__in=[*model.objects.values_list('pk', flat=True)])


class InputsTestCase(InputsBaseTestCase):  # TODO: rename EmailInputTestCase
    def _get_email_input(self, backend, **backend_cfg):
        return self._get_input(CreateEmailInput, backend, **backend_cfg)

    def test_empty_email_input(self):
        email_input = CreateEmailInput()

        self.assertIs(False, email_input.has_backends)

    def test_create_email_input01(self):
        "Unauthorized user."
        email_input = self._get_email_input(ContactFakeBackend, limit_froms=('creme@crm.org',))

        self.assertIs(True, email_input.has_backends)
        self.assertFalse(WaitingAction.objects.all())
        email_input.create(self._get_pop_email(senders=('crm@creme.org',)))
        self.assertFalse(WaitingAction.objects.all())

    def test_create_email_input02(self):
        "Bad password."
        email_input = self._get_email_input(ContactFakeBackend, password='creme')

        self.assertFalse(WaitingAction.objects.all())
        email_input.create(self._get_pop_email(senders=('fulbert@cremecrm.org',)))
        self.assertFalse(WaitingAction.objects.all())

    def test_create_email_input03(self):
        "Text mail sandboxed"
        user = self.user
        email_input = self._get_email_input(
            ContactFakeBackend,
            password='creme', subject='create_ce',
            body_map={'user_id': user.id, 'created': ''},
        )
        self.assertFalse(WaitingAction.objects.all())
        email_input.create(self._get_pop_email(
            body=f'password=creme\nuser_id={user.id}\ncreated=01/02/2003\n',
            senders=('creme@crm.org',),
            subject='create_ce',
        ))

        wactions = WaitingAction.objects.all()
        self.assertEqual(1, len(wactions))
        self.assertDictEqual(
            {'user_id': str(user.id), 'created': '01/02/2003'},
            wactions[0].data
        )

    @skipIfCustomContact
    def test_create_email_input04(self):
        "Text mail with creation (unsandboxed)."
        user = self.user
        email_input = self._get_email_input(
            ContactFakeBackend,
            password='creme',
            in_sandbox=False, subject="create_ce",
            body_map={
                'user_id':    user.id,
                'created':    '',
                'first_name': '',
            },
        )

        c_count = Contact.objects.count()
        q_contact_existing_ids = self._get_existing_q(Contact)

        self.assertFalse(WaitingAction.objects.all())
        email_input.create(self._get_pop_email(
            body=f'password=creme\nuser_id={user.id}\ncreated=01-02-2003\nfirst_name=é',
            senders=('creme@crm.org',),
            subject='create_ce',
        ))
        self.assertFalse(WaitingAction.objects.all())
        self.assertEqual(c_count + 1, Contact.objects.count())

        ce = Contact.objects.filter(q_contact_existing_ids)[0]
        self.assertEqual(user, ce.user)
        self.assertEqual(self.create_datetime(year=2003, month=2, day=1), ce.created)

    @skipIfCustomContact
    def test_create_email_input05(self):
        "Html mail sandboxed."
        user = self.user
        email_input = self._get_email_input(
            ContactFakeBackend, password='creme',
            subject='create_ce',
            body_map={
                'user_id': user.id,
                'created': '',
            },
        )

        c_count = Contact.objects.count()

        self.assertFalse(WaitingAction.objects.all())
        email_input.create(self._get_pop_email(
            body_html="""<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN">
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
</html>""",
            senders=('creme@crm.org',),
            subject='create_ce',
        ))
        self.assertEqual(1, WaitingAction.objects.count())
        self.assertEqual(c_count, Contact.objects.count())
        self.assertDictEqual(
            {'user_id': user.id, 'created': '01-02-2003'},
            WaitingAction.objects.all()[0].data
        )

    @skipIfCustomContact
    def test_create_email_input06(self):
        "Html mail with creation"
        user = self.user
        email_input = self._get_email_input(
            ContactFakeBackend,
            password='creme',
            subject='create_ce', in_sandbox=False,
            body_map={
                'user_id': user.id,
                'created': '',
            },
        )
        c_count = Contact.objects.count()
        q_contact_existing_ids = self._get_existing_q(Contact)

        self.assertEqual(0, WaitingAction.objects.count())
        email_input.create(self._get_pop_email(
            body_html="""<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN">
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
</html>""",
            senders=('creme@crm.org',),
            subject='create_ce',
        ))
        self.assertFalse(WaitingAction.objects.all())
        self.assertEqual(1 + c_count, Contact.objects.count())

        ce = Contact.objects.filter(q_contact_existing_ids)[0]
        self.assertEqual(user, ce.user)
        self.assertEqual(self.create_datetime(year=2003, month=2, day=1), ce.created)

    def test_create_email_input07(self):
        "Text mail sandboxed with one multiline"
        user = self.user
        email_input = self._get_email_input(
            ContactFakeBackend,
            password='creme',
            subject='create_ce',
            body_map={
                'user_id': user.id,
                'created': '',
                'description': '',
            },
        )

        self.assertFalse(WaitingAction.objects.all())
        email_input.create(self._get_pop_email(
            body=(
                f'password=creme\nuser_id={user.id}\ncreated=01/02/2003\n'
                f'description=[[I\n want to\n create a    \ncreme entity\n]]\n'
            ),
            senders=('creme@crm.org',),
            subject='create_ce',
        ))
        self.assertEqual(1, WaitingAction.objects.count())
        self.assertDictEqual(
            {
                'user_id': str(user.id),
                'created': '01/02/2003',
                'description': 'I\n want to\n create a    \ncreme entity\n',
            },
            WaitingAction.objects.all()[0].data
        )

    def test_create_email_input08(self):
        "Text mail sand-boxed with a weird multiline and some almost same field names."
        user = self.user
        email_input = self._get_email_input(
            ContactFakeBackend,
            password='creme',
            subject='create_ce',
            body_map={
                'user_id':     user.id,
                'created':     '',
                'description': '',
            },
        )

        self.assertFalse(WaitingAction.objects.all())

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
        user_id={}
        created=01/02/2003

        description3=[[


        Not empty


        ]]

        """.format(user.id)

        email_input.create(self._get_pop_email(
            body=body, senders=('creme@crm.org',), subject='create_ce',
        ))
        wactions = WaitingAction.objects.all()
        self.assertEqual(1, len(wactions))
        self.assertDictEqual(
            {
                'user_id':     str(user.id),
                'created':     '01/02/2003',
                'description': (
                    'I\n\n        want\n\n        to\n                    create\n'
                    '                a\ncreme\nentity\n\n        '
                ),
            },
            wactions[0].data,
        )

    def test_create_email_input09(self):
        "Text mail sandboxed with malformed multi-lines."
        user = self.user
        email_input = self._get_email_input(
            ContactFakeBackend,
            password='creme',
            in_sandbox=True, subject='create_ce',
            body_map={
                'user_id':     user.id,
                'created':     '',
                'description': '',
            },
        )
        self.assertFalse(WaitingAction.objects.all())

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
        user_id={}
        description2=[[I'am the
        second description
        created=01/02/2003

        description3=[[


        Not empty


        ]]

        """.format(user.id)

        email_input.create(self._get_pop_email(
            body=body, senders=('creme@crm.org',), subject='create_ce',
        ))
        wactions = WaitingAction.objects.all()
        self.assertEqual(1, len(wactions))
        self.assertDictEqual(
            {
                'user_id':     str(user.id),
                'created':     '01/02/2003',
                'description': 'I',
            },
            wactions[0].data,
        )

    def test_create_email_input10(self):
        "Html mail sand-boxed with one multiline."
        user = self.user
        email_input = self._get_email_input(
            ContactFakeBackend,
            password='creme',
            subject='create_ce',
            body_map={
                'user_id': user.id,
                'created': '',
                'description': '',
            },
        )

        body_html = """<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN">
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
        email_input.create(self._get_pop_email(
            body_html=body_html, senders=('creme@crm.org',), subject='create_ce',
        ))

        wactions = WaitingAction.objects.all()
        self.assertEqual(1, len(wactions))
        self.assertDictEqual(
            {
                'user_id':     user.id,
                'created':     '01-02-2003',
                'description': 'I\n want to\n create a    \ncreme entity\n',
            },
            wactions[0].data,
        )

    def test_create_email_input11(self):
        """HTML mail sand-boxed with more than one multi-line and some almost
        same field names.
        """
        user = self.user
        email_input = self._get_email_input(
            ContactFakeBackend,
            password='creme',
            subject='create_ce',
            body_map={
                'user_id': user.id,
                'created': '',
                'description': '',
            },
        )

        body_html = """<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN">
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
        email_input.create(PopEmail(
            body_html=body_html, senders=('creme@crm.org',), subject='create_ce',
        ))

        wactions = WaitingAction.objects.all()
        self.assertEqual(1, len(wactions))
        self.assertDictEqual(
            {
                'user_id':     user.id,
                'created':     '01-02-2003',
                'description': 'I\n want to\n create a    \ncreme entity\n',
            },
            wactions[0].data,
        )

    def test_create_email_input12(self):
        "HTML mail sandboxed with more than one multi-line but malformed."
        user = self.user
        email_input = self._get_email_input(
            ContactFakeBackend,
            password='creme',
            subject='create_ce',
            body_map={
                'user_id':     user.id,
                'created':     '',
                'description': '',
            },
        )

        body_html = """<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN">
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
        email_input.create(self._get_pop_email(
            body_html=body_html, senders=('creme@crm.org',), subject='create_ce',
        ))

        wactions = WaitingAction.objects.all()
        self.assertEqual(1, len(wactions))
        self.assertDictEqual(
            {
                'user_id': user.id,
                'created': '01-02-2003',
                'description': 'I',
            },
            wactions[0].data,
        )

    def test_create_email_input13(self):
        "Text mail sandboxed by user (user found by its email address)."
        user = self.user
        self._set_sandbox_by_user()

        email_input = self._get_email_input(
            ContactFakeBackend,
            password='creme', subject='create_ce',
            body_map={
                'user_id': user.id,
                'created': '',
            },
        )
        self.assertFalse(WaitingAction.objects.all())

        email_input.create(self._get_pop_email(
            body=f'password=creme\nuser_id={user.id}\ncreated=01/02/2003\n',
            senders=('user@cremecrm.com',),
            subject='create_ce',
        ))
        self.assertFalse(WaitingAction.objects.filter(user=None))

        wactions = WaitingAction.objects.filter(user=get_user_model().objects.get_admin())
        self.assertEqual(1, len(wactions))
        self.assertDictEqual(
            {'user_id': str(user.id), 'created': '01/02/2003'}, wactions[0].data,
        )

    @skipIfCustomContact
    def test_create_email_input14(self):
        "Text mail un-sandboxed but by user"
        user = self.user
        other_user = self.other_user

        self._set_sandbox_by_user()

        email_input = self._get_email_input(
            ContactFakeBackend,
            password='creme', subject='create_ce',
            body_map={
                'user_id': user.id,
                'created': '',
            },
            in_sandbox=False,
        )

        c_count = Contact.objects.count()
        existing_c = [*Contact.objects.values_list('pk', flat=True)]

        self.assertEqual(0, WaitingAction.objects.count())
        self.assertEqual(0, History.objects.count())

        email_input.create(self._get_pop_email(
            body=f'password=creme\nuser_id={user.id}\ncreated=01/02/2003\n',
            senders=(other_user.email,),
            subject='create_ce',
        ))
        self.assertFalse(WaitingAction.objects.all())
        self.assertEqual(c_count + 1, Contact.objects.count())
        self.assertEqual(1, History.objects.filter(user=other_user).count())
        self.assertFalse(History.objects.filter(user=None))

        with self.assertNoException():
            ce = Contact.objects.exclude(pk__in=existing_c).get()

        self.assertEqual(other_user, History.objects.all()[0].user)
        # Sandbox by user doesn't have to change the assignation set in the mail
        self.assertEqual(user, ce.user)

    @skipIfCustomContact
    def test_create_email_input15(self):
        "Text mail sandboxed by user and created later"
        user = self.user
        other_user = self.other_user
        self._set_sandbox_by_user()

        email_input = self._get_email_input(
            ContactFakeBackend, password='creme',
            subject='create_ce',
            body_map={
                'user_id': user.id,
                'created': '',
            },
        )
        c_count = Contact.objects.count()
        existing_c = [*Contact.objects.all().values_list('pk', flat=True)]
        self.assertFalse(WaitingAction.objects.all())
        self.assertFalse(History.objects.all())

        email_input.create(self._get_pop_email(
            body=f'password=creme\nuser_id={user.id}\ncreated=01/02/2003\n',
            senders=(other_user.email,),
            subject='create_ce',
        ))
        self.assertEqual(1, WaitingAction.objects.count())
        self.assertFalse(History.objects.all())
        self.assertEqual(c_count, Contact.objects.count())

        wa = WaitingAction.objects.all()[0]
        self.assertEqual(other_user, wa.user)

        email_input.get_backend(CrudityBackend.normalize_subject('create_ce')).create(wa)
        self.assertEqual(c_count + 1, Contact.objects.count())
        self.assertEqual(1, History.objects.count())

        self.assertEqual(user, Contact.objects.get(~Q(pk__in=existing_c)).user)
        self.assertEqual(other_user, History.objects.all()[0].user)

    @skipIfCustomContact
    def test_create_email_input16(self):
        "Text mail with creation."
        user = self.user

        email_input = self._get_email_input(
            ContactFakeBackend,
            password='creme',
            in_sandbox=False,
            subject='create_contact',
            body_map={
                'user_id':    user.id,
                'created':    '',
                'url_site':   '',
            },
            model=Contact,
        )
        contact_count = Contact.objects.count()
        self.assertFalse(WaitingAction.objects.all())

        email_input.create(PopEmail(
            body=f'password=creme\nuser_id={user.id}\ncreated=01-02-2003\nurl_site=plop',
            senders=('creme@crm.org',),
            subject='create_contact',
        ))
        self.assertFalse(WaitingAction.objects.all())
        self.assertEqual(contact_count + 1, Contact.objects.count())

        contact = self.get_object_or_fail(Contact, url_site='plop')
        self.assertEqual(user, contact.user)
        self.assertEqual(self.create_datetime(year=2003, month=2, day=1), contact.created)

    def test_get_owner01(self):
        "The sandbox is not by user."
        user = self.user
        email_input = self._get_email_input(
            ContactFakeBackend,
            password='creme',
            subject='create_ce',
            body_map={'user_id': user.id},
        )
        self.assertIsNone(email_input.get_owner(False, sender='user@cremecrm.com'))

    def test_get_owner02(self):
        "The user matches."
        self._set_sandbox_by_user()
        user = self.user
        other_user = self.other_user

        email_input = self._get_email_input(
            ContactFakeBackend,
            password='creme',
            subject='create_ce',
            body_map={
                'user_id': user.id,
                'created': '',
            },
        )
        self.assertEqual(other_user, email_input.get_owner(True, sender=other_user.email))

    def test_get_owner03(self):
        "The user doesn't match"
        self._set_sandbox_by_user()
        user = self.user

        email_input = self._get_email_input(
            ContactFakeBackend,
            password='creme',
            subject='create_ce',
            body_map={
                'user_id': user.id,
                'created': '',
            },
        )
        self.assertEqual(
            get_user_model().objects.get_admin(),
            email_input.get_owner(True, sender='another_user@cremecrm.com'),
        )

    @skipIfCustomContact
    def test_create_contact01(self):
        "Text mail sandboxed"
        user = self.user
        email_input = self._get_email_input(
            ContactFakeBackend,
            password='creme',
            subject='create_contact',  # TODO: factorise
            body_map={
                'user_id':     user.id,
                'first_name':  '',
                'last_name':   '',
                'email':       'none@none.com',
                'description': '',
                'birthday':    '',
                'created':     '',
                'url_site':    '',
            },
            model=Contact,
        )

        body = [
            'password=creme',
            f'user_id={user.id}',
            'created=01/02/2003',
            'last_name=Bros',
            'first_name=Mario',
            'email=mario@bros.com',
            'url_site=http://mario.com',
            'birthday=02/08/1987',
            'description=[[A plumber]]',
        ]

        self.assertEqual(0, WaitingAction.objects.count())
        email_input.create(self._get_pop_email(
            body='\n'.join(body),
            senders=('creme@crm.org',),
            subject='create_contact',
        ))

        wactions = WaitingAction.objects.all()
        self.assertEqual(1, len(wactions))

        wa = wactions[0]
        self.assertDictEqual(
            {
                'user_id':     str(user.id),
                'created':     '01/02/2003',
                'last_name':   'Bros',
                'first_name':  'Mario',
                'email':       'mario@bros.com',
                'url_site':    'http://mario.com',
                'birthday':    '02/08/1987',
                'description': 'A plumber',
            },
            wa.data,
        )

        email_input.get_backend(CrudityBackend.normalize_subject('create_contact')).create(wa)

        contact = self.get_object_or_fail(Contact, first_name='Mario', last_name='Bros')
        self.assertEqual(user, contact.user)
        # TODO: should 'created' be set manually ??
        self.assertEqual(self.create_datetime(year=2003, month=2, day=1), contact.created)
        self.assertEqual('mario@bros.com', contact.email)
        self.assertEqual('http://mario.com', contact.url_site)
        self.assertEqual(date(year=1987, month=8, day=2), contact.birthday)
        self.assertEqual('A plumber', contact.description)

    # TODO: move some validation code from Activity form to model (start<end etc...)
    @skipIfCustomActivity
    def test_create_activity01(self):
        "Datetimes with or without timezone"
        from creme.activities import get_activity_model

        Activity = get_activity_model()

        class ActivityFakeBackend(CrudityBackend):
            model = Activity

        title = 'My Meeting'
        self.assertFalse(Activity.objects.filter(title=title))

        user = self.user
        subject = 'create_activity'
        email_input = self._get_email_input(
            ActivityFakeBackend,
            password='creme',
            subject=subject,
            body_map={
                'user_id':     user.id,
                'title':       '',
                'type_id':     ACTIVITYTYPE_MEETING,
                'sub_type_id': ACTIVITYSUBTYPE_MEETING_MEETING,
                'start':       '',
                'end':         '',
            },
            model=Activity,
        )

        body = [
            'password=creme',
            f'title={title}',
            'start=2013-06-15 12:00:00+03:00',
            'end=2013-06-15 12:28:45',
        ]

        self.assertEqual(0, WaitingAction.objects.count())
        email_input.create(self._get_pop_email(
            body='\n'.join(body),
            senders=('creme@crm.org',),
            subject=subject,
        ))

        wactions = WaitingAction.objects.all()
        self.assertEqual(1, len(wactions))

        is_created, activity = email_input.get_backend(
            CrudityBackend.normalize_subject(subject)
        ).create(wactions[0])
        self.assertTrue(is_created)
        self.assertIsInstance(activity, Activity)

        activity = self.refresh(activity)
        self.assertEqual(user,                            activity.user)
        self.assertEqual(title,                           activity.title)
        self.assertEqual(ACTIVITYTYPE_MEETING,            activity.type.id)
        self.assertEqual(ACTIVITYSUBTYPE_MEETING_MEETING, activity.sub_type.id)

        create_dt = self.create_datetime
        self.assertEqual(
            create_dt(year=2013, month=6, day=15, hour=9, utc=True),
            activity.start,
        )
        self.assertEqual(
            create_dt(year=2013, month=6, day=15, hour=12, minute=28, second=45),
            activity.end,
        )


@skipIfCustomContact
class InfopathInputEmailTestCase(InputsBaseTestCase):
    def _build_attachment(
            self,
            # filename='',
            filename='Attached.xsn',
            content_type='application/x-microsoft-infopathform',
            content=b''):
        return filename, SimpleUploadedFile(filename, content, content_type=content_type)

    def _get_infopath_input(self, backend, **backend_cfg):
        return self._get_input(CreateInfopathInput, backend, **backend_cfg)

    def test_create01(self):
        "Unauthorized user."
        infopath_input = self._get_infopath_input(
            ContactFakeBackend, limit_froms=('creme@cremecrm.com',)
        )

        self.assertFalse(WaitingAction.objects.all())
        infopath_input.create(self._get_pop_email(
            body='', body_html='',
            senders=('crm@cremecrm.com',),
            attachments=[self._build_attachment()],
        ))
        self.assertFalse(WaitingAction.objects.all())

    def test_create02(self):
        "Bad password."
        infopath_input = self._get_infopath_input(ContactFakeBackend, password='creme')

        self.assertFalse(WaitingAction.objects.all())
        infopath_input.create(self._get_pop_email(
            body='', body_html='',
            senders=('creme@cremecrm.com',),
            attachments=[self._build_attachment()],
        ))
        self.assertFalse(WaitingAction.objects.all())

    def test_create03(self):
        "Allowed password, subject but attachment content_type is not allowed."
        user = self.user
        infopath_input = self._get_infopath_input(
            ContactFakeBackend,
            password='creme',
            in_sandbox=False,
            subject='create_ce_infopath',
            body_map={
                'user_id': user.id,
                'created': '',
            },
        )

        self.assertEqual(0, WaitingAction.objects.count())
        infopath_input.create(self._get_pop_email(
            body='password=creme',
            senders=('creme@cremecrm.com',),
            subject='create_ce_infopath',
            attachments=[self._build_attachment(content_type='text/invalid')],
        ))
        self.assertFalse(WaitingAction.objects.all())

    def test_create04(self):
        "Allowed but empty XML"
        user = self.user
        infopath_input = self._get_infopath_input(
            ContactFakeBackend,
            password='creme', in_sandbox=False,
            subject='create_ce_infopath',
            body_map={
                'user_id': user.id,
                'created': '',
            },
        )

        self.assertFalse(WaitingAction.objects.all())
        infopath_input.create(self._get_pop_email(
            body='password=creme',
            senders=('creme@cremecrm.com',),
            subject='create_ce_infopath',
            attachments=[self._build_attachment()],
        ))
        self.assertFalse(WaitingAction.objects.all())

    def test_create05(self):
        "Allowed but bad XML."
        user = self.user
        infopath_input = self._get_infopath_input(
            ContactFakeBackend,
            password='creme',
            in_sandbox=False,
            subject='create_ce_infopath',
            body_map={
                'user_id': user.id,
                'created': '',
            },
        )

        self.assertFalse(WaitingAction.objects.all())
        infopath_input.create(self._get_pop_email(
            body='password=creme',
            senders=('creme@cremecrm.com',),
            subject='create_ce_infopath',
            attachments=[self._build_attachment(content=b'invalid')],
        ))
        self.assertFalse(WaitingAction.objects.all())

    def test_create06(self):
        "Allowed with valid XML."
        user = self.user
        other_user = self.other_user
        xml_content = r"""
        <?xml version="1.0" encoding="UTF-8"?><?mso-infoPathSolution solutionVersion="1.0.0.14" productVersion="12.0.0" PIVersion="1.0.0.0" href="file:///C:\Users\Raph\Desktop\Infopath\create_contact.xsn" name="urn:schemas-microsoft-com:office:infopath:create-contact:-myXSD-2011-07-04T07-44-13" ?><?mso-application progid="InfoPath.Document" versionProgid="InfoPath.Document.2"?><my:CremeCRMCrudity xmlns:my="http://schemas.microsoft.com/office/infopath/2003/myXSD/2011-07-04T07:44:13" xml:lang="fr">
            <my:user_id>{}</my:user_id>
            <my:created xsi:nil="true" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">2003-02-01</my:created>
            <my:description>
                <div xmlns="http://www.w3.org/1999/xhtml">My creme entity</div>
                <div xmlns="http://www.w3.org/1999/xhtml"> </div>
                <div xmlns="http://www.w3.org/1999/xhtml">description</div>
            </my:description>
        </my:CremeCRMCrudity>""".format(other_user.id)  # NOQA

        infopath_input = self._get_infopath_input(
            ContactFakeBackend,
            password='creme',
            subject='create_ce_infopath',
            body_map={
                'user_id':     user.id,
                'created':     '',
                'description': '',
            },
        )

        self.assertFalse(WaitingAction.objects.all())
        infopath_input.create(PopEmail(
            body='password=creme',
            senders=('creme@cremecrm.com',),
            subject='create_ce_infopath',
            attachments=[self._build_attachment(content=xml_content.encode())],
        ))
        self.assertEqual(1, WaitingAction.objects.count())

        wa = WaitingAction.objects.all()[0]
        self.assertDictEqual(
            {
                'user_id':     str(other_user.id),
                'created':     '2003-02-01',
                'description': 'My creme entity\n\ndescription',
            },
            wa.data,
        )
        self.assertIsNone(wa.user)  # Sandbox is not by user

    def test_create07(self):
        "Allowed with valid but weird xml"
        user = self.user
        other_user = self.other_user
        xml_content = r"""

        <?xml version="1.0" encoding="UTF-8"?>
<?mso-infoPathSolution solutionVersion="1.0.0.14" productVersion="12.0.0" PIVersion="1.0.0.0" href="file:///C:\Users\Raph\Desktop\Infopath\create_contact.xsn" name="urn:schemas-microsoft-com:office:infopath:create-contact:-myXSD-2011-07-04T07-44-13" ?><?mso-application progid="InfoPath.Document" versionProgid="InfoPath.Document.2"?><my:CremeCRMCrudity xmlns:my="http://schemas.microsoft.com/office/infopath/2003/myXSD/2011-07-04T07:44:13" xml:lang="fr">



            <my:user_id>{}</my:user_id>
                                                    <my:created xsi:nil="true" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">2003-02-01</my:created>
        <my:description>
                    <div xmlns="http://www.w3.org/1999/xhtml">My creme entity</div>

                <div xmlns="http://www.w3.org/1999/xhtml"> </div>
        <div xmlns="http://www.w3.org/1999/xhtml">description</div>



            </my:description> </my:CremeCRMCrudity>""".format(other_user.id)  # NOQA

        infopath_input = self._get_infopath_input(
            ContactFakeBackend,
            password='creme',
            subject='create_ce_infopath',
            body_map={
                'user_id': user.id,
                'created': '',
                'description': '',
            },
        )

        self.assertEqual(0, WaitingAction.objects.count())
        infopath_input.create(self._get_pop_email(
            body='password=creme',
            senders=('creme@cremecrm.com',),
            subject='create_ce_infopath',
            attachments=[self._build_attachment(content=xml_content.encode())],
        ))

        wactions = WaitingAction.objects.all()
        self.assertEqual(1, len(wactions))
        self.assertDictEqual(
            {
                'user_id':     str(other_user.id),
                'created':     '2003-02-01',
                'description': 'My creme entity\n\ndescription',
            },
            wactions[0].data
        )

    def test_create08(self):
        "Allowed with valid xml with sandbox by user (no user found by its email address)."
        user = self.user
        other_user = self.other_user
        self._set_sandbox_by_user()

        xml_content = r"""<?xml version="1.0" encoding="UTF-8"?>
<?mso-infoPathSolution solutionVersion="1.0.0.14" productVersion="12.0.0" PIVersion="1.0.0.0"
  href="file:///C:\Users\Raph\Desktop\Infopath\create_contact.xsn"
  name="urn:schemas-microsoft-com:office:infopath:create-contact:-myXSD-2011-07-04T07-44-13" ?>
<?mso-application progid="InfoPath.Document" versionProgid="InfoPath.Document.2"?>
<my:CremeCRMCrudity
 xmlns:my="http://schemas.microsoft.com/office/infopath/2003/myXSD/2011-07-04T07:44:13"
 xml:lang="fr">
    <my:user_id>{}</my:user_id>
    <my:created xsi:nil="true"
        xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">2003-02-01</my:created>
    <my:description>
        <div xmlns="http://www.w3.org/1999/xhtml">My creme entity</div>
        <div xmlns="http://www.w3.org/1999/xhtml"> </div>
        <div xmlns="http://www.w3.org/1999/xhtml">description</div>
    </my:description>
</my:CremeCRMCrudity>""".format(other_user.id)

        infopath_input = self._get_infopath_input(
            ContactFakeBackend,
            password='creme',
            subject='create_ce_infopath',
            body_map={
                'user_id':     user.id,
                'created':     '',
                'description': '',
            },
        )

        self.assertEqual(0, WaitingAction.objects.count())
        infopath_input.create(self._get_pop_email(
            body='password=creme',
            senders=('creme@cremecrm.com',),  # <== no user has this address
            subject='create_ce_infopath',
            attachments=[self._build_attachment(content=xml_content.encode())],
        ))
        self.assertEqual(1, WaitingAction.objects.count())

        wa = WaitingAction.objects.all()[0]
        self.assertEqual(
            {
                'user_id':     str(other_user.id),
                'created':     '2003-02-01',
                'description': 'My creme entity\n\ndescription',
            },
            wa.data
        )
        self.assertEqual(get_user_model().objects.get_admin(), wa.user)

    def test_create09(self):
        "Allowed with valid xml with sandbox by user with real match on email."
        user = self.user
        other_user = self.other_user
        self._set_sandbox_by_user()

        xml_content = r"""
<?xml version="1.0" encoding="UTF-8"?><?mso-infoPathSolution solutionVersion="1.0.0.14" productVersion="12.0.0" PIVersion="1.0.0.0" href="file:///C:\Users\Raph\Desktop\Infopath\create_contact.xsn" name="urn:schemas-microsoft-com:office:infopath:create-contact:-myXSD-2011-07-04T07-44-13" ?><?mso-application progid="InfoPath.Document" versionProgid="InfoPath.Document.2"?><my:CremeCRMCrudity xmlns:my="http://schemas.microsoft.com/office/infopath/2003/myXSD/2011-07-04T07:44:13" xml:lang="fr">
    <my:user_id>{}</my:user_id>
    <my:created xsi:nil="true" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">2003-02-01</my:created>
    <my:description>
        <div xmlns="http://www.w3.org/1999/xhtml">My creme entity</div>
        <div xmlns="http://www.w3.org/1999/xhtml"> </div>
        <div xmlns="http://www.w3.org/1999/xhtml">description</div>
    </my:description>
</my:CremeCRMCrudity>""".format(other_user.id)  # NOQA

        infopath_input = self._get_infopath_input(
            ContactFakeBackend,
            password='creme',
            subject='create_ce_infopath',
            body_map={
                'user_id':     user.id,
                'created':     '',
                'description': '',
            },
        )

        self.assertEqual(0, WaitingAction.objects.count())
        infopath_input.create(self._get_pop_email(
            body='password=creme',
            senders=(other_user.email,),
            subject='create_ce_infopath',
            attachments=[self._build_attachment(content=xml_content.encode())],
        ))

        wactions = WaitingAction.objects.all()
        self.assertEqual(1, len(wactions))

        wa = wactions[0]
        self.assertDictEqual(
            {
                'user_id':     str(other_user.id),
                'created':     '2003-02-01',
                'description': 'My creme entity\n\ndescription',
            },
            wa.data
        )
        self.assertEqual(other_user, wa.user)

    def test_create10(self):
        "Allowed with valid xml with no sandbox with default values"
        user = self.user

        xml_content = r"""
<?xml version="1.0" encoding="UTF-8"?><?mso-infoPathSolution solutionVersion="1.0.0.14" productVersion="12.0.0" PIVersion="1.0.0.0" href="file:///C:\Users\Raph\Desktop\Infopath\create_contact.xsn" name="urn:schemas-microsoft-com:office:infopath:create-contact:-myXSD-2011-07-04T07-44-13" ?><?mso-application progid="InfoPath.Document" versionProgid="InfoPath.Document.2"?><my:CremeCRMCrudity xmlns:my="http://schemas.microsoft.com/office/infopath/2003/myXSD/2011-07-04T07:44:13" xml:lang="fr">
</my:CremeCRMCrudity>"""  # NOQA

        infopath_input = self._get_infopath_input(
            ContactFakeBackend,
            password='creme',
            in_sandbox=False,
            subject='create_ce_infopath',
            body_map={
                'user_id': user.id,
                'created': '2011-10-09',
                'description': 'default',
            },
        )

        c_count = Contact.objects.count()
        q_c_existing_ids = self._get_existing_q(Contact)

        self.assertFalse(WaitingAction.objects.all())
        infopath_input.create(self._get_pop_email(
            body='password=creme',
            senders=('other_user@cremecrm.com',),
            subject='create_ce_infopath',
            attachments=[self._build_attachment(content=xml_content.encode())],
        ))
        self.assertFalse(WaitingAction.objects.all())
        self.assertEqual(c_count + 1, Contact.objects.count())

        ce = Contact.objects.filter(q_c_existing_ids)[0]
        self.assertEqual(user, ce.user)
        self.assertEqual(self.create_datetime(year=2011, month=10, day=9), ce.created)

    def test_create11(self):
        "Allowed with valid XML with no sandbox but by user with real match on email."
        user = self.user
        other_user = self.other_user
        self._set_sandbox_by_user()

        xml_content = r"""
<?xml version="1.0" encoding="UTF-8"?><?mso-infoPathSolution solutionVersion="1.0.0.14" productVersion="12.0.0" PIVersion="1.0.0.0" href="file:///C:\Users\Raph\Desktop\Infopath\create_contact.xsn" name="urn:schemas-microsoft-com:office:infopath:create-contact:-myXSD-2011-07-04T07-44-13" ?><?mso-application progid="InfoPath.Document" versionProgid="InfoPath.Document.2"?><my:CremeCRMCrudity xmlns:my="http://schemas.microsoft.com/office/infopath/2003/myXSD/2011-07-04T07:44:13" xml:lang="fr">
    <my:user_id>{}</my:user_id>
    <my:created xsi:nil="true" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">2003-02-01</my:created>
    <my:description>
        <div xmlns="http://www.w3.org/1999/xhtml">My creme entity</div>
        <div xmlns="http://www.w3.org/1999/xhtml"> </div>
        <div xmlns="http://www.w3.org/1999/xhtml">description</div>
    </my:description>
</my:CremeCRMCrudity>""".format(other_user.id)  # NOQA

        infopath_input = self._get_infopath_input(
            ContactFakeBackend, password='creme',
            in_sandbox=False,
            subject='create_ce_infopath',
            body_map={
                'user_id': user.id,
                'created': '',
            },
        )

        c_count = Contact.objects.count()
        q_c_existing_ids = self._get_existing_q(Contact)

        self.assertEqual(0, WaitingAction.objects.count())
        infopath_input.create(PopEmail(
            body='password=creme',
            senders=('other_user@cremecrm.com',),
            subject='create_ce_infopath',
            attachments=[self._build_attachment(content=xml_content.encode())],
        ))
        self.assertFalse(WaitingAction.objects.all())
        self.assertEqual(c_count + 1, Contact.objects.count())

        contact = Contact.objects.filter(q_c_existing_ids)[0]
        self.assertEqual(other_user, contact.user)
        self.assertEqual(self.create_datetime(year=2003, month=2, day=1), contact.created)

    def test_create_contact01(self):
        "Sandboxed with image."
        user = self.user
        xml_content = r"""
<?xml version="1.0" encoding="UTF-8"?><?mso-infoPathSolution solutionVersion="1.0.0.14" productVersion="12.0.0" PIVersion="1.0.0.0" href="file:///C:\Users\User\Desktop\Infopath\create_contact.xsn" name="urn:schemas-microsoft-com:office:infopath:create-contact:-myXSD-2011-07-04T07-44-13" ?><?mso-application progid="InfoPath.Document" versionProgid="InfoPath.Document.2"?><my:CremeCRMCrudity xmlns:my="http://schemas.microsoft.com/office/infopath/2003/myXSD/2011-07-04T07:44:13" xml:lang="fr">
    <my:user_id>{}</my:user_id>
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
</my:CremeCRMCrudity>""".format(user.id)  # NOQA

        infopath_input = self._get_infopath_input(
            ContactFakeBackend,
            password='creme',
            subject="create_ce_infopath",
            body_map={
                'user_id':     user.id,
                'first_name':  '',
                'last_name':   '',
                'email':       'none@none.com',
                'description': '',
                'birthday':    '',
                'created':     '',
                'url_site':    '',
                'image':       '',
            },
            model=Contact
        )

        q_contact_existing_ids = ~Q(pk__in=[*Contact.objects.all().values_list('pk', flat=True)])
        self.assertFalse(WaitingAction.objects.all())
        infopath_input.create(self._get_pop_email(
            body='password=creme',
            senders=('user@cremecrm.com',),
            subject='create_ce_infopath',
            attachments=[self._build_attachment(content=xml_content.encode())],
        ))
        self.assertEqual(1, WaitingAction.objects.count())

        wa = WaitingAction.objects.all()[0]
        img_content = (
            b'x0lGQRQAAAABAAAAAAAAAHwCAAAGAAAAYgAuAHAAbgBnAAAAiVBORw0KGgoAAAANS'
            b'UhEUgAAABAAAAAQCAYAAAAf8/9hAAAABHNCSVQICAgIfAhkiAAAAAlwSFlzAAABuw'
            b'AAAbsBOuzj4gAAABl0RVh0U29mdHdhcmUAd3d3Lmlua3NjYXBlLm9yZ5vuPBoAAAH'
            b'5SURBVDiNpZM9a1RBFIbfd87M3N3szW6iYoIYlYBgY6FNwMafIOJPsLCwEm3UQoKF'
            b'Yhk7/4lYGqxtRPAr6kIS3KjZTbIfc+/MsfAjyV5FwYFTnAPnmfc9Z4aqiv85drzQe'
            b'JQ9YENOmpaZEsPm7OEZdtvb7dWL6xf+CuAtnjp6eebaKAVLA5SD1Hu9/LYJYvZPCs'
            b'y+LCErY1QKYK2AgHACgEf6NwsZGmKo4j2gChKCBoAhRO7zOhRFAp7oTX35S7Wqor5'
            b'UP39oYfohatoyM2aOJMtQoAgFhl+Hq0URi9AtyI4eSz08j1f1zD4FNPGcn3eni1GA'
            b's4KYdjdjGnLEJ4KK9uhDAAWxMoOiG9eNIXzdQ2xlMfC1DMYI2ATwOwAccpc5ZJmvN'
            b'nuPeq0GI3QI30sVgCpf9VcG7wadsAYF8MOBEQPnLayxSIU67WMT23izF8C9L5G3ef'
            b'bElbmnqOlEMQhIUbXz7PNHBmXc0sdpA/f0rq5ULexmXVWNACBOYBKC7qTj0alPm7g'
            b'x3rwPQJKObkKHSUFArACKEgIYwRCrGFQGtNcCQU4uTh7s2/4l15IFmZZ5Nak1Wgvv'
            b'bc8vWbFfKIwkyxhir4/+J72jJcd/Ixdpc+QHoo1OS3XipIkIjt8cGXv5Vr5RAVQkL'
            b'tLnyKcUan4GLGhKU+y82Ol8A49h31zz9A1IAAAAAElFTkSuQmCC'
        )
        filename, blob = decode_b64binary(img_content)
        expected_data = {
            'user_id': str(user.id),
            'created': '2003-02-01',
            'last_name': 'Bros', 'first_name': 'Mario',
            'email': 'mario@bros.com', 'url_site': 'http://mario.com',
            'birthday': '02/08/1987', 'description': 'A plumber',
            'image': (filename, blob),
        }
        self.maxDiff = None
        # self.assertEqual(expected_data, wa.get_data())
        self.assertEqual(expected_data, wa.data)

        infopath_input.get_backend(
            CrudityBackend.normalize_subject('create_ce_infopath'),
        ).create(wa)
        contact = Contact.objects.filter(q_contact_existing_ids)[0]

        self.assertEqual(user, contact.user)
        self.assertEqual(self.create_datetime(year=2003, month=2, day=1), contact.created)
        self.assertEqual('Bros', contact.last_name)
        self.assertEqual('Mario', contact.first_name)
        self.assertEqual('mario@bros.com', contact.email)
        self.assertEqual('http://mario.com', contact.url_site)
        self.assertEqual(self.create_datetime(year=1987, month=8, day=2).date(), contact.birthday)
        self.assertEqual('A plumber', contact.description)
        self.assertTrue(contact.image)

        with contact.image.filedata.open() as f:
            self.assertEqual(blob, f.read())

    def _get_languages(self):
        languages = [*Language.objects.all()]
        length = len(languages)

        if length < 3:
            create = Language.objects.create

            for i in range(1, 4 - length):
                create(code=f'c{i}', name=f'Langues #{i}')

        return languages

    def test_create_contact02(self):
        "Sandboxed with M2M."
        user = self.user
        languages = self._get_languages()

        xml_content = r"""
<?xml version="1.0" encoding="UTF-8"?><?mso-infoPathSolution solutionVersion="1.0.0.14" productVersion="12.0.0" PIVersion="1.0.0.0" href="file:///C:\Users\User\Desktop\Infopath\create_contact.xsn" name="urn:schemas-microsoft-com:office:infopath:create-contact:-myXSD-2011-07-04T07-44-13" ?><?mso-application progid="InfoPath.Document" versionProgid="InfoPath.Document.2"?><my:CremeCRMCrudity xmlns:my="http://schemas.microsoft.com/office/infopath/2003/myXSD/2011-07-04T07:44:13" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xml:lang="fr">
    <my:user_id>{}</my:user_id>
    <my:created xsi:nil="true" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">2003-02-01</my:created>
    <my:first_name>Mario</my:first_name>
    <my:last_name>Bros</my:last_name>
    <my:url_site>http://mario.com</my:url_site>
    <my:email>mario@bros.com</my:email>
    <my:birthday xsi:nil="true" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">02/08/1987</my:birthday>
    <my:languages>
        <my:languages_value xsi:nil="true"></my:languages_value>
        <my:languages_value>{}</my:languages_value>
        <my:languages_value>{}</my:languages_value>
    </my:languages>
    <my:description>
        <div xmlns="http://www.w3.org/1999/xhtml">A plumber</div>
    </my:description>
</my:CremeCRMCrudity>""".format(user.id, languages[0].id, languages[1].id)  # NOQA

        infopath_input = self._get_infopath_input(
            ContactFakeBackend,
            password='creme',
            subject="create_ce_infopath",
            body_map={
                'user_id':     user.id,
                'first_name':  '',
                'last_name':   '',
                'email':       'none@none.com',
                'description': '',
                'birthday':    '',
                'created':     '',
                'url_site':    '',
                # 'language':    ''
                'languages':    ''
            },
            model=Contact,
        )

        q_contact_existing_ids = self._get_existing_q(Contact)
        self.assertFalse(WaitingAction.objects.all())
        infopath_input.create(self._get_pop_email(
            body='password=creme',
            senders=('user@cremecrm.com',),
            subject='create_ce_infopath',
            attachments=[self._build_attachment(content=xml_content.encode())],
        ))

        wactions = WaitingAction.objects.all()
        self.assertEqual(1, len(wactions))

        wa = wactions[0]
        expected_data = {
            'user_id': str(user.id),
            'created': '2003-02-01',
            'last_name': 'Bros', 'first_name': 'Mario',
            'email': 'mario@bros.com', 'url_site': 'http://mario.com',
            'birthday': '02/08/1987', 'description': 'A plumber',
            # 'language': f'\n{languages[0].id}\n{languages[1].id}',
            'languages': f'\n{languages[0].id}\n{languages[1].id}',
        }
        self.assertEqual(expected_data, wa.data)

        infopath_input.get_backend(
            CrudityBackend.normalize_subject('create_ce_infopath'),
        ).create(wa)
        contact = Contact.objects.filter(q_contact_existing_ids)[0]

        self.assertEqual(user, contact.user)
        self.assertEqual(self.create_datetime(year=2003, month=2, day=1), contact.created)
        self.assertEqual('Bros', contact.last_name)
        self.assertEqual('Mario', contact.first_name)
        self.assertEqual('mario@bros.com', contact.email)
        self.assertEqual('http://mario.com', contact.url_site)
        self.assertEqual(self.create_datetime(year=1987, month=8, day=2).date(), contact.birthday)
        self.assertEqual('A plumber', contact.description)
        # self.assertSetEqual({languages[0], languages[1]}, {*contact.language.all()})
        self.assertSetEqual({languages[0], languages[1]}, {*contact.languages.all()})

    def test_create_contact03(self):
        "Unsandboxed with M2M."
        user = self.user
        languages = self._get_languages()

        xml_content = r"""
<?xml version="1.0" encoding="UTF-8"?><?mso-infoPathSolution solutionVersion="1.0.0.14" productVersion="12.0.0" PIVersion="1.0.0.0" href="file:///C:\Users\User\Desktop\Infopath\create_contact.xsn" name="urn:schemas-microsoft-com:office:infopath:create-contact:-myXSD-2011-07-04T07-44-13" ?><?mso-application progid="InfoPath.Document" versionProgid="InfoPath.Document.2"?><my:CremeCRMCrudity xmlns:my="http://schemas.microsoft.com/office/infopath/2003/myXSD/2011-07-04T07:44:13" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xml:lang="fr">
    <my:user_id>{}</my:user_id>
    <my:created xsi:nil="true" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">2003-02-01</my:created>
    <my:first_name>Mario</my:first_name>
    <my:last_name>Bros</my:last_name>
    <my:url_site>http://mario.com</my:url_site>
    <my:email>mario@bros.com</my:email>
    <my:birthday xsi:nil="true" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">02/08/1987</my:birthday>
    <my:languages>
        <my:languages_value xsi:nil="true"></my:languages_value>
        <my:languages_value>{}</my:languages_value>
        <my:languages_value>{}</my:languages_value>
    </my:languages>
    <my:description>
        <div xmlns="http://www.w3.org/1999/xhtml">A plumber</div>
    </my:description>
</my:CremeCRMCrudity>""".format(user.id, languages[0].id, languages[1].id)  # NOQA

        infopath_input = self._get_infopath_input(
            ContactFakeBackend,
            password='creme',
            subject='create_ce_infopath',
            body_map={
                'user_id':     user.id,
                'first_name':  '',
                'last_name':   '',
                'email':       'none@none.com',
                'description': '',
                'birthday':    '',
                'created':     '',
                'url_site':    '',
                # 'language':    ''
                'languages':    ''
            },
            model=Contact,
            in_sandbox=False,
        )

        q_contact_existing_ids = self._get_existing_q(Contact)
        self.assertFalse(WaitingAction.objects.all())
        infopath_input.create(self._get_pop_email(
            body='password=creme', senders=('user@cremecrm.com',),
            subject='create_ce_infopath',
            attachments=[self._build_attachment(content=xml_content.encode())],
        ))
        self.assertFalse(WaitingAction.objects.all())
        self.assertEqual(1, Contact.objects.filter(q_contact_existing_ids).count())

        contact = Contact.objects.filter(q_contact_existing_ids)[0]
        self.assertEqual(user, contact.user)
        self.assertEqual(self.create_datetime(year=2003, month=2, day=1), contact.created)
        self.assertEqual('Bros', contact.last_name)
        self.assertEqual('Mario', contact.first_name)
        self.assertEqual('mario@bros.com', contact.email)
        self.assertEqual('http://mario.com', contact.url_site)
        self.assertEqual(self.create_datetime(year=1987, month=8, day=2).date(), contact.birthday)
        self.assertEqual('A plumber', contact.description)
        # self.assertSetEqual({*languages[:2]}, {*contact.language.all()})
        self.assertSetEqual({*languages[:2]}, {*contact.languages.all()})

    @skipIfCustomFolder
    @skipIfCustomDocument
    def test_create_document01(self):
        "Sandboxed with image"
        user = self.user
        self.maxDiff = None
        folder = Folder.objects.create(user=user, title='test_create_document01')

        img_content = (
            b"x0lGQRQAAAABAAAAAAAAAHwCAAAGAAAAYgAuAHAAbgBnAAAAiVBORw0KGgoAAAANS"
            b"UhEUgAAABAAAAAQCAYAAAAf8/9hAAAABHNCSVQICAgIfAhkiAAAAAlwSFlzAAABuw"
            b"AAAbsBOuzj4gAAABl0RVh0U29mdHdhcmUAd3d3Lmlua3NjYXBlLm9yZ5vuPBoAAAH"
            b"5SURBVDiNpZM9a1RBFIbfd87M3N3szW6iYoIYlYBgY6FNwMafIOJPsLCwEm3UQoKF"
            b"Yhk7/4lYGqxtRPAr6kIS3KjZTbIfc+/MsfAjyV5FwYFTnAPnmfc9Z4aqiv85drzQe"
            b"JQ9YENOmpaZEsPm7OEZdtvb7dWL6xf+CuAtnjp6eebaKAVLA5SD1Hu9/LYJYvZPCs"
            b"y+LCErY1QKYK2AgHACgEf6NwsZGmKo4j2gChKCBoAhRO7zOhRFAp7oTX35S7Wqor5"
            b"UP39oYfohatoyM2aOJMtQoAgFhl+Hq0URi9AtyI4eSz08j1f1zD4FNPGcn3eni1GA"
            b"s4KYdjdjGnLEJ4KK9uhDAAWxMoOiG9eNIXzdQ2xlMfC1DMYI2ATwOwAccpc5ZJmvN"
            b"nuPeq0GI3QI30sVgCpf9VcG7wadsAYF8MOBEQPnLayxSIU67WMT23izF8C9L5G3ef"
            b"bElbmnqOlEMQhIUbXz7PNHBmXc0sdpA/f0rq5ULexmXVWNACBOYBKC7qTj0alPm7g"
            b"x3rwPQJKObkKHSUFArACKEgIYwRCrGFQGtNcCQU4uTh7s2/4l15IFmZZ5Nak1Wgvv"
            b"bc8vWbFfKIwkyxhir4/+J72jJcd/Ixdpc+QHoo1OS3XipIkIjt8cGXv5Vr5RAVQkL"
            b"tLnyKcUan4GLGhKU+y82Ol8A49h31zz9A1IAAAAAElFTkSuQmCC"
        )
        xml_content = r"""
<?xml version="1.0" encoding="UTF-8"?><?mso-infoPathSolution solutionVersion="1.0.0.14" productVersion="12.0.0" PIVersion="1.0.0.0" href="file:///C:\Users\User\Desktop\Infopath\create_document.xsn" name="urn:schemas-microsoft-com:office:infopath:create-document:-myXSD-2011-07-04T07-44-13" ?><?mso-application progid="InfoPath.Document" versionProgid="InfoPath.Document.2"?><my:CremeCRMCrudity xmlns:my="http://schemas.microsoft.com/office/infopath/2003/myXSD/2011-07-04T07:44:13" xml:lang="fr">
    <my:user_id>{}</my:user_id>
    <my:title>My doc</my:title>
    <my:linked_folder_id>{}</my:linked_folder_id>
    <my:filedata>{}</my:filedata>
    <my:description>
        <div xmlns="http://www.w3.org/1999/xhtml">A document</div>
    </my:description>
</my:CremeCRMCrudity>""".format(user.id, folder.id, img_content.decode())  # NOQA

        infopath_input = self._get_infopath_input(
            DocumentFakeBackend,
            password='creme',
            subject='create_ce_infopath',
            body_map={
                'user_id':     user.id,
                'filedata':    '',
                'title':       '',
                'description': '',
                'linked_folder_id':   ''
            },
        )

        q_document_existing_ids = self._get_existing_q(Document)
        self.assertEqual(0, WaitingAction.objects.count())
        infopath_input.create(self._get_pop_email(
            body='password=creme',
            senders=('user@cremecrm.com',),
            subject='create_ce_infopath',
            attachments=[self._build_attachment(content=xml_content.encode())],
        ))

        wactions = WaitingAction.objects.all()
        self.assertEqual(1, len(wactions))

        wa = wactions[0]
        filename, blob = decode_b64binary(img_content)
        self.assertDictEqual(
            {
                'user_id':          str(user.id),
                'title':            'My doc',
                'linked_folder_id': str(folder.id),
                'description':      'A document',
                'filedata':         (filename, blob),
            },
            wa.data
        )

        infopath_input.get_backend(
            CrudityBackend.normalize_subject('create_ce_infopath')
        ).create(wa)

        document = Document.objects.filter(q_document_existing_ids)[0]
        self.assertEqual(user, document.user)
        self.assertEqual(folder, document.linked_folder)
        self.assertEqual('My doc', document.title)
        self.assertEqual('A document', document.description)
        self.assertTrue(document.filedata)

        blob = decode_b64binary(img_content)[1]
        with document.filedata.open() as f:
            self.assertEqual(blob, f.read())


class FileSystemInputTestCase(CrudityTestCase):
    tmp_dir_path = None

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.tmp_dir_path = mkdtemp(prefix='creme_crudity_fsinput')

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()

        if cls.tmp_dir_path is not None:
            rmtree(cls.tmp_dir_path)

    def setUp(self):
        super().setUp()
        self.login()

    @classmethod
    def get_deletable_file_path(cls, name):
        ext = '.ini'

        tmpfile = NamedTemporaryFile(prefix=name, suffix=ext, delete=False, dir=cls.tmp_dir_path)
        tmpfile.close()

        copy(join(dirname(__file__), 'data', name + ext), tmpfile.name)

        return tmpfile.name

    def test_error01(self):
        "Unknown file."
        inifile_input = IniFileInput()
        subject = CrudityBackend.normalize_subject('test_create_contact')
        backend = self.FakeContactBackend({'subject': subject})

        inifile_input.add_backend(backend)
        path = join(dirname(__file__), 'data', 'unknown.ini')

        with self.assertNoException():
            with self.assertLogs(level='WARNING') as logs_manager:
                ret_backend = IniFileInput().create(path)

        self.assertIsNone(ret_backend)
        self.assertListEqual(
            logs_manager.output,
            [
                f'WARNING:creme.crudity.inputs.filesystem:IniFileInput.create(): '
                f'invalid ini file ({path})',
            ],
        )

    def test_error02(self):
        "Invalid format."
        inifile_input = IniFileInput()
        subject = CrudityBackend.normalize_subject('test_create_contact')
        backend = self.FakeContactBackend({'subject': subject})

        inifile_input.add_backend(backend)
        path = self.get_deletable_file_path('test_error_01')

        with self.assertNoException():
            with self.assertLogs(level='WARNING') as logs_manager:
                ret_backend = IniFileInput().create(path)

        self.assertIsNone(ret_backend)
        self.assertListEqual(
            logs_manager.output,
            [
                f'WARNING:creme.crudity.inputs.filesystem:IniFileInput.create(): '
                f'invalid ini file : File contains no section headers.\n'
                f"file: '{path}', line: 1\n'action: TEST_CREATE_CONTACT\\n'",
            ],
        )

    def test_error03(self):
        "No head."
        inifile_input = IniFileInput()
        subject = CrudityBackend.normalize_subject('test_create_contact')
        backend = self.FakeContactBackend({'subject': subject})

        inifile_input.add_backend(backend)
        path = self.get_deletable_file_path('test_error_02')

        with self.assertNoException():
            with self.assertLogs(level='WARNING') as logs_manager:
                ret_backend = IniFileInput().create(path)

        self.assertIsNone(ret_backend)
        self.assertEqual(
            logs_manager.output,
            [
                "WARNING:creme.crudity.inputs.filesystem:IniFileInput.create(): "
                "invalid file content for {} (No section: 'head')".format(path),
            ],
        )

    def test_subject_dont_matches(self):
        inifile_input = IniFileInput()
        subject = CrudityBackend.normalize_subject('test_create_orga')
        backend = self.FakeContactBackend({'subject': subject})

        inifile_input.add_backend(backend)

        with self.assertNoException():
            ok = IniFileInput().create(self.get_deletable_file_path('test_ok_01'))

        # self.assertIs(ok, False)
        self.assertIsNone(ok)

    def test_sandbox01(self):
        self.assertFalse(WaitingAction.objects.all())

        inifile_input = IniFileInput()
        subject = CrudityBackend.normalize_subject('test_create_contact')
        backend = self.FakeContactBackend({
            'subject': subject,
            'in_sandbox': True,
            'body_map': {
                'user_id':     1,
                'last_name':   '',
                'first_name':  '',
                'description': '',
            },
        })

        inifile_input.add_backend(backend)

        file_path = self.get_deletable_file_path('test_ok_01')

        with self.assertNoException():
            ok = inifile_input.create(file_path)

        self.assertIsInstance(ok, CrudityBackend)

        wactions = WaitingAction.objects.all()
        self.assertEqual(1, len(wactions))

        waction = wactions[0]
        self.assertDictEqual(
            {
                'user_id':     '1',
                'first_name':  'Frodo',
                'last_name':   'Baggins',
                'description': 'this hobbit will\nsave the world',
            },
            waction.data
        )

        owner = waction.user
        self.assertIsNotNone(owner)
        self.assertTrue(owner.is_superuser)

        self.assertFalse(exists(file_path))

    def test_sandbox02(self):
        "Smaller body_map."
        self.assertFalse(WaitingAction.objects.all())

        inifile_input = IniFileInput()
        subject = CrudityBackend.normalize_subject('test_create_contact')
        backend = self.FakeContactBackend({
            'subject':    subject,
            'in_sandbox': True,
            'body_map':   {
                'user_id':     1,
                'last_name':   '',
                'first_name':  '',
                # 'description': '',
            },
        })

        inifile_input.add_backend(backend)

        with self.assertNoException():
            ok = inifile_input.create(self.get_deletable_file_path('test_ok_01'))

        self.assertIsNotNone(ok)

        wactions = WaitingAction.objects.all()
        self.assertEqual(1, len(wactions))
        self.assertDictEqual(
            {
                'user_id':     '1',
                'first_name':  'Frodo',
                'last_name':   'Baggins',
                # 'description': 'this hobbit will\nsave the world',
            },
            wactions[0].data
        )

    def test_sandbox_by_user01(self):
        self._set_sandbox_by_user()

        inifile_input = IniFileInput()
        subject = CrudityBackend.normalize_subject('test_create_contact')
        backend = self.FakeContactBackend({
            'subject':    subject,
            'in_sandbox': True,
            'body_map':   {
                'user_id':     1,
                'last_name':   '',
                'first_name':  '',
            },
        })

        inifile_input.add_backend(backend)

        with self.assertNoException():
            ok = inifile_input.create(self.get_deletable_file_path('test_ok_02'))

        self.assertIsNotNone(ok)

        wactions = WaitingAction.objects.all()
        self.assertEqual(1, len(wactions))

        waction = wactions[0]
        self.assertDictEqual(
            {
                'user_id':    '1',
                'first_name': 'Bilbo',
                'last_name':  'Baggins',
            },
            waction.data
        )
        self.assertEqual(self.other_user, waction.user)

    def test_sandbox_by_user02(self):
        "Unknown username."
        self._set_sandbox_by_user()

        inifile_input = IniFileInput()
        subject = CrudityBackend.normalize_subject('test_create_contact')
        backend = self.FakeContactBackend({
            'subject':    subject,
            'in_sandbox': True,
            'body_map':   {
                'user_id':     1,
                'last_name':   '',
                'first_name':  '',
            },
        })

        inifile_input.add_backend(backend)
        path = self.get_deletable_file_path('test_error_03')

        with self.assertNoException():
            with self.assertLogs(level='WARNING') as logs_manager:
                ret_backend = inifile_input.create(path)

        self.assertIsNotNone(ret_backend)
        self.assertListEqual(
            logs_manager.output,
            [
                f"WARNING:creme.crudity.inputs.filesystem:IniFileInput.create(): "
                f"no user ([head] section) corresponds to {{'username': 'iaminvalid'}} ({path})",
            ],
        )

        wactions = WaitingAction.objects.all()
        self.assertEqual(1, len(wactions))

        waction = wactions[0]
        self.assertDictEqual(
            {
                'user_id':    '1',
                'first_name': 'Samwise',
                'last_name':  'Gamgee',
            },
            waction.data
        )
        owner = waction.user
        self.assertIsNotNone(owner)
        self.assertNotEqual(self.other_user, owner)
        self.assertTrue(owner.is_superuser)

    def test_no_sandbox01(self):
        inifile_input = IniFileInput()
        subject = CrudityBackend.normalize_subject('test_create_contact')
        backend = self.FakeContactBackend({
            'subject':    subject,
            'in_sandbox': False,
            'body_map':   {
                'user_id':     1,
                'last_name':   '',
                'first_name':  '',
                'description': '',
            },
        })
        backend.fetcher_name = 'fs'

        inifile_input.add_backend(backend)

        with self.assertNoException():
            ok = inifile_input.create(self.get_deletable_file_path('test_ok_01'))

        self.assertIsNotNone(ok)
        self.assertFalse(WaitingAction.objects.all())

        c = self.get_object_or_fail(FakeContact, first_name='Frodo', last_name='Baggins')
        self.assertEqual('this hobbit will\nsave the world', c.description)

        history = self.get_object_or_fail(History, entity=c.id)
        self.assertEqual('fs - ini', history.source)
        self.assertEqual('create',   history.action)

        owner = history.user
        self.assertIsNotNone(owner)
        self.assertTrue(owner.is_superuser)
