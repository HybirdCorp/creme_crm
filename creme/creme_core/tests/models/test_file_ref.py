# -*- coding: utf-8 -*-

try:
    from datetime import timedelta
    from os.path import join, exists, basename

    from django.conf import settings
    from django.db.transaction import atomic

    from .. import base
    from creme.creme_core.creme_jobs import temp_files_cleaner_type
    from creme.creme_core.models import Job, FileRef, FakeFolder, FakeDocument, FakeFileComponent
    from creme.creme_core.utils.date_period import date_period_registry
    from creme.creme_core.utils.file_handling import FileCreator
except Exception as e:
    print('Error in <{}>: {}'.format(__name__, e))


def _create_file(name):
    rel_media_dir_path = join('upload', 'creme_core-tests', 'models')
    final_path = FileCreator(join(settings.MEDIA_ROOT, rel_media_dir_path), name).create()

    with open(final_path, 'w') as f:
        f.write('I am the content')

    return join(rel_media_dir_path, basename(final_path))


class FileRefTestCase(base.CremeTestCase):
    def _get_job(self, days=1):
        job = self.get_object_or_fail(Job, type_id=temp_files_cleaner_type.id)
        job.data = {'delay': date_period_registry.get_period('days', days).as_dict()}
        job.save()

        return job

    def _oldify_temp_file(self, temp_file, days):
        "Make the instance older"
        FileRef.objects \
               .filter(id=temp_file.id) \
               .update(created=temp_file.created
                               - date_period_registry.get_period('days', days).as_timedelta()
                               - timedelta(hours=1)
                      )

    def test_basename01(self):
        path = _create_file('FileRefTestCase_test_basename01.txt')

        with self.assertNoException():
            FileRef.objects.create(filedata=path, basename='test_basename01.txt')

    def test_basename02(self):
        name = 'FileRefTestCase_test_basename02.txt'
        path = _create_file(name)

        with self.assertNoException():
            file_ref = FileRef.objects.create(filedata=path)

        self.assertEqual(name, file_ref.basename)

    def test_job01(self):
        "File is too young to be deleted (just created)"
        job = self._get_job(days=1)
        path = _create_file('FileRefTestCase_test_job01.txt')
        temp_file = FileRef.objects.create(filedata=path)
        self.assertIs(temp_file.temporary, True)
        self.assertIsNone(temp_file.user)

        temp_files_cleaner_type.execute(job)
        self.assertStillExists(temp_file)
        self.assertTrue(exists(temp_file.filedata.path))

    def test_job02(self):
        "File is old enough to be deleted"
        days = 1
        job = self._get_job(days=days)
        path = _create_file('FileRefTestCase_test_job02.txt')
        file_ref = FileRef.objects.create(filedata=path)
        full_path = file_ref.filedata.path

        self._oldify_temp_file(file_ref, days)

        temp_files_cleaner_type.execute(job)
        self.assertDoesNotExist(file_ref)
        self.assertFalse(exists(full_path))

    def test_job03(self):
        "File is too young to be deleted"
        job = self._get_job(days=2)
        path = _create_file('FileRefTestCase_test_job03.txt')
        file_ref = FileRef.objects.create(filedata=path)

        self._oldify_temp_file(file_ref, days=1)

        temp_files_cleaner_type.execute(job)
        self.assertStillExists(file_ref)

    def test_job04(self):
        "File is not temporary"
        job = self._get_job(days=1)
        path = _create_file('FileRefTestCase_test_job04.txt')
        file_ref = FileRef.objects.create(filedata=path, temporary=False)

        self._oldify_temp_file(file_ref, days=2)

        temp_files_cleaner_type.execute(job)
        self.assertStillExists(file_ref)

    def test_create_at_deletion01(self):
        user = self.login()

        existing_ids = [*FileRef.objects.values_list('id', flat=True)]
        path = _create_file('FileRefTestCase_test_create_at_deletion.txt')

        folder = FakeFolder.objects.create(user=user, title='X-files')
        doc = FakeDocument.objects.create(user=user, title='Roswell.txt', linked_folder=folder, filedata=path)

        full_path = doc.filedata.path

        doc.delete()
        self.assertDoesNotExist(doc)

        file_refs = FileRef.objects.exclude(id__in=existing_ids)
        self.assertEqual(1, len(file_refs))

        file_ref = file_refs[0]
        self.assertTrue(file_ref.temporary)
        self.assertIsNone(file_ref.user)
        self.assertEqual(full_path, file_ref.filedata.path)
        self.assertTrue(exists(full_path))

    def test_create_at_deletion02(self):
        "Empty FileField."
        existing_ids = [*FileRef.objects.values_list('id', flat=True)]
        embed_doc = FakeFileComponent.objects.create()
        self.assertNoException(embed_doc.delete)
        self.assertFalse(FileRef.objects.exclude(id__in=existing_ids))


class FileRefTestDeleteCase(base.CremeTransactionTestCase):
    def test_delete_model_with_file01(self):
        user = self.login()

        existing_ids = [*FileRef.objects.values_list('id', flat=True)]
        path = _create_file('FileRefTestDeleteCase_test_delete_model_with_file01.txt')

        folder = FakeFolder.objects.create(user=user, title='X-files')
        doc = FakeDocument.objects.create(user=user, title='Roswell.txt', linked_folder=folder, filedata=path)

        full_path = doc.filedata.path

        with atomic():
            doc.delete()

        self.assertDoesNotExist(doc)

        file_refs = FileRef.objects.exclude(id__in=existing_ids)
        self.assertEqual(1, len(file_refs))

        file_ref = file_refs[0]
        self.assertTrue(file_ref.temporary)
        self.assertIsNone(file_ref.user)
        self.assertEqual(full_path, file_ref.filedata.path)
        self.assertTrue(exists(full_path))

    def test_delete_model_with_file02(self):
        user = self.login()

        existing_ids = [*FileRef.objects.values_list('id', flat=True)]
        path = _create_file('FileRefTestDeleteCase_test_delete_model_with_file02.txt')

        folder = FakeFolder.objects.create(user=user, title='X-files')
        doc = FakeDocument.objects.create(user=user, title='Roswell.txt', linked_folder=folder, filedata=path)

        full_path = doc.filedata.path

        try:
            with atomic():
                doc.delete()
                raise ValueError('I cause rollback')
        except ValueError:
            pass

        doc = self.get_object_or_fail(FakeDocument, id=doc.id)
        self.assertEqual(full_path, doc.filedata.path)
        self.assertTrue(exists(full_path))

        self.assertFalse(FileRef.objects.exclude(id__in=existing_ids))
