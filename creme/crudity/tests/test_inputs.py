from datetime import date
from os.path import dirname, exists, join
from shutil import copy, rmtree
from tempfile import NamedTemporaryFile, mkdtemp

from django.apps import apps
from django.db.models.query_utils import Q
from django.test.utils import override_settings

from creme.activities.constants import UUID_SUBTYPE_MEETING_MEETING
from creme.activities.models import ActivitySubType
from creme.creme_core.models import FakeContact
from creme.persons.tests.base import skipIfCustomContact

from ..backends.models import CrudityBackend
from ..fetchers.pop import PopEmail
from ..inputs.email import CreateEmailInput
from ..inputs.filesystem import IniFileInput
from ..models import History, WaitingAction
from .base import Contact, ContactFakeBackend, CrudityTestCase

if apps.is_installed('creme.activities'):
    from creme.activities.tests.base import skipIfCustomActivity
else:
    from unittest import SkipTest

    def skipIfCustomActivity(test_func):
        def _aux(*args, **kwargs):
            raise SkipTest('The app "activities" is not installed.')

        return _aux


# @override_settings(
#     USE_L10N=False,
#     DATE_INPUT_FORMATS=['%d/%m/%Y', '%d-%m-%Y'],
#     DATETIME_INPUT_FORMATS=['%Y-%m-%d %H:%M'],
# )
class InputsBaseTestCase(CrudityTestCase):  # TODO: rename EmailInputBaseTestCase ?
    def setUp(self):
        super().setUp()
        self.user = self.login_as_root_and_get()

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

        waction = self.get_alone_element(WaitingAction.objects.all())
        self.assertDictEqual(
            {'user_id': str(user.id), 'created': '01/02/2003'},
            waction.data,
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
            body='password=creme\nuser_id={user_id}\ncreated={created}\nfirst_name=é'.format(
                user_id=user.id,
                created=self.formfield_value_date(2003, 2, 1),
            ),
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
            # body_html="""<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN">
            # <html>
            #   <head>
            #     <meta http-equiv="content-type" content="text/html;
            #       charset=ISO-8859-1">
            #   </head>
            #   <body text="#3366ff" bgcolor="#ffffff">
            #     <font face="Calibri">password=contact<br>
            #       password=creme<br>
            #       created=01-02-2003<br>
            #     </font>
            #   </body>
            # </html>""",
            body_html=f"""<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN">
        <html>
          <head>
            <meta http-equiv="content-type" content="text/html;
              charset=ISO-8859-1">
          </head>
          <body text="#3366ff" bgcolor="#ffffff">
            <font face="Calibri">password=contact<br>
              password=creme<br>
              created={self.formfield_value_date(2003, 2, 1)}<br>
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
        waction = self.get_alone_element(WaitingAction.objects.all())
        self.assertDictEqual(
            {
                'user_id':     str(user.id),
                'created':     '01/02/2003',
                'description': (
                    'I\n\n        want\n\n        to\n                    create\n'
                    '                a\ncreme\nentity\n\n        '
                ),
            },
            waction.data,
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
        waction = self.get_alone_element(WaitingAction.objects.all())
        self.assertDictEqual(
            {
                'user_id':     str(user.id),
                'created':     '01/02/2003',
                'description': 'I',
            },
            waction.data,
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

        waction = self.get_alone_element(WaitingAction.objects.all())
        self.assertDictEqual(
            {
                'user_id':     user.id,
                'created':     '01-02-2003',
                'description': 'I\n want to\n create a    \ncreme entity\n',
            },
            waction.data,
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

        waction = self.get_alone_element(WaitingAction.objects.all())
        self.assertDictEqual(
            {
                'user_id':     user.id,
                'created':     '01-02-2003',
                'description': 'I\n want to\n create a    \ncreme entity\n',
            },
            waction.data,
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

        self.assertFalse(WaitingAction.objects.count())
        email_input.create(self._get_pop_email(
            body_html=body_html, senders=('creme@crm.org',), subject='create_ce',
        ))

        waction = self.get_alone_element(WaitingAction.objects.all())
        self.assertDictEqual(
            {
                'user_id': user.id,
                'created': '01-02-2003',
                'description': 'I',
            },
            waction.data,
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

        waction = self.get_alone_element(
            WaitingAction.objects.filter(user=self.get_root_user())
        )
        self.assertDictEqual(
            {'user_id': str(user.id), 'created': '01/02/2003'}, waction.data,
        )

    @skipIfCustomContact
    def test_create_email_input14(self):
        "Text mail un-sandboxed but by user"
        user = self.user
        other_user = self.create_user()

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
        other_user = self.create_user()
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
            # body=f'password=creme\nuser_id={user.id}\ncreated=01-02-2003\nurl_site=plop',
            body=(
                f'password=creme\n'
                f'user_id={user.id}\n'
                f'created={self.formfield_value_date(2003, 2, 1)}\n'
                f'url_site=plop'
            ),
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
        other_user = self.create_user()

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
        "The user doesn't match."
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
            self.get_root_user(),
            email_input.get_owner(True, sender='another_user@cremecrm.com'),
        )

    @skipIfCustomContact
    @override_settings(LANGUAGE_CODE='fr')
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

        waction = self.get_alone_element(WaitingAction.objects.all())
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
            waction.data,
        )

        email_input.get_backend(
            CrudityBackend.normalize_subject('create_contact')
        ).create(waction)

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
        sub_type = self.get_object_or_fail(ActivitySubType, uuid=UUID_SUBTYPE_MEETING_MEETING)
        email_input = self._get_email_input(
            ActivityFakeBackend,
            password='creme',
            subject=subject,
            body_map={
                'user_id':     user.id,
                'title':       '',
                # 'type_id':     ACTIVITYTYPE_MEETING,
                # 'sub_type_id': ACTIVITYSUBTYPE_MEETING_MEETING,
                'type_id':     sub_type.type_id,
                'sub_type_id': sub_type.id,
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

        waction = self.get_alone_element(WaitingAction.objects.all())

        is_created, activity = email_input.get_backend(
            CrudityBackend.normalize_subject(subject)
        ).create(waction)
        self.assertTrue(is_created)
        self.assertIsInstance(activity, Activity)

        activity = self.refresh(activity)
        self.assertEqual(user,             activity.user)
        self.assertEqual(title,            activity.title)
        # self.assertEqual(ACTIVITYTYPE_MEETING,            activity.type.id)
        # self.assertEqual(ACTIVITYSUBTYPE_MEETING_MEETING, activity.sub_type.id)
        self.assertEqual(sub_type.type_id, activity.type.id)
        self.assertEqual(sub_type.id,      activity.sub_type.id)

        create_dt = self.create_datetime
        self.assertEqual(
            create_dt(year=2013, month=6, day=15, hour=9, utc=True),
            activity.start,
        )
        self.assertEqual(
            create_dt(year=2013, month=6, day=15, hour=12, minute=28, second=45),
            activity.end,
        )


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
        self.user = self.login_as_root_and_get()

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

        waction = self.get_alone_element(WaitingAction.objects.all())
        self.assertDictEqual(
            {
                'user_id':     '1',
                'first_name':  'Frodo',
                'last_name':   'Baggins',
                'description': 'this hobbit will\nsave the world',
            },
            waction.data,
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

        waction = self.get_alone_element(WaitingAction.objects.all())
        self.assertDictEqual(
            {
                'user_id':     '1',
                'first_name':  'Frodo',
                'last_name':   'Baggins',
                # 'description': 'this hobbit will\nsave the world',
            },
            waction.data,
        )

    def test_sandbox_by_user01(self):
        # other_user = self.other_user
        other_user = self.create_user(index=1)
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

        waction = self.get_alone_element(WaitingAction.objects.all())
        self.assertDictEqual(
            {
                'user_id':    '1',
                'first_name': 'Bilbo',
                'last_name':  'Baggins',
            },
            waction.data,
        )
        self.assertEqual(other_user, waction.user)

    def test_sandbox_by_user02(self):
        "Unknown username."
        other_user = self.create_user(index=1)
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

        waction = self.get_alone_element(WaitingAction.objects.all())
        self.assertDictEqual(
            {
                'user_id':    '1',
                'first_name': 'Samwise',
                'last_name':  'Gamgee',
            },
            waction.data,
        )

        owner = waction.user
        self.assertIsNotNone(owner)
        self.assertNotEqual(other_user, owner)
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
