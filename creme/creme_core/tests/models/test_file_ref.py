from datetime import timedelta
from math import ceil
from os import path as os_path

from django.db.transaction import atomic
from django.utils.translation import gettext as _

from creme.creme_core.creme_jobs import temp_files_cleaner_type
from creme.creme_core.models import (
    FakeDocument,
    FakeFileComponent,
    FakeFolder,
    FileRef,
    Job,
)
from creme.creme_core.utils.date_period import date_period_registry

from .. import base


class FileRefTestCase(base.CremeTestCase):
    def _get_job(self, days=1):
        job = self.get_object_or_fail(Job, type_id=temp_files_cleaner_type.id)
        job.data = {'delay': date_period_registry.get_period('days', days).as_dict()}
        job.save()

        return job

    @staticmethod
    def _oldify_temp_file(temp_file, days):
        "Make the instance older."
        FileRef.objects.filter(
            id=temp_file.id,
        ).update(
            created=(
                temp_file.created
                - date_period_registry.get_period('days', days).as_timedelta()
                - timedelta(hours=1)
            ),
        )

    def test_basename01(self):
        path = self.create_uploaded_file(
            file_name='FileRefTestCase_test_basename01.txt',
            dir_name='models',
        )

        with self.assertNoException():
            fileref = FileRef.objects.create(filedata=path, basename='test_basename01.txt')

        self.assertEqual('', fileref.description)

    def test_basename02(self):
        name = 'FileRefTestCase_test_basename02.txt'
        path = self.create_uploaded_file(file_name=name, dir_name='models')

        with self.assertNoException():
            file_ref = FileRef.objects.create(filedata=path)

        self.assertEqual(name, file_ref.basename)

    def test_job01(self):
        "File is too young to be deleted (just created)"
        job = self._get_job(days=1)
        path = self.create_uploaded_file(
            file_name='FileRefTestCase_test_job01.txt',
            dir_name='models',
        )
        temp_file = FileRef.objects.create(filedata=path)
        self.assertIs(temp_file.temporary, True)
        self.assertIsNone(temp_file.user)

        temp_files_cleaner_type.execute(job)
        self.assertStillExists(temp_file)
        self.assertTrue(os_path.exists(temp_file.filedata.path))

    def test_job02(self):
        "File is old enough to be deleted."
        days = 1
        job = self._get_job(days=days)
        path = self.create_uploaded_file(
            file_name='FileRefTestCase_test_job02.txt',
            dir_name='models',
        )
        file_ref = FileRef.objects.create(filedata=path)
        full_path = file_ref.filedata.path

        self._oldify_temp_file(file_ref, days)

        temp_files_cleaner_type.execute(job)
        self.assertDoesNotExist(file_ref)
        self.assertFalse(os_path.exists(full_path))

    def test_job03(self):
        "File is too young to be deleted."
        job = self._get_job(days=2)
        path = self.create_uploaded_file(
            file_name='FileRefTestCase_test_job03.txt',
            dir_name='models',
        )
        file_ref = FileRef.objects.create(filedata=path)

        self._oldify_temp_file(file_ref, days=1)

        temp_files_cleaner_type.execute(job)
        self.assertStillExists(file_ref)

    def test_job04(self):
        "File is not temporary."
        job = self._get_job(days=1)
        path = self.create_uploaded_file(
            file_name='FileRefTestCase_test_job04.txt',
            dir_name='models',
        )
        file_ref = FileRef.objects.create(filedata=path, temporary=False)

        self._oldify_temp_file(file_ref, days=2)

        temp_files_cleaner_type.execute(job)
        self.assertStillExists(file_ref)

    def test_create_at_deletion01(self):
        user = self.get_root_user()

        existing_ids = [*FileRef.objects.values_list('id', flat=True)]
        path = self.create_uploaded_file(
            file_name='FileRefTestCase_test_create_at_deletion.txt',
            dir_name='models',
        )

        folder = FakeFolder.objects.create(user=user, title='X-files')
        doc = FakeDocument.objects.create(
            user=user,
            title='Roswell.txt',
            linked_folder=folder,
            filedata=path,
        )

        full_path = doc.filedata.path

        doc.delete()
        self.assertDoesNotExist(doc)

        file_ref = self.get_alone_element(FileRef.objects.exclude(id__in=existing_ids))
        self.assertTrue(file_ref.temporary)
        self.assertIsNone(file_ref.user)
        self.assertEqual(full_path, file_ref.filedata.path)
        self.assertTrue(os_path.exists(full_path))
        self.assertEqual(
            _('Deletion of «{}»').format(doc),
            file_ref.description,
        )

    def test_create_at_deletion02(self):
        "Empty FileField."
        existing_ids = [*FileRef.objects.values_list('id', flat=True)]
        embed_doc = FakeFileComponent.objects.create()
        self.assertNoException(embed_doc.delete)
        self.assertFalse(FileRef.objects.exclude(id__in=existing_ids))


