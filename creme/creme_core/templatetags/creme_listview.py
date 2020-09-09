# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2020  Hybird
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
from collections import defaultdict

from django.contrib.auth import get_user_model
from django.template import Library
from django.template.loader import get_template

from ..core.paginator import FlowPaginator
from ..gui.bulk_update import bulk_update_registry
from ..gui.pager import PagerContext
from ..utils.unicode_collation import collator

logger = logging.getLogger(__name__)
register = Library()


@register.inclusion_tag('creme_core/templatetags/listview/entity-filters.html')
def listview_entity_filters(*, model, user, efilters, show_buttons):
    efilter = efilters.selected

    if efilter:
        efilter_id = efilter.id
        can_edit   = efilter.can_edit(user)[0]
        can_delete = efilter.can_delete(user)[0]
    else:
        efilter_id = 0
        can_edit = can_delete = False

    return {
        'user': user,
        'model': model,
        'entity_filters': efilters,
        'efilter_id': efilter_id,
        'can_edit': can_edit,
        'can_delete': can_delete,
        'show_buttons': show_buttons,
    }


@register.inclusion_tag('creme_core/templatetags/listview/header-filters.html')
def listview_header_filters(*, model, user, hfilters, show_buttons):
    selected_hfilter = hfilters.selected

    grouped_hfilters = defaultdict(list)
    for hfilter in hfilters:
        grouped_hfilters[hfilter.user_id].append(hfilter)

    global_header_filters = grouped_hfilters.pop(None, ())
    my_header_filters     = grouped_hfilters.pop(user.id, ())

    if grouped_hfilters:
        users = get_user_model().objects.in_bulk(grouped_hfilters.keys())
        other_header_filters = [
            (users.get(user_id), user_hfilters)
            for user_id, user_hfilters in grouped_hfilters.items()
        ]

        sort_key = collator.sort_key
        other_header_filters.sort(key=lambda t: sort_key(str(t[0])))
    else:
        other_header_filters = ()

    return {
        'model': model,

        'global_header_filters': global_header_filters,
        'my_header_filters':     my_header_filters,
        'other_header_filters':  other_header_filters,

        'selected': selected_hfilter,

        'can_edit':   selected_hfilter.can_edit(user)[0],
        'can_delete': selected_hfilter.can_delete(user)[0],

        'show_buttons': show_buttons,
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
def listview_buttons(context, *, model, buttons):
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
def listview_header_colspan(*, cells, is_readonly, is_single_select):
    colspan = (
        len(cells)
        if is_readonly else
        sum(2 if cell.type_id != 'actions' else 1 for cell in cells)
    )

    return colspan if is_single_select else colspan + 1


@register.filter('listview_column_colspan')
def get_column_colspan(cell, is_readonly):
    return 2 if cell.type_id != 'actions' and not is_readonly else 1


@register.inclusion_tag('creme_core/templatetags/listview/td-action.html')
def listview_td_action_for_cell(*, cell, instance, user):
    from creme.creme_core.views.entity import _bulk_has_perm

    return {
        # TODO: pass the registry in a list-view context
        'edit_url':  bulk_update_registry.inner_uri(cell=cell, instance=instance, user=user),
        'edit_perm': _bulk_has_perm(instance, user),
    }


@register.inclusion_tag('creme_core/templatetags/listview/entity-actions.html')
def listview_entity_actions(*, cell, instance, user):
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
def listview_header_actions(*, cell, user):
    return {
        'actions': cell.bulk_actions(user),
    }
