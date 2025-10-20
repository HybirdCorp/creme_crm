from django.utils.timezone import now

from creme.creme_config.models import AdminHistoryLine
from creme.creme_core.models import CremeUser
from creme.creme_core.tests.base import CremeTestCase


# BrickTestCaseMixin
class AdminHistoryTestCase(CremeTestCase):
    def test_user_creation(self):
        self.login_as_root()

        old_count = AdminHistoryLine.objects.count()
        self.create_user()
        self.assertEqual(old_count + 1, AdminHistoryLine.objects.count())

        line = AdminHistoryLine.objects.order_by('-id')[0]
        self.assertEqual(CremeUser, line.content_type.model_class())
        self.assertEqual('root',    line.username)
        self.assertDatetimesAlmostEqual(now(), line.date)
        # TODO: type CREATION
        # TODO: fields values?
        # TODO: by_wf_engine?

        self.fail('TODO: brick on user config page')
        # TODO: self.fail('TODO: portal')