class FileRefTestDeleteCase(base.CremeTransactionTestCase):
    def test_delete_model_with_file01(self):
        user = self.create_user()

        existing_ids = [*FileRef.objects.values_list('id', flat=True)]
        path = self.create_uploaded_file(
            file_name='FileRefTestDeleteCase_test_delete_model_with_file01.txt',
            dir_name='models',
        )

        folder = FakeFolder.objects.create(user=user, title='X-files')
        doc = FakeDocument.objects.create(
            user=user, title='Roswell.txt', linked_folder=folder, filedata=path,
        )

        full_path = doc.filedata.path

        with atomic():
            doc.delete()

        self.assertDoesNotExist(doc)

        file_ref = self.get_alone_element(FileRef.objects.exclude(id__in=existing_ids))
        self.assertTrue(file_ref.temporary)
        self.assertIsNone(file_ref.user)
        self.assertEqual(full_path, file_ref.filedata.path)
        self.assertTrue(os_path.exists(full_path))

    def test_delete_model_with_file02(self):
        user = self.create_user()

        existing_ids = [*FileRef.objects.values_list('id', flat=True)]
        path = self.create_uploaded_file(
            file_name='FileRefTestDeleteCase_test_delete_model_with_file02.txt',
            dir_name='models',
        )

        folder = FakeFolder.objects.create(user=user, title='X-files')
        doc = FakeDocument.objects.create(
            user=user, title='Roswell.txt', linked_folder=folder, filedata=path,
        )

        full_path = doc.filedata.path

        try:
            with atomic():
                doc.delete()
                raise ValueError('I cause rollback')
        except ValueError:
            pass

        doc = self.get_object_or_fail(FakeDocument, id=doc.id)
        self.assertEqual(full_path, doc.filedata.path)
        self.assertTrue(os_path.exists(full_path))

        self.assertFalse(FileRef.objects.exclude(id__in=existing_ids))

    def test_delete_model_with_file__path_too_long(self):
        user = self.create_user()
        old_count = FileRef.objects.count()

        max_length = FileRef._meta.get_field('filedata').max_length
        pattern = '_very'
        pattern_count = ceil(max_length / len(pattern))
        path = os_path.join(
            'creme_core-tests', 'models',
            f'a_file_with_a{pattern * pattern_count}_long_name',
        )

        folder = FakeFolder.objects.create(user=user, title='X-files')
        doc = FakeDocument.objects.create(
            user=user, title='Roswell.txt', linked_folder=folder,
            # filedata=path,
        )

        # NB: too long for the current field, so we assign it in a volatile way
        #     in order the length is not checked
        doc.filedata = path

        with self.assertLogs(level='CRITICAL') as log_cm:
            with atomic():
                doc.delete()

        self.assertDoesNotExist(doc)
        self.assertEqual(old_count, FileRef.objects.count())

        message = self.get_alone_element(log_cm.output)
        self.assertIn(
            'Error while deleting an instance of <FakeDocument>; ',
            message,
        )
