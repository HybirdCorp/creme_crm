# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2010  Hybird
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
from django.forms.fields import CharField
from django.forms.widgets import Textarea
from django.utils.translation import ugettext_lazy as _

from creme_core.forms import CremeEntityForm, CremeForm, FieldBlockManager
from creme_core.forms.fields import MultiCremeEntityField

from sms.models.campaign import SMSCampaign
from sms.models.sendlist import SendList


class CampaignCreateForm(CremeEntityForm):
    sendlists = MultiCremeEntityField(label=_(u'Listes de diffusion associées'),
                                      required=False, model=SendList)

    class Meta(CremeEntityForm.Meta):
        model = SMSCampaign


class CampaignEditForm(CremeEntityForm):
    class Meta:
        model   = SMSCampaign
        exclude = CremeEntityForm.Meta.exclude + ('sendlists',)


class CampaignAddSendListForm(CremeForm):
    sendlists = MultiCremeEntityField(label=_(u'Listes'),
                                      required=False, model=SendList)

    blocks = FieldBlockManager(('general', _(u'Listes de diffusion'), '*'))

    def __init__(self, campaign, *args, **kwargs):
        super(CampaignAddSendListForm, self).__init__(*args, **kwargs)
        self.campaign = campaign

    #in fact duplicate is not a problem with django's m2m
    def clean_lists(self):
        sendlists = self.cleaned_data['sendlists']
        current_lists   = frozenset(self.campaign.sendlists.values_list('pk', flat=True))
        duplicate     = [sendlist for sendlist in sendlists if sendlist.id in current_lists]

        if duplicate:
            raise ValidationError(u"La(es) liste(s) suivante(s) est déja présente dans la campagne: " #i8n....
                                  + u', '.join(sendlist.name for sendlist in duplicate))

        return sendlists

    def save(self):
        add_sendlist = self.campaign.sendlists.add
        for sendlist in self.cleaned_data['sendlists']:
            add_sendlist(sendlist)
