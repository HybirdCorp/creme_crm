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

from django.db.models import Q
from django.template import Library
from django.utils.functional import partition

from ..core.notification import OUTPUT_WEB
from ..gui.menu import menu_registry
from ..models import MenuConfigItem, Notification

logger = logging.getLogger(__name__)
register = Library()


@register.inclusion_tag('creme_core/templatetags/menu.html', takes_context=True)
def menu_display(context):
    user = context['user']
    regular_items, role_items = partition(
        lambda item: item.superuser or bool(item.role_id),
        MenuConfigItem.objects.filter(
            Q(role=user.role, superuser=user.is_superuser)
            | Q(role=None, superuser=False)
        ),
    )
    context['entries'] = [
        (entry, entry.render(context))
        for entry in menu_registry.get_entries(role_items or regular_items)
    ]

    return context


@register.simple_tag
def menu_notifications(user):
    from ..views.notification import LastWebNotifications

    qs = Notification.objects.filter(
        user=user, discarded=None, output=OUTPUT_WEB,
    )

    return {
        'count': qs.count(),
        'notifications': [
            notif.to_dict(user)
            for notif in qs.order_by('-id')
                           .select_related('channel')[:LastWebNotifications.limit]
        ],
    }
