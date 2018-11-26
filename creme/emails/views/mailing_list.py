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

import warnings

from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.utils.decorators import method_decorator
from django.utils.translation import ugettext_lazy as _  # ugettext

from creme.creme_core.auth import build_creation_perm as cperm
from creme.creme_core.auth.decorators import login_required, permission_required
from creme.creme_core.utils import get_from_POST_or_404
from creme.creme_core.views import generic
from creme.creme_core.views.decorators import require_model_fields

from creme import persons

from .. import get_mailinglist_model
from ..constants import DEFAULT_HFILTER_MAILINGLIST
from ..forms import mailing_list as ml_forms


Contact      = persons.get_contact_model()
Organisation = persons.get_organisation_model()
MailingList  = get_mailinglist_model()

# Function views --------------------------------------------------------------


def abstract_add_mailinglist(request, form=ml_forms.MailingListForm,
                             submit_label=MailingList.save_label,
                            ):
    warnings.warn('emails.views.mailing_list.abstract_add_mailinglist() is deprecated ; '
                  'use the class-based view MailingListCreation instead.',
                  DeprecationWarning
                 )
    return generic.add_entity(request, form,
                              extra_template_dict={'submit_label': submit_label},
                             )


def abstract_edit_mailinglist(request, ml_id, form=ml_forms.MailingListForm):
    warnings.warn('emails.views.mailing_list.abstract_edit_mailinglist() is deprecated ; '
                  'use the class-based view MailingListEdition instead.',
                  DeprecationWarning
                 )
    return generic.edit_entity(request, ml_id, MailingList, form)


def abstract_view_mailinglist(request, ml_id,
                              template='emails/view_mailing_list.html',
                             ):
    warnings.warn('emails.views.mailing_list.abstract_view_mailinglist() is deprecated ; '
                  'use the class-based view MailingListDetail instead.',
                  DeprecationWarning
                 )
    return generic.view_entity(request, ml_id, MailingList, template=template)


@login_required
@permission_required(('emails', cperm(MailingList)))
def add(request):
    warnings.warn('emails.views.mailing_list.add() is deprecated.', DeprecationWarning)
    return abstract_add_mailinglist(request)


@login_required
@permission_required('emails')
def edit(request, ml_id):
    warnings.warn('emails.views.mailing_list.edit() is deprecated.', DeprecationWarning)
    return abstract_edit_mailinglist(request, ml_id)


@login_required
@permission_required('emails')
def detailview(request, ml_id):
    warnings.warn('emails.views.mailing_list.detailview() is deprecated.', DeprecationWarning)
    return abstract_view_mailinglist(request, ml_id)


@login_required
@permission_required('emails')
def listview(request):
    return generic.list_view(request, MailingList, hf_pk=DEFAULT_HFILTER_MAILINGLIST)

# @login_required
# @permission_required('emails')
# @require_model_fields(Contact, 'email')
# def add_contacts(request, ml_id):
#     return generic.add_to_entity(
#         request, ml_id, ml_forms.AddContactsForm,
#         ugettext('New contacts for «%s»'),
#         entity_class=MailingList,
#         submit_label=_('Link the contacts'),  # todo: multi_link_label ??
#         template='creme_core/generics/blockform/link_popup.html',
#     )

# @login_required
# @permission_required('emails')
# @require_model_fields(Contact, 'email')
# def add_contacts_from_filter(request, ml_id):
#     return generic.add_to_entity(
#         request, ml_id, ml_forms.AddContactsFromFilterForm,
#         ugettext('New contacts for «%s»'),
#         entity_class=MailingList,
#         submit_label=_('Link the contacts'),
#         template='creme_core/generics/blockform/link_popup.html',
#     )

# @login_required
# @permission_required('emails')
# @require_model_fields(Organisation, 'email')
# def add_organisations(request, ml_id):
#     return generic.add_to_entity(
#         request, ml_id, ml_forms.AddOrganisationsForm,
#         ugettext('New organisations for «%s»'),
#         entity_class=MailingList,
#         submit_label=_('Link the organisations'),
#         template='creme_core/generics/blockform/link_popup.html',
#     )

# @login_required
# @permission_required('emails')
# @require_model_fields(Organisation, 'email')
# def add_organisations_from_filter(request, ml_id):
#     return generic.add_to_entity(
#         request, ml_id, ml_forms.AddOrganisationsFromFilterForm,
#         ugettext('New organisations for «%s»'),
#         entity_class=MailingList,
#         submit_label=_('Link the organisations'),
#         template='creme_core/generics/blockform/link_popup.html',
#     )

# @login_required
# @permission_required('emails')
# def add_children(request, ml_id):
#     return generic.add_to_entity(
#         request, ml_id, ml_forms.AddChildForm,
#         ugettext('New child lists for «%s»'),
#         entity_class=MailingList,
#         submit_label=_('Link the mailing list'),
#         template='creme_core/generics/blockform/link_popup.html',
#     )


# TODO: Conflict error if 'email' field is hidden ?
@login_required
@permission_required('emails')
def _delete_aux(request, ml_id, deletor):
    subobject_id = get_from_POST_or_404(request.POST, 'id')
    ml = get_object_or_404(MailingList, pk=ml_id)

    request.user.has_perm_to_change_or_die(ml)

    deletor(ml, subobject_id)

    if request.is_ajax():
        return HttpResponse()

    return redirect(ml)


def delete_contact(request, ml_id):
    return _delete_aux(request, ml_id, lambda ml, contact_id: ml.contacts.remove(contact_id))


def delete_organisation(request, ml_id):
    return _delete_aux(request, ml_id, lambda ml, orga_id: ml.organisations.remove(orga_id))


def delete_child(request, ml_id):
    return _delete_aux(request, ml_id, lambda ml, child_id: ml.children.remove(child_id))


# Class-based views  ----------------------------------------------------------

class MailingListCreation(generic.EntityCreation):
    model = MailingList
    form_class = ml_forms.MailingListForm


class MailingListDetail(generic.EntityDetail):
    model = MailingList
    template_name = 'emails/view_mailing_list.html'
    pk_url_kwarg = 'ml_id'


class MailingListEdition(generic.EntityEdition):
    model = MailingList
    form_class = ml_forms.MailingListForm
    pk_url_kwarg = 'ml_id'


class _AddingToMailingList(generic.RelatedToEntityFormPopup):
    template_name = 'creme_core/generics/blockform/link-popup.html'
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
