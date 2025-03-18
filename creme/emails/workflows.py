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

from __future__ import annotations

from django.conf import settings
from django.utils.html import format_html
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _

from creme.creme_core.core.workflow import (
    WorkflowAction,
    WorkflowRegistry,
    workflow_registry,
)
from creme.creme_core.models import CremeEntity, CremeUser
from creme.emails.models import WorkflowEmail


# Recipients -------------------------------------------------------------------
# TODO: docstring + types
class ActionRecipient:
    type_id = '??'

    @classmethod
    def config_formfield(cls, user, entity_source=None):
        raise NotImplementedError

    @classmethod
    def from_dict(cls, data: dict, registry: WorkflowRegistry):
        raise NotImplementedError

    def to_dict(self):
        return {'type': self.type_id}

    def render(self, user):
        raise NotImplementedError

    def extract(self, context: dict) -> tuple[str, CremeEntity | None]:
        raise NotImplementedError


class LiteralRecipient(ActionRecipient):
    type_id = 'literal'

    def __init__(self, *, email_address):
        self._email_address = email_address

    def __eq__(self, other):
        return isinstance(other, type(self)) and self.email_address == other.email_address

    def __repr__(self):
        return f'LiteralRecipient(email_address="{self._email_address}")'

    @property
    def email_address(self):
        return self._email_address

    @classmethod
    def config_formfield(cls, user, entity_source=None):
        from .forms.workflows import LiteralRecipientField

        return LiteralRecipientField(
            label=_('Fixed email address'),
        ) if entity_source is None else None

    def extract(self, context):
        # return self._email_address
        return (self._email_address, None)

    @classmethod
    def from_dict(cls, data, registry):
        return cls(email_address=data['email'])

    def to_dict(self):
        d = super().to_dict()
        d['email'] = self.email_address

        return d

    def render(self, user):
        # TODO: mark_safe?
        return _('To: {recipient}').format(recipient=self.email_address)


class FixedUserRecipient(ActionRecipient):
    type_id = 'fixed_user'

    # TODO: accept UUID too?
    def __init__(self, *, user):
        # TODO: in property 'user'?
        # TODO: errors?
        if isinstance(user, str):
            # self._user = CremeUser.objects.get(username=user)
            self._user = CremeUser.objects.get(uuid=user)
        else:
            assert isinstance(user, CremeUser)
            self._user = user

    def __eq__(self, other):
        return isinstance(other, type(self)) and self.user == other.user

    def __repr__(self):
        return f'FixedUserRecipient(user={self._user})'

    @classmethod
    def config_formfield(cls, user, entity_source=None):
        from .forms.workflows import FixedUserRecipientField

        return FixedUserRecipientField(
            label=_('Fixed user'),
        ) if entity_source is None else None

    def extract(self, context):
        # return self._user.email
        return (self._user.email, None)

    @property
    def user(self):
        return self._user

    @classmethod
    def from_dict(cls, data, registry):
        return cls(user=data['user'])

    def to_dict(self):
        d = super().to_dict()
        # d['user'] = self._user.username
        d['user'] = str(self._user.uuid)

        return d

    def render(self, user):
        # TODO: escape?
        recipient = self.user
        # TODO: <a> to user/contact?
        return gettext('To: {user} <{email}>').format(
            user=recipient, email=recipient.email,
        )


# TODO: factorise with EntityFKSource?
class UserFKRecipient(ActionRecipient):
    type_id = 'user_fk'

    def __init__(self, *, entity_source, field_name):
        self._entity_source = entity_source
        self._field_name = field_name

    def __eq__(self, other):
        return (
            isinstance(other, type(self))
            and self._entity_source == other._entity_source
            and self._field_name == other._field_name
        )

    def __repr__(self):
        return (
            f'UserFKRecipient('
            f'entity_source={self._entity_source!r}), '
            f'field_name="{self._field_name}"'
            f')'
        )

    @classmethod
    def config_formfield(cls, user, entity_source=None):
        from .forms.workflows import UserFKRecipientField

        return None if entity_source is None else UserFKRecipientField(
            label=gettext('Field to a user of: {source}').format(
                source=entity_source.render(user=user, mode=entity_source.HTML),
            ),
            entity_source=entity_source,
        )

    def extract(self, context):
        # TODO: errors
        instance = self._entity_source.extract(context=context)
        if instance:
            user = getattr(instance, self._field_name)
            if user:
                # NB: even if we could return the instance as concerned entity,
                #     here the user IS the important information.
                return (user.email, None)

        return ('', None)

    @property
    def entity_source(self):
        return self._entity_source

    @property
    def field_name(self):
        return self._field_name

    @classmethod
    def from_dict(cls, data, registry):
        return cls(
            entity_source=registry.build_action_source(data['entity']),
            field_name=data['field'],
        )

    def to_dict(self):
        d = super().to_dict()
        d['entity'] = self._entity_source.to_dict()
        d['field'] = self._field_name

        return d

    def render(self, user):
        # TODO: mark_safe?
        source = self._entity_source

        return gettext('To: user «{field}» of: {source}').format(
            field=source.model._meta.get_field(self._field_name).verbose_name,
            source=source.render(user=user, mode=source.HTML),
        )


