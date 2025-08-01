################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2025  Hybird
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

from dataclasses import dataclass
from datetime import datetime, time
from json import dumps as json_dump

from django import forms
from django.template.base import Template, VariableNode
from django.utils.timezone import make_aware, now
from django.utils.translation import gettext_lazy as _

from creme.creme_core import forms as core_forms
from creme.creme_core.auth import EntityCredentials
from creme.creme_core.core.history import toggle_history
from creme.creme_core.forms.widgets import CalendarWidget, PrettySelect

from .. import get_emailtemplate_model
from ..models import EmailSending, EmailSendingConfigItem, LightWeightEmail


# Widgets ----------------------------------------------------------------------
# TODO: move to creme_core?
class _SendingConfigSelect(PrettySelect):
    def create_option(self, *args, extra_data, **kwargs):
        option = super().create_option(*args, **kwargs)
        if extra_data:
            attrs = option['attrs']
            for k, v in extra_data.items():
                attrs[f'data-{k}'] = v

        return option

    def optgroups(self, name, value, attrs=None):
        selected_value = value[0] if value else None
        sub_group = [
            self.create_option(
                name,
                value=opt_value,
                label=opt_label,
                selected=str(opt_value) == selected_value,
                index=0,
                extra_data=opt_extra_data,
            ) for opt_value, opt_label, opt_extra_data in self.choices
        ]

        return [(
            None,  # group name
            sub_group,
            0,  # index
        )]

    # NB: we do not call <normalize_choices> because it causes a SQL query to be
    #     done during migrate (& which makes it fail).
    # TODO: rewrite a Widget from scratch which do not inherit ChoiceWidget
    #       & so behaves correctly which our unusual 3-tuples choices?
    @PrettySelect.choices.setter
    def choices(self, value):
        # self._choices = normalize_choices(value)
        self._choices = value


class SendingConfigWidget(forms.MultiWidget):
    template_name = 'emails/forms/widgets/sending-config.html'

    def __init__(self, choices=(), attrs=None):
        super().__init__(
            widgets=(
                _SendingConfigSelect(
                    choices=choices,
                    attrs={'data-emails-sending_config-source': True},
                ),
                forms.EmailInput(
                    attrs={'data-emails-sending_config-target': True},
                ),
            ),
            attrs={'class': 'emails-sending_config', **(attrs or {})},
        )

    @property
    def choices(self):
        return self.widgets[0].choices

    @choices.setter
    def choices(self, choices):
        self.widgets[0].choices = choices

    def decompress(self, value):
        return (value[0], value[1]) if value else (None, None)


# Fields -----------------------------------------------------------------------
class SendingConfigField(forms.MultiValueField):
    widget = SendingConfigWidget

    model = EmailSendingConfigItem

    @dataclass(frozen=True)
    class Configuration:
        item: EmailSendingConfigItem
        sender: str

    def __init__(self, **kwargs):
        items = forms.ModelChoiceField(queryset=self.model.objects.none(), empty_label=None)
        super().__init__((items, forms.EmailField()), **kwargs)
        self.queryset = self.model.objects.all()

    def __deepcopy__(self, memo):
        result = super().__deepcopy__(memo)

        # Need to force a new CallableChoiceWithDefaultIterator to be created.
        result.queryset = self.queryset

        return result

    def compress(self, data_list):
        return self.Configuration(
            item=data_list[0], sender=data_list[1],
        ) if data_list and all(data_list) else None

    @property
    def queryset(self):
        return self.fields[0].queryset

    @queryset.setter
    def queryset(self, value):
        # NB: we copy the old-fashioned CallableChoiceIterator because the new
        #     one (i.e django.utils.choices.CallableChoiceIterator) does not
        #     like our 3-tuples.
        class CallableChoiceWithDefaultIterator:
            def __init__(this, choices_func):
                this.choices_func = choices_func

            def __iter__(this):
                yield from this.choices_func()

        qs = value.all()
        self.fields[0].queryset = qs
        self.widget.choices = CallableChoiceWithDefaultIterator(
            lambda: (
                (
                    str(item.id),
                    item.name,
                    {'default_sender': item.default_sender}
                ) for item in qs
            )
        )


# Forms ------------------------------------------------------------------------
class SendingConfigItemCreationForm(core_forms.CremeModelForm):
    password = forms.CharField(
        label=_('Password'),
        required=False,
        strip=False,
        widget=forms.PasswordInput(attrs={'autocomplete': 'new-password'}),
    )

    class Meta:
        model = EmailSendingConfigItem
        fields = (
            'name', 'host', 'username', 'password', 'port', 'use_tls', 'default_sender',
        )

    def save(self, *args, **kwargs):
        password = self.cleaned_data['password']
        if password:
            self.instance.password = password
        return super().save(*args, **kwargs)


class SendingConfigItemEditionForm(core_forms.CremeModelForm):
    class Meta:
        model = EmailSendingConfigItem
        fields = (
            'name', 'host', 'username', 'port', 'use_tls', 'default_sender',
        )


