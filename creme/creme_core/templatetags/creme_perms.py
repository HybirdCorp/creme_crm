################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2023-2025  Hybird
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

from django import template

register = template.Library()


@register.filter
def has_perm_to_create(user, ctype):
    return user.has_perm_to_create(ctype)


@register.filter
def has_perm_to_export(user, ctype):
    return user.has_perm_to_export(ctype)


@register.filter
def has_perm_to_list(user, ctype):
    return user.has_perm_to_list(ctype)


@register.filter
def has_perm_to_view(user, entity):
    return user.has_perm_to_view(entity)


@register.filter
def has_perm_to_change(user, entity):
    return user.has_perm_to_change(entity)


@register.filter
def has_perm_to_delete(user, entity):
    return user.has_perm_to_delete(entity)


@register.filter
def has_perm_to_link(user, entity_or_ctype):
    return user.has_perm_to_link(entity_or_ctype)


@register.filter
def has_perm_to_unlink(user, entity):
    return user.has_perm_to_unlink(entity)


@register.filter
def has_perm_to_access(user, app_label):
    return user.has_perm_to_access(app_label)


@register.filter
def has_perm_to_admin(user, app_label):
    return user.has_perm_to_admin(app_label)


@register.filter
def has_special_perm(user, special_perm):
    return user.has_special_perm(special_perm)
