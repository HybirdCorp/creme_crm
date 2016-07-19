# -*- coding: utf-8 -*-

from os.path import basename
from tempfile import NamedTemporaryFile
from unittest import skipIf

from django.core.urlresolvers import reverse

from creme.creme_core.tests.base import CremeTestCase

try:
    from creme import documents

    skip_document_tests = documents.document_model_is_custom()
    skip_folder_tests   = documents.folder_model_is_custom()

    Document = documents.get_document_model()
    Folder = documents.get_folder_model()
except Exception as e:
    print('Error in <%s>: %s' % (__name__, e))

    skip_document_tests = skip_folder_tests = False


def skipIfCustomDocument(test_func):
    return skipIf(skip_document_tests, 'Custom document model in use')(test_func)


def skipIfCustomFolder(test_func):
    return skipIf(skip_folder_tests, 'Custom folder model in use')(test_func)


class _DocumentsTestCase(CremeTestCase):
    clean_files_in_teardown = True  # see CremeTestCase

    @classmethod
    def setUpClass(cls):
        CremeTestCase.setUpClass()
        # cls.populate('creme_core', 'documents')
        cls.ADD_DOC_URL = reverse('documents__create_document')

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

        return self.get_object_or_fail(Document, title=title)
