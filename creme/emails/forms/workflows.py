################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2025  Hybird
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
from django.db.models import EmailField as ModelEmailField
from django.db.models import ForeignKey
from django.forms import Textarea
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext_lazy

from creme import persons
from creme.creme_core.auth import EntityCredentials
from creme.creme_core.core.field_tags import FieldTag
from creme.creme_core.forms import FieldBlockManager
from creme.creme_core.forms import fields as core_fields
from creme.creme_core.forms import workflows as core_wf_forms
from creme.emails import get_emailtemplate_model
from creme.emails import workflows as emails_wf
from creme.emails.constants import SUBJECT_LENGTH
from creme.emails.core.validators import TemplateVariablesValidator
from creme.emails.workflows import ActionRecipient


class LiteralRecipientField(forms.EmailField):
    def clean(self, value):
        email = super().clean(value)

        return emails_wf.LiteralRecipient(email_address=email) if email else None

    def prepare_value(self, value):
        return value.email_address


class FixedUserRecipientField(forms.ModelChoiceField):
    def __init__(self, **kwargs):
        super().__init__(
            queryset=get_user_model().objects.filter(
                is_active=True, is_team=False, is_staff=False,
            ),
            empty_label=None,
            **kwargs
        )

    def clean(self, value):
        user = super().clean(value)

        return emails_wf.FixedUserRecipient(user=user) if user else None

    def prepare_value(self, value):
        return value.id if isinstance(value, get_user_model()) else value.user.id


class UserFKRecipientField(forms.ChoiceField):
    def __init__(self, entity_source, **kwargs):
        User = get_user_model()
        super().__init__(**{
            **kwargs,
            # TODO: ignore hidden fields
            'choices': [
                (model_field.name, model_field.verbose_name)
                for model_field in entity_source.model._meta.fields
                if isinstance(model_field, ForeignKey)
                and issubclass(model_field.related_model, User)
                and model_field.get_tag(FieldTag.VIEWABLE)  # TODO: test
            ],
        })
        self.entity_source = entity_source

    def clean(self, value):
        field_name = super().clean(value)

        return emails_wf.UserFKRecipient(
            entity_source=self.entity_source, field_name=field_name,
        )  if field_name else None

    def prepare_value(self, value):
        return value.field_name


# TODO: factorise with UserFKRecipientField?
class RegularEmailFieldRecipientField(forms.ChoiceField):
    def __init__(self, entity_source, **kwargs):
        super().__init__(**{
            **kwargs,
            # TODO: ignore hidden fields
            'choices': [
                (model_field.name, model_field.verbose_name)
                for model_field in entity_source.model._meta.fields
                if isinstance(model_field, ModelEmailField)
                and model_field.get_tag(FieldTag.VIEWABLE)  # TODO: test
            ],
        })
        self.entity_source = entity_source

    def clean(self, value):
        field_name = super().clean(value)

        return emails_wf.RegularEmailFieldRecipient(
            entity_source=self.entity_source, field_name=field_name,
        )  if field_name else None

    def prepare_value(self, value):
        return value.field_name


class ActionRecipientField(core_fields.UnionField):
    def __init__(self, trigger=None, user=None, registry=emails_wf.recipients_registry, **kwargs):
        super().__init__(**kwargs)
        self.recipients_registry = registry
        self._user = user
        self.trigger = trigger

    def _update_sub_fields(self):
        user    = self._user
        trigger = self._trigger

        fields_choices = []

        if trigger and user:
            for recipient_cls in self.recipients_registry.recipient_classes:
                field = recipient_cls.config_formfield(user=user, entity_source=None)
                if field is not None:
                    fields_choices.append(
                        (recipient_cls.config_formfield_kind_id(), field)
                    )

            for source in trigger.root_sources():
                for recipient_cls in self.recipients_registry.recipient_classes:
                    field = recipient_cls.config_formfield(user=user, entity_source=source)
                    if field is not None:
                        fields_choices.append(
                            (recipient_cls.config_formfield_kind_id(sub_source=source), field)
                        )

        self.fields_choices = fields_choices

    @property
    def trigger(self):
        return self._trigger

    @trigger.setter
    def trigger(self, trigger):
        self._trigger = trigger
        self._update_sub_fields()

    @property
    def user(self):
        return self._user

    @user.setter
    def user(self, user):
        self._user = user
        self._update_sub_fields()

    def prepare_value(self, value):
        if value:
            assert isinstance(value, ActionRecipient)
            selected_kind_id = value.config_formfield_kind_id(sub_source=value.sub_source)
            field = next(
                field
                for kind_id, field in self.fields_choices
                if kind_id == selected_kind_id
            )

            return selected_kind_id, {selected_kind_id: field.prepare_value(value)}


