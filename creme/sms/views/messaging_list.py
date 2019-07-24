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

# import warnings

# from django.http import HttpResponse
# from django.shortcuts import get_object_or_404, redirect
from django.utils.translation import gettext_lazy as _

# from creme.creme_core.auth import build_creation_perm as cperm
# from creme.creme_core.auth.decorators import login_required, permission_required
from creme.creme_core.utils import get_from_POST_or_404
from creme.creme_core.views import generic

from .. import get_messaginglist_model
from ..constants import DEFAULT_HFILTER_MLIST
from ..forms import messaging_list as ml_forms

MessagingList = get_messaginglist_model()


# def abstract_add_messaginglist(request, form=ml_forms.MessagingListForm,
#                                submit_label=MessagingList.save_label,
#                               ):
#     warnings.warn('sms.views.messaging_list.abstract_add_messaginglist() is deprecated ; '
#                   'use the class-based view MessagingListDetail instead.',
#                   DeprecationWarning
#                  )
#     return generic.add_entity(request, form,
#                               extra_template_dict={'submit_label': submit_label},
#                              )


# def abstract_edit_messaginglist(request, mlist_id, form=ml_forms.MessagingListForm):
#     warnings.warn('sms.views.messaging_list.abstract_edit_messaginglist() is deprecated ; '
#                   'use the class-based view MessagingListDetail instead.',
#                   DeprecationWarning
#                  )
#     return generic.edit_entity(request, mlist_id, MessagingList, form)


# def abstract_view_messaginglist(request, mlist_id,
#                                 template='sms/view_messaginglist.html',
#                                ):
#     warnings.warn('sms.views.messaging_list.abstract_view_messaginglist() is deprecated ; '
#                   'use the class-based view MessagingListDetail instead.',
#                   DeprecationWarning
#                  )
#     return generic.view_entity(request, mlist_id, MessagingList, template=template)


# @login_required
# @permission_required(('sms', cperm(MessagingList)))
# def add(request):
#     warnings.warn('sms.views.messaging_list.add() is deprecated.', DeprecationWarning)
#     return abstract_add_messaginglist(request)


# @login_required
# @permission_required('sms')
# def edit(request, mlist_id):
#     warnings.warn('sms.views.messaging_list.edit() is deprecated.', DeprecationWarning)
#     return abstract_edit_messaginglist(request, mlist_id)


# @login_required
# @permission_required('sms')
# def detailview(request, mlist_id):
#     warnings.warn('sms.views.messaging_list.detailview() is deprecated.', DeprecationWarning)
#     return abstract_view_messaginglist(request, mlist_id)


# @login_required
# @permission_required('sms')
# def listview(request):
#     return generic.list_view(request, MessagingList, hf_pk=DEFAULT_HFILTER_MLIST)


# @login_required
# @permission_required('sms')
# def _delete_aux(request, mlist_id, deletor):
#     subobject_id   = get_from_POST_or_404(request.POST, 'id')
#     messaging_list = get_object_or_404(MessagingList, pk=mlist_id)
#
#     request.user.has_perm_to_change_or_die(messaging_list)
#
#     deletor(messaging_list, subobject_id)
#
#     if request.is_ajax():
#         return HttpResponse()
#
#     return redirect(messaging_list)
#
#
# def delete_contact(request, mlist_id):
#     return _delete_aux(request, mlist_id, lambda ml, contact_id: ml.contacts.remove(contact_id))
class ContactRemoving(generic.base.EntityRelatedMixin, generic.CremeDeletion):
    permissions = 'sms'
    entity_classes = MessagingList
    entity_id_url_kwarg = 'mlist_id'

    contact_id_arg = 'id'

    def perform_deletion(self, request):
        contact_id = get_from_POST_or_404(request.POST, self.contact_id_arg, cast=int)
        self.get_related_entity().contacts.remove(contact_id)


class MessagingListCreation(generic.EntityCreation):
    model = MessagingList
    form_class = ml_forms.MessagingListForm


class MessagingListDetail(generic.EntityDetail):
    model = MessagingList
    template_name = 'sms/view_messaginglist.html'
    pk_url_kwarg = 'mlist_id'


class MessagingListEdition(generic.EntityEdition):
    model = MessagingList
    form_class = ml_forms.MessagingListForm
    pk_url_kwarg = 'mlist_id'


class MessagingListsList(generic.EntitiesList):
    model = MessagingList
    default_headerfilter_id = DEFAULT_HFILTER_MLIST


class ContactsAdding(generic.AddingInstanceToEntityPopup):
    # model = Contact
    form_class = ml_forms.AddContactsForm
    template_name = 'creme_core/generics/blockform/link-popup.html'
    entity_id_url_kwarg = 'mlist_id'
    entity_classes = MessagingList
    title = _('New contacts for «{entity}»')
    submit_label = _('Link the contacts')


class ContactsAddingFromFilter(ContactsAdding):
    form_class = ml_forms.AddContactsFromFilterForm
