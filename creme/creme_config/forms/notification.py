################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2024-2025  Hybird
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
from django.utils.translation import gettext_lazy as _
from django.utils.translation import ngettext

from creme.creme_core import models
from creme.creme_core.core.notification import notification_registry
from creme.creme_core.forms import CremeModelForm


class ChannelForm(CremeModelForm):
    default_outputs = forms.MultipleChoiceField(
        label=_('Default outputs'),
        help_text=_("Default outputs used by users' configurations"),
        choices=notification_registry.output_choices,
    )

    class Meta(CremeModelForm.Meta):
        model = models.NotificationChannel

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        fields = self.fields
        chan = self.instance

        if chan.type_id:
            del fields['name']
            del fields['description']

        if chan.pk:
            del fields['required']

        output_f = fields['default_outputs']
        output_f.initial = chan.default_outputs

    def save(self, *args, **kwargs):
        self.instance.default_outputs = self.cleaned_data['default_outputs']
        return super().save(*args, **kwargs)


class ChannelRequirementForm(CremeModelForm):
    class Meta(CremeModelForm.Meta):
        model = models.NotificationChannel
        fields = ('required',)

    def _get_items_to_update(self):
        return models.NotificationChannelConfigItem.objects.filter(
            channel=self.instance, outputs=[],
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.required:
            help_text = _(
                'If the channel is not required anymore, '
                'users could configure it to receive no notification'
            )
        else:
            count = self._get_items_to_update().count()
            # TODO: if count?
            help_text = ngettext(
                'If the channel is set as required, the configuration of '
                '{count} user will be updated to use the default configuration',
                'If the channel is set as required, the configuration of '
                '{count} users will be updated to use the default configuration',
                count
            ).format(count=count)

        self.fields['required'].help_text = help_text

    # TODO: only if changed
    def save(self, *args, **kwargs):
        instance = super().save(*args, **kwargs)

        if instance.required:
            self._get_items_to_update().update(outputs=instance.default_outputs)

        return instance


class ChannelConfigItemForm(CremeModelForm):
    outputs = forms.MultipleChoiceField(
        label=_('Outputs'),
        choices=notification_registry.output_choices,
    )

    class Meta(CremeModelForm.Meta):
        model = models.NotificationChannelConfigItem

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        item = self.instance

        output_f = self.fields['outputs']
        output_f.initial = item.outputs
        output_f.required = item.channel.required

    def save(self, *args, **kwargs):
        self.instance.outputs = self.cleaned_data['outputs']
        return super().save(*args, **kwargs)
