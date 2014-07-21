# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2014  Hybird
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

from django.conf import settings
from django.template import Library
from django.utils.html import escape

from ..constants import ICON_SIZE_MAP
from ..gui.icon_registry import icon_registry
from ..utils.media import get_creme_media_url


register = Library()

@register.inclusion_tag('creme_core/templatetags/widgets/add_button.html', takes_context=True)
def get_add_button(context, entity, user):
    #context.update({
            #'can_add': user.has_perm_to_create(entity),
           #})
    context['can_add'] = user.has_perm_to_create(entity)
    return context

@register.inclusion_tag('creme_core/templatetags/widgets/delete_button.html', takes_context=True)
def get_delete_button(context, entity, user):
    #context.update({
            #'can_delete': user.has_perm_to_delete(entity),
           #})
    context['can_delete'] = user.has_perm_to_delete(entity)
    return context

@register.inclusion_tag('creme_core/templatetags/widgets/restore_button.html', takes_context=True)
def get_restore_button(context, entity, user): #TODO: factorise
    #context.update({
            #'can_delete': user.has_perm_to_delete(entity),
           #})
    context['can_delete'] = user.has_perm_to_delete(entity)
    return context

@register.inclusion_tag('creme_core/templatetags/widgets/edit_button.html', takes_context=True)
def get_edit_button(context, entity, user):
    #context.update({
            #'can_change': user.has_perm_to_change(entity),
           #})
    context['can_change'] = user.has_perm_to_change(entity)
    return context

@register.inclusion_tag('creme_core/templatetags/widgets/clone_button.html', takes_context=True)
def get_clone_button(context, entity, user):
    #context.update({
            #'can_create': user.has_perm_to_create(entity),
           #})
    context['can_create'] = user.has_perm_to_create(entity)
    return context

@register.inclusion_tag('creme_core/templatetags/widgets/entity_actions.html', takes_context=True)
def get_entity_actions(context, entity):
    #user = context['request'].user
    user = context['user']

    context.update({
            'id':      entity.id,
            'actions': entity.get_actions(user),
           })
    return context

@register.simple_tag
def widget_entity_hyperlink(entity, user, ignore_deleted=False): #TODO: takes_context for user ???
    "{% widget_entity_hyperlink my_entity user %}"
    if user.has_perm_to_view(entity):
        return u'<a href="%s"%s>%s</a>' % (
                        entity.get_absolute_url(),
                        ' class="is_deleted"' if entity.is_deleted and not ignore_deleted else '',
                        escape(entity)
                    )

    #return entity.allowed_unicode(user)
    return settings.HIDDEN_VALUE

@register.inclusion_tag('creme_core/templatetags/widgets/select_or_msg.html')
def widget_select_or_msg(items, void_msg):
    return {'items': items, 'void_msg': void_msg}

def _get_image_path_for_model(theme, model, size):
    path = icon_registry.get(model, ICON_SIZE_MAP[size])

    if not path:
        return ''

    try:
        path = get_creme_media_url(theme, path)
    except KeyError:
        path = ''

    return path

def _get_image_for_model(theme, model, size):
    path = _get_image_path_for_model(theme, model, size)
    return u'<img src="%(src)s" alt="%(title)s" title="%(title)s" />' % {
                    #'src':   media_url(path),
                    'src':   path,
                    'title': model._meta.verbose_name,
                }

@register.simple_tag(takes_context=True)
def get_image_for_object(context, obj, size): #size='default' ??
    """{% get_image_for_object object 'big' %}"""
    return _get_image_for_model(context['THEME_NAME'], obj.__class__, size)

@register.simple_tag(takes_context=True)
def get_image_for_ctype(context, ctype, size):
    """{% get_image_for_ctype ctype 'small' %}"""
    return _get_image_for_model(context['THEME_NAME'], ctype.model_class(), size)

@register.simple_tag(takes_context=True)
def get_image_path_for_ctype(context, ctype, size):
    """{% get_image_path_for_ctype ctype 'small' %}"""
    return _get_image_path_for_model(context['THEME_NAME'], ctype.model_class(), size)
