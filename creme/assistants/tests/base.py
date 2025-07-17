from functools import partial

from creme.creme_core import creme_jobs
from creme.creme_core.core.workflow import WorkflowEngine
from creme.creme_core.models import FakeContact, Job
from creme.creme_core.models.history import (
    TYPE_AUX_CREATION,
    TYPE_DELETION,
    HistoryLine,
)
from creme.creme_core.tests.base import CremeTestCase


class AssistantsTestCase(CremeTestCase):
    def login_as_assistants_user(self, *, allowed_apps=('creme_core', ), **kwargs):
        return super().login_as_standard(allowed_apps=['assistants', *allowed_apps], **kwargs)

    def create_entity(self, user, **kwargs):
        return FakeContact.objects.create(
            user=user, first_name='Ranma', last_name='Saotome', **kwargs,
        )

    def aux_test_merge(self, creator, assertor, moved_count=1):
        user  = self.login_as_root_and_get()
        create_contact = partial(FakeContact.objects.create, user=user)
        contact01 = create_contact(first_name='Ryoga', last_name='Hibiki')
        contact02 = create_contact(first_name='Ryoag', last_name='Hibiik')

        creator(user, contact01, contact02)
        old_count = HistoryLine.objects.count()

        response = self.client.post(
            self.build_merge_url(contact01, contact02),
            follow=True,
            data={
                'user_1':      user.id,
                'user_2':      user.id,
                'user_merged': user.id,

                'first_name_1':      contact01.first_name,
                'first_name_2':      contact02.first_name,
                'first_name_merged': contact01.first_name,

                'last_name_1':      contact01.last_name,
                'last_name_2':      contact02.last_name,
                'last_name_merged': contact01.last_name,
            },
        )
        self.assertNoFormError(response)

        self.assertDoesNotExist(contact02)

        with self.assertNoException():
            contact01 = self.refresh(contact01)

        assertor(contact01)

        hlines = [*HistoryLine.objects.order_by('id')]
        # 1 deletion line + N * TYPE_AUX_CREATION lines
        self.assertEqual(old_count + 1 + moved_count, len(hlines))

        if moved_count:
            hline = hlines[-2]
            self.assertEqual(TYPE_AUX_CREATION, hline.type)
            self.assertEqual(contact01, hline.entity.get_real_entity())

        hline = hlines[-1]
        self.assertEqual(TYPE_DELETION, hline.type)
        self.assertEqual(str(contact02), hline.entity_repr)

    def get_reminder_job(self):
        return self.get_object_or_fail(Job, type_id=creme_jobs.reminder_type.id)

    def execute_reminder_job(self, job=None):
        # Empty the Queue to avoid log messages
        WorkflowEngine.get_current()._queue.pickup()

        job = job or self.get_reminder_job()
        creme_jobs.reminder_type.execute(job)

        return job
