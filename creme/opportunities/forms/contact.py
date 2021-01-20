# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2019-2021  Hybird
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

from django.db.transaction import atomic
from django.forms.fields import BooleanField
from django.utils.translation import gettext as _

from creme import persons
from creme.creme_core.forms.base import CremeEntityQuickForm
from creme.creme_core.models import Relation
from creme.persons.constants import REL_SUB_EMPLOYED_BY

Contact = persons.get_contact_model()


# NB: not CremeEntityForm to ignore custom fields, relations & properties
class RelatedContactForm(CremeEntityQuickForm):
    class Meta:
        model = Contact
        fields = ('user', 'last_name', 'first_name', 'phone', 'email')

    def __init__(self, opportunity, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.opportunity = opportunity

        target = opportunity.target

        if isinstance(target, persons.get_organisation_model()):
            has_perm = self.user.has_perm_to_link

            # TODO: Label() if not allowed ?
            if has_perm(target) and has_perm(Contact):
                self.fields['is_employed'] = BooleanField(
                    label=_('Is employed by «{}»?').format(opportunity.target),
                    required=False,
                )

    @atomic
    def save(self, *args, **kwargs):
        contact = super().save(*args, **kwargs)

        if self.cleaned_data.get('is_employed', False):
            Relation.objects.create(
                user=self.user,
                subject_entity=contact,
                type_id=REL_SUB_EMPLOYED_BY,
                object_entity=self.opportunity.target,
            )

        return contact
