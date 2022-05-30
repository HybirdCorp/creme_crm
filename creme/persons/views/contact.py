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

from typing import Optional, Type, Union

from django import forms
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _

from creme import persons
from creme.creme_core.core.exceptions import ConflictError
from creme.creme_core.forms.validators import validate_linkable_model
from creme.creme_core.gui.custom_form import CustomFormDescriptor
from creme.creme_core.models import Relation, RelationType
from creme.creme_core.views import generic

from .. import custom_forms
from ..constants import DEFAULT_HFILTER_CONTACT
from ..forms import contact as c_forms
from ..models import AbstractOrganisation

Contact = persons.get_contact_model()
Organisation = persons.get_organisation_model()


class _ContactBaseCreation(generic.EntityCreation):
    model = Contact
    form_class: Union[Type[forms.BaseForm], CustomFormDescriptor] = \
        custom_forms.CONTACT_CREATION_CFORM


class ContactCreation(_ContactBaseCreation):
    pass


class RelatedContactCreation(_ContactBaseCreation):
    title = _('Create a contact related to «{organisation}»')
    orga_id_url_kwarg = 'orga_id'
    rtype_id_url_kwarg = 'rtype_id'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.linked_orga = None

    def get(self, *args, **kwargs):
        self.linked_orga = self.get_linked_orga()
        return super().get(*args, **kwargs)

    def post(self, *args, **kwargs):
        self.linked_orga = self.get_linked_orga()
        return super().post(*args, **kwargs)

    def check_view_permissions(self, user):
        super(RelatedContactCreation, self).check_view_permissions(user=user)
        self.request.user.has_perm_to_link_or_die(Contact)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()

        rtype = self.get_rtype()
        if rtype:
            kwargs['forced_relations'] = [
                Relation(object_entity=self.linked_orga, type=rtype),
            ]

        return kwargs

    def get_form_class(self):
        form_cls = super().get_form_class()
        rtype = self.get_rtype()

        if rtype:
            return form_cls

        linked_orga = self.linked_orga
        get_ct = ContentType.objects.get_for_model

        class RelatedContactForm(form_cls):
            rtype_for_organisation = forms.ModelChoiceField(
                label=gettext('Status in «{organisation}»').format(
                    organisation=linked_orga,
                ),
                # TODO: factorise (see User form hooking)
                queryset=RelationType.objects.filter(
                    subject_ctypes=get_ct(Contact),
                    symmetric_type__subject_ctypes=get_ct(Organisation),
                    is_internal=False,
                ),
            )

            blocks = form_cls.blocks.new({
                'id': 'relation_to_orga',
                'label': 'Status in organisation',
                'fields': ['rtype_for_organisation'],
                'order': 0,
            })

            def clean_rtype_for_organisation(this):
                rtype = this.cleaned_data['rtype_for_organisation']

                this._check_properties([rtype])  # Checks subject's properties

                needed_object_ptypes = rtype.object_properties.all()
                if needed_object_ptypes:
                    object_prop_ids = {
                        prop.type_id for prop in self.linked_orga.get_properties()
                    }
                    object_missing_ptypes = [
                        ptype
                        for ptype in needed_object_ptypes
                        if ptype.id not in object_prop_ids
                    ]

                    if object_missing_ptypes:
                        raise ValidationError(
                            gettext(
                                'The entity «%(entity)s» has no property «%(property)s» which is '
                                'required by the relationship «%(predicate)s».'
                            ) % {
                                'entity': self.linked_orga,
                                'property': object_missing_ptypes[0],
                                'predicate': rtype.predicate,
                            }
                        )

                return rtype

            def clean_user(this):
                super().clean_user()

                return validate_linkable_model(
                    Contact, this.user, owner=this.cleaned_data['user'],
                )

            def _get_relations_to_create(this):
                relations = super()._get_relations_to_create()
                rtype = this.cleaned_data.get('rtype_for_organisation')
                instance = this.instance

                if rtype:
                    relations.append(Relation(
                        subject_entity=instance,
                        type=rtype,
                        object_entity=self.linked_orga,
                        user=instance.user,
                    ))

                return relations

        return RelatedContactForm

    def get_linked_orga(self) -> AbstractOrganisation:
        orga = get_object_or_404(Organisation, id=self.kwargs[self.orga_id_url_kwarg])

        user = self.request.user
        user.has_perm_to_view_or_die(orga)  # Displayed in the form....
        user.has_perm_to_link_or_die(orga)

        return orga

    def get_rtype(self) -> Optional[RelationType]:
        rtype_id = self.kwargs.get(self.rtype_id_url_kwarg)

        if rtype_id:
            rtype = get_object_or_404(RelationType, id=rtype_id)

            if rtype.is_internal:
                raise ConflictError(
                    'This RelationType cannot be used because it is internal.'
                )

            if not rtype.is_compatible(self.linked_orga):
                raise ConflictError(
                    'This RelationType is not compatible with Organisation as subject'
                )

            if not rtype.symmetric_type.is_compatible(Contact):
                raise ConflictError(
                    'This RelationType is not compatible with Contact as relationship-object'
                )

            return rtype.symmetric_type

        return None

    # def get_success_url(self):
    #     return self.linked_orga.get_absolute_url()

    def get_title_format_data(self):
        data = super().get_title_format_data()
        data['organisation'] = self.linked_orga

        return data


class ContactDetail(generic.EntityDetail):
    model = Contact
    template_name = 'persons/view_contact.html'
    pk_url_kwarg = 'contact_id'


class ContactEdition(generic.EntityEdition):
    model = Contact
    form_class: Union[Type[forms.BaseForm], CustomFormDescriptor] = \
        custom_forms.CONTACT_EDITION_CFORM
    pk_url_kwarg = 'contact_id'


class ContactNamesEdition(generic.EntityEditionPopup):
    model = Contact
    form_class: Type[c_forms.ContactNamesForm] = c_forms.ContactNamesForm
    pk_url_kwarg = 'contact_id'


class ContactsList(generic.EntitiesList):
    model = Contact
    default_headerfilter_id = DEFAULT_HFILTER_CONTACT
