# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2013  Hybird
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
from django.forms.util import ValidationError
from django.utils.translation import ugettext as _

from ..utils import entities2unicode


def validate_editable_entities(entities, user):
    has_perm = user.has_perm_to_change
    uneditable = entities2unicode((e for e in entities if not has_perm(e)), user)

    if uneditable:
        raise ValidationError(_(u"Some entities are not editable: %s") % uneditable)

    return entities

#TODO: factorise ??
def validate_linkable_entities(entities, user):
    has_perm = user.has_perm_to_link
    unlinkable = entities2unicode((e for e in entities if not has_perm(e)), user)

    if unlinkable:
        raise ValidationError(_(u"Some entities are not linkable: %s") % unlinkable)

    return entities

def validate_linkable_entity(entity, user):
    try:
        user.has_perm_to_link_or_die(entity)
    except PermissionDenied as e:
        raise ValidationError(unicode(e))

    return entity

def validate_linkable_model(model, user, owner):
    if not user.has_perm_to_link(model, owner=owner):
        raise ValidationError(_(u'You are not allowed to link with the «%s» of this user.') %
                                    model._meta.verbose_name_plural
                             )

    return owner
