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

from django.utils.translation import gettext as _

from creme.creme_core.views.generic import RelatedToEntityFormPopup

from .. import get_messaginglist_model
from ..forms import recipient as forms
from ..models import Recipient


class _RecipientsAddingBase(RelatedToEntityFormPopup):
    # model = Recipient
    entity_id_url_kwarg = 'mlist_id'
    entity_classes = get_messaginglist_model()
    title = _('New recipients for «{entity}»')
    submit_label = Recipient.multi_save_label


class RecipientsAdding(_RecipientsAddingBase):
    form_class = forms.MessagingListAddRecipientsForm


class RecipientsAddingFromCSV(_RecipientsAddingBase):
    form_class = forms.MessagingListAddCSVForm
