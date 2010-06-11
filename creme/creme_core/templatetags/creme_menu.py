# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2010  Hybird
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
from django.db.models import Q

from creme_core.models import PreferedMenuItem, ButtonMenuItem
from creme_core.entities_access.permissions import user_has_acces_to_application
from creme_core.gui.menu import creme_menu, new_creme_menu
from creme_core.gui.last_viewed import last_viewed_items
from creme_core.gui.button_menu import button_registry


register = Library()

class ItemMenu(object):
    __slots__ = ('app_name', 'app_url', 'items_menu')

    def __init__ (self, name, url, items):
        self.app_name = name
        self.app_url = url
        self.items_menu = items

    def __cmp__(self, other):
        return cmp(self.app_name, other.app_name)

#@register.inclusion_tag('templatetags/creme_menu.html')
#def generate_creme_menu ():
    #list_item = []
    #for key , value in creme_menu.app_menu.iteritems():
        #item = ItemMenu ()
        #item.app_name = value.app_menu_name
        #item.app_url = value.app_url
        #item.items_menu = value.items
        #list_item.append( item )

    #return {'menu': list_item}

from django.conf import settings

if settings.USE_STRUCT_MENU:
    @register.inclusion_tag('creme_core/templatetags/treecreme_menu.html')
    def generate_treecreme_menu(request):
        items = [ItemMenu(appitem.app_menu_name, appitem.app_url, appitem.items)
                    for appitem in creme_menu.app_menu.itervalues()
                        if user_has_acces_to_application(request, appitem.app_name)
                ]
        items.sort()

        return {'menu':items}

else:
    from django.utils.html import escape
    from django.utils.safestring import mark_safe


    @register.inclusion_tag('creme_core/templatetags/newtreecreme_menu.html')
    def generate_treecreme_menu(request):
        result = ""
        for one_item in new_creme_menu.items:
            result += one_item.render()
        return {'menu':mark_safe (result)}


@register.inclusion_tag('creme_core/templatetags/prefered_menu.html')
def get_prefered_menu(request):
    return {'items': PreferedMenuItem.objects.filter(Q(user=request.user) | Q(user__isnull=True)).order_by('order')}

@register.inclusion_tag('creme_core/templatetags/last_items_menu.html')
def get_last_items_menu(request):
    return {'items': last_viewed_items(request)}

@register.inclusion_tag('creme_core/templatetags/menu_buttons.html', takes_context=True)
def get_button_menu(context):
    entity = context['object']
    bmi = ButtonMenuItem.objects.filter(Q(content_type=entity.entity_type)|Q(content_type__isnull=True)).order_by('order').values_list('button_id', flat=True)

    context['buttons'] = [button.render(context) for button in button_registry.get_buttons(bmi, entity)]

    return context

