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


register = Library()

@register.inclusion_tag('creme_core/templatetags/widgets/add_button.html', takes_context=True)
def get_add_button(context, entity, user):
    meta = entity._meta
    context.update({
            'can_add': user.has_perm('%s.add_%s' % (meta.app_label, meta.object_name.lower()))
           })
    return context

@register.inclusion_tag('creme_core/templatetags/widgets/delete_button.html', takes_context=True)
def get_delete_button(context, entity, user):
    context.update({
            'can_delete': entity.can_delete(user),
           })
    return context

@register.inclusion_tag('creme_core/templatetags/widgets/edit_button.html', takes_context=True)
def get_edit_button(context, entity, user):
    context.update({
            'can_change': entity.can_change(user),
           })
    return context

@register.inclusion_tag('creme_core/templatetags/widgets/entity_actions.html', takes_context=True)
def get_entity_actions(context, entity):
    user = context['request'].user

    context.update({
            'id':      entity.id,
            'actions': entity.get_actions(user),
           })
    return context

@register.inclusion_tag('creme_core/templatetags/widgets/select_or_msg.html')
def widget_select_or_msg(items, void_msg):
    return {'items': items, 'void_msg': void_msg}
