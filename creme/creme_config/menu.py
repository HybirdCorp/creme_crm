################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2021-2025  Hybird
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

from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext_lazy

from creme.creme_core import models
from creme.creme_core.gui import menu

from . import auth as config_auth
from .registry import config_registry


# TODO: js widget instead of URL
class TimezoneEntry(menu.FixedURLEntry):
    id = 'creme_config-timezone'
    label = _("*User's timezone*")
    url_name = 'creme_config__user_settings'

    def render_label(self, context):
        return gettext('Time zone: {}').format(context['TIME_ZONE'])


class MySettingsEntry(menu.FixedURLEntry):
    id = 'creme_config-my_settings'
    label = _('My settings')
    url_name = 'creme_config__user_settings'


class CurrentAppConfigEntry(menu.MenuEntry):
    id = 'creme_config-current_app'
    label = _("*Current app's settings*")

    config_registry = config_registry
    single_instance = True

    @staticmethod
    def guess_current_app_label(context):
        instance = context.get('object')
        if instance is not None:
            return type(instance)._meta.app_label

        view = context.get('view')
        if view:
            model = getattr(view, 'model', None)
            if model is not None:
                return model._meta.app_label

            permissions = getattr(view, 'permissions', None)
            if isinstance(permissions, str):
                return permissions
            # TODO: check if prefix of all permissions are equal?

        # TODO: parse URL ?

        return None

    def guess_current_app_config(self, context):
        label = self.guess_current_app_label(context)
        if label and label != 'creme_config':
            try:
                return self.config_registry.get_app_registry(label)
            except LookupError:
                pass

        return None

    def render(self, context):
        app_config = self.guess_current_app_config(context)

        if app_config is None:
            return ''

        label = _('Configuration of «{app}»').format(app=app_config.verbose_name)

        if not context['user'].has_perm_to_admin(app_config.name):
            return format_html(
                '<span class="ui-creme-navigation-text-entry forbidden">{}</span>',
                label,
            )

        return format_html(
            '<a href="{url}">{label}</a>',
            url=app_config.portal_url,
            label=label,
        )


class _ConfigURLEntry(menu.FixedURLEntry):
    permissions = 'creme_config'


class ConfigPortalEntry(_ConfigURLEntry):
    id = 'creme_config-portal'
    label = _('General configuration')
    url_name = 'creme_config__portal'


class WorldConfigEntry(_ConfigURLEntry):
    id = 'creme_config-world'
    label = _('Instance')
    url_name = 'creme_config__world_settings'


class WorkflowsConfigEntry(_ConfigURLEntry):
    id = 'creme_config-workflows'
    label = _('Workflows')
    url_name = 'creme_config__workflows'


class BricksConfigEntry(_ConfigURLEntry):
    id = 'creme_config-bricks'
    label = _('Blocks')
    url_name = 'creme_config__bricks'


class CustomFieldsConfigEntry(_ConfigURLEntry):
    id = 'creme_config-custom_fields'
    label = models.CustomField._meta.verbose_name_plural
    url_name = 'creme_config__custom_fields'


class CustomEntityTypesConfigEntry(_ConfigURLEntry):
    id = 'creme_config-custom_entities'
    label = models.CustomEntityType._meta.verbose_name_plural
    url_name = 'creme_config__custom_entity_types'


class FieldsConfigEntry(_ConfigURLEntry):
    id = 'creme_config-fields'
    label = _('Fields')
    url_name = 'creme_config__fields'


class CustomFormsConfigEntry(_ConfigURLEntry):
    id = 'creme_config-custom_forms'
    label = _('Custom forms')
    url_name = 'creme_config__custom_forms'


class HistoryConfigEntry(_ConfigURLEntry):
    id = 'creme_config-history'
    label = _('History')
    url_name = 'creme_config__history'


class MenuConfigEntry(_ConfigURLEntry):
    id = 'creme_config-menu'
    label = _('Menu')
    url_name = 'creme_config__menu'


class NotificationConfigEntry(_ConfigURLEntry):
    id = 'creme_config-notification'
    label = _('Notifications')
    url_name = 'creme_config__notification'


class ButtonsConfigEntry(_ConfigURLEntry):
    id = 'creme_config-buttons'
    label = _('Button menu')
    url_name = 'creme_config__buttons'


class SearchConfigEntry(_ConfigURLEntry):
    id = 'creme_config-search'
    label = pgettext_lazy('creme_core-noun', 'Search')
    url_name = 'creme_config__search'


class PropertyTypesConfigEntry(_ConfigURLEntry):
    id = 'creme_config-property_types'
    label = models.CremePropertyType._meta.verbose_name_plural
    url_name = 'creme_config__ptypes'


class RelationTypesConfigEntry(_ConfigURLEntry):
    id = 'creme_config-relation_types'
    label = models.RelationType._meta.verbose_name_plural
    url_name = 'creme_config__rtypes'


class UsersConfigEntry(_ConfigURLEntry):
    id = 'creme_config-users'
    label = _('Users')
    url_name = 'creme_config__users'
    permissions = config_auth.user_config_perm.as_perm


