# -*- coding: utf-8 -*-

from tempfile import NamedTemporaryFile

from bleach._vendor import html5lib
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse

from creme.creme_core.auth.entity_credentials import EntityCredentials
from creme.creme_core.creme_jobs.mass_import import mass_import_type
from creme.creme_core.models import MassImportJobResult, SetCredentials
from creme.creme_core.utils.xlwt_utils import XlwtWriter
from creme.documents.models import Document, Folder, FolderCategory

from ..base import CremeTestCase


class ViewsTestCase(CremeTestCase):
    def login(self, is_superuser=True, *args, **kwargs):
        user = super().login(is_superuser, *args, **kwargs)

        SetCredentials.objects.create(
            role=self.role,
            value=(
                EntityCredentials.VIEW | EntityCredentials.CHANGE | EntityCredentials.DELETE |
                EntityCredentials.LINK | EntityCredentials.UNLINK
            ),
            set_type=SetCredentials.ESET_OWN,
        )

        return user

    def _set_all_creds_except_one(self, excluded):  # TODO: in CremeTestCase ?
        value = EntityCredentials.NONE

        for cred in (EntityCredentials.VIEW, EntityCredentials.CHANGE,
                     EntityCredentials.DELETE, EntityCredentials.LINK,
                     EntityCredentials.UNLINK):
            if cred != excluded:
                value |= cred

        SetCredentials.objects.create(role=self.user.role, value=value,
                                      set_type=SetCredentials.ESET_ALL,
                                     )


class BrickTestCaseMixin:
    def get_html_tree(self, content):
        return html5lib.parse(content, namespaceHTMLElements=False)

    def get_brick_node(self, tree, brick_id):
        brick_node = tree.find(f".//div[@id='{brick_id}']")
        self.assertIsNotNone(brick_node, f'The brick id="{brick_id}" is not found.')

        classes = brick_node.attrib.get('class')
        self.assertIsNotNone(
            classes,
            f'The brick id="{brick_id}" is not a valid brick (no "class" attribute).'
        )
        self.assertIn(
            'brick', classes.split(),
            f'The brick id="{brick_id}" is not a valid brick (no "brick" class).'
        )

        return brick_node

    def assertNoBrick(self, tree, brick_id):
        self.assertIsNone(
            tree.find(f".//div[@id='{brick_id}']"),
            f'The brick id="{brick_id}" has been unexpectedly found.'
        )

    def assertInstanceLink(self, brick_node, entity):
        link_node = brick_node.find(f".//a[@href='{entity.get_absolute_url()}']")
        self.assertIsNotNone(link_node)
        self.assertEqual(str(entity), link_node.text)

    def assertNoInstanceLink(self, brick_node, entity):
        self.assertIsNone(brick_node.find(f".//a[@href='{entity.get_absolute_url()}']"))

    def assertBrickHasClass(self, brick_node, css_class):
        self.assertIn(css_class, brick_node.attrib.get('class').split())

    def assertBrickHasNotClass(self, brick_node, css_class):
        self.assertNotIn(css_class, brick_node.attrib.get('class').split())

    def get_brick_tile(self, content_node, key):
        tile_node = content_node.find(f'.//div[@data-key="{key}"]')
        self.assertIsNotNone(tile_node)

        value_node = tile_node.find('.//span[@class="brick-tile-value"]')
        self.assertIsNotNone(value_node)

        return value_node

    def get_brick_title(self, brick_node):
        span_node = brick_node.find('.//span[@class="brick-title"]')
        self.assertIsNotNone(span_node)

        return span_node.text.strip()

    def get_brick_header_buttons(self, brick_node):
        buttons_node = brick_node.find('.//div[@class="brick-header-buttons"]')
        self.assertIsNotNone(buttons_node)

        return buttons_node

    def assertBrickHeaderHasButton(self, buttons_node, url, label):
        button_node = buttons_node.find(f'.//a[@href="{url}"]')
        if button_node is None:
            self.fail(
                'The <a> markup with href="{url}" has not been found (URLs found: {found}).'.format(
                    url=url,
                    found=', '.join(
                        '"{}"'.format(a.attrib.get('href'))
                        for a in buttons_node.findall('.//a')
                    ),
                )
            )

        button_label = button_node.attrib.get('title')  # TODO: get the inner-span instead ?
        if label != button_label:
            self.fail(
                f'The button has been found but with a different label:\n'
                f'Expected: {label}\n'
                f'Found: {button_label}'
            )

    def assertBrickHeaderHasNoButton(self, buttons_node, url):
        button_node = buttons_node.find(f'.//a[@href="{url}"]')
        if button_node is not None:
            self.fail(f'The <a> markup with href="{url}" has been unexpectedly found.')


# class CSVImportBaseTestCaseMixin:
class MassImportBaseTestCaseMixin:
    def _assertNoResultError(self, results):
        for r in results:
            if r.messages:
                self.fail(f'Import error: {r.messages}')

    def _build_file(self, content, extension=None):
        tmpfile = NamedTemporaryFile(suffix=".%s" % extension if extension else '')
        tmpfile.write(content)
        tmpfile.flush()

        return tmpfile

    def _build_doc(self, tmpfile):
        tmpfile.file.seek(0)
        category = FolderCategory.objects.create(id=10, name='Test category')
        folder = Folder.objects.create(user=self.user, title='Test folder',
                                       parent_folder=None,
                                       category=category,
                                      )

        title = 'Test doc'
        response = self.client.post(reverse('documents__create_document'), follow=True,
                                    data={'user':        self.user.id,
                                          'title':       title,
                                          'description': 'CSV file for contacts',
                                          'filedata':    tmpfile,
                                          'linked_folder': folder.id,
                                         },
                                   )
        self.assertNoFormError(response)

        with self.assertNoException():
            doc = Document.objects.get(title=title)

        return doc

    def _build_csv_doc(self, lines, separator=',', extension='csv'):
        content = '\n'.join(separator.join(f'"{item}"' for item in line) for line in lines)
        tmpfile = self._build_file(content.encode(), extension)

        return self._build_doc(tmpfile)

    def _build_xls_doc(self, lines, extension='xls'):
        tmpfile = self._build_file(b'', extension)
        wb = XlwtWriter()
        for line in lines:
            wb.writerow(line)
        wb.save(tmpfile.name)

        return self._build_doc(tmpfile)

    def _build_import_url(self, model):
        ct = ContentType.objects.get_for_model(model)
        return reverse('creme_core__mass_import', args=(ct.id,))

    def _get_job(self, response):
        with self.assertNoException():
            return response.context['job']

    def _get_job_results(self, job):
        return MassImportJobResult.objects.filter(job=job)

    def _execute_job(self, response):
        job = self._get_job(response)
        mass_import_type.execute(job)

        return job