class EmailSendingActionForm(core_wf_forms.BaseWorkflowActionForm):
    recipient = ActionRecipientField(label=_('Recipient'))
    subject = forms.CharField(label=_('Subject'), max_length=SUBJECT_LENGTH)
    source = core_wf_forms.SourceField(label=_('Entity which is used as template variable'))
    body = forms.CharField(
        label=_('Body'), widget=Textarea,
        validators=[TemplateVariablesValidator(allowed_variables=['entity'])],
        # Translators: do not translate "{{entity}}"
        help_text=_('You can use the variable {{entity}} to display the entity chosen above')
    )

    blocks = FieldBlockManager(
        {'id': 'general', 'label': _('Sending an email'), 'fields': '*'},
        {'id': 'body',    'label': _('Email body'),       'fields': ('source', 'body')},
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        fields = self.fields
        recipient_f = fields['recipient']
        recipient_f.trigger = fields['source'].trigger = self.instance.trigger

        action = self.action
        if action is not None:
            recipient_f.initial = action.recipient
            fields['subject'].initial = action.subject
            fields['source'].initial = action.entity_source
            fields['body'].initial = action.body

    def clean_body(self):
        body = self.cleaned_data['body']

        # TODO: standalone validator?
        if '{%' in body and '%}' in body:
            raise ValidationError(gettext('The tags like {% … %} are forbidden'))

        return body

    def _build_action(self, cleaned_data):
        return emails_wf.EmailSendingAction(
            # [0] == recipient kind ID
            recipient=cleaned_data['recipient'][1],
            entity_source=cleaned_data['source'][1],
            subject=cleaned_data['subject'],
            body=cleaned_data['body'],
        )


class TemplateSendingActionForm(core_wf_forms.BaseWorkflowActionForm):
    recipient = ActionRecipientField(label=_('Recipient'))
    source = core_wf_forms.SourceField(label=_('Entity which is used to fill the template'))
    template = core_fields.CreatorEntityField(
        label=pgettext_lazy('emails', 'Template'),
        model=get_emailtemplate_model(),
        credentials=EntityCredentials.VIEW,
    )

    blocks = FieldBlockManager({
        'id': 'general', 'label': _('Sending an email'), 'fields': '*',
    })

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        fields = self.fields
        recipient_f = fields['recipient']
        recipient_f.trigger = fields['source'].trigger = self.instance.trigger

        action = self.action
        if action is not None:
            recipient_f.initial = action.recipient
            fields['source'].initial = action.entity_source
            fields['template'].initial = action.template.id

    def clean_source(self):
        # [0] == source kind ID
        source = self.cleaned_data['source'][1]

        if not issubclass(
            source.model, (persons.get_contact_model(), persons.get_organisation_model())
        ):
            raise ValidationError(
                gettext('The entity must be a Contact or an Organisation.'),
            )

        return source

    def _build_action(self, cleaned_data):
        return emails_wf.TemplateSendingAction(
            # [0] == recipient kind ID
            recipient=cleaned_data['recipient'][1],
            entity_source=cleaned_data['source'],
            template=cleaned_data['template'],
        )
