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
from django.db.models import EmailField as ModelEmailField
from django.db.models import ForeignKey
from django.forms import Textarea
from django.utils.translation import gettext_lazy as _

from creme.creme_core.core.field_tags import FieldTag
from creme.creme_core.forms import FieldBlockManager
from creme.creme_core.forms.fields import UnionField
from creme.creme_core.forms.workflows import BaseWorkflowActionForm
from creme.emails.constants import SUBJECT_LENGTH
from creme.emails.workflows import EmailSendingAction, recipients_registry


class LiteralRecipientField(forms.EmailField):
    def clean(self, value):
        from ..workflows import LiteralRecipient

        email = super().clean(value)
        return LiteralRecipient(email_address=email) if email else None


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
        from ..workflows import FixedUserRecipient

        user = super().clean(value)
        return FixedUserRecipient(user=user) if user else None


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
        from ..workflows import UserFKRecipient

        field_name = super().clean(value)
        return UserFKRecipient(
            entity_source=self.entity_source, field_name=field_name,
        )  if field_name else None


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
        from ..workflows import RegularEmailFieldRecipient

        field_name = super().clean(value)
        return RegularEmailFieldRecipient(
            entity_source=self.entity_source, field_name=field_name,
        )  if field_name else None


# TODO: complete
# TODO: RegularEmailFieldRecipientField => can be empty => remove it
class ActionRecipientField(UnionField):
    # def __init__(self, trigger=None, , registry=workflow_registry, **kwargs):
    def __init__(self, trigger=None, user=None, **kwargs):
        super().__init__(**kwargs)
        self._user = user
        self.trigger = trigger

    def _update_sub_fields(self):
        user    = self._user
        trigger = self._trigger

        fields_choices = []

        if trigger and user:
            # TODO: argument for recipients_registry
            for recipient_cls in recipients_registry.recipient_classes:
                field = recipient_cls.config_formfield(user=user, entity_source=None)
                if field is not None:
                    fields_choices.append(
                        (recipient_cls.type_id, field)
                    )

            for source in trigger.root_sources():
                for recipient_cls in recipients_registry.recipient_classes:
                    field = recipient_cls.config_formfield(user=user, entity_source=source)
                    if field is not None:
                        # TODO: check characters for type_id in registry => forbid "|"
                        fields_choices.append(
                            (f'{source.type_id}|{recipient_cls.type_id}', field)
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


class EmailSendingActionForm(BaseWorkflowActionForm):
    recipient = ActionRecipientField(label=_('Recipient'))
    subject = forms.CharField(label=_('Subject'), max_length=SUBJECT_LENGTH)
    body = forms.CharField(label=_('Body'), widget=Textarea)

    blocks = FieldBlockManager({
        'id': 'general', 'label': _('Sending an email'), 'fields': '*',
    })

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['recipient'].trigger = self.instance.trigger

    def _build_action(self, cleaned_data):
        # [0] == recipient kind ID
        recipient = cleaned_data['recipient'][1]

        return EmailSendingAction(
            recipient=recipient,
            subject=cleaned_data['subject'],
            body=cleaned_data['body'],
        )
