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
from django.db.models import ForeignKey, Model
from django.utils.translation import gettext_lazy as _

User = get_user_model()


class ConditionDynamicOperand:
    """Represent special value for right operand in conditions."""
    type_id: str  # = None
    verbose_name = ''
    model = Model  # OVERRIDE THIS -- model class related to the operand.

    def __init__(self, user):
        self.user = user

    def resolve(self):
        "Get the effective value  to use in QuerySet."
        raise NotImplementedError()

    def validate(self, *, field, value):
        """Raise a validation error if the value is invalid.

        @param field: Model field.
        @param value: POSTed value.
        @raise: ValidationError.
        """
        field.formfield().clean(value)


class CurrentUserOperand(ConditionDynamicOperand):
    """Special value <Current/logged user (ie "me") & its teams>.
    Operand for condition on fields ForeignKey(CremeUser, ...).
    """
    type_id = '__currentuser__'
    verbose_name = _('Current user')
    model = User

    def resolve(self):
        user = self.user

        if user is None:
            return None

        teams = user.teams

        return [user.id, *(t.id for t in teams)] if teams else user.id

    def validate(self, *, field, value):
        if isinstance(field, ForeignKey) and \
           issubclass(field.remote_field.model, User) and \
           value == self.type_id:
            return

        # return field.formfield().clean(value)
        field.formfield().clean(value)


all_operands = (
    CurrentUserOperand,
)
