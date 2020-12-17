# -*- coding: utf-8 -*-

from django.urls import reverse
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.utils.translation import gettext as _

from creme.creme_core.gui.menu import ContainerItem, ViewableItem

from .registry import config_registry


# TODO: js widget instead of URL
class TimezoneItem(ViewableItem):
    def __init__(self, id, icon=None, icon_label=''):
        super().__init__(id=id, icon=icon, icon_label=icon_label)

    def render(self, context, level=0):
        return format_html(
            '<a href="{url}">{icon}{label}</a>',
            url=reverse('creme_config__user_settings'),
            icon=self.render_icon(context),
            label=_('Time zone: {}').format(context['TIME_ZONE']),
        )


class CurrentAppConfigItem(ViewableItem):
    config_registry = config_registry

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
            # TODO: check is prefix of all permissions are equal?

        # TODO: parse URL ?

        return None

    def guess_current_app_config(self, context):
        label = self.guess_current_app_label(context)
        if label:
            try:
                return self.config_registry.get_app_registry(label)
            except LookupError:
                pass

        return None

    def render(self, context, level=0):
        app_config = self.guess_current_app_config(context)

        if app_config is None:
            return ''

        icon = self.render_icon(context)
        label = _('Configuration of «{app}»').format(app=app_config.verbose_name)

        if not context['user'].has_perm_to_admin(app_config.name):
            return format_html(
                '<span class="ui-creme-navigation-text-entry forbidden">{}{}</span>',
                icon, label,
            )

        return format_html(
            '<a href="{url}">{icon}{label}</a>',
            url=app_config.portal_url, icon=icon, label=label,
        )


class ConfigContainerItem(ContainerItem):
    # NB: http://google.github.io/material-design-icons/action/svg/ic_settings_24px.svg
    SVG_DATA = """<svg xmlns="http://www.w3.org/2000/svg" style="display: none;">
  <defs>
    <g id="creme_config-menu_icon">
      <path d="M0 0h24v24h-24z" fill="none"/>
      <path d="M19.43 12.98c.04-.32.07-.64.07-.98s-.03-.66-.07-.98l2.11-1.65c.19-.15.24-.42.12-.64l-2-3.46c-.12-.22-.39-.3-.61-.22l-2.49 1c-.52-.4-1.08-.73-1.69-.98l-.38-2.65c-.03-.24-.24-.42-.49-.42h-4c-.25 0-.46.18-.49.42l-.38 2.65c-.61.25-1.17.59-1.69.98l-2.49-1c-.23-.09-.49 0-.61.22l-2 3.46c-.13.22-.07.49.12.64l2.11 1.65c-.04.32-.07.65-.07.98s.03.66.07.98l-2.11 1.65c-.19.15-.24.42-.12.64l2 3.46c.12.22.39.3.61.22l2.49-1c.52.4 1.08.73 1.69.98l.38 2.65c.03.24.24.42.49.42h4c.25 0 .46-.18.49-.42l.38-2.65c.61-.25 1.17-.59 1.69-.98l2.49 1c.23.09.49 0 .61-.22l2-3.46c.12-.22.07-.49-.12-.64l-2.11-1.65zm-7.43 2.52c-1.93 0-3.5-1.57-3.5-3.5s1.57-3.5 3.5-3.5 3.5 1.57 3.5 3.5-1.57 3.5-3.5 3.5z"/>
    </g>
  </defs>
</svg>"""  # NOQA

    def render_icon(self, context):
        return mark_safe(
            "<svg viewBox='0 0 24 24' ><use xlink:href='#creme_config-menu_icon' /></svg>"
        )

    def render(self, context, level=0):
        return mark_safe(self.SVG_DATA + super().render(context))
