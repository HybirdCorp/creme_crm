# -*- coding: utf-8 -*-

from datetime import timedelta

from django.conf import settings
from django.urls import reverse
from django.utils.timezone import now
from django.utils.translation import gettext as _

from creme.creme_core.models import SettingValue
from creme.creme_core.tests.base import skipIfNotInstalled
from creme.crudity.constants import SETTING_CRUDITY_SANDBOX_BY_USER
from creme.crudity.fetchers.pop import PopEmail
from creme.crudity.models import History
from creme.crudity.utils import is_sandbox_by_user
from creme.documents.models import FolderCategory

# from ..constants import (
#     MAIL_STATUS_SENT,
#     MAIL_STATUS_SYNCHRONIZED,
#     MAIL_STATUS_SYNCHRONIZED_SPAM,
#     MAIL_STATUS_SYNCHRONIZED_WAITING,
# )
from .base import EntityEmail, _EmailsTestCase, skipIfCustomEntityEmail


@skipIfNotInstalled('creme.crudity')
@skipIfCustomEntityEmail
class EmailsCrudityTestCase(_EmailsTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        from ..crudity_register import EntityEmailBackend
        cls.EntityEmailBackend = EntityEmailBackend

    def setUp(self):
        super().setUp()
        self.login()
        self._category_to_restore = None

    def tearDown(self):
        super().tearDown()
        cat = self._category_to_restore

        if cat is not None:
            FolderCategory.objects.filter(name=cat.name).delete()
            cat.save()

    cfg = {
        # "fetcher": "email",
        # "input": "raw",
        # "method": "create",
        # "model": "emails.entityemail",
        'password': '',
        'limit_froms': (),
        'in_sandbox': True,
        'body_map': {},
        'subject': '*',

        'source':         'emails - raw',
        'verbose_source': 'Email - Raw',
        'verbose_method': 'Create',
    }

    # def test_spam(self):  # DEPRECATED
    #     emails = self._create_emails()
    #
    #     self.assertEqual([MAIL_STATUS_SENT] * 4, [e.status for e in emails])
    #
    #     url = reverse('emails__crudity_spam')
    #     self.assertPOST200(url)
    #     self.assertPOST200(url, data={'ids': [e.id for e in emails]})
    #
    #     refresh = self.refresh
    #     self.assertListEqual(
    #         [MAIL_STATUS_SYNCHRONIZED_SPAM] * 4,
    #         [refresh(e).status for e in emails]
    #     )

    # def test_validated(self):  # DEPRECATED
    #     emails = self._create_emails()
    #
    #     self.assertPOST200(
    #         reverse('emails__crudity_validated'),
    #         data={'ids': [e.id for e in emails]},
    #     )
    #
    #     refresh = self.refresh
    #     self.assertListEqual(
    #         [MAIL_STATUS_SYNCHRONIZED] * 4,
    #         [refresh(e).status for e in emails]
    #     )

    # def test_waiting(self):  # DEPRECATED
    #     emails = self._create_emails()
    #
    #     self.assertPOST200(
    #         reverse('emails__crudity_waiting'),
    #         data={'ids': [e.id for e in emails]},
    #     )
    #
    #     refresh = self.refresh
    #     self.assertListEqual(
    #         [MAIL_STATUS_SYNCHRONIZED_WAITING] * 4,
    #         [refresh(e).status for e in emails]
    #     )

    def test_set_status01(self):
        "Validated."
        emails = self._create_emails()
        # self.assertEqual([MAIL_STATUS_SENT] * 4, [e.status for e in emails])
        self.assertEqual([EntityEmail.Status.SENT] * 4, [e.status for e in emails])

        url = reverse('emails__crudity_set_email_status', args=('validated',))
        self.assertGET405(url)
        self.assertPOST200(url)

        data = {'ids': [e.id for e in emails]}
        self.assertPOST404(
            reverse('emails__crudity_set_email_status', args=('invalid',)),
            data=data,
        )

        self.assertPOST200(url, data=data)
        refresh = self.refresh
        self.assertListEqual(
            # [MAIL_STATUS_SYNCHRONIZED] * 4,
            [EntityEmail.Status.SYNCHRONIZED] * 4,
            [refresh(e).status for e in emails]
        )

    def test_set_status02(self):
        "Spam."
        emails = self._create_emails()

        self.assertPOST200(
            reverse('emails__crudity_set_email_status', args=('spam',)),
            data={'ids': [e.id for e in emails]},
        )

        refresh = self.refresh
        self.assertListEqual(
            # [MAIL_STATUS_SYNCHRONIZED_SPAM] * 4,
            [EntityEmail.Status.SYNCHRONIZED_SPAM] * 4,
            [refresh(e).status for e in emails],
        )

    def test_set_status03(self):
        "Waiting."
        emails = self._create_emails()

        self.assertPOST200(
            reverse('emails__crudity_set_email_status', args=('waiting',)),
            data={'ids': [e.id for e in emails]},
        )

        refresh = self.refresh
        self.assertListEqual(
            # [MAIL_STATUS_SYNCHRONIZED_WAITING] * 4,
            [EntityEmail.Status.SYNCHRONIZED_WAITING] * 4,
            [refresh(e).status for e in emails],
        )

    def test_synchronisation(self):
        response = self.assertGET200(reverse('emails__crudity_sync'))
        self.assertTemplateUsed(response, 'emails/synchronize.html')

        get = response.context.get
        self.assertEqual(
            reverse('crudity__reload_actions_bricks'),
            get('bricks_reload_url')
        )

        bricks = get('bricks')

        for backend in settings.CRUDITY_BACKENDS:
            if backend.get('fetcher') == 'email' and backend.get('subject') == '*':
                self.assertIsList(bricks, min_length=1)
                break
        else:
            self.assertIsNone(bricks)

        # TODO: complete

    def test_create01(self):
        "Shared sandbox"
        user = self.user
        other_user = self.other_user

        sv = self.get_object_or_fail(
            SettingValue,
            key_id=SETTING_CRUDITY_SANDBOX_BY_USER,
        )
        self.assertEqual(False, sv.value)

        backend = self.EntityEmailBackend(self.cfg)
        # self.assertFalse(backend.is_sandbox_by_user)
        self.assertFalse(is_sandbox_by_user())

        email = PopEmail(
            body='Hi', body_html='<i>Hi</i>', subject='Test email crudity',
            senders=[other_user.email], ccs=[user.email],
            tos=['natsuki.hagiwara@ichigo.jp', 'kota.ochiai@ichigo.jp'],
        )
        backend.fetcher_fallback(email, user)

        e_email = self.get_object_or_fail(EntityEmail, subject=email.subject)
        # self.assertEqual(MAIL_STATUS_SYNCHRONIZED_WAITING, e_email.status)
        self.assertEqual(EntityEmail.Status.SYNCHRONIZED_WAITING, e_email.status)
        self.assertEqual(email.body,      e_email.body)
        self.assertEqual(email.body_html, e_email.body_html)
        self.assertEqual(user,            e_email.user)
        self.assertEqual(e_email.sender, 'mireille@noir.jp')
        self.assertIsNone(e_email.reception_date)

        with self.assertNoException():
            recipients = {r.strip() for r in e_email.recipient.split(',')}

        self.assertSetEqual({user.email, email.tos[0], email.tos[1]}, recipients)

        history = self.get_object_or_fail(History, entity=e_email.id)
        self.assertEqual('create',      history.action)
        self.assertEqual('email - raw', history.source)
        self.assertEqual(user,          history.user)
        self.assertEqual(
            _('Creation of {entity}').format(entity=e_email),
            history.description,
        )

    def test_create02(self):
        "Sandbox by user + dates."
        user = self.user
        other_user = self.other_user

        sv = self.get_object_or_fail(
            SettingValue,
            key_id=SETTING_CRUDITY_SANDBOX_BY_USER,
        )
        sv.value = True
        sv.save()

        backend = self.EntityEmailBackend(self.cfg)
        # self.assertTrue(backend.is_sandbox_by_user)
        self.assertTrue(is_sandbox_by_user())

        email = PopEmail(
            body='Hi', body_html='<i>Hi</i>', subject='Test email crudity',
            senders=[other_user.email], ccs=[user.email],
            tos=['natsuki.hagiwara@ichigo.jp', 'kota.ochiai@ichigo.jp'],
            # replace(microsecond=0)  -> MySQL does not like microseconds...
            dates=[now().replace(microsecond=0) - timedelta(hours=1)],
        )
        backend.fetcher_fallback(email, user)

        e_email = self.get_object_or_fail(EntityEmail, subject=email.subject)
        self.assertEqual(email.body, e_email.body)
        self.assertEqual(other_user, e_email.user)  # <== not 'user' !
        self.assertEqual(email.dates[0], e_email.reception_date)

        history = self.get_object_or_fail(History, entity=e_email.id)
        self.assertEqual(other_user, history.user)  # <== not 'user' !

    # TODO: authorize_senders return False
    # TODO: attachments
