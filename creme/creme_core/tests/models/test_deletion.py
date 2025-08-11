from functools import partial

from django.contrib.contenttypes.models import ContentType
from django.db.models.deletion import ProtectedError
from django.utils.translation import gettext as _
from django.utils.translation import ngettext

from creme.creme_core.core.deletion import FixedValueReplacer, SETReplacer
from creme.creme_core.core.workflow import WorkflowEngine
from creme.creme_core.creme_jobs import deletor_type
from creme.creme_core.models import (
    DeletionCommand,
    FakeCivility,
    FakeContact,
    FakeOrganisation,
    FakeSector,
    FakeTicket,
    FakeTicketPriority,
    Job,
    JobResult,
)
from creme.creme_core.utils.translation import smart_model_verbose_name

from ..base import CremeTestCase


class DeletionCommandTestCase(CremeTestCase):
    def _create_job(self, user):
        return Job.objects.create(type_id=deletor_type.id, user=user)

    def _execute_job(self, job):
        # Empty the Queue to avoid log messages
        WorkflowEngine.get_current()._queue.pickup()

        deletor_type.execute(job)

    def test_creme_replace_null(self):
        user = self.get_root_user()
        civ = FakeCivility.objects.create(title='Kun')
        contact = FakeContact.objects.create(
            user=user, civility=civ,
            last_name='Hattori', first_name='Hanzo',
        )

        civ.delete()
        self.assertDoesNotExist(civ)

        contact = self.assertStillExists(contact)
        self.assertIsNone(contact.civility)

    def test_creme_replace(self):
        user = self.get_root_user()
        sector = FakeSector.objects.create(title='Ninja')
        orga = FakeOrganisation.objects.create(
            user=user, sector=sector, name='Hattori clan',
        )

        with self.assertRaises(ProtectedError):
            sector.delete()

        self.assertStillExists(sector)

        orga = self.assertStillExists(orga)
        self.assertEqual(sector, orga.sector)

    def test_deletion_command01(self):
        user = self.get_root_user()

        civ = FakeCivility.objects.create(title='Kun')
        job = self._create_job(user)
        dcom = DeletionCommand.objects.create(
            content_type=ContentType.objects.get_for_model(FakeCivility),
            job=job,
            pk_to_delete=str(civ.pk),
            deleted_repr=str(civ),
            replacers=[],
        )

        self.assertEqual(civ, dcom.instance_to_delete)

    def test_deletion_command02(self):
        "<instance_to_delete> setter."
        user = self.get_root_user()

        sector = FakeSector.objects.create(title='Ninja')
        job = self._create_job(user)
        dcom = DeletionCommand.objects.create(
            job=job,
            instance_to_delete=sector,
            replacers=[],
        )
        dcom = self.refresh(dcom)
        self.assertEqual(
            ContentType.objects.get_for_model(FakeSector),
            dcom.content_type
        )
        self.assertEqual(str(sector.id), dcom.pk_to_delete)
        self.assertEqual(sector.title,   dcom.deleted_repr)
        self.assertEqual(sector,         dcom.instance_to_delete)
        self.assertEqual([], dcom.replacers)

    def test_deletion_command_replacers01(self):
        user = self.get_root_user()

        create_sector = FakeSector.objects.create
        sector     = create_sector(title='Shinobi')
        sector2del = create_sector(title='Ninja')

        job = self._create_job(user)

        field1 = FakeContact._meta.get_field('sector')
        field2 = FakeOrganisation._meta.get_field('sector')

        dcom = DeletionCommand.objects.create(
            job=job,
            instance_to_delete=sector2del,
            replacers=[
                FixedValueReplacer(model_field=field1, value=sector),
                FixedValueReplacer(model_field=field2, value=sector),
            ],
        )

        replacers = self.refresh(dcom).replacers
        self.assertIsList(replacers, length=2)

        replacer1 = replacers[0]
        self.assertIsInstance(replacer1, FixedValueReplacer)
        self.assertEqual(field1, replacer1.model_field)
        self.assertEqual(sector, replacer1.get_value())

        self.assertEqual(field2, replacers[1].model_field)

        # with self.assertRaises(TypeError):  TODO?
        with self.assertRaises(AttributeError):
            DeletionCommand.objects.create(
                job=job,
                instance_to_delete=sector,
                replacers=[(1, 2)],
            )

    def test_deletion_command_replacers02(self):
        "SETReplacer"
        user = self.get_root_user()
        prio2del = FakeTicketPriority.objects.create(name='Not so important')

        job = self._create_job(user)
        field = FakeTicket._meta.get_field('priority')
        dcom = DeletionCommand.objects.create(
            job=job,
            instance_to_delete=prio2del,
            replacers=[SETReplacer(model_field=field)],
        )

        replacers = self.refresh(dcom).replacers
        self.assertIsList(replacers, length=1)

        replacer = replacers[0]
        self.assertIsInstance(replacer, SETReplacer)
        self.assertEqual(field, replacer.model_field)

    def test_deletor_job01(self):
        "No replacement."
        user = self.get_root_user()

        civ = FakeCivility.objects.create(title='Kun')
        contact = FakeContact.objects.create(
            user=user, civility=civ,
            last_name='Hattori', first_name='Hanzo',
        )

        job = self._create_job(user)
        dcom = DeletionCommand.objects.create(
            job=job,
            instance_to_delete=civ,
            replacers=[],
        )
        self.assertEqual(0, dcom.total_count)
        self.assertEqual(0, dcom.updated_count)

        self.assertListEqual(
            [
                _('Deleting «{object}» ({model})').format(
                    object=civ.title, model='Test civility',
                ),
            ],
            deletor_type.get_description(job),
        )
        progress = deletor_type.progress(job)
        self.assertIsNone(progress.percentage)
        self.assertEqual(
            ngettext(
                '{count} entity updated.',
                '{count} entities updated.',
                0
            ).format(count=0),
            progress.label,
        )

        self._execute_job(job)
        self.assertDoesNotExist(civ)

        contact = self.assertStillExists(contact)
        self.assertIsNone(contact.civility)

        self.assertFalse(deletor_type.get_stats(self.refresh(job)))

        job.delete()
        self.assertDoesNotExist(dcom)

    def test_deletor_job02(self):
        "One replacement."
        user = self.get_root_user()

        civ = FakeCivility.objects.first()
        civ2del = FakeCivility.objects.create(title='Kun')

        contact = FakeContact.objects.create(
            user=user, civility=civ2del, last_name='Hattori', first_name='Genzo',
        )

        job = self._create_job(user)
        DeletionCommand.objects.create(
            job=job,
            instance_to_delete=civ2del,
            replacers=[
                FixedValueReplacer(
                    model_field=FakeContact._meta.get_field('civility'),
                    value=civ,
                ),
            ],
            total_count=1,
        )
        progress = deletor_type.progress(job)
        self.assertEqual(0, progress.percentage)
        self.assertFalse(progress.label)

        self._execute_job(job)
        self.assertDoesNotExist(civ2del)
        self.assertEqual(civ, self.refresh(contact).civility)

        self.assertFalse(JobResult.objects.filter(job=job))

        job = self.refresh(job)
        self.assertListEqual(
            [
                ngettext(
                    '{count} entity updated.',
                    '{count} entities updated.',
                    1
                ).format(count=1),
            ],
            deletor_type.get_stats(job),
        )
        progress = deletor_type.progress(job)
        self.assertEqual(100, progress.percentage)
        self.assertFalse(progress.label)

        # NB: we check the description is OK _after_ the instance is deleted
        self.assertListEqual(
            [
                _('Deleting «{object}» ({model})').format(
                    object=civ2del.title, model='Test civility',
                ),
                _('In «{model} - {field}», replace by «{new}»').format(
                    model='Test Contact',
                    field=_('Civility'),
                    new=civ.title,
                ),
            ],
            deletor_type.get_description(job),
        )

    def test_deletor_job03(self):
        "Several Replacement."
        user = self.get_root_user()

        civ = FakeCivility.objects.first()
        civ2del = FakeCivility.objects.create(title='Kun')

        create_contact = partial(FakeContact.objects.create, user=user, civility=civ2del)
        contact1 = create_contact(last_name='Hattori', first_name='Genzo')
        contact2 = create_contact(last_name='Hattori', first_name='Hanzo')

        job = self._create_job(user)
        DeletionCommand.objects.create(
            job=job,
            instance_to_delete=civ2del,
            replacers=[
                FixedValueReplacer(
                    model_field=FakeContact._meta.get_field('civility'),
                    value=civ,
                ),
            ],
        )

        self._execute_job(job)
        self.assertDoesNotExist(civ2del)
        self.assertEqual(civ, self.refresh(contact1).civility)
        self.assertEqual(civ, self.refresh(contact2).civility)

        self.assertFalse(JobResult.objects.filter(job=job))

        job = self.refresh(job)
        self.assertListEqual(
            [
                ngettext(
                    '{count} entity updated.',
                    '{count} entities updated.',
                    2
                ).format(count=2),
            ],
            deletor_type.get_stats(job),
        )

    def test_deletor_job04(self):
        "No replacement + exception."
        user = self.get_root_user()
        sector = FakeSector.objects.create(title='Ninja')
        orga = FakeOrganisation.objects.create(
            user=user, sector=sector, name='Hattori clan',
        )

        job = self._create_job(user)
        DeletionCommand.objects.create(
            job=job,
            instance_to_delete=sector,
            replacers=[],
        )

        self._execute_job(job)
        self.assertStillExists(sector)
        self.assertEqual(sector, self.refresh(orga).sector)

        jresult = self.get_object_or_fail(JobResult, job=job)
        self.assertListEqual(
            [
                _(
                    '«{instance}» can not be deleted because of its '
                    'dependencies: {dependencies}'
                ).format(
                    instance=sector,
                    dependencies=_('{count} {model}').format(
                        count=1,
                        model=smart_model_verbose_name(FakeOrganisation, 1),
                    ),
                ),
            ],
            jresult.messages,
        )
