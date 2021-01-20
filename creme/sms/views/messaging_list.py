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

from .. import custom_forms, get_messaginglist_model
from ..constants import DEFAULT_HFILTER_MLIST
from ..forms import messaging_list as ml_forms

MessagingList = get_messaginglist_model()


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
    form_class = custom_forms.MESSAGINGLIST_CREATION_CFORM


class MessagingListDetail(generic.EntityDetail):
    model = MessagingList
    template_name = 'sms/view_messaginglist.html'
    pk_url_kwarg = 'mlist_id'


class MessagingListEdition(generic.EntityEdition):
    model = MessagingList
    form_class = custom_forms.MESSAGINGLIST_EDITION_CFORM
    pk_url_kwarg = 'mlist_id'


class MessagingListsList(generic.EntitiesList):
    model = MessagingList
    default_headerfilter_id = DEFAULT_HFILTER_MLIST


@method_decorator(
    require_model_fields(persons.get_contact_model(), 'mobile'),
    name='dispatch',
)
class ContactsAdding(generic.RelatedToEntityFormPopup):
    # model = Contact
    form_class = ml_forms.AddContactsForm
    template_name = 'creme_core/generics/blockform/link-popup.html'
    entity_id_url_kwarg = 'mlist_id'
    entity_classes = MessagingList
    title = _('New contacts for «{entity}»')
    submit_label = _('Link the contacts')


class ContactsAddingFromFilter(ContactsAdding):
    form_class = ml_forms.AddContactsFromFilterForm
