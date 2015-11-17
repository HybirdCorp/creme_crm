# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2015  Hybird
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

# from django.core.urlresolvers import reverse
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.utils.translation import ugettext_lazy as _, ugettext

from creme.creme_core.auth import build_creation_perm as cperm
from creme.creme_core.auth.decorators import login_required, permission_required
from creme.creme_core.utils import get_from_POST_or_404
from creme.creme_core.views.decorators import require_model_fields
from creme.creme_core.views.generic import (add_entity, add_to_entity,
        edit_entity, view_entity, list_view)

from creme.persons import get_contact_model, get_organisation_model

from .. import get_mailinglist_model
from ..forms.mailing_list import (MailingListForm, AddChildForm,
        AddContactsForm, AddOrganisationsForm,
        AddContactsFromFilterForm, AddOrganisationsFromFilterForm)
#from ..models import MailingList


Contact      = get_contact_model()
Organisation = get_organisation_model()
MailingList  = get_mailinglist_model()


def abstract_add_mailinglist(request, form=MailingListForm,
                             submit_label=_('Save the mailing list')
                            ):
    return add_entity(request, form,
                      extra_template_dict={'submit_label': submit_label},
                     )


def abstract_edit_mailinglist(request, ml_id, form=MailingListForm):
    return edit_entity(request, ml_id, MailingList, form)


def abstract_view_mailinglist(request, ml_id,
                              template='emails/view_mailing_list.html'
                             ):
    return view_entity(request, ml_id, MailingList, template=template,
                       # '/emails/mailing_list',
                      )


@login_required
# @permission_required(('emails', 'emails.add_mailinglist'))
@permission_required(('emails', cperm(MailingList)))
def add(request):
    return abstract_add_mailinglist(request)


@login_required
@permission_required('emails')
def edit(request, ml_id):
    return abstract_edit_mailinglist(request, ml_id)


@login_required
@permission_required('emails')
def detailview(request, ml_id):
    return abstract_view_mailinglist(request, ml_id)


@login_required
@permission_required('emails')
def listview(request):
    return list_view(request, MailingList,
                     # extra_dict={'add_url': '/emails/mailing_list/add'}
                     # extra_dict={'add_url': reverse('emails__create_mlist')},
                    )


@login_required
@permission_required('emails')
@require_model_fields(Contact, 'email')
def add_contacts(request, ml_id):
    return add_to_entity(request, ml_id, AddContactsForm,
                         ugettext(u'New contacts for «%s»'),
                         entity_class=MailingList,
                         submit_label=_('Link the contacts'),
                        )


@login_required
@permission_required('emails')
@require_model_fields(Contact, 'email')
def add_contacts_from_filter(request, ml_id):
    return add_to_entity(request, ml_id, AddContactsFromFilterForm,
                         ugettext(u'New contacts for «%s»'),
                         entity_class=MailingList,
                         submit_label=_('Link the contacts'),
                        )


@login_required
@permission_required('emails')
@require_model_fields(Organisation, 'email')
def add_organisations(request, ml_id):
    return add_to_entity(request, ml_id, AddOrganisationsForm,
                         ugettext(u'New organisations for «%s»'),
                         entity_class=MailingList,
                         submit_label=_('Link the organisations'),
                        )


@login_required
@permission_required('emails')
@require_model_fields(Organisation, 'email')
def add_organisations_from_filter(request, ml_id):
    return add_to_entity(request, ml_id, AddOrganisationsFromFilterForm,
                         ugettext(u'New organisations for «%s»'),
                         entity_class=MailingList,
                         submit_label=_('Link the organisations'),
                        )


@login_required
@permission_required('emails')
def add_children(request, ml_id):
    return add_to_entity(request, ml_id, AddChildForm,
                         ugettext(u'New child lists for «%s»'),
                         entity_class=MailingList,
                         submit_label=_('Link the mailing lists'),
                        )


# TODO: Conflict error if 'email' field is hidden ?
@login_required
@permission_required('emails')
def _delete_aux(request, ml_id, deletor):
    subobject_id = get_from_POST_or_404(request.POST, 'id')
    ml = get_object_or_404(MailingList, pk=ml_id)

    request.user.has_perm_to_change_or_die(ml)

    deletor(ml, subobject_id)

    if request.is_ajax():
        return HttpResponse("", content_type="text/javascript")

    return redirect(ml)


def delete_contact(request, ml_id):
    return _delete_aux(request, ml_id, lambda ml, contact_id: ml.contacts.remove(contact_id))


def delete_organisation(request, ml_id):
    return _delete_aux(request, ml_id, lambda ml, orga_id: ml.organisations.remove(orga_id))


def delete_child(request, ml_id):
    return _delete_aux(request, ml_id, lambda ml, child_id: ml.children.remove(child_id))
