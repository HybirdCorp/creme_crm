# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2016  Hybird
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

from django.core.exceptions import PermissionDenied
from django.forms.utils import ValidationError
from django.utils.translation import ugettext as _, ugettext_lazy

from ..utils import entities2unicode

def validate_authenticated_user(user, message, code, **kwargs):
    if user is None or not user.is_authenticated():
        raise ValidationError(message.format(**kwargs), code=code)

# TODO: factorise
# VIEW ----------------------
def validate_viewable_entity(entity, user, code='viewnotallowed'):
    validate_authenticated_user(user, ugettext_lazy(u'Not authenticated user is not allowed to view entities'), code)

    try:
        user.has_perm_to_view_or_die(entity)
    except PermissionDenied as e:
        raise ValidationError(unicode(e), code=code)

    return entity


def validate_viewable_entities(entities, user, code='viewnotallowed'):
    validate_authenticated_user(user, ugettext_lazy(u'Not authenticated user is not allowed to view entities'), code)

    has_perm = user.has_perm_to_view
    unviewable = entities2unicode((e for e in entities if not has_perm(e)), user)

    if unviewable:
        raise ValidationError(_(u'Some entities are not viewable: %s') % unviewable, code=code)

    return entities


# CHANGE ----------------------
def validate_editable_entity(entity, user, code='changenotallowed'):
    validate_authenticated_user(user, ugettext_lazy(u'Not authenticated user is not allowed to edit entities'), code)

    try:
        user.has_perm_to_change_or_die(entity)
    except PermissionDenied as e:
        raise ValidationError(unicode(e), code=code)

    return entity


def validate_editable_entities(entities, user, code='changenotallowed'):
    validate_authenticated_user(user, ugettext_lazy(u'Not authenticated user is not allowed to edit entities'), code)

    has_perm = user.has_perm_to_change
    uneditable = entities2unicode((e for e in entities if not has_perm(e)), user)

    if uneditable:
        raise ValidationError(_(u'Some entities are not editable: %s') % uneditable, code=code)

    return entities


# LINK ----------------------
def validate_linkable_entity(entity, user, code='linknotallowed'):
    validate_authenticated_user(user, ugettext_lazy(u'Not authenticated user is not allowed to link entities'), code)

    try:
        user.has_perm_to_link_or_die(entity)
    except PermissionDenied as e:
        raise ValidationError(unicode(e), code=code)

    return entity


def validate_linkable_entities(entities, user, code='linknotallowed'):
    validate_authenticated_user(user, ugettext_lazy(u'Not authenticated user is not allowed to link entities'), code)

    has_perm = user.has_perm_to_link
    unlinkable = entities2unicode((e for e in entities if not has_perm(e)), user)

    if unlinkable:
        raise ValidationError(_(u'Some entities are not linkable: %s') % unlinkable, code=code)

    return entities


def validate_linkable_model(model, user, owner, code='linknotallowed'):
    validate_authenticated_user(user, ugettext_lazy(u'Not authenticated user is not allowed to link «{model}»'),
                                code=code,
                                model=model._meta.verbose_name_plural)

    if not user.has_perm_to_link(model, owner=owner):
        raise ValidationError(_(u'You are not allowed to link with the «%s» of this user.') %
                                    model._meta.verbose_name_plural,
                              code=code,
                             )

    return owner
