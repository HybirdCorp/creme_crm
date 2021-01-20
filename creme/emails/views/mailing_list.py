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

from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _

from creme import persons
from creme.creme_core.utils import get_from_POST_or_404
from creme.creme_core.views import generic
from creme.creme_core.views.decorators import require_model_fields

from .. import custom_forms, get_mailinglist_model
from ..constants import DEFAULT_HFILTER_MAILINGLIST
from ..forms import mailing_list as ml_forms

Contact      = persons.get_contact_model()
Organisation = persons.get_organisation_model()
MailingList  = get_mailinglist_model()


class MailingListCreation(generic.EntityCreation):
    model = MailingList
    form_class = custom_forms.MAILINGLIST_CREATION_CFORM


class MailingListDetail(generic.EntityDetail):
    model = MailingList
    template_name = 'emails/view_mailing_list.html'
    pk_url_kwarg = 'ml_id'


class MailingListEdition(generic.EntityEdition):
    model = MailingList
    form_class = custom_forms.MAILINGLIST_EDITION_CFORM
    pk_url_kwarg = 'ml_id'


class MailingListsList(generic.EntitiesList):
    model = MailingList
    default_headerfilter_id = DEFAULT_HFILTER_MAILINGLIST


class _AddingToMailingList(generic.RelatedToEntityFormPopup):
    template_name = 'creme_core/generics/blockform/link-popup.html'
    permissions = 'emails'
    entity_id_url_kwarg = 'ml_id'
    entity_classes = MailingList


@method_decorator(require_model_fields(Contact, 'email'), name='dispatch')
class ContactsAdding(_AddingToMailingList):
    # model = Contact
    form_class = ml_forms.AddContactsForm
    title = _('New contacts for «{entity}»')
    submit_label = _('Link the contacts')  # TODO: multi_link_label ??


class ContactsAddingFromFilter(ContactsAdding):
    form_class = ml_forms.AddContactsFromFilterForm


@method_decorator(require_model_fields(Organisation, 'email'), name='dispatch')
class OrganisationsAdding(_AddingToMailingList):
    # model = Organisation
    form_class = ml_forms.AddOrganisationsForm
    title = _('New organisations for «{entity}»')
    submit_label = _('Link the organisations')  # TODO: multi_link_label ??


class OrganisationsAddingFromFilter(OrganisationsAdding):
    form_class = ml_forms.AddOrganisationsFromFilterForm


class ChildrenAdding(_AddingToMailingList):
    # model = MailingList
    form_class = ml_forms.AddChildForm
    title = _('New child list for «{entity}»')
    submit_label = _('Link the mailing list')


# TODO: Conflict error if 'email' field is hidden ?
class _RemovingFromMailingList(generic.base.EntityRelatedMixin, generic.CremeDeletion):
    permissions = 'emails'
    entity_classes = MailingList
    entity_id_url_kwarg = 'ml_id'

    obj2del_id_arg = 'id'
    m2m_name = 'SETME'

    def perform_deletion(self, request):
        obj2del_id = get_from_POST_or_404(request.POST, self.obj2del_id_arg)
        getattr(self.get_related_entity(), self.m2m_name).remove(obj2del_id)


class ContactRemoving(_RemovingFromMailingList):
    m2m_name = 'contacts'


class OrganisationRemoving(_RemovingFromMailingList):
    m2m_name = 'organisations'


class ChildRemoving(_RemovingFromMailingList):
    m2m_name = 'children'
