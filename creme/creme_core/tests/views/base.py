import warnings
from tempfile import NamedTemporaryFile

from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from django.utils.translation import gettext as _

from creme.creme_core.auth.entity_credentials import EntityCredentials
from creme.creme_core.creme_jobs.mass_import import mass_import_type
from creme.creme_core.models import MassImportJobResult, SetCredentials
from creme.creme_core.utils.translation import plural
from creme.creme_core.utils.xlwt_utils import XlwtWriter
from creme.documents.models import Document, Folder, FolderCategory

from ..base import CremeTestCase


class ViewsTestCase(CremeTestCase):
    # def login(self, is_superuser=True, *args, **kwargs):
    #     user = super().login(is_superuser, *args, **kwargs)
    #
    #     SetCredentials.objects.create(
    #         role=self.role,
    #         value=(
    #             EntityCredentials.VIEW
    #             | EntityCredentials.CHANGE
    #             | EntityCredentials.DELETE
    #             | EntityCredentials.LINK
    #             | EntityCredentials.UNLINK
    #         ),
    #         set_type=SetCredentials.ESET_OWN,
    #     )
    #
    #     return user

    # TODO: in CremeTestCase ?
    def _set_all_perms_on_own(self, user):
        SetCredentials.objects.create(
            role=user.role,
            value=(
                EntityCredentials.VIEW
                | EntityCredentials.CHANGE
                | EntityCredentials.DELETE
                | EntityCredentials.LINK
                | EntityCredentials.UNLINK
            ),
            set_type=SetCredentials.ESET_OWN,
        )

    # TODO: in CremeTestCase ?
    # def _set_all_creds_except_one(self, excluded):
    def _set_all_creds_except_one(self, *, user, excluded):
        value = EntityCredentials.NONE

        for cred in (
                EntityCredentials.VIEW,
                EntityCredentials.CHANGE,
                EntityCredentials.DELETE,
                EntityCredentials.LINK,
                EntityCredentials.UNLINK,
        ):
            if cred != excluded:
                value |= cred

        SetCredentials.objects.create(
            # role=self.user.role, value=value,
            role=user.role, value=value,
            set_type=SetCredentials.ESET_ALL,
        )


class BrickTestCaseMixin:
    # def get_brick_node(self, tree, brick_id):
    def get_brick_node(self, tree, brick):
        # brick_id = getattr(brick, 'id_', brick)
        brick_id = getattr(brick, 'id', brick)

        brick_node = tree.find(f".//div[@id='{brick_id}']")
        if brick_node is None:
            self.fail(f'The brick id="{brick_id}" is not found.')

        classes = brick_node.attrib.get('class')
        if classes is None:
            self.fail(
                f'The brick id="{brick_id}" is not a valid brick (no "class" attribute).'
            )

        if 'brick' not in classes.split():
            self.fail(
                f'The brick id="{brick_id}" is not a valid brick (no "brick" class).'
            )

        return brick_node

    def assertNoBrick(self, tree, brick_id):
        if tree.find(f".//div[@id='{brick_id}']") is not None:
            self.fail(
                f'The brick id="{brick_id}" has been unexpectedly found.'
            )

    def assertInstanceLink(self, brick_node, entity):
        link_node = self.get_html_node_or_fail(
            brick_node, f".//a[@href='{entity.get_absolute_url()}']"
        )
        self.assertEqual(str(entity), link_node.text)

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
    def iter_instance_button_nodes(instances_button_node, *, data_action=None):
        for a_node in instances_button_node.findall('.//a'):
            classes_attr = a_node.attrib.get('class')
            if classes_attr is None:
                continue

            if (
                'menu_button' in classes_attr.split()
                and (
                    not data_action
                    or data_action == a_node.attrib.get('data-action')
                )
            ):
                yield a_node

        for span_node in instances_button_node.findall('.//span'):
            classes_attr = span_node.attrib.get('class')
            if classes_attr and 'menu_button' in classes_attr.split():
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

    def _build_doc(self, tmpfile, user=None):
        if user is None:
            warnings.warn(
                f'Passing no "user" argument to the methods '
                f'{type(self).__name__}._build_*doc() is deprecated.',
                DeprecationWarning
            )

            user = self.user

        tmpfile.file.seek(0)
        category = FolderCategory.objects.create(id=10, name='Test category')
        folder = Folder.objects.create(
            user=user, title='Test folder',
            parent_folder=None,
            category=category,
        )

        title = 'Test doc'
        response = self.client.post(
            reverse('documents__create_document'), follow=True,
            data={
                'user':          user.id,
                'title':         title,
                'description':   'CSV file for contacts',
                'filedata':      tmpfile,
                'linked_folder': folder.id,
            },
        )
        self.assertNoFormError(response)

        with self.assertNoException():
            doc = Document.objects.get(title=title)

        return doc

    # def _build_csv_doc(self, lines, separator=',', extension='csv'):
    def _build_csv_doc(self, lines, *, user=None, separator=',', extension='csv'):
        content = '\n'.join(
            separator.join(f'"{item}"' for item in line) for line in lines
        )
        tmpfile = self._build_file(content.encode(), extension)

        return self._build_doc(tmpfile, user=user)

    # def _build_xls_doc(self, lines, extension='xls'):
    def _build_xls_doc(self, lines, *, user=None, extension='xls'):
        tmpfile = self._build_file(b'', extension)
        wb = XlwtWriter()
        for line in lines:
            wb.writerow(line)
        wb.save(tmpfile.name)

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
