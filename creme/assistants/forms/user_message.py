################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2024  Hybird
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

from django.contrib.auth import get_user_model
from django.forms import ModelMultipleChoiceField
from django.utils.translation import gettext_lazy as _

from creme.creme_core.forms import CremeModelForm

from ..models import UserMessage


class UserMessageForm(CremeModelForm):
    users = ModelMultipleChoiceField(
        queryset=get_user_model().objects.filter(is_staff=False),
        label=_('Recipients'),
        help_text=_(
            'Each time a team is selected, a message is sent to each teammate '
            '(do not worry, there can not be any duplicate).'
        ),
    )

    class Meta:
        model = UserMessage
        fields = ('title', 'body', 'priority')

    def __init__(self, entity=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.entity = entity

        # TODO: generalise this behavior to all forms ???
        self.fields['priority'].empty_label = None

    def save(self, *args, **kwargs):
        # NB: we do not call super() because we create several instances
        cdata = self.cleaned_data
        UserMessage.objects.create_for_users(
            users=cdata['users'],
            title=cdata['title'], body=cdata['body'],
            priority=cdata['priority'],
            sender=self.user,
            entity=self.entity,
        )
