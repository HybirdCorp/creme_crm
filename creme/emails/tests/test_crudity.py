# -*- coding: utf-8 -*-

try:
    from datetime import timedelta

    from django.utils.timezone import now
    from django.utils.translation import ugettext as _

    from creme.creme_core.models import SettingValue
    from creme.creme_core.tests.base import CremeTestCase

#    from creme.documents import get_folder_model
#    from creme.documents.constants import DOCUMENTS_FROM_EMAILS, DOCUMENTS_FROM_EMAILS_NAME
    from creme.documents.models import FolderCategory #, Folder

    from creme.crudity.constants import SETTING_CRUDITY_SANDBOX_BY_USER
    from creme.crudity.fetchers.pop import PopEmail
    from creme.crudity.models import History

    from ..constants import MAIL_STATUS_SYNCHRONIZED_WAITING
    from ..crudity_register import EntityEmailBackend
    from ..models import EntityEmail
    from .base import skipIfCustomEntityEmail
except Exception as e:
    print('Error in <%s>: %s' % (__name__, e))


__all__ = ('EmailsCrudityTestCase',)


@skipIfCustomEntityEmail
class EmailsCrudityTestCase(CremeTestCase):
    @classmethod
    def setUpClass(cls):
        CremeTestCase.setUpClass()
        cls.populate('documents', 'crudity')

    def setUp(self):
        self.login()
        self._category_to_restore = None

    def tearDown(self):
        cat = self._category_to_restore

        if cat is not None:
            FolderCategory.objects.filter(name=cat.name).delete()
            cat.save()

    cfg = {
            #"fetcher": "email",
            #"input": "raw",
            #"method": "create",
            #"model": "emails.entityemail",
            "password": "",
            "limit_froms": (),
            "in_sandbox": True,
            "body_map": {},
            "subject": u"*",

            'source':         'emails - raw',
            'verbose_source': 'Email - Raw', #_(u"Email - Raw"),
            'verbose_method': 'Create',  #_(u"Create")
          }

    def test_create01(self):
        "Shared sandbox"
        user = self.user
        other_user = self.other_user

        sv = self.get_object_or_fail(SettingValue, key_id=SETTING_CRUDITY_SANDBOX_BY_USER)
        self.assertEqual(False, sv.value)

        backend = EntityEmailBackend(self.cfg)
        self.assertFalse(backend.is_sandbox_by_user)

        email = PopEmail(body='Hi', body_html='<i>Hi</i>', subject='Test email crudity',
                         senders=[other_user.email], ccs=[user.email],
                         tos=['natsuki.hagiwara@ichigo.jp', 'kota.ochiai@ichigo.jp'],
                        )
        backend.fetcher_fallback(email, user)

        e_email = self.get_object_or_fail(EntityEmail, subject=email.subject)
        self.assertEqual(MAIL_STATUS_SYNCHRONIZED_WAITING, e_email.status)
        self.assertEqual(email.body,                       e_email.body)
        self.assertEqual(email.body_html,                  e_email.body_html)
        self.assertEqual(user,                             e_email.user)
        self.assertEqual(e_email.sender, 'mireille@noir.jp')
        self.assertIsNone(e_email.reception_date)

        with self.assertNoException():
            recipients = {r.strip() for r in e_email.recipient.split(',')}

        self.assertEqual({user.email, email.tos[0], email.tos[1]}, recipients)

        history = self.get_object_or_fail(History, entity=e_email.id)
        self.assertEqual('create',      history.action)
        self.assertEqual('email - raw', history.source)
        self.assertEqual(user,          history.user)
        self.assertEqual(_('Creation of %(entity)s') % {'entity': e_email},
                         history.description
                        )

    def test_create02(self):
        "Sandbox by user + dates"
        user = self.user
        other_user = self.other_user

        sv = self.get_object_or_fail(SettingValue, key_id=SETTING_CRUDITY_SANDBOX_BY_USER)
        sv.value = True
        sv.save()

        backend = EntityEmailBackend(self.cfg)
        self.assertTrue(backend.is_sandbox_by_user)

        email = PopEmail(body='Hi', body_html='<i>Hi</i>', subject='Test email crudity',
                         senders=[other_user.email], ccs=[user.email],
                         tos=['natsuki.hagiwara@ichigo.jp', 'kota.ochiai@ichigo.jp'],
                         # replace(microsecond=0)  -> MySQL does not like microseconds...
                         dates=[now().replace(microsecond=0) - timedelta(hours=1)],
                        )
        backend.fetcher_fallback(email, user)

        e_email = self.get_object_or_fail(EntityEmail, subject=email.subject)
        self.assertEqual(email.body, e_email.body)
        self.assertEqual(other_user, e_email.user) #<== not 'user' !
        self.assertEqual(email.dates[0], e_email.reception_date)

        history = self.get_object_or_fail(History, entity=e_email.id)
        self.assertEqual(other_user, history.user) #<== not 'user' !

#    def test_create_with_deleted_category01(self):
#        "Create category if it has been deleted"
#        self._category_to_restore = old_cat = self.get_object_or_fail(FolderCategory, pk=DOCUMENTS_FROM_EMAILS)
#        old_cat.delete()
#
#        user = self.user
#        other_user = self.other_user
#
#        backend = EntityEmailBackend(self.cfg)
#        email = PopEmail(body='Hi', body_html='<i>Hi</i>', subject='Test email crudity',
#                         senders=[other_user.email], ccs=[user.email],
#                         tos=['natsuki.hagiwara@ichigo.jp', 'kota.ochiai@ichigo.jp'],
#                        )
#        backend.fetcher_fallback(email, user)
#        self.get_object_or_fail(EntityEmail, subject=email.subject)
#
#        cat = self.get_object_or_fail(FolderCategory, pk=DOCUMENTS_FROM_EMAILS)
#        self.assertEqual(DOCUMENTS_FROM_EMAILS_NAME, cat.name)
#
#    def test_create_with_deleted_category02(self):
#        "Create category if it has been deleted, and another one created with the same name"
#        user = self.user
#        other_user = self.other_user
#
#        backend = EntityEmailBackend(self.cfg)
#        email = PopEmail(body='Hi', body_html='<i>Hi</i>', subject='Test email crudity',
#                         senders=[other_user.email], ccs=[user.email],
#                         tos=['natsuki.hagiwara@ichigo.jp', 'kota.ochiai@ichigo.jp'],
#                        )
#        backend.fetcher_fallback(email, user)
#        self.get_object_or_fail(EntityEmail, subject=email.subject)
#
#        folder = self.get_object_or_fail(get_folder_model(), title=_(u"%(username)s's files received by email") % {
#                                                                'username': user.username,
#                                                            },
#                                        )
#
#        self._category_to_restore = old_cat = folder.category
#        old_cat.delete()
#        self.assertIsNone(self.refresh(folder).category)
#
#        FolderCategory.objects.create(name=unicode(DOCUMENTS_FROM_EMAILS_NAME))
#
#        email.subject += '#2'
#        backend.fetcher_fallback(email, user)
#        self.get_object_or_fail(EntityEmail, subject=email.subject)

    #TODO: authorize_senders return False
    #TODO: attachments
