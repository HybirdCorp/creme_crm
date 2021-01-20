# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2019-2021  Hybird
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

from django.urls import reverse
from django.utils.html import format_html, format_html_join
from django.utils.safestring import mark_safe
from django.utils.translation import gettext as _

from creme.creme_core.core.entity_cell import EntityCellVolatile
from creme.creme_core.gui.actions import ActionsRegistry
from creme.creme_core.gui.listview import ListViewButton
from creme.persons import get_contact_model

from . import constants

Contact = get_contact_model()


class EventDetailButton(ListViewButton):
    template_name = 'events/listview/buttons/event-detail.html'


class AddContactsButton(ListViewButton):
    template_name = 'events/listview/buttons/link-contacts.html'


class RelatedContactsActionsRegistry(ActionsRegistry):
    def __init__(self, event, *args, **kwargs):
        super(RelatedContactsActionsRegistry, self).__init__(*args, **kwargs)
        self.event = event

    def _instance_actions_kwargs(self, *args, **kwargs):
        kwargs = super()._instance_actions_kwargs(*args, **kwargs)
        kwargs['event'] = self.event

        return kwargs


class _BaseEventEntityCellVolatile(EntityCellVolatile):
    html = (
        """<select onchange="creme.events.saveContactStatus('{url}', this);"{attrs}>"""
        """{options}"""
        """</select>"""
    )

    def __init__(self, event, **kwargs):
        super().__init__(model=Contact, **kwargs)
        self.event = event

    def has_relation(self, entity, rtype_id):
        id_ = self.event.id
        return any(
            id_ == relation.object_entity_id
            for relation in entity.get_relations(rtype_id)
        )

    def _render_select(self, entity, user, change_url, status_map, current_status):
        has_perm = user.has_perm_to_link

        return format_html(
            self.html,
            url=change_url,
            attrs=(
                ''
                if has_perm(self.event) and has_perm(entity) else
                mark_safe(' disabled="True"')
            ),
            options=format_html_join(
                '', '<option value="{}"{}>{}</option>',
                (
                    (
                        status,
                        ' selected' if status == current_status else '',
                        status_name,
                    ) for status, status_name in status_map.items()
                )
            ),
        )

    def render_csv(self, entity, user):
        return 'Unused'


class EntityCellVolatileInvitation(_BaseEventEntityCellVolatile):
    def __init__(self, event, value='invitation_management', **kwargs):
        super().__init__(event=event, value=value, **kwargs)

    def render_html(self, entity, user):
        has_relation = self.has_relation

        if not has_relation(entity, constants.REL_SUB_IS_INVITED_TO):
            current_status = constants.INV_STATUS_NOT_INVITED
        elif has_relation(entity, constants.REL_SUB_ACCEPTED_INVITATION):
            current_status = constants.INV_STATUS_ACCEPTED
        elif has_relation(entity, constants.REL_SUB_REFUSED_INVITATION):
            current_status = constants.INV_STATUS_REFUSED
        else:
            current_status = constants.INV_STATUS_NO_ANSWER

        return self._render_select(
            entity=entity, user=user,
            change_url=reverse('events__set_invitation_status', args=(self.event.id, entity.id)),
            status_map=constants.INV_STATUS_MAP,
            current_status=current_status,
        )

    @property
    def title(self):
        return _('Invitation')


class EntityCellVolatilePresence(_BaseEventEntityCellVolatile):
    def __init__(self, event, value='presence_management', **kwargs):
        super().__init__(event=event, value=value, **kwargs)

    def render_html(self, entity, user):
        has_relation = self.has_relation

        if has_relation(entity, constants.REL_SUB_CAME_EVENT):
            current_status = constants.PRES_STATUS_COME
        elif has_relation(entity, constants.REL_SUB_NOT_CAME_EVENT):
            current_status = constants.PRES_STATUS_NOT_COME
        else:
            current_status = constants.PRES_STATUS_DONT_KNOW

        return self._render_select(
            entity=entity, user=user,
            change_url=reverse('events__set_presence_status', args=(self.event.id, entity.id)),
            status_map=constants.PRES_STATUS_MAP,
            current_status=current_status,
        )

    @property
    def title(self):
        return _('Presence')
