################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2022-2023  Hybird
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
################################################################################

from pathlib import Path

from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils.formats import number_format
from django.utils.translation import gettext
from PIL.Image import open as open_img

from creme.creme_core import get_world_settings_model
from creme.creme_core.forms import CremeModelForm
from creme.creme_core.forms.widgets import NoPreviewClearableFileInput
from creme.creme_core.templatetags.creme_image import image_scale_to_frame


class WorldSettingsBaseForm(CremeModelForm):
    class Meta(CremeModelForm.Meta):
        model = get_world_settings_model()
        fields = ()


class MenuIconForm(WorldSettingsBaseForm):
    class Meta(WorldSettingsBaseForm.Meta):
        fields = ('menu_icon',)
        widgets = {'menu_icon': NoPreviewClearableFileInput}

    def clean_menu_icon(self):
        menu_icon = self.cleaned_data['menu_icon']

        # TODO: extract in a formfield
        if menu_icon and menu_icon.size > settings.MENU_ICON_MAX_SIZE:
            raise ValidationError(
                gettext('The file is too large (maximum size: {} bytes)').format(
                    number_format(settings.MENU_ICON_MAX_SIZE),
                )
            )

        return menu_icon

    def save(self, *args, **kwargs):
        instance = self.instance
        file_data = self.cleaned_data.get('menu_icon')

        if file_data:
            with open_img(file_data) as img:
                size = img.size

                if (
                    size[0] > settings.MENU_ICON_MAX_WIDTH
                    or size[1] > settings.MENU_ICON_MAX_HEIGHT
                ):
                    img = img.resize(image_scale_to_frame(
                        size,
                        width=settings.MENU_ICON_MAX_WIDTH,
                        height=settings.MENU_ICON_MAX_HEIGHT,
                    ))

                relative_path = Path(
                    *instance._meta.get_field('menu_icon').upload_to.split('/'),
                    f'menu_icon.{file_data.image.format.lower()}'
                )
                absolute_path = Path(settings.MEDIA_ROOT) / relative_path

                # We create the missing directories
                absolute_path.parent.mkdir(mode=0o755, parents=True, exist_ok=True)

                img.save(absolute_path)
                instance.menu_icon = str(relative_path)
        else:
            # TODO: instance.menu_icon.delete() ? (currently we keep the file)
            instance.menu_icon = None

        instance.save()


class PasswordFeaturesForm(WorldSettingsBaseForm):
    class Meta(WorldSettingsBaseForm.Meta):
        fields = ('password_change_enabled', 'password_reset_enabled')


class UserDisplayedNameForm(WorldSettingsBaseForm):
    class Meta(WorldSettingsBaseForm.Meta):
        fields = ('user_name_change_enabled',)
