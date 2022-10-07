from datetime import timedelta
from functools import partial

from django.contrib.sessions.models import Session
from django.utils.timezone import now
from django.utils.translation import gettext as _

from creme.creme_core.creme_jobs import sessions_cleaner_type
from creme.creme_core.models import Job

from .. import base


class SessionTestCase(base.CremeTestCase):
    def test_session_cleaner_job(self):
        job = self.get_object_or_fail(Job, type_id=sessions_cleaner_type.id)

        self.assertListEqual(
            [_("Remove expired user sessions")],
            sessions_cleaner_type.get_description(job),
        )

        key1 = '123456'
        key2 = '789632'
        create_session = partial(Session.objects.save, session_dict={'whatever': 'some data'})
        now_value = now()
        create_session(session_key=key1, expire_date=now_value + timedelta(days=1))
        create_session(session_key=key2, expire_date=now_value - timedelta(days=1))

        sessions_cleaner_type.execute(job)
        self.assertTrue(Session.objects.filter(session_key=key1).exists())
        self.assertFalse(Session.objects.filter(session_key=key2).exists())
