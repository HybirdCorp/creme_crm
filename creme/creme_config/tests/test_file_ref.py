from django.urls import reverse
from django.utils.translation import gettext as _
from django.utils.translation import pgettext

from creme.creme_config.bricks import FileRefsBrick
from creme.creme_core.models import FileRef
from creme.creme_core.tests.base import CremeTestCase
from creme.creme_core.tests.views.base import BrickTestCaseMixin


class FileRefTestCase(BrickTestCaseMixin, CremeTestCase):
    PORTAL_URL = reverse('creme_config__file_refs')

    def test_portal(self):
        self.login_as_super(is_staff=True)
        path = self.create_uploaded_file(
            file_name='FileRefTestCase_test_portal.txt',
            dir_name='models',
        )
        FileRef.objects.create(filedata=path, user=self.get_root_user())

        response = self.assertGET200(self.PORTAL_URL)
        self.assertTemplateUsed(response, 'creme_config/portals/file-ref.html')

        reload_url = reverse('creme_core__reload_bricks')
        self.assertEqual(reload_url, response.context.get('bricks_reload_url'))

        brick_node1 = self.get_brick_node(
            self.get_html_tree(response.content), brick=FileRefsBrick,
        )
        self.assertBrickTitleEqual(
            brick_node1,
            count=1,
            title='{count} Temporary file',
            plural_title='{count} Temporary files',
        )
        self.assertListEqual(
            [
                pgettext('creme_core-temporary_file', 'Created'),
                _('Owner user'), _('Path'),
                _('To be deleted by the job?'), _('Description'), _('Actions'),
            ],
            self.get_brick_table_column_titles(brick_node1),
        )
        rows = self.get_brick_table_rows(brick_node1)
        table_cells = self.get_alone_element(rows).findall('.//td')
        self.assertEqual(6, len(table_cells))
        self.assertEqual(path, table_cells[2].text)

        # Reload ---
        rl_data = self.assertGET200(
            reload_url,
            data={'brick_id': [FileRefsBrick.id]},
        ).json()
        self.assertIsList(rl_data, length=1)

        brick_data = rl_data[0]
        self.assertEqual(FileRefsBrick.id, brick_data[0])

        brick_node2 = self.get_brick_node(
            self.get_html_tree(brick_data[1]), brick=FileRefsBrick,
        )
        self.assertBrickTitleEqual(
            brick_node2,
            count=1,
            title='{count} Temporary file',
            plural_title='{count} Temporary files',
        )

    def test_portal__not_staff(self):
        self.login_as_root()
        self.assertGET403(self.PORTAL_URL)

        # Reload ---
        rl_data = self.assertGET200(
            reverse('creme_core__reload_bricks'),
            data={'brick_id': [FileRefsBrick.id]},
        ).json()
        self.assertIsList(rl_data, length=1)

        brick_data = rl_data[0]
        self.assertEqual(FileRefsBrick.id, brick_data[0])

        brick_node = self.get_brick_node(
            self.get_html_tree(brick_data[1]), brick=FileRefsBrick,
        )
        # TODO: method?
        self.assertIn('brick-forbidden', brick_node.attrib.get('class'))
