# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2021  Hybird
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

from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _

from creme.creme_core.core.exceptions import ConflictError
from creme.creme_core.models import CremePropertyType
from creme.persons.views import contact as contact_views

from .. import gui
from ..constants import PROP_IS_A_SALESMAN


class SalesManCreation(contact_views.ContactCreation):
    title = _('Create a salesman')
    submit_label = _('Save the salesman')

    def check_view_permissions(self, user):
        super().check_view_permissions(user=user)

        ptype = get_object_or_404(CremePropertyType, id=PROP_IS_A_SALESMAN)

        if not ptype.enabled:
            raise ConflictError(
                gettext(
                    'The property type «{}» is disabled; you should enable it '
                    'or remove the menu entries referencing salesmen.'
                ).format(ptype.text)
            )

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['forced_ptypes'] = [PROP_IS_A_SALESMAN]

        return kwargs


class SalesMenList(contact_views.ContactsList):
    title = _('List of salesmen')
    internal_q = Q(properties__type=PROP_IS_A_SALESMAN)

    def get_buttons(self):
        return super().get_buttons()\
                      .replace(old=gui.CreationButton, new=gui.SalesManCreationButton)