# TODO: factorise with UserFKRecipient? (wait for entity-mail/workflow-mail)
class RegularEmailFieldRecipient(ActionRecipient):
    type_id = 'regular_field'

    def __init__(self, *, entity_source, field_name):
        self._entity_source = entity_source
        self._field_name = field_name

    def __eq__(self, other):
        return (
            isinstance(other, type(self))
            and self._entity_source == other._entity_source
            and self._field_name == other._field_name
        )

    def __repr__(self):
        return (
            f'RegularEmailFieldRecipient('
            f'entity_source={self._entity_source!r}), '
            f'field_name="{self._field_name}"'
            f')'
        )

    @classmethod
    def config_formfield(cls, user, entity_source=None):
        from .forms.workflows import RegularEmailFieldRecipientField

        if entity_source is None:
            return None

        field = RegularEmailFieldRecipientField(
            label=gettext('Email field of: {source}').format(
                source=entity_source.render(user=user, mode=entity_source.HTML),
            ),
            entity_source=entity_source,
        )

        return field if field.choices else None

    def extract(self, context):
        # TODO: errors
        instance = self._entity_source.extract(context=context)

        # return None if instance is None else getattr(instance, self._field_name)
        return (
            ('', None)
            if instance is None else
            (getattr(instance, self._field_name), instance)
        )

    @property
    def entity_source(self):
        return self._entity_source

    @property
    def field_name(self):
        return self._field_name

    @classmethod
    def from_dict(cls, data, registry):
        return cls(
            entity_source=registry.build_action_source(data['entity']),
            field_name=data['field'],
        )

    def to_dict(self):
        d = super().to_dict()
        d['entity'] = self._entity_source.to_dict()
        d['field'] = self._field_name

        return d

    def render(self, user):
        # TODO: mark_safe?
        source = self._entity_source

        return gettext('To: field «{field}» of: {source}').format(
            field=source.model._meta.get_field(self._field_name).verbose_name,
            source=source.render(user=user, mode=source.HTML),
        )


class ActionRecipientsRegistry:
    def __init__(self):
        self._recipient_classes = {}

    @property
    def recipient_classes(self):
        yield from self._recipient_classes.values()

    # TODO: error
    def register(self,
                 *recipient_classes: type[ActionRecipient],
                 ) -> ActionRecipientsRegistry:
        classes = self._recipient_classes

        for cls in recipient_classes:
            classes[cls.type_id] = cls

        return self

    # TODO: unregister

    def build_recipient(self, data: dict) -> ActionRecipient:
        # TODO: error
        return self._recipient_classes[data['type']].from_dict(
            data=data,
            registry=workflow_registry,  # TODO: attribute for that?
        )


recipients_registry = ActionRecipientsRegistry().register(
    LiteralRecipient,
    FixedUserRecipient,
    UserFKRecipient,
    RegularEmailFieldRecipient,
)


# Actions ----------------------------------------------------------------------
class EmailSendingAction(WorkflowAction):
    type_id = 'emails-email_sending'
    verbose_name = _('Sending an email')

    # TODO: docstring
    def __init__(self, *,
                 recipient: ActionRecipient,
                 subject: str,
                 body: str,
                 ):
        self._recipient = recipient
        self._subject = subject
        self._body = body

    @classmethod
    def config_form_class(cls):
        from .forms.workflows import EmailSendingActionForm
        return EmailSendingActionForm

    @property
    def body(self):
        return self._body

    @property
    def recipient(self):
        return self._recipient

    @property
    def subject(self):
        return self._subject

    def execute(self, context):
        recipient, concerned_entity = self._recipient.extract(context)
        if recipient:
            # TODO: if concerned_entity => create EntityEmail instead
            WorkflowEmail.objects.create(
                sender=settings.EMAIL_SENDER,
                recipient=recipient,
                subject=self._subject,
                body=self._body,
            )

    def to_dict(self) -> dict:
        d = super().to_dict()
        d['recipient'] = self._recipient.to_dict()
        d['subject'] = self._subject
        d['body'] = self._body

        return d

    @classmethod
    def from_dict(cls, data: dict, registry):
        # TODO: errors
        return cls(
            recipient=recipients_registry.build_recipient(data['recipient']),
            subject=data['subject'],
            body=data['body'],
        )

    def render(self, user):
        return format_html(
            '<div>'
            '{label}'
            ' <ul>'
            '  <li>{recipient}</li>'
            '  <li>{subject}</li>'
            '  <li>{body_label}<br><p>{body}</p></li>'
            ' </ul>'
            '</div>',
            label=gettext('Sending an email:'),
            recipient=self._recipient.render(user=user),
            subject=gettext('Subject: {subject}').format(subject=self._subject),
            body_label=gettext('Body:'),
            body=self._body,
        )
