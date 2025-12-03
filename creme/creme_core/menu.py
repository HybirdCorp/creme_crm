################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2025  Hybird
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

import logging
import math

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import PermissionDenied
from django.urls import reverse
from django.utils.html import format_html, format_html_join
from django.utils.safestring import mark_safe
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _
from django.utils.translation import ngettext

from . import get_world_settings_model
from .auth import SUPERUSER_PERM
from .forms.menu import FixedURLEntryForm
from .gui import menu, quick_forms
from .models import CremeEntity, LastViewedEntity
from .models.pinned_entity import PinnedEntities
from .utils.serializers import json_encode
from .utils.unicode_collation import collator

logger = logging.getLogger(__name__)


class HomeEntry(menu.FixedURLEntry):
    id = 'creme_core-home'
    label = _('Home')
    url_name = 'creme_core__home'


class MyPageEntry(menu.FixedURLEntry):
    id = 'creme_core-my_page'
    label = _('My page')
    url_name = 'creme_core__my_page'


class JobsEntry(menu.FixedURLEntry):
    id = 'creme_core-jobs'
    label = _('Jobs')
    url_name = 'creme_core__jobs'
    permissions = SUPERUSER_PERM


class MyJobsEntry(menu.FixedURLEntry):
    id = 'creme_core-my_jobs'
    label = _('My jobs')
    url_name = 'creme_core__my_jobs'


class LogoutEntry(menu.FixedURLEntry):
    id = 'creme_core-logout'
    label = _('Log out')
    url_name = 'creme_logout'

    def render(self, context):
        return format_html(
            '<form id="logout-form" method="post" action="{url}">'
            # see django.template.backends.utils.csrf_input()
            ' <input type="hidden" name="csrfmiddlewaretoken" value="{token}">'
            ' <button type="submit">{label}</button>'
            '</form>',
            url=self.url,
            label=self.render_label(context),
            token=context.get('csrf_token'),
        )


class TrashEntry(menu.FixedURLEntry):
    """Menu entry rendering as a link to the Creme trash."""
    id = 'creme_core-trash'
    label = _('Trash')
    url_name = 'creme_core__trash'

    def render(self, context):
        count = CremeEntity.objects.filter(is_deleted=True).count()

        return format_html(
            '<a href="{url}">'
            '{label} '
            '<span class="ui-creme-navigation-punctuation">(</span>'
            '{count}'
            '<span class="ui-creme-navigation-punctuation">)</span>'
            '</a>',
            url=self.url,
            label=_('Trash'),
            count=ngettext(
                '{count} entity',
                '{count} entities',
                count,
            ).format(count=count),
        )


class PasswordChangeEntry(menu.FixedURLEntry):
    id = 'creme_core-password'
    label = _('Change password')
    url_name = 'creme_core__change_own_password'

    def check_permissions(self, user):
        # NB: notice that even when superusers cannot change their password here,
        #     they still can use the creme_config's view.
        #     So it can be perceived as inconsistent, but it avoids that users
        #     do not understand why the menu entry is not disabled when the
        #     feature is disabled.
        super().check_permissions(user)

        if not get_world_settings_model().objects.instance().password_change_enabled:
            raise PermissionDenied(gettext(
                'Your configuration forbids not superusers to change their own password'
            ))


class RoleSwitchEntry(menu.MenuEntry):
    """Menu entry rendering button to switch to another role."""
    id = 'creme_core-role_switch'
    label = _('Available roles')
    url_name = 'creme_core__switch_role'

    def render(self, context):
        user = context['user']

        if not user.is_superuser:
            roles = [*user.roles.all()]
            # TODO: user.normalize_roles(roles)?
            if len(roles) >= 2:
                selected_id = user.role_id
                url_name = self.url_name
                home_url = reverse('creme_core__home')

                return format_html(
                    '<span class="ui-creme-navigation-title">{label}</span>{roles}',
                    label=self.label,
                    roles=format_html_join(
                        '\n',
                        '''<button class="{class}" {attr}'''
                        '''onclick="creme.utils.ajaxQuery('{url}', {{action: 'post'}}).onDone(function(){{ creme.utils.goTo('{home_url}'); }}).start()">'''  # NOQA
                        '''<div class="marker-{marker_suffix}"></div>{role}'''
                        '''</button>''',
                        (
                            {
                                'class': 'disabled-role' if role.deactivated_on else '',
                                'attr': (
                                    'disabled '
                                    if role.id == selected_id or role.deactivated_on else
                                    ''
                                ),
                                'url': reverse(url_name, args=(user.id, role.id)),
                                'home_url': home_url,
                                'marker_suffix': (
                                    'selected' if role.id == selected_id else 'not-selected'
                                ),
                                'role': role,
                            } for role in roles
                        ),
                    ),
                )

        return mark_safe(
            '<span class="ui-creme-navigation-title ui-creme-navigation-empty" />'
        )


