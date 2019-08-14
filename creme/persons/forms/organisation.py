# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2019  Hybird
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

from django import forms
from django.utils.translation import gettext_lazy as _

from creme.creme_core import forms as core_corms
from creme.creme_core.auth.entity_credentials import EntityCredentials
from creme.creme_core.forms import validators
from creme.creme_core.models import Relation

from .. import get_organisation_model, constants

from .base import _BasePersonForm

Organisation = get_organisation_model()


class _OrganisationBaseForm(_BasePersonForm):
    class Meta(_BasePersonForm.Meta):
        model = get_organisation_model()


class OrganisationForm(_OrganisationBaseForm):
    pass


class CustomerForm(_OrganisationBaseForm):
    # TODO: manage not viewable organisations (should not be very useful anyway)
    customers_managed_orga = forms.ModelChoiceField(
        label=_('Related managed organisation'),
        queryset=Organisation.objects.filter_managed_by_creme(),
        empty_label=None,
    )
    customers_rtypes = forms.MultipleChoiceField(
        label=_('Relationships'),
        choices=(
            (constants.REL_SUB_CUSTOMER_SUPPLIER, _('Is a customer')),
            (constants.REL_SUB_PROSPECT,          _('Is a prospect')),
            (constants.REL_SUB_SUSPECT,           _('Is a suspect')),
        ),
    )

    blocks = _OrganisationBaseForm.blocks.new(
        ('customer_relation', _('Suspect / prospect / customer'),
         ('customers_managed_orga', 'customers_rtypes')
        ),
    )

    def _get_relations_to_create(self):
        instance = self.instance
        cdata = self.cleaned_data

        return super()._get_relations_to_create().extend(
            Relation(
                user=instance.user,
                subject_entity=instance,
                type_id=rtype_id,
                object_entity=cdata['customers_managed_orga'],
            ) for rtype_id in cdata['customers_rtypes']
        )

    def clean_customers_managed_orga(self):
        return validators.validate_linkable_entity(
            entity=self.cleaned_data['customers_managed_orga'],
            user=self.user,
        )

    def clean_user(self):
        return validators.validate_linkable_model(
            model=Organisation, user=self.user, owner=self.cleaned_data['user'],
        )


class ManagedOrganisationsForm(core_corms.CremeForm):
    organisations = core_corms.MultiCreatorEntityField(
        label=_('Set as managed'),
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
