# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2018  Hybird
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

from django.utils.translation import ugettext_lazy as _

from creme.creme_core.auth.entity_credentials import EntityCredentials
from creme.creme_core.forms import CremeForm, MultiCreatorEntityField

from .. import get_organisation_model
from .base import _BasePersonForm


class OrganisationForm(_BasePersonForm):
    class Meta(_BasePersonForm.Meta):
        model = get_organisation_model()


class ManagedOrganisationsForm(CremeForm):
    organisations = MultiCreatorEntityField(label=_(u'Set as managed'),
                                            model=get_organisation_model(),
                                            credentials=EntityCredentials.CHANGE,
                                            q_filter={'is_managed': False},
                                            # Created Organisations are never already managed, so it's a not a problem.
                                            force_creation=True,
                                           )

    def save(self, *args, **kwargs):
        for organisation in self.cleaned_data['organisations']:
            organisation.is_managed = True
            organisation.save(*args, **kwargs)
