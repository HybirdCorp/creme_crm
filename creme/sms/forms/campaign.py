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

from django.forms import ValidationError
from django.utils.translation import ugettext_lazy as _

from creme.creme_core.forms import CremeEntityForm, CremeForm, FieldBlockManager
from creme.creme_core.forms.fields import MultiCreatorEntityField

from .. import get_smscampaign_model, get_messaginglist_model


SMSCampaign   = get_smscampaign_model()
MessagingList = get_messaginglist_model()


class CampaignCreateForm(CremeEntityForm):
    class Meta(CremeEntityForm.Meta):
        model = SMSCampaign


class CampaignEditForm(CremeEntityForm):
    class Meta:
        model   = SMSCampaign
        exclude = CremeEntityForm.Meta.exclude + ('messaging_lists',)


class CampaignAddListForm(CremeForm):
    messaging_lists = MultiCreatorEntityField(label=_(u'Lists'), required=False, model=MessagingList)

    error_messages = {
        'already_linked': _(u'Following lists are already related to this campaign: %(lists)s'),
    }

    blocks = FieldBlockManager(('general', _(u'Messaging lists'), '*'))

    def __init__(self, entity, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.campaign = entity

    # In fact duplicate is not a problem with django's m2m
    def clean_lists(self):
        messaging_lists = self.cleaned_data['messaging_lists']
        current_lists   = frozenset(self.campaign.lists.values_list('pk', flat=True))
        duplicate       = [mlist for mlist in messaging_lists if mlist.id in current_lists]

        if duplicate:
            raise ValidationError(self.error_messages['already_linked'],
                                  params={'lists': u', '.join(mlist.name for mlist in duplicate)},
                                  code='already_linked',
                                 )

        return messaging_lists

    def save(self):
        add_mlist = self.campaign.lists.add
        for mlist in self.cleaned_data['messaging_lists']:
            add_mlist(mlist)
