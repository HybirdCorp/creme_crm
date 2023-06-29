################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2023  Hybird
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

from django.utils.timezone import now
from django.utils.translation import gettext_lazy as _

from creme.creme_core.forms import CreatorEntityField, CremeModelForm

from .. import get_messagetemplate_model
from ..models.message import MESSAGE_STATUS_NOTSENT, Message, Sending


class SendingCreationForm(CremeModelForm):
    template = CreatorEntityField(label=_('Message template'), model=get_messagetemplate_model())

    class Meta:
        model = Sending
        fields = ()

    def __init__(self, entity, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.campaign = entity

    def save(self, *args, **kwargs):
        instance = self.instance
        template = self.cleaned_data['template']

        instance.campaign = self.campaign
        instance.template = template
        instance.date = now()
        super().save()

        instance.content = (template.subject + ' : ' + template.body) if template else ''
        instance.save()

        for phone in instance.campaign.all_phone_numbers():
            Message.objects.create(
                phone=phone, sending=instance, status=MESSAGE_STATUS_NOTSENT,
            )

        Message.send(instance)

        return instance
