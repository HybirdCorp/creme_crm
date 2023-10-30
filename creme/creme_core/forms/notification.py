################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2024  Hybird
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

from django import forms
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils.timezone import now
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _

from creme.creme_core import models
from creme.creme_core.constants import UUID_CHANNEL_SYSTEM
from creme.creme_core.forms import CremeForm
from creme.creme_core.notification import UpgradeAnnouncement


class SystemUpgradeAnnouncementForm(CremeForm):
    start = forms.DateTimeField(label=_('Start'))
    message = forms.CharField(
        label=_('Extra message'), widget=forms.Textarea, required=False,
        help_text=_('Use it to give additional information, like expected duration'),
    )

    def clean_start(self):
        start = self.cleaned_data['start']

        if start < now():
            raise ValidationError(gettext('Start must be in the future'))

        return start

    def save(self, *args, **kwargs):
        cdata = self.cleaned_data
        models.Notification.objects.send(
            channel=UUID_CHANNEL_SYSTEM,
            # NB: excluding team is just an optimization, send() expands them
            users=[
                *get_user_model().objects
                                 .filter(is_team=False, is_active=True)
                                 .exclude(is_staff=True)
            ],
            content=UpgradeAnnouncement(
                start=cdata['start'], message=cdata['message'],
            ),
        )
