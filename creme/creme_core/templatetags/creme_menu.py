# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2018  Hybird
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

import warnings

# from django.conf import settings
from django.db.models import Q
from django.template import Library
# from django.utils.safestring import mark_safe

from ..gui.button_menu import button_registry
from ..gui.menu import creme_menu
from ..models import ButtonMenuItem


register = Library()


# if settings.OLD_MENU:
#     from sys import maxint as MAXINT
#
#     from django.template.context import RequestContext
#
#     from ..utils.unicode_collation import collator
#
#     warnings.warn('The old templatetags (settings.OLD_MENU = True) are deprecated.',
#                   DeprecationWarning
#                  )
#
#     class MenuItem(object):
#         __slots__ = ('url', 'name', 'has_perm')
#
#         def __init__(self, url, name, has_perm):
#             self.url = url
#             self.name = name
#             self.has_perm = has_perm
#
#         def __unicode__(self):
#             return u'<MenuItem: name:%s url:%s perm:%s>' % (self.name, self.url, self.has_perm)
#
#
#     class MenuAppItem(object):
#         __slots__ = ('app_name', 'url', 'force_order', 'items', 'sort_key')
#
#         def __init__(self, name, url, force_order, items, user):
#             self.app_name = unicode(name)
#             self.url = url
#             self.force_order = force_order
#             has_perm = user.has_perm
#             self.items = [MenuItem(item.url, item.name, has_perm(item.perm)) for item in items]
#             if force_order is None:
#                 self.sort_key = collator.sort_key(self.app_name)
#
#         def __unicode__(self):
#             return u'<MenuAppItem: app:%s url:%s>' % (self.app_name, self.url)
#
#         def __cmp__(self, other):
#             force_order1 = self.force_order
#             force_order2 = other.force_order
#
#             if force_order1 is not None:
#                 return cmp(force_order1, force_order2 if force_order2 is not None else MAXINT)
#
#             if force_order2 is not None:
#                 return 1
#
#             return cmp(self.sort_key, other.sort_key)
#
#
#     @register.inclusion_tag('creme_core/templatetags/treecreme_menu.html')
#     def generate_treecreme_menu(request):
#         user = request.user
#         has_perm = user.has_perm
#         items = [MenuAppItem(appitem.name, appitem.app_url, appitem.force_order, appitem.items, user)
#                     for appitem in creme_menu
#                         if has_perm(appitem.app_name)
#                 ]
#         items.sort()
#
#         return RequestContext(request, {'menu': items})
#
#
#     @register.simple_tag
#     def menu_display():
#         return mark_safe('<p>NEW MENU DISABLED</p>')
# else:
#     @register.simple_tag
#     def generate_treecreme_menu(request):
#         return mark_safe('<p>OLD MENU DISABLED</p>')
#
#
#     @register.simple_tag(takes_context=True)
#     def menu_display(context):
#         return creme_menu.render(context)
@register.simple_tag(takes_context=True)
def menu_display(context):
    return creme_menu.render(context)


# @register.inclusion_tag('creme_core/templatetags/prefered_menu.html')
# def get_prefered_menu(request):
#     warnings.warn('{% get_prefered_menu %} is deprecated.', DeprecationWarning)
#
#     from ..models import PreferedMenuItem
#
#     return {'items': PreferedMenuItem.objects.filter(Q(user=request.user) |
#                                                      Q(user__isnull=True)
#                                                     ).order_by('order'),
#            }


# @register.inclusion_tag('creme_core/templatetags/last_items_menu.html')
# def get_last_items_menu(request):
#     warnings.warn('{% get_last_items_menu %} is deprecated.', DeprecationWarning)
#
#     from ..gui.last_viewed import LastViewedItem
#
#     return {'items': LastViewedItem.get_all(request)}


# @register.inclusion_tag('creme_core/templatetags/menu_buttons.html', takes_context=True)
# def get_button_menu(context):
#     warnings.warn('The tag {% get_button_menu %} is deprecated ; use {% menu_buttons_display %} instead.',
#                   DeprecationWarning
#                  )
#
#     return menu_buttons_display(context)


# TODO: rename template file (menu-buttons.html)
@register.inclusion_tag('creme_core/templatetags/menu_buttons.html', takes_context=True)
def menu_buttons_display(context):
    entity = context['object']
    bmi = ButtonMenuItem.objects.filter(Q(content_type=entity.entity_type) |
                                        Q(content_type__isnull=True)
                                       ) \
                                .exclude(button_id='') \
                                .order_by('order') \
                                .values_list('button_id', flat=True)

    button_ctxt = context.flatten()
    context['buttons'] = [button.render(button_ctxt)
                            for button in button_registry.get_buttons(bmi, entity)
                         ]

    return context
