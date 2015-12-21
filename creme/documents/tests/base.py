# -*- coding: utf-8 -*-

# from os import remove as delete_file, listdir, makedirs
from os.path import basename  # join, exists
from tempfile import NamedTemporaryFile
from unittest import skipIf

# from django.conf import settings
from django.core.urlresolvers import reverse

from creme.creme_core.tests.base import CremeTestCase

# from ..models import Folder, Document

try:
    from .. import (document_model_is_custom, folder_model_is_custom,
            get_document_model, get_folder_model)

    skip_document_tests = document_model_is_custom()
    skip_folder_tests   = folder_model_is_custom()

    Document = get_document_model()
    Folder = get_folder_model()
except Exception as e:
    print('Error in <%s>: %s' % (__name__, e))

    skip_document_tests = skip_folder_tests = False


def skipIfCustomDocument(test_func):
    return skipIf(skip_document_tests, 'Custom document model in use')(test_func)


def skipIfCustomFolder(test_func):
    return skipIf(skip_folder_tests, 'Custom folder model in use')(test_func)


class _DocumentsTestCase(CremeTestCase):
    clean_files_in_teardown = True # see CremeTestCase
    #ADD_DOC_URL = '/documents/document/add'

    @classmethod
    def setUpClass(cls):
        CremeTestCase.setUpClass()
        cls.populate('creme_core', 'documents')

#        cls.dir_path = dir_path = join(settings.MEDIA_ROOT, 'upload', 'documents')
#
#        if exists(dir_path):
#            cls.existing_files = set(listdir(dir_path))
#        else:
#            makedirs(dir_path, 0755)
#            cls.existing_files = set()

        cls.ADD_DOC_URL = reverse('documents__create_document')

#    def tearDown(self):
#        dir_path = self.dir_path
#        existing_files = self.existing_files
#
#        for filename in listdir(dir_path):
#            if filename not in existing_files:
#                delete_file(join(dir_path, filename))

    def _build_filedata(self, content_str, suffix='.txt'):
        tmpfile = NamedTemporaryFile(suffix=suffix, delete=False)
        tmpfile.write(content_str)
        tmpfile.flush()

        # We close and reopen in order to have a file with the right name (so we must specify delete=False)
        tmpfile.close()

        name = tmpfile.name

        return open(name, 'rb'), basename(name)

    def _create_doc(self, title, file_obj=None, folder=None, description=None):
        file_obj = file_obj or self._build_filedata('%s : Content' % title)[0]
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

#        return response
        return self.get_object_or_fail(Document, title=title)
