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

from django.shortcuts import get_object_or_404
from django.utils.translation import gettext_lazy as _

from creme.creme_core.core.exceptions import ConflictError
from creme.creme_core.models import RelationType
from creme.creme_core.views import generic

from .. import get_contact_model, get_organisation_model
from ..constants import DEFAULT_HFILTER_CONTACT
from ..forms import contact as c_forms

Contact = get_contact_model()


class _ContactBaseCreation(generic.EntityCreation):
    model = Contact
    form_class = c_forms.ContactForm
    template_name = 'persons/add_contact_form.html'


class ContactCreation(_ContactBaseCreation):
    pass


class RelatedContactCreation(_ContactBaseCreation):
    form_class = c_forms.RelatedContactForm
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
        kwargs['linked_orga'] = self.linked_orga
        kwargs['rtype'] = self.get_rtype()

        return kwargs

    def get_linked_orga(self):
        orga = get_object_or_404(get_organisation_model(),
                                 id=self.kwargs[self.orga_id_url_kwarg],
                                )

        user = self.request.user
        user.has_perm_to_view_or_die(orga)  # Displayed in the form....
        user.has_perm_to_link_or_die(orga)

        return orga

    def get_rtype(self):
        rtype_id = self.kwargs.get(self.rtype_id_url_kwarg)

        if rtype_id:
            rtype = get_object_or_404(RelationType, id=rtype_id)

            if rtype.is_internal:
                raise ConflictError('This RelationType cannot be used because it is internal.')

            if not rtype.is_compatible(self.linked_orga):
                raise ConflictError('This RelationType is not compatible with Organisation as subject')

            if not rtype.symmetric_type.is_compatible(Contact):
                raise ConflictError('This RelationType is not compatible with Contact as relationship-object')

            return rtype.symmetric_type

    def get_success_url(self):
        return self.linked_orga.get_absolute_url()

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
    form_class = c_forms.ContactForm
    template_name = 'persons/edit_contact_form.html'
    pk_url_kwarg = 'contact_id'


class ContactNamesEdition(generic.EntityEditionPopup):
    model = Contact
    form_class = c_forms.ContactNamesForm
    pk_url_kwarg = 'contact_id'


class ContactsList(generic.EntitiesList):
    model = Contact
    default_headerfilter_id = DEFAULT_HFILTER_CONTACT