class CremeEntry(menu.ContainerEntry):
    """Special Entry 'Creme' with hard coded children."""
    id = 'creme_core-creme'
    # label = 'Creme'
    is_required = True
    single_instance = True
    accepts_children = False

    class UserSeparatorEntry(menu.Separator1Entry):
        id = 'creme_core-user_separator'
        label = _('User')

    # Hint: add entry classes here from your file apps.py if you need
    # (see apps 'creme_config' & 'persons').
    child_classes = [
        HomeEntry,
        TrashEntry,
        UserSeparatorEntry,
        MyPageEntry,
        MyJobsEntry,
        PasswordChangeEntry,
        RoleSwitchEntry,
        menu.Separator1Entry,  # End of "user" group
        LogoutEntry,
    ]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._children[:] = (cls() for cls in self.child_classes)
        self.label = settings.SOFTWARE_LABEL


class QuickFormsEntries(menu.MenuEntrySequence):
    """Display an Entry for each quick-form registered ;
    an inner-popup dialog is displayed when clicking on an entry.
    """
    id = 'creme_core-quick_forms'
    label = _('*Quick forms*')
    form_class = FixedURLEntryForm

    quickforms_registry = quick_forms.quickform_registry

    class QuickCreationEntry(menu.MenuEntry):
        id = 'creme_core-quick_forms-link'

        def __init__(self, **kwargs):
            super().__init__(**kwargs)
            self.model = self.data['model']

        @property
        def url(self):
            return reverse(
                'creme_core__quick_form',
                args=(ContentType.objects.get_for_model(self.model).id,),
            )

        def render(self, context):
            return format_html(
                '<a href="#" data-href="{url}" class="quickform-menu-link">{label}</a>',
                url=self.url, label=self.label,
            ) if context['user'].has_perm_to_create(self.model) else format_html(
                '<span class="ui-creme-navigation-text-entry forbidden">{}</span>',
                self.label,
            )

    def __iter__(self):
        models = [
            (str(model._meta.verbose_name), model)
            for model in self.quickforms_registry.models
        ]

        if models:
            sort_key = collator.sort_key
            models.sort(key=lambda t: sort_key(t[0]))

            for vname, model in models:
                yield self.QuickCreationEntry(data={'label': vname, 'model': model})
        else:
            yield menu.MenuEntry(data={'label': _('No type available')})


class EntitiesCreationEntry(menu.MenuEntry):
    """Entry which displays a specific dialog when you click on it.
    This dialog proposes several creation links, grouped by theme.
    """
    id = 'creme_core-creation_forms'
    label = _('Other type of entity')
    form_class = FixedURLEntryForm

    creation_menu_registry = menu.creation_menu_registry

    def as_grid(self, user) -> list[list[dict]]:
        """ Build JSON-ifiable information  used by JavaScript to render the grid of links.

        @param user: Current user (CremeUser instance).
        @return: list of lists of dictionaries.
        """
        # TODO: cache some results ?
        groups = [*self.creation_menu_registry]

        # We compute the size of a square grid which will contain our items
        length = len(groups)
        grid_size = int(math.ceil(math.sqrt(length)))
        holes = grid_size ** 2 - length  # Number of empty cells in the grid

        grid = []
        group_it = iter(groups)

        for row_weigth in range(grid_size, 0, -1):
            row = []

            if not holes:
                col_max_idx = grid_size
            else:
                # We compute the number of holes which remain if we create a
                # hole per (remaining) row
                if holes - row_weigth > 0:
                    holes -= 2
                    col_max_idx = grid_size - 2
                else:
                    holes -= 1
                    col_max_idx = grid_size - 1

            for col_idx in range(col_max_idx):
                link_group = next(group_it)

                row.append({
                    'label': str(link_group.label),
                    'links': [link.to_dict(user) for link in link_group],
                })

            grid.append(row)

        return grid

    def render(self, context):
        return format_html(
            '<a href="" class="anyform-menu-link" title="{title}" data-grouped-links="{links}">'
            '{label}'
            '</a>',
            title=_('Create an entity of any type'),
            links=json_encode(self.as_grid(context['user'])),
            label=self.render_label(context),
        )


