################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2021-2024  Hybird
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

from django.template import Library
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _

# TODO: make public ?
from creme.creme_core.core.entity_cell import CELLS_MAP
from creme.creme_core.templatetags.creme_bricks import _brick_menu_state_action
from creme.creme_core.utils.date_period import date_period_registry

register = Library()


def _assistants_brick_menu_hide_action(context, *, url, hidden, in_label, out_label):
    return _brick_menu_state_action(
        context,
        url=url,
        action_id='update',
        current_state=not hidden,
        in_label=in_label,
        out_label=out_label,
        __value='false' if hidden else 'true',
    )


@register.inclusion_tag('creme_core/templatetags/bricks/menu-action.html', takes_context=True)
def assistants_brick_menu_hide_validated_alerts_action(context, url, hidden):
    return _assistants_brick_menu_hide_action(
        context,
        url=url,
        hidden=hidden,
        in_label=_('Hide validated alerts'),
        out_label=_('Show validated alerts'),
    )


@register.inclusion_tag('creme_core/templatetags/bricks/menu-action.html', takes_context=True)
def assistants_brick_menu_hide_validated_todos_action(context, url, hidden):
    return _assistants_brick_menu_hide_action(
        context,
        url=url,
        hidden=hidden,
        in_label=_('Hide validated todos'),
        out_label=_('Show validated todos'),
    )


# TODO: DateOffset class with verbose __str__() instead?
@register.simple_tag
def assistants_verbose_date_offset(offset_dict, entity):
    # Translators: Used in small popover panel to display relative trigger dates for Alerts
    # period: a (translated) string, like "1 hour" or "2 weeks".
    # relative: "after" or "before" (translated too; see msgid in the same .po file)
    # field: verbose name of a field, like "date of creation".
    return gettext('{period} {relative} «{field}»').format(
        period=date_period_registry.deserialize(offset_dict['period']),
        relative=gettext('after') if offset_dict['sign'] == 1 else gettext('before'),
        field=CELLS_MAP.build_cell_from_dict(type(entity), offset_dict['cell']).title,
    )
