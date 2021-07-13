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

from typing import Type, Union

from django import forms
from django.db.models.query_utils import Q
from django.db.transaction import atomic
from django.http import HttpResponse
from django.urls import reverse
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _

from creme.creme_core.core.exceptions import ConflictError
from creme.creme_core.forms import validators
from creme.creme_core.gui.custom_form import CustomFormDescriptor
from creme.creme_core.gui.listview import CreationButton
from creme.creme_core.models import Relation
from creme.creme_core.utils import get_from_POST_or_404
from creme.creme_core.views import generic

from .. import constants, custom_forms, get_organisation_model
from ..forms import organisation as orga_forms

Organisation = get_organisation_model()


# class OrganisationCreationBase(generic.EntityCreation):
class OrganisationCreation(generic.EntityCreation):
    model = Organisation
    form_class: Union[Type[forms.BaseForm], CustomFormDescriptor] = \
        custom_forms.ORGANISATION_CREATION_CFORM


# class OrganisationCreation(OrganisationCreationBase):
#     pass


# class CustomerCreation(OrganisationCreationBase):
class CustomerCreation(OrganisationCreation):
    title = _('Create a suspect / prospect / customer')

    def check_view_permissions(self, user):
        super().check_view_permissions(user=user)
        user.has_perm_to_link_or_die(Organisation)

    def get_form_class(self):
        form_cls = super().get_form_class()

        class CustomerForm(form_cls):
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
                    (constants.REL_SUB_PROSPECT, _('Is a prospect')),
                    (constants.REL_SUB_SUSPECT, _('Is a suspect')),
                ),
            )

            blocks = form_cls.blocks.new({
                'id': 'customer_relation',
                'label': _('Suspect / prospect / customer'),
                'fields': ('customers_managed_orga', 'customers_rtypes'),
                'order': 0,
            })

            def _get_relations_to_create(this):
                instance = this.instance
                cdata = this.cleaned_data

                return super()._get_relations_to_create().extend(
                    Relation(
                        user=instance.user,
                        subject_entity=instance,
                        type_id=rtype_id,
                        object_entity=cdata['customers_managed_orga'],
                    ) for rtype_id in cdata['customers_rtypes']
                )

            def clean_customers_managed_orga(this):
                return validators.validate_linkable_entity(
                    entity=this.cleaned_data['customers_managed_orga'],
                    user=this.user,
                )

            def clean_user(this):
                super().clean_user()

                return validators.validate_linkable_model(
                    model=Organisation, user=this.user, owner=this.cleaned_data['user'],
                )

        return CustomerForm


class OrganisationDetail(generic.EntityDetail):
    model = Organisation
    template_name = 'persons/view_organisation.html'
    pk_url_kwarg = 'orga_id'


class OrganisationEdition(generic.EntityEdition):
    model = Organisation
    form_class: Union[Type[forms.BaseForm], CustomFormDescriptor] = \
        custom_forms.ORGANISATION_EDITION_CFORM
    pk_url_kwarg = 'orga_id'


class OrganisationsList(generic.EntitiesList):
    model = Organisation
    default_headerfilter_id = constants.DEFAULT_HFILTER_ORGA


# TODO: set the HF in the url ?
class MyLeadsAndMyCustomersList(OrganisationsList):
    title = _('List of my suspects / prospects / customers')
    default_headerfilter_id = constants.DEFAULT_HFILTER_ORGA_CUSTOMERS

    def get_buttons(self):
        # TODO: disable if cannot link
        class CustomerCreationButton(CreationButton):
            def get_label(this, request, model):
                return CustomerCreation.title

            def get_url(this, request, model):
                return reverse('persons__create_customer')  # TODO: attribute ?

        return super().get_buttons()\
                      .replace(old=CreationButton, new=CustomerCreationButton)

    def get_internal_q(self):
        return Q(
            relations__type__in=(
                constants.REL_SUB_CUSTOMER_SUPPLIER,
                constants.REL_SUB_PROSPECT,
                constants.REL_SUB_SUSPECT,
            ),
            relations__object_entity__in=[
                o.id for o in Organisation.objects.filter_managed_by_creme()
            ],
        )


class ManagedOrganisationsAdding(generic.CremeFormPopup):
    form_class = orga_forms.ManagedOrganisationsForm
    permissions = 'creme_core.can_admin'
    title = _('Add some managed organisations')
    submit_label = _('Save the modifications')


class OrganisationUnmanage(generic.base.EntityRelatedMixin, generic.CheckedView):
    permissions = 'creme_core.can_admin'
    entity_classes = Organisation
    organisation_id_arg = 'id'

    def build_related_entity_queryset(self, model):
        return super().build_related_entity_queryset(model=model).filter(is_managed=True)

    def get_related_entity_id(self):
        return get_from_POST_or_404(self.request.POST, self.organisation_id_arg, cast=int)

    def post(self, *args, **kwargs):
        orga = self.get_related_entity()

        with atomic():
            self.update(orga)

        return HttpResponse()

    def update(self, orga) -> None:
        ids = (
            type(orga).objects
                      .select_for_update()
                      .filter(is_managed=True)
                      .values_list('id', flat=True)
        )

        if orga.id in ids:  # In case a concurrent call to this view has been done
            if len(ids) >= 2:
                orga.is_managed = False
                orga.save()
            else:
                raise ConflictError(
                    gettext('You must have at least one managed organisation.')
                )