class RolesConfigEntry(_ConfigURLEntry):
    id = 'creme_config-roles'
    label = _('Roles and credentials')
    url_name = 'creme_config__roles'
    permissions = config_auth.role_config_perm.as_perm


class EntityFiltersConfigEntry(_ConfigURLEntry):
    id = 'creme_config-entity_filters'
    label = _('Filters')
    url_name = 'creme_config__efilters'


class HeaderFiltersConfigEntry(_ConfigURLEntry):
    id = 'creme_config-header_filters'
    label = _('Views')
    url_name = 'creme_config__hfilters'


class FileRefsEntry(_ConfigURLEntry):
    id = 'creme_config-file_refs'
    label = _('Temporary files')
    url_name = 'creme_config__file_refs'

    def render(self, context):
        return super().render(context=context) if context['user'].is_staff else ''


class CremeConfigEntry(menu.ContainerEntry):
    id = 'creme_config-main'
    label = _('Configuration')
    is_required = True
    single_instance = True
    accepts_children = False

    # NB: http://google.github.io/material-design-icons/action/svg/ic_settings_24px.svg
    SVG_DATA = """<svg xmlns="http://www.w3.org/2000/svg" style="display: none;">
  <defs>
    <g id="creme_config-menu_icon">
      <path d="M0 0h24v24h-24z" fill="none"/>
      <path d="M19.43 12.98c.04-.32.07-.64.07-.98s-.03-.66-.07-.98l2.11-1.65c.19-.15.24-.42.12-.64l-2-3.46c-.12-.22-.39-.3-.61-.22l-2.49 1c-.52-.4-1.08-.73-1.69-.98l-.38-2.65c-.03-.24-.24-.42-.49-.42h-4c-.25 0-.46.18-.49.42l-.38 2.65c-.61.25-1.17.59-1.69.98l-2.49-1c-.23-.09-.49 0-.61.22l-2 3.46c-.13.22-.07.49.12.64l2.11 1.65c-.04.32-.07.65-.07.98s.03.66.07.98l-2.11 1.65c-.19.15-.24.42-.12.64l2 3.46c.12.22.39.3.61.22l2.49-1c.52.4 1.08.73 1.69.98l.38 2.65c.03.24.24.42.49.42h4c.25 0 .46-.18.49-.42l.38-2.65c.61-.25 1.17-.59 1.69-.98l2.49 1c.23.09.49 0 .61-.22l2-3.46c.12-.22.07-.49-.12-.64l-2.11-1.65zm-7.43 2.52c-1.93 0-3.5-1.57-3.5-3.5s1.57-3.5 3.5-3.5 3.5 1.57 3.5 3.5-1.57 3.5-3.5 3.5z"/>
    </g>
  </defs>
</svg>"""  # NOQA

    class CredentialsSeparatorEntry(menu.Separator1Entry):
        id = 'creme_config-credentials_separator'
        label = _('Credentials management')

    class ListviewsSeparatorEntry(menu.Separator1Entry):
        id = 'creme_config-listviews_separator'
        label = _('List-views management')

    # NB: 'ContainerEntry.render()' always generates <li> tags, even for empty
    #     entries, so we cannot use Separator1Entry because the top border will
    #     always be displayed even for not staff users.
    # TODO: we could entirely define 'CremeConfigEntry.render()', but improving
    #       ContainerEntry would be better.
    #       Idea: the property "children" could become a classical method like
    #             "get_children(self, context)" to skip entries depending on the context.
    #       (remove/rework the CSS class when it's done)
    class StaffSeparatorEntry(menu.MenuEntry):
        id = 'creme_config-staff_separator'
        type = 'creme_config-staff_separator'
        label = _('Staff tools')

        def render(self, context):
            return self.render_label(context) if context['user'].is_staff else ''

    children_classes = [
        ConfigPortalEntry,
        CurrentAppConfigEntry,

        menu.Separator1Entry,

        WorldConfigEntry,
        BricksConfigEntry,
        CustomFieldsConfigEntry,
        CustomEntityTypesConfigEntry,
        FieldsConfigEntry,
        CustomFormsConfigEntry,
        WorkflowsConfigEntry,
        HistoryConfigEntry,
        MenuConfigEntry,
        NotificationConfigEntry,
        ButtonsConfigEntry,
        SearchConfigEntry,
        PropertyTypesConfigEntry,
        RelationTypesConfigEntry,

        CredentialsSeparatorEntry,
        UsersConfigEntry,
        RolesConfigEntry,

        ListviewsSeparatorEntry,
        EntityFiltersConfigEntry,
        HeaderFiltersConfigEntry,

        StaffSeparatorEntry,
        FileRefsEntry,
    ]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._children[:] = (cls() for cls in self.children_classes)

    def render_label(self, context):
        return mark_safe(
            '<svg viewBox="0 0 24 24"><use xlink:href="#creme_config-menu_icon" /></svg>'
        )

    def render(self, context):
        return mark_safe(self.SVG_DATA + super().render(context))
