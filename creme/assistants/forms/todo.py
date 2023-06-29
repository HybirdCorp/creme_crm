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

from datetime import datetime, time

from django.forms import TypedChoiceField
from django.utils.timezone import localtime, make_aware
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _

from creme.creme_core.forms import CremeModelForm
from creme.creme_core.forms.widgets import CalendarWidget

from ..models import ToDo


class ToDoForm(CremeModelForm):
    deadline_hour = TypedChoiceField(
        label=_('Deadline hour'), coerce=int,
        choices=[(i, '%ih' % i) for i in range(0, 24)],
        required=False, empty_value=None, initial=8,
        help_text=_('The hour is used only if you set the deadline date.'),
    )

    class Meta(CremeModelForm.Meta):
        model = ToDo
        widgets = {'deadline': CalendarWidget}
        help_texts = {
            'user': _(
                'The owner is only used to send emails (a deadline is required).\n'
                'Hint: the choice «Same owner than the entity» allows to always '
                'send the email to the owner of the entity, even if it is changed.'
            ),
            'deadline': _(
                'If you set a deadline, an email is sent to the owner of the Todo '
                'when it is about to expire (the job «Reminders» must be enabled), '
                'if the Todo is not marked as done before.\n'
                'Hint: if the owner is a team, every teammate receives an email.'
            ),
        }

    def __init__(self, entity, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.instance.real_entity = entity

        fields = self.fields
        fields['user'].empty_label = gettext(
            'Same owner than the entity (currently «{user}»)'
        ).format(user=entity.user)

        deadline = self.instance.deadline
        if deadline:
            fields['deadline_hour'].initial = localtime(deadline).hour

    def clean(self):
        cdata = super().clean()

        if not self._errors:
            get_data = cdata.get
            deadline = get_data('deadline')

            if deadline:
                deadline_hour = get_data('deadline_hour')

                if deadline_hour is None:
                    self.add_error(
                        'deadline_hour',
                        _('The hour is required if you set a date.'),
                    )
                else:
                    cdata['deadline'] = make_aware(
                        datetime.combine(deadline, time(deadline_hour))
                    )

        return cdata
