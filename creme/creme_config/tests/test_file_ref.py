from django.urls import reverse
from django.utils.translation import gettext as _

from creme.creme_config.bricks import FileRefsBrick
from creme.creme_core.models import FileRef
from creme.creme_core.tests.base import CremeTestCase
from creme.creme_core.tests.views.base import BrickTestCaseMixin


class FileRefTestCase(BrickTestCaseMixin, CremeTestCase):
    PORTAL_URL = reverse('creme_config__file_refs')
    # @staticmethod
    # def _build_edit_url(fconf):
    #     return reverse('creme_config__edit_fields_config', args=(fconf.pk,))

    def test_portal(self):
        self.login_as_super(is_staff=True)
        path = self.create_uploaded_file(
            file_name='FileRefTestCase_test_portal.txt',
            dir_name='models',
        )
        FileRef.objects.create(filedata=path, user=self.get_root_user())

        response = self.assertGET200(self.PORTAL_URL)
        self.assertTemplateUsed(response, 'creme_config/portals/file-ref.html')

        brick_node = self.get_brick_node(
            self.get_html_tree(response.content), brick=FileRefsBrick,
        )
        self.assertBrickTitleEqual(
            brick_node,
            count=1,
            title='{count} Temporary file',
            plural_title='{count} Temporary files',
        )
        self.assertListEqual(
            [_('Created'), _('Owner user'), _('Path'), _('Is temporary?')],
            self.get_brick_table_column_titles(brick_node),
        )
        rows = self.get_brick_table_rows(brick_node)
        table_cells = self.get_alone_element(rows).findall('.//td')
        self.assertEqual(4, len(table_cells))
        self.assertEqual(path, table_cells[2].text)

    def test_portal__not_staff(self):
        self.login_as_root()
        self.assertGET403(self.PORTAL_URL)
