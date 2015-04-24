# -*- coding: utf-8 -*-

try:
    from tempfile import NamedTemporaryFile
    from unittest import skipIf

    from django.contrib.contenttypes.models import ContentType
    from django.core.urlresolvers import reverse

    from ..base import CremeTestCase
    from creme.creme_core.auth.entity_credentials import EntityCredentials
    from creme.creme_core.models import SetCredentials

    from creme.documents.models import Document, Folder, FolderCategory
except Exception as e:
    print('Error in <%s>: %s' % (__name__, e))

try:
    from creme.creme_core.utils.xlwt_utils import XlwtWriter
    from creme.creme_core.registry import import_backend_registry
    no_XLS_lib = 'xls' not in import_backend_registry.iterkeys()
except:
    no_XLS_lib = True


def skipIfNoXLSLib(test_func):
    return skipIf(no_XLS_lib, "Skip tests, couldn't find xlwt or xlrd libs")(test_func)


class ViewsTestCase(CremeTestCase):
    def login(self, is_superuser=True, *args, **kwargs):
        user = super(ViewsTestCase, self).login(is_superuser, *args, **kwargs)

        SetCredentials.objects.create(role=self.role,
                                      value=EntityCredentials.VIEW   |
                                            EntityCredentials.CHANGE |
                                            EntityCredentials.DELETE |
                                            EntityCredentials.LINK   |
                                            EntityCredentials.UNLINK,
                                      set_type=SetCredentials.ESET_OWN
                                     )

        return user

    def _set_all_creds_except_one(self, excluded): #TODO: in CremeTestCase ?
        value = EntityCredentials.NONE

        for cred in (EntityCredentials.VIEW, EntityCredentials.CHANGE,
                     EntityCredentials.DELETE, EntityCredentials.LINK,
                     EntityCredentials.UNLINK):
            if cred != excluded:
                value |= cred

        SetCredentials.objects.create(role=self.user.role, value=value,
                                      set_type=SetCredentials.ESET_ALL
                                     )


class CSVImportBaseTestCaseMixin(object):
    clean_files_in_teardown = True #see CremeTestCase

    def _build_file(self, content, extension=None):
        tmpfile = NamedTemporaryFile(suffix=".%s" % extension if extension else '')
        tmpfile.write(content)
        tmpfile.flush()

        return tmpfile

    def _build_doc(self, tmpfile):
        tmpfile.file.seek(0)
        category = FolderCategory.objects.create(id=10, name=u'Test category')
        folder = Folder.objects.create(user=self.user, title=u'Test folder',
                                       parent_folder=None,
                                       category=category,
                                      )

        title = 'Test doc'
#        response = self.client.post('/documents/document/add', follow=True,
        response = self.client.post(reverse('documents__create_document'), follow=True,
                                    data={'user':        self.user.id,
                                          'title':       title,
                                          'description': 'CSV file for contacts',
                                          'filedata':    tmpfile,
                                          'folder':      folder.id,
                                         }
                                   )
        self.assertNoFormError(response)

        with self.assertNoException():
            doc = Document.objects.get(title=title)

        return doc

    def _build_csv_doc(self, lines, separator=',', extension='csv'):
        content = u'\n'.join(separator.join(u'"%s"' % item for item in line) for line in lines)
        content = str(content.encode('utf8'))

        tmpfile = self._build_file(content, extension)

        return self._build_doc(tmpfile)

    def _build_xls_doc(self, lines, extension='xls'):
        tmpfile = self._build_file('', extension)
        wb = XlwtWriter()
        for line in lines:
            wb.writerow(line)
        wb.save(tmpfile.name)

        return self._build_doc(tmpfile)

    def _build_import_url(self, model):
        ct = ContentType.objects.get_for_model(model)
        return '/creme_core/list_view/import/%s?list_url=%s' % (ct.id, model.get_lv_absolute_url())