# class RecentEntitiesEntry(menu.MenuEntry):
#     """Entry displaying links to detail-views recently consulted."""
#     id = 'creme_core-recent_entities'
#     label = _('Recent entities')
#     level = 0
#     single_instance = True
#
#     def render(self, context):
#         from .gui.last_viewed import LastViewedItem
#
#         lv_items = LastViewedItem.get_all(context['request'])
#
#         if lv_items:
#             li_tags = format_html_join(
#                 '\n',
#                 '<li>'
#                 '<a href="{url}">'
#                 '<span class="ui-creme-navigation-ctype">{ctype}</span>'
#                 '{name}'
#                 '</a>'
#                 '</li>',
#                 (
#                     {'url': lvi.url, 'ctype': lvi.ctype, 'name': lvi.name}
#                     for lvi in lv_items
#                 ),
#             )
#         else:
#             li_tags = format_html(
#                 '<li><span class="ui-creme-navigation-text-entry">{}</span></li>',
#                 gettext('No recently visited entity'),
#             )
#
#         return format_html(
#             '{label}<ul>{li_tags}</ul>',
#             label=self.render_label(context),
#             li_tags=li_tags,
#         )
class QuickAccessEntry(menu.ContainerEntry):
    """Entry displaying links to detail-views recently consulted & to pinned entities."""
    id = 'creme_core-recent_entities'  # TODO: change + data migration
    label = _('Quick access')
    level = 0
    single_instance = True
    accepts_children = False

    class RecentEntitiesEntries(menu.MenuEntrySequence):
        # id = 'creme_core-recent_entities'
        label = 'Recent entities'

        class RecentEntityEntry(menu.MenuEntry):
            id = 'creme_core-recent_entity-link'

            def __init__(self, last_viewed_entity):
                super().__init__()
                self.url = last_viewed_entity.real_entity.get_absolute_url()
                self.ctype = last_viewed_entity.entity_ctype
                self.label = str(last_viewed_entity.real_entity)

            def render(self, context):
                return format_html(
                    '<a href="{url}">'
                    '<span class="ui-creme-navigation-ctype">{ctype}</span>'
                    '{label}'
                    '</a>',
                    url=self.url, label=self.label, ctype=self.ctype,
                )

        def __init__(self, user, **kwargs):
            super().__init__(**kwargs)
            self.user = user

        def __iter__(self):
            last_viewed_entities = LastViewedEntity.objects.filter(
                user=self.user, entity__is_deleted=False,
            ).prefetch_related('real_entity')[:settings.LAST_ENTITIES_MENU_SIZE]

            if last_viewed_entities:
                for lve in last_viewed_entities:
                    yield self.RecentEntityEntry(last_viewed_entity=lve)
            else:
                yield menu.MenuEntry(data={'label': _('No recently visited entity')})

    class PinnedEntitiesEntries(menu.MenuEntrySequence):  # TODO: factorise
        # id = 'creme_core-pinned_entities'
        label = 'Pinned entities'

        class PinnedEntityEntry(menu.MenuEntry):
            id = 'creme_core-pinned_entity-link'

            def __init__(self, pinned_entity):
                super().__init__()
                entity = pinned_entity.real_entity
                self.url = entity.get_absolute_url()
                self.ctype = pinned_entity.entity_ctype
                self.label = str(entity)
                self.is_deleted = entity.is_deleted

            def render(self, context):
                return format_html(
                    '<a href="{url}" class="{cls}">'
                    '<span class="ui-creme-navigation-ctype">{ctype}</span>'
                    '{label}'
                    '</a>',
                    url=self.url, label=self.label, ctype=self.ctype,
                    cls='is_deleted' if self.is_deleted else '',
                )

        def __init__(self, user, **kwargs):
            super().__init__(**kwargs)
            self.user = user

        def __iter__(self):
            pinned_entities = [*PinnedEntities.get_for_user(self.user)]
            if pinned_entities:
                for pinned in pinned_entities:
                    yield self.PinnedEntityEntry(pinned_entity=pinned)
            else:
                yield menu.MenuEntry(data={'label': _('No pinned entity')})

    def render(self, context):
        user = context['user']
        # NB: se set children in render() which is ugly, but we need user to
        #     compute sub-entries.
        self._children = [
            menu.Separator1Entry(data={'label': _('Recent entities')}),
            self.RecentEntitiesEntries(user=user),
            menu.Separator1Entry(data={'label': _('Pinned entities')}),
            self.PinnedEntitiesEntries(user=user),
        ]

        return super().render(context)
