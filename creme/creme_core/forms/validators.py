# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2011  Hybird
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

from creme_core.models import CremeEntity
from creme_core.utils import entities2unicode


def validate_editable_entities(entities, user):
    CremeEntity.populate_credentials(entities, user)

    uneditable = entities2unicode((e for e in entities if not e.can_change(user)), user)

    if uneditable:
        raise ValidationError(_(u"Some entities are not editable: %s") % uneditable)

    return entities

#TODO: factorise ??
def validate_linkable_entities(entities, user):
    CremeEntity.populate_credentials(entities, user)

    unlinkable = entities2unicode((e for e in entities if not e.can_link(user)), user)

    if unlinkable:
        raise ValidationError(_(u"Some entities are not linkable: %s") % unlinkable)

    return entities

def validate_linkable_entity(entity, user):
    try:
        entity.can_link_or_die(user)
    except PermissionDenied, e:
        raise ValidationError(unicode(e))

    return entity
