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

from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.utils.translation import ugettext_lazy as _, ugettext

from creme.creme_core.auth import build_creation_perm as cperm
from creme.creme_core.auth.decorators import login_required, permission_required
from creme.creme_core.views.generic import (add_entity, add_to_entity,
        edit_entity, view_entity, list_view)
from creme.creme_core.utils import get_from_POST_or_404

from .. import get_messaginglist_model
from ..constants import DEFAULT_HFILTER_MLIST
from ..forms.messaging_list import MessagingListForm, AddContactsForm, AddContactsFromFilterForm


MessagingList = get_messaginglist_model()


def abstract_add_messaginglist(request, form=MessagingListForm,
                               submit_label=MessagingList.save_label,
                              ):
    return add_entity(request, form,
                      extra_template_dict={'submit_label': submit_label},
                     )


def abstract_edit_messaginglist(request, mlist_id, form=MessagingListForm):
    return edit_entity(request, mlist_id, MessagingList, form)


def abstract_view_messaginglist(request, mlist_id,
                                template='sms/view_messaginglist.html',
                               ):
    return view_entity(request, mlist_id, MessagingList, template=template)


@login_required
# @permission_required(('sms', 'sms.add_messaginglist'))
@permission_required(('sms', cperm(MessagingList)))
def add(request):
    return abstract_add_messaginglist(request)


@login_required
@permission_required('sms')
def edit(request, mlist_id):
    return abstract_edit_messaginglist(request, mlist_id)


@login_required
@permission_required('sms')
def detailview(request, mlist_id):
    return abstract_view_messaginglist(request, mlist_id)


@login_required
@permission_required('sms')
def listview(request):
    return list_view(request, MessagingList, hf_pk=DEFAULT_HFILTER_MLIST)


@login_required
@permission_required('sms')
def add_contacts(request, mlist_id):
    return add_to_entity(request, mlist_id, AddContactsForm,
                         ugettext(u'New contacts for «%s»'),
                         entity_class=MessagingList,
                         submit_label=_(u'Link the contacts'),
                         template='creme_core/generics/blockform/link_popup.html',
                        )


@login_required
@permission_required('sms')
def add_contacts_from_filter(request, mlist_id):
    return add_to_entity(request, mlist_id, AddContactsFromFilterForm,
                         ugettext(u'New contacts for «%s»'),
                         entity_class=MessagingList,
                         submit_label=_(u'Link the contacts'),
                         template='creme_core/generics/blockform/link_popup.html',
                        )


@login_required
@permission_required('sms')
def _delete_aux(request, mlist_id, deletor):
    subobject_id   = get_from_POST_or_404(request.POST, 'id')
    messaging_list = get_object_or_404(MessagingList, pk=mlist_id)

    request.user.has_perm_to_change_or_die(messaging_list)

    deletor(messaging_list, subobject_id)

    if request.is_ajax():
        # return HttpResponse('', content_type='text/javascript')
        return HttpResponse()

    return redirect(messaging_list)


def delete_contact(request, mlist_id):
    return _delete_aux(request, mlist_id, lambda ml, contact_id: ml.contacts.remove(contact_id))
