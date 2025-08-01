import logging
from random import randint
from tempfile import NamedTemporaryFile
from xml.etree import ElementTree

import openpyxl
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from django.utils.translation import gettext as _

from creme.creme_core.creme_jobs.mass_import import mass_import_type
from creme.creme_core.gui.bricks import Brick
from creme.creme_core.models import MassImportJobResult
from creme.creme_core.utils.translation import plural
from creme.creme_core.utils.xlwt_utils import XlwtWriter
from creme.documents.models import Document, Folder, FolderCategory

logger = logging.getLogger(__name__)


class AppPermissionBrick(Brick):
    id = Brick.generate_id('creme_core', 'test_views_generic')
    verbose_name = 'Block which need "persons" permission'
    permissions = ['persons']

    detail_str = '<div id="brick-{id}" data-brick-id="{id}" class="brick">DETAIL</div>'
    home_str = '<div id="brick-{id}" data-brick-id="{id}" class="brick">HOME</div>'

    def detailview_display(self, context):
        return self.detail_str.format(id=self.id)

    def home_display(self, context):
        return self.home_str.format(id=self.id)


class BrickTestCaseMixin:
    def get_brick_node(self, tree, brick):
        brick_id = getattr(brick, 'id', brick)

        brick_node = tree.find(f".//div[@id='brick-{brick_id}']")
        if brick_node is None:
            self.fail(f'The brick node id="brick-{brick_id}" is not found.')

        classes = brick_node.attrib.get('class')
        if classes is None:
            self.fail(
                f'The brick node id="brick-{brick_id}" is invalid (no "class" attribute).'
            )

        if 'brick' not in classes.split():
            self.fail(
                f'The brick node id="brick-{brick_id}" is invalid (no "brick" class).'
            )

        return brick_node

    def assertNoBrick(self, tree, brick_id):
        if tree.find(f".//div[@id='brick-{brick_id}']") is not None:
            self.fail(
                f'The brick node id="brick-{brick_id}" has been unexpectedly found.'
            )

    def assertInstanceLink(self, brick_node, entity, check_text=True):
        link_node = self.get_html_node_or_fail(
            brick_node, f".//a[@href='{entity.get_absolute_url()}']"
        )
        if check_text:
            self.assertEqual(str(entity), link_node.text.strip())

        return link_node

    def assertNoInstanceLink(self, brick_node, entity):
        self.assertIsNone(brick_node.find(f".//a[@href='{entity.get_absolute_url()}']"))

    def assertBrickHasClass(self, brick_node, css_class):
        self.assertIn(css_class, brick_node.attrib.get('class').split())

    def assertBrickHasNotClass(self, brick_node, css_class):
        self.assertNotIn(css_class, brick_node.attrib.get('class').split())

    def get_brick_tile(self, content_node, key):
        tile_node = self.get_html_node_or_fail(content_node, f'.//div[@data-key="{key}"]')

        return self.get_html_node_or_fail(tile_node, './/span[@class="brick-tile-value"]')

    def get_brick_title(self, brick_node):
        return self.get_html_node_or_fail(
            brick_node, './/span[@class="brick-title"]',
        ).text.strip()

    def get_brick_header_buttons(self, brick_node):
        return self.get_html_node_or_fail(brick_node, './/div[@class="brick-header-buttons"]')

    def assertBrickHeaderHasButton(self, buttons_node, url, label):
        button_node = buttons_node.find(f'.//a[@href="{url}"]')
        if button_node is None:
            self.fail(
                'The <a> markup with href="{url}" has not been found '
                '(URLs found: {found}).'.format(
                    url=url,
                    found=', '.join(
                        f'"{a.attrib.get("href")}"'
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

    def assertBrickHasAction(self, brick_node, url, action_type='edit'):
        action_node = brick_node.find(f'.//a[@href="{url}"]')
        if action_node is None:
            self.fail(
                'The <a> markup with href="{url}" has not been found '
                '(URLs found: {found}).'.format(
                    url=url,
                    found=', '.join(
                        '"{}"'.format(a.attrib.get('href'))
                        for a in brick_node.findall('.//a')
                    ),
                )
            )

        css_class = action_node.attrib.get('class')
        self.assertIsNotNone(css_class, 'No attribute "class" found.')
        self.assertIn('brick-action', css_class)
        self.assertIn(f'action-type-{action_type}', css_class)

    def assertBrickHasNoAction(self, brick_node, url):
        for action_node in brick_node.findall(f'.//a[@href="{url}"]'):
            css_class = action_node.attrib.get('class')
            if css_class and 'brick-action' in css_class:
                self.fail(f'The <a> markup with href="{url}" has been unexpectedly found.')

    def assertBrickTitleEqual(self, brick_node, count, title, plural_title):
        self.assertEqual(
            _(plural_title if plural(count) else title).format(count=count),
            self.get_brick_title(brick_node),
        )

    def get_brick_table_column_titles(self, brick_node):
        row_node = self.get_html_node_or_fail(
            brick_node, './/table[@class="brick-table-content"]/thead/tr'
        )

        return [span.text for span in row_node.findall('.//th/span')]

    def get_brick_table_rows(self, brick_node):
        body_node = self.get_html_node_or_fail(
            brick_node, './/table[@class="brick-table-content"]/tbody'
        )
        return body_node.findall('.//tr')


class ButtonTestCaseMixin:
    def get_global_buttons_node(self, tree):
        for div_node in tree.findall('.//div'):
            classes_attr = div_node.attrib.get('class')
            if classes_attr is None:
                continue

            classes = classes_attr.split()
            if 'buttons-list' in classes and 'global-buttons' in classes:
                return div_node

        self.fail('The global buttons node has not been found.')

    def get_instance_buttons_node(self, tree):
        for div_node in tree.findall('.//div'):
            classes_attr = div_node.attrib.get('class')
            if classes_attr is None:
                continue

            classes = classes_attr.split()
            if 'buttons-list' in classes and 'instance-buttons' in classes:
                return div_node

        self.fail('The instance buttons node has not been found.')

    @staticmethod
    def iter_button_nodes(buttons_node, *, tags=('a', 'span'), data_action=None, href=None):
        if 'a' in tags:
            for a_node in buttons_node.findall('.//a'):
                classes_attr = a_node.attrib.get('class')
                if classes_attr:
                    if (
                        'menu_button' in classes_attr.split()
                        and (
                            not data_action
                            or data_action == a_node.attrib.get('data-action')
                        ) and (
                            href is None
                            or href == a_node.attrib.get('href')
                        )
                    ):
                        yield a_node

        if 'span' in tags:
            for span_node in buttons_node.findall('.//span'):
                classes_attr = span_node.attrib.get('class')
                if classes_attr:
                    classes = classes_attr.split()
                    if 'menu_button' in classes:
                        if 'forbidden' not in classes:
                            logger.warning(
                                'A <span> button without "forbidden" class has been found: %s',
                                ElementTree.tostring(span_node),
                            )

                        yield span_node


class MassImportBaseTestCaseMixin:
    def _assertNoResultError(self, results):
        for r in results:
            if r.messages:
                self.fail(f'Import error: {r.messages}')

    @staticmethod
    def _build_file(content, extension=None):
        tmpfile = NamedTemporaryFile(suffix=f'.{extension}' if extension else '')
        tmpfile.write(content)
        tmpfile.flush()

        return tmpfile

    def _build_doc(self, tmpfile, user):
        tmpfile.file.seek(0)
        category = FolderCategory.objects.get_or_create(name='Test category')[0]
        folder = Folder.objects.create(
            user=user, title='Test folder',
            parent_folder=None,
            category=category,
        )

        title = f'Test doc #{randint(0, 1000):04}'
        response = self.client.post(
            reverse('documents__create_document'),
            follow=True,
            data={
                'user':          user.id,
                'title':         title,
                'description':   'CSV file for contacts',
                'filedata':      tmpfile,
                'linked_folder': folder.id,
            },
        )
        self.assertNoFormError(response)

        return self.get_object_or_fail(Document, title=title)

    def _build_csv_doc(self, lines, *, user, separator=',', extension='csv'):
        content = '\n'.join(
            separator.join(f'"{item}"' for item in line) for line in lines
        )
        tmpfile = self._build_file(content.encode(), extension)

        return self._build_doc(tmpfile, user=user)

    def _build_xls_doc(self, lines, *, user, extension='xls'):
        tmpfile = self._build_file(b'', extension)
        wb = XlwtWriter()
        for line in lines:
            wb.writerow(line)
        wb.save(tmpfile.name)

        return self._build_doc(tmpfile, user=user)

    def _build_xlsx_doc(self, lines, *, user, extension='xlsx'):
        tmpfile = self._build_file(b'', extension)
        workbook = openpyxl.Workbook()

        append = workbook.active.append
        for line in lines:
            append(line)
        workbook.save(tmpfile.name)

        return self._build_doc(tmpfile, user=user)

    @staticmethod
    def _build_import_url(model):
        ct = ContentType.objects.get_for_model(model)
        return reverse('creme_core__mass_import', args=(ct.id,))

    def _get_job(self, response):
        with self.assertNoException():
            return response.context['job']

    @staticmethod
    def _get_job_results(job):
        return MassImportJobResult.objects.filter(job=job)

    def _execute_job(self, response):
        job = self._get_job(response)
        mass_import_type.execute(job)

        return job
