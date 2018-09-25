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

from django.utils.translation import ugettext as _

# from creme.creme_core.auth.decorators import login_required, permission_required
# from creme.creme_core.views.generic import add_to_entity
from creme.creme_core.views.generic.add import AddingToEntity

from .. import get_messaginglist_model
from ..forms import recipient as forms
from ..models import Recipient


# @login_required
# @permission_required('sms')
# def add(request, mlist_id):
#     return add_to_entity(request, mlist_id, forms.MessagingListAddRecipientsForm,
#                          _('New recipients for «%s»'),
#                          entity_class=get_messaginglist_model(),
#                          submit_label=Recipient.multi_save_label,
#                         )
class RecipientsAdding(AddingToEntity):
    model = Recipient
    form_class = forms.MessagingListAddRecipientsForm
    entity_id_url_kwarg = 'mlist_id'
    entity_classes = get_messaginglist_model()
    title_format = _('New recipients for «{}»')
    submit_label = Recipient.multi_save_label


# @login_required
# @permission_required('sms')
# def add_from_csv(request, mlist_id):
#     return add_to_entity(request, mlist_id, forms.MessagingListAddCSVForm,
#                          _('New recipients for «%s»'),
#                          entity_class=get_messaginglist_model(),
#                          submit_label=Recipient.multi_save_label,
#                         )
class RecipientsAddingFromCSV(RecipientsAdding):
    form_class = forms.MessagingListAddCSVForm
    entity_classes = get_messaginglist_model()
