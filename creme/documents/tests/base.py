 # -*- coding: utf-8 -*-

from os import remove as delete_file, listdir, makedirs
from os.path import basename, join, exists
from tempfile import NamedTemporaryFile

from django.conf import settings

from creme_core.tests.base import CremeTestCase

from documents.models import Folder


class _DocumentsTestCase(CremeTestCase):
    ADD_DOC_URL = '/documents/document/add'

    @classmethod
    def setUpClass(cls):
        cls.populate('creme_core', 'creme_config', 'documents')

        cls.dir_path = dir_path = join(settings.MEDIA_ROOT, 'upload', 'documents')

        if exists(dir_path):
            cls.existing_files = set(listdir(dir_path))
        else:
            makedirs(dir_path, 0755)
            cls.existing_files = set()

    def tearDown(self):
        dir_path = self.dir_path
        existing_files = self.existing_files

        for filename in listdir(dir_path):
            if filename not in existing_files:
                delete_file(join(dir_path, filename))

    def _build_filedata(self, content_str, suffix='.txt'):
        tmpfile = NamedTemporaryFile(suffix=suffix, delete=False)
        tmpfile.write(content_str)
        tmpfile.flush()

        #we close and reopen in order to have a file with the right name (so we must specify delete=False)
        tmpfile.close()

        name = tmpfile.name

        return open(name, 'rb'), basename(name)

    def _create_doc(self, title, file_obj, folder=None, description=None):
        folder = folder or Folder.objects.all()[0]
        data = {'user':     self.user.pk,
                'title':    title,
                'filedata': file_obj,
                'folder':   folder.id,
               }

        if description is not None:
            data['description'] = description

        response = self.client.post(self.ADD_DOC_URL, follow=True, data=data)
        self.assertNoFormError(response)

        return response
