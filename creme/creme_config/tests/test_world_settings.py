from pathlib import Path

from django.conf import settings
from django.test.utils import override_settings
from django.urls import reverse
from django.utils.formats import number_format
from django.utils.translation import gettext as _
from PIL.Image import open as open_img

from creme.creme_config.bricks import WorldSettingsBrick
from creme.creme_core import get_world_settings_model
from creme.creme_core.tests.base import CremeTestCase
from creme.creme_core.tests.views.base import BrickTestCaseMixin

MAX_SIZE = 2048
WorldSettings = get_world_settings_model()


@override_settings(
    MENU_ICON_MAX_WIDTH=36,
    MENU_ICON_MAX_HEIGHT=36,
    MENU_ICON_MAX_SIZE=MAX_SIZE,
)
class WorldSettingsTestCase(BrickTestCaseMixin, CremeTestCase):
    def test_portal(self):
        self.login_as_root()

        response = self.assertGET200(reverse('creme_config__world_settings'))
        self.assertTemplateUsed(response, 'creme_config/portals/world-settings.html')
        self.assertEqual(
            reverse('creme_core__reload_bricks'),
            response.context.get('bricks_reload_url'),
        )

        self.get_brick_node(self.get_html_tree(response.content), brick=WorldSettingsBrick)

    @override_settings(MENU_ICON_MAX_SIZE=4092)
    def test_edit_menu_icon01(self):
        self.login_as_root()

        self.assertEqual(1, WorldSettings.objects.count())

        url = reverse('creme_config__edit_world_setting', args=('menu_icon',))
        response1 = self.assertGET200(url)
        self.assertEqual(
            _("Edit the instance's settings"), response1.context.get('title'),
        )
        self.assertEqual(
            _('Save the modifications'), response1.context.get('submit_label'),
        )

        # POST -----------------------------------------------------------------
        uploaded_path1 = Path(
            settings.CREME_ROOT, 'static', 'chantilly', 'images', 'creme_22.png',
        )
        self.assertTrue(uploaded_path1.exists())

        with open(uploaded_path1, 'rb') as image_file1:
            response2 = self.client.post(url, data={'menu_icon': image_file1})

        self.assertNoFormError(response2)

        w_settings = WorldSettings.objects.get()
        path1 = Path(w_settings.menu_icon.path)
        self.assertEqual('menu_icon.png', path1.name)

        with self.assertNoException():
            with open_img(path1) as img_fd1:
                img_size1 = img_fd1.size
                img_format1 = img_fd1.format
        self.assertEqual((22, 22), img_size1)
        self.assertEqual('PNG',    img_format1)

        # POST + overwrite file ------------------------------------------------
        uploaded_path2 = Path(
            settings.CREME_ROOT, 'static', 'chantilly', 'images', 'wait.gif',
        )
        self.assertTrue(uploaded_path2.exists())

        with open(uploaded_path2, 'rb') as image_file2:
            response3 = self.client.post(url, data={'menu_icon': image_file2})

        self.assertNoFormError(response3)

        w_settings = self.refresh(w_settings)
        path2 = Path(w_settings.menu_icon.path)
        self.assertEqual('menu_icon.gif', path2.name)

        with self.assertNoException():
            with open_img(path2) as img_fd2:
                img_size2 = img_fd2.size
                img_format2 = img_fd2.format
        self.assertEqual((16, 16), img_size2)
        self.assertEqual('GIF',    img_format2)

        # POST + file cleaning -------------------------------------------------
        self.assertNoFormError(
            self.client.post(url, data={'menu_icon-clear': 'on'}),
        )
        self.assertEqual('', self.refresh(w_settings).menu_icon)
        self.assertTrue(Path(path2).exists())  # TODO: delete the file?

    @override_settings(MENU_ICON_MAX_SIZE=3145728)
    def test_edit_menu_icon02(self):
        "Image resized if too big."
        self.login_as_root()

        uploaded_path = Path(
            settings.CREME_ROOT, 'static', 'common', 'images', 'creme_logo.png',
        )
        self.assertTrue(uploaded_path.exists())

        with open_img(uploaded_path) as img_fd1:
            size1 = img_fd1.size
        self.assertEqual((569, 170), size1)

        field_name = 'menu_icon'

        with open(uploaded_path, 'rb') as image_file:
            response = self.client.post(
                reverse('creme_config__edit_world_setting', args=(field_name,)),
                data={field_name: image_file},
            )

        self.assertNoFormError(response)

        w_settings = WorldSettings.objects.get()

        with self.assertNoException():
            with open_img(w_settings.menu_icon.path) as img_fd2:
                size2 = img_fd2.size
        self.assertEqual((36, 11), size2)

    def test_edit_menu_icon03(self):
        "Image file too large."
        self.login_as_root()

        uploaded_path = Path(
            settings.CREME_ROOT, 'static', 'common', 'images', 'creme_logo.png',
        )
        self.assertTrue(uploaded_path.exists())
        self.assertLess(MAX_SIZE, uploaded_path.stat().st_size)

        field_name = 'menu_icon'

        with open(uploaded_path, 'rb') as image_file:
            response = self.assertPOST200(
                reverse('creme_config__edit_world_setting', args=(field_name,)),
                data={field_name: image_file},
            )
            self.assertFormError(
                self.get_form_or_fail(response),
                field=field_name,
                errors=_('The file is too large (maximum size: {} bytes)').format(
                    number_format(MAX_SIZE),
                ),
            )

    def test_edit_menu_icon04(self):
        "Reject not image."
        self.login_as_root()

        uploaded_path = Path(
            settings.CREME_ROOT, 'static', 'common', 'images', 'fulbert', 'fulbert.blend',
        )
        self.assertTrue(uploaded_path.exists())

        field_name = 'menu_icon'

        with open(uploaded_path, 'rb') as image_file:
            response = self.assertPOST200(
                reverse('creme_config__edit_world_setting', args=(field_name,)),
                data={field_name: image_file},
            )

        self.assertFormError(
            self.get_form_or_fail(response),
            field=field_name,
            errors=_(
                "Upload a valid image. The file you uploaded was either not an "
                "image or a corrupted image."
            ),
        )

    def test_edit_menu_icon05(self):
        "Check image type."
        self.login_as_root()

        source_path = Path(
            settings.CREME_ROOT, 'static', 'chantilly', 'images', 'creme_22.png',
        )
        self.assertTrue(source_path.exists())

        field_name = 'menu_icon'

        with open(source_path, 'rb') as image_file:
            file_data = self.build_filedata(content=image_file.read(), suffix='.jpg')

        response = self.client.post(
            reverse('creme_config__edit_world_setting', args=(field_name,)),
            data={field_name: file_data},
        )
        self.assertNoFormError(response)

        path = Path(WorldSettings.objects.get().menu_icon.path)
        self.assertEqual('menu_icon.png', path.name)

        with self.assertNoException():
            with open_img(path) as img_fd2:
                img_size = img_fd2.size
                img_format = img_fd2.format
        self.assertEqual((22, 22), img_size)
        self.assertEqual('PNG',    img_format)

    def test_edit_menu_icon_error01(self):
        "Not superuser."
        self.login_as_standard(admin_4_apps=['creme_core'])
        self.assertGET403(reverse('creme_config__edit_world_setting', args=('menu_icon',)))

    def test_edit_menu_icon_error02(self):
        "Invalid field name."
        self.login_as_root()
        self.assertGET404(reverse('creme_config__edit_world_setting', args=('invalid',)))

    def test_edit_password_features(self):
        self.login_as_root()

        url = reverse('creme_config__edit_world_setting', args=('password',))
        response1 = self.assertGET200(url)
        self.assertEqual(
            _("Edit the instance's settings"), response1.context.get('title'),
        )
        self.assertEqual(
            _('Save the modifications'), response1.context.get('submit_label'),
        )

        # POST #1
        response2 = self.client.post(
            url,
            data={
                'password_reset_enabled': 'on',
                'password_change_enabled': '',
            },
        )
        self.assertNoFormError(response2)

        w_settings = WorldSettings.objects.get()
        self.assertTrue(w_settings.password_reset_enabled)
        self.assertFalse(w_settings.password_change_enabled)

        # POST #2
        response3 = self.client.post(
            url,
            data={
                'password_reset_enabled': '',
                'password_change_enabled': 'on',
            },
        )
        self.assertNoFormError(response3)

        w_settings = self.refresh(w_settings)
        self.assertFalse(w_settings.password_reset_enabled)
        self.assertTrue(w_settings.password_change_enabled)

    def test_edit_displayed_name(self):
        self.login_as_root()
        self.assertTrue(WorldSettings.objects.get().user_name_change_enabled)

        url = reverse('creme_config__edit_world_setting', args=('displayed_name',))
        response1 = self.assertGET200(url)
        self.assertEqual(
            _("Edit the instance's settings"), response1.context.get('title'),
        )
        self.assertEqual(
            _('Save the modifications'), response1.context.get('submit_label'),
        )

        # POST
        response2 = self.client.post(
            url,
            data={
                'user_name_change_enabled': '',
            },
        )
        self.assertNoFormError(response2)

        w_settings = WorldSettings.objects.get()
        self.assertFalse(w_settings.user_name_change_enabled)
