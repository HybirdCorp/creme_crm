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

from __future__ import annotations

import logging
from collections import defaultdict
from collections.abc import Sequence
from typing import TYPE_CHECKING

from django.contrib.auth import get_user_model
from django.db.models.query_utils import Q
from django.template import Library
from django.template.loader import get_template

from ..core.paginator import FlowPaginator
from ..gui.bulk_update import bulk_update_registry
from ..gui.pager import PagerContext
from ..utils.queries import QSerializer
from ..utils.unicode_collation import collator
from ..views.generic import EntitiesList

if TYPE_CHECKING:
    from ..core.entity_cell import EntityCell, EntityCellActions
    from ..gui.listview import ListViewButtonList
    from ..models import CremeEntity, CremeUser
    from ..models.entity_filter import EntityFilterList
    from ..models.header_filter import HeaderFilterList

logger = logging.getLogger(__name__)
register = Library()


def _group_filters(user, filters):
    grouped_filters = defaultdict(list)
    for filter_ in filters:
        grouped_filters[filter_.user_id].append(filter_)

    global_filters = grouped_filters.pop(None, ())
    user_filters   = grouped_filters.pop(user.id, ())

    if grouped_filters:
        users = get_user_model().objects.in_bulk(grouped_filters.keys())
        other_filters = [
            (users.get(user_id), user_filters)
            for user_id, user_filters in grouped_filters.items()
        ]

        sort_key = collator.sort_key
        other_filters.sort(key=lambda t: sort_key(str(t[0])))
    else:
        other_filters = ()

    return global_filters, user_filters, other_filters


@register.inclusion_tag('creme_core/templatetags/listview/entity-filters.html')
def listview_entity_filters(*,
                            model: type[CremeEntity],
                            user: CremeUser,
                            efilters: EntityFilterList,
                            show_buttons: bool,
                            ):
    global_efilters, my_efilters, other_efilters = _group_filters(user=user, filters=efilters)

    selected_efilter = efilters.selected
    if selected_efilter:
        edition_allowed, edition_error = selected_efilter.can_edit(user)
        deletion_allowed, deletion_error = selected_efilter.can_delete(user)
    else:
        edition_allowed = deletion_allowed = False
        edition_error = deletion_error = ''

    return {
        'user': user,
        'model': model,

        'global_efilters': global_efilters,
        'my_efilters': my_efilters,
        'other_efilters': other_efilters,

        'selected': selected_efilter,

        'show_buttons': show_buttons,

        'edition_allowed': edition_allowed,
        'edition_error': edition_error,

        'deletion_allowed': deletion_allowed,
        'deletion_error': deletion_error,
    }


@register.inclusion_tag('creme_core/templatetags/listview/header-filters.html')
def listview_header_filters(*,
                            model: type[CremeEntity],
                            user: CremeUser,
                            hfilters: HeaderFilterList,
                            show_buttons: bool,
                            ):
    grouped_hfilters = defaultdict(list)
    for hfilter in hfilters:
        grouped_hfilters[hfilter.user_id].append(hfilter)

    global_header_filters, my_header_filters, other_header_filters = _group_filters(
        user=user, filters=hfilters,
    )

    selected_hfilter = hfilters.selected
    edition_allowed, edition_error = selected_hfilter.can_edit(user)
    deletion_allowed, deletion_error = selected_hfilter.can_delete(user)

    return {
        'model': model,

        'global_header_filters': global_header_filters,
        'my_header_filters':     my_header_filters,
        'other_header_filters':  other_header_filters,

        'selected': selected_hfilter,

        'show_buttons': show_buttons,

        'edition_allowed': edition_allowed,
        'edition_error': edition_error,

        'deletion_allowed': deletion_allowed,
        'deletion_error': deletion_error,
    }


class PagerRenderer:
    template_name = ''

    def render(self, page):
        return get_template(self.template_name).render(self.get_context(page))

    def get_context(self, page):
        return {'page': page}


class FlowPagerRenderer(PagerRenderer):
    template_name = 'creme_core/templatetags/listview/paginator-fast.html'


class DefaultPagerRenderer(PagerRenderer):
    template_name = 'creme_core/templatetags/listview/paginator-slow.html'

    def get_context(self, page):
        return {'pager': PagerContext(page)}


PAGINATOR_RENDERERS = {
    FlowPaginator: FlowPagerRenderer,
}


@register.simple_tag
def listview_pager(page):
    renderer_class = PAGINATOR_RENDERERS.get(page.paginator.__class__, DefaultPagerRenderer)
    return renderer_class().render(page)


@register.inclusion_tag('creme_core/templatetags/listview/buttons.html', takes_context=True)
def listview_buttons(context, *, model: type[CremeEntity], buttons: ListViewButtonList):
    request = context['request']  # TODO: argument ?

    return {
        'request': request,
        'user': request.user,
        'model': model,
        'list_view_state': context['list_view_state'],
        'buttons': (
            (button, button.get_context(request=request, lv_context=context))
            for button in buttons.instances
        ),
    }


@register.simple_tag
def listview_header_colspan(*,
                            cells: Sequence[EntityCell],
                            is_readonly: bool,
                            is_single_select: bool,
                            ):
    colspan = (
        len(cells)
        if is_readonly else
        sum(2 if cell.type_id != 'actions' else 1 for cell in cells)
    )

    return colspan if is_single_select else colspan + 1


@register.filter('listview_column_colspan')
def get_column_colspan(cell: EntityCell, is_readonly: bool):
    return 2 if cell.type_id != 'actions' and not is_readonly else 1


@register.inclusion_tag('creme_core/templatetags/listview/td-action.html')
def listview_td_action_for_cell(*, cell: EntityCell, instance: CremeEntity, user: CremeUser):
    from creme.creme_core.views.entity import _bulk_has_perm

    return {
        # TODO: pass the registry in a list-view context
        'edit_url':  bulk_update_registry.inner_uri(instance=instance, cells=[cell]),
        'edit_perm': _bulk_has_perm(instance, user),
    }


@register.inclusion_tag('creme_core/templatetags/listview/entity-actions.html')
def listview_entity_actions(*, cell: EntityCell, instance: CremeEntity, user: CremeUser):
    actions = cell.instance_actions(instance=instance, user=user)
    count = len(actions)

    return {
        'id': instance.id,
        'actions': {
            'default': actions[0] if count > 0 else None,
            'others': actions[1:] if count > 1 else [],
        },
    }


@register.inclusion_tag('creme_core/templatetags/listview/header-actions.html')
def listview_header_actions(*, cell: EntityCellActions, user: CremeUser):
    return {
        'actions': cell.bulk_actions(user),
    }


@register.simple_tag
def listview_q_argument(**kwargs):
    """Build the GET argument to pass to a list-view which encodes an arbitrary
    filter query (i.e. to limit the listed entities).

    @param kwargs: Items in the form <field=value>.

    Example:
        <a href="{% url 'my_app__list_my_entities' %}?{% listview_q_argument relations__type=REL_SUB_FOOBAR relations__object_entity=object.id %}">
            Linked entities
        </a>
    """  # NOQA
    return '{arg}={value}'.format(
        arg=EntitiesList.requested_q_arg,
        # TODO: possibility to use OR?
        value=QSerializer().dumps(Q(**kwargs)),
    )
