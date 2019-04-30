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

from django.utils.translation import gettext_lazy as _

from creme.creme_core.views.generic import RelatedToEntityFormPopup

from .. import get_mailinglist_model
from ..forms import recipient as forms
from ..models import EmailRecipient


class _RecipientsAddingBase(RelatedToEntityFormPopup):
    # model = EmailRecipient
    # form_class = to be set
    title = _('New recipients for «{entity}»')
    submit_label = EmailRecipient.multi_save_label
    entity_id_url_kwarg = 'ml_id'
    entity_classes = get_mailinglist_model()


class RecipientsAdding(_RecipientsAddingBase):
    form_class = forms.MailingListAddRecipientsForm


class RecipientsAddingFromCSV(_RecipientsAddingBase):
    form_class = forms.MailingListAddCSVForm
