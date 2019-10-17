# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2013-2019  Hybird
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

from django.contrib.auth import get_user_model
from django.db.models import ForeignKey
from django.utils.translation import gettext_lazy as _


# class EntityFilterVariable:
class ConditionDynamicOperand:
    """Represent special value for right operand in conditions."""
    # CURRENT_USER = '__currentuser__'
    type_id = None
    verbose_name = ''

    def __init__(self, user):
        self.user = user

    # def resolve(self, value, user=None):
    def resolve(self):
        "Get the effective value  to use in QuerySet."
        raise NotImplementedError()

    # def validate(self, field, value):
    def validate(self, *, field, value):
        """Raise a validation error if the value is invalid.

        @param field: Model field.
        @param value: POSTed value.
        @raise: ValidationError.
        """
        # return field.formfield().clean(value)
        field.formfield().clean(value)


# class _CurrentUserVariable(EntityFilterVariable):
class CurrentUserOperand(ConditionDynamicOperand):
    """Special value <Current/logged user (ie "me") & its teams>.
    Operand for condition on fields ForeignKey(CremeUser, ...).
    """
    type_id = '__currentuser__'
    verbose_name = _('Current user')

    # def resolve(self, value, user=None):
    def resolve(self):
        # return user.pk if user is not None else None
        user = self.user

        if user is None:
            return None

        teams = user.teams

        return [user.id, *(t.id for t in teams)] if teams else user.id

    # def validate(self, field, value):
    #     if not isinstance(field, ForeignKey) or not issubclass(field.remote_field.model, get_user_model()):
    #         return field.formfield().clean(value)
    #
    #     if isinstance(value, str) and value == EntityFilterVariable.CURRENT_USER:
    #         return
    #
    #     return field.formfield().clean(value)
    def validate(self, *, field, value):
        if isinstance(field, ForeignKey) and \
           issubclass(field.remote_field.model, get_user_model()) and \
           value == self.type_id:
            return

        # return field.formfield().clean(value)
        field.formfield().clean(value)


all_operands = (
    CurrentUserOperand,
)