class SendingConfigItemPasswordEditionForm(core_forms.CremeModelForm):
    password = forms.CharField(
        label=_('Password'),
        required=False,
        strip=False,
        widget=forms.PasswordInput(attrs={'autocomplete': 'new-password'}),
    )

    class Meta:
        model = EmailSendingConfigItem
        fields = ('password',)

    def save(self, *args, **kwargs):
        self.instance.password = self.cleaned_data['password']
        return super().save(*args, **kwargs)


class SendingCreationForm(core_forms.CremeModelForm):
    config = SendingConfigField(
        label=_('Sender'),
        help_text=_(
            'Beware to use an email address compatible with the chosen SMTP server'
        ),
    )
    template = core_forms.CreatorEntityField(
        label=_('Email template'), model=get_emailtemplate_model(),
        credentials=EntityCredentials.VIEW,
    )

    sending_date = forms.DateTimeField(
        label=_('Sending date'), required=False, widget=CalendarWidget,
        help_text=_('Required only of the sending is deferred.'),
    )
    hour = forms.IntegerField(
        label=_('Sending hour'), required=False, min_value=0, max_value=23,
    )
    minute = forms.IntegerField(
        label=_('Sending minute'), required=False, min_value=0, max_value=59,
    )

    error_messages = {
        'forbidden': _(
            'You are not allowed to modify the sender address, '
            'please contact your administrator.'
        ),
    }

    blocks = core_forms.CremeModelForm.blocks.new({
        'id': 'sending_date',
        'label': _('Sending date'),
        'fields': ['type', 'sending_date', 'hour', 'minute'],
    })

    class Meta:
        model = EmailSending
        exclude = ('sender', 'config_item')

    def __init__(self, entity, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.campaign = entity

        # TODO: pass from the view?
        assert self.instance.pk is None
        item = EmailSendingConfigItem.objects.first()
        if item is not None:
            self.fields['config'].initial = [item.id, item.default_sender]

    def clean(self):
        cleaned_data = super().clean()

        if cleaned_data['type'] == EmailSending.Type.DEFERRED:
            sending_date = cleaned_data['sending_date']

            if sending_date is None:
                self.add_error(
                    'sending_date',
                    _('Sending date required for a deferred sending'),
                )
            else:
                get_data = cleaned_data.get
                sending_date = make_aware(datetime.combine(
                    sending_date,
                    time(
                        hour=int(get_data('hour') or 0),
                        minute=int(get_data('minute') or 0),
                    ),
                ))

                if sending_date < now():
                    self.add_error(
                        'sending_date',
                        _('Sending date must be is the future'),
                    )
                else:
                    cleaned_data['sending_date'] = sending_date
        else:
            cleaned_data['sending_date'] = now()

        return cleaned_data

    def _get_variables(self, body):  # TODO: move in Emailtemplate ??
        return (
            varnode.filter_expression.var.var
            for varnode in Template(body).nodelist.get_nodes_by_type(VariableNode)
        )

    def save(self):
        instance = self.instance
        cleaned_data = self.cleaned_data

        instance.campaign = self.campaign

        config = cleaned_data['config']
        instance.config_item = config.item
        instance.sender      = config.sender

        template = cleaned_data['template']
        instance.subject   = template.subject
        instance.body      = template.body
        instance.body_html = template.body_html
        instance.signature = template.signature

        super().save()

        # M2M need a pk -> after save
        attachments = instance.attachments
        for attachment in template.attachments.all():
            attachments.add(attachment)

        var_names = [
            *self._get_variables(template.body),
            *self._get_variables(template.body_html),
        ]

        with toggle_history(enabled=False):
            for address, recipient_entity in instance.campaign.all_recipients():
                mail = LightWeightEmail(
                    sending=instance,
                    sender=instance.sender,
                    recipient=address,
                    sending_date=instance.sending_date,
                    real_recipient=recipient_entity,
                )

                if recipient_entity:
                    context = {}

                    for var_name in var_names:
                        val = getattr(recipient_entity, var_name, None)
                        if val:
                            context[var_name] = str(val)

                    if context:
                        mail.body = json_dump(context, separators=(',', ':'))

                mail.genid_n_save()

        return instance


# TODO: we probably want to edit the type/sending_date, with some constraints
class SendingEditionForm(core_forms.CremeModelForm):
    config = SendingConfigField(
        label=_('Sender'),
        help_text=_(
            'Beware to use an email address compatible with the chosen SMTP server'
        ),
    )

    class Meta(core_forms.CremeModelForm.Meta):
        model = EmailSending
        fields = ()

    def __init__(self, entity, *args, **kwargs):
        super().__init__(*args, **kwargs)
        instance = self.instance
        item = instance.config_item
        if item is not None:
            self.fields['config'].initial = [item.id, instance.sender]

    def save(self):
        instance = self.instance
        config = self.cleaned_data['config']
        instance.config_item = config.item
        instance.sender      = config.sender

        return super().save()
