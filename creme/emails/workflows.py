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

import re
from typing import TYPE_CHECKING

from django.conf import settings
from django.contrib.auth import get_user_model
from django.template import Context, Template
from django.template.loader import get_template
from django.utils.html import format_html
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _

from creme import emails
from creme.creme_core.core.workflow import (
    WorkflowAction,
    WorkflowActionSource,
    WorkflowRegistry,
    workflow_registry,
)
from creme.creme_core.models import Relation
from creme.creme_core.templatetags.creme_widgets import widget_entity_hyperlink
from creme.emails.constants import REL_SUB_MAIL_RECEIVED
from creme.emails.models import WorkflowEmail
from creme.emails.models.template import body_validator

if TYPE_CHECKING:
    from django.forms import Field as FormField

    from creme.creme_core.models import CremeEntity, CremeUser

User = get_user_model()
EntityEmail = emails.get_entityemail_model()
EmailTemplate = emails.get_emailtemplate_model()


# Recipients -------------------------------------------------------------------
class ActionRecipient:
    """Base class to represent email recipient (extracted from the Workflow's
    context) for actions which send emails.
    """
    type_id: str = ''

    @classmethod
    def config_formfield(cls,
                         user: CremeUser,
                         entity_source: WorkflowActionSource | None = None,
                         ) -> FormField:
        """Returns a form field which can be used in the configuration form of a
        WorkflowAction.
        @return A field with a 'clean()' method which returns an instance of
                'ActionRecipient'.
        """
        raise NotImplementedError

    @classmethod
    def from_dict(cls, data: dict, registry: WorkflowRegistry) -> ActionRecipient:
        """Build an instance from a dictionary (produced by the method to_dict()."""
        raise NotImplementedError

    def to_dict(self) -> dict:
        """Serialize to a JSON friendly dictionary
        Hint: see the method 'from_dict()' too.
        """
        return {'type': self.type_id}

    def render(self, user: CremeUser) -> str:
        """Render as HTML to describe in the configuration UI."""
        raise NotImplementedError

    def extract(self, context: dict) -> tuple[str, CremeEntity | None]:
        """Extract the recipient address (to use for the email to send)
        from the Workflow's context.
        @return A tuple (email_address, creme_entity).
                If 'email_address' if empty string, no email will be sent.
                If 'creme_entity' is not <None>, an instance of 'EntityEmail' is
                created & is link to 'creme_entity'. If 'creme_entity' is None,
                a WorkflowEmail is created (so it's not visible in any detail view).
        """
        raise NotImplementedError


class LiteralRecipient(ActionRecipient):
    """A recipient corresponding to a fixed email address."""
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
        return (self._email_address, None)

    @classmethod
    def from_dict(cls, data, registry):
        return cls(email_address=data['email'])

    def to_dict(self):
        d = super().to_dict()
        d['email'] = self.email_address

        return d

    def render(self, user):
        return _('To: {recipient}').format(recipient=self.email_address)


class FixedUserRecipient(ActionRecipient):
    """A recipient corresponding to a fixed user (remember that all users have
    an email address).
    """
    type_id = 'fixed_user'

    # TODO: accept UUID too?
    def __init__(self, *, user):
        # TODO: in property 'user'?
        # TODO: errors?
        if isinstance(user, str):
            self._user = User.objects.get(uuid=user)
        else:
            assert isinstance(user, User)
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
        # TODO: warn in config that no mail will be sent when user is inactive
        user = self._user
        return (user.email if user.is_active else '', None)

    @property
    def user(self):
        return self._user

    @classmethod
    def from_dict(cls, data, registry):
        return cls(user=data['user'])

    def to_dict(self):
        d = super().to_dict()
        d['user'] = str(self._user.uuid)

        return d

    def render(self, user):
        recipient = self.user
        # TODO: link <a> to user/contact?
        return gettext('To: {user} <{email}>').format(
            user=recipient, email=recipient.email,
        )


# TODO: factorise with EntityFKSource?
class _BaseFKRecipient(ActionRecipient):
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
            f'{type(self).__name__}('
            f'entity_source={self._entity_source!r}), '
            f'field_name="{self._field_name}"'
            f')'
        )

    @property
    def entity_source(self):
        return self._entity_source

    @property
    def field_name(self):
        return self._field_name

    def _extract_from_instance(self, instance):
        raise NotImplementedError

    def extract(self, context):
        # TODO: errors
        instance = self._entity_source.extract(context=context)

        return ('', None) if instance is None else self._extract_from_instance(instance)

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


class UserFKRecipient(_BaseFKRecipient):
    """A recipient with is read from a ForeignKey to a user (remember that all
    users have an email address).
    """
    type_id = 'user_fk'

    @classmethod
    def config_formfield(cls, user, entity_source=None):
        from .forms.workflows import UserFKRecipientField

        return None if entity_source is None else UserFKRecipientField(
            label=gettext('Field to a user of: {source}').format(
                source=entity_source.render(user=user, mode=entity_source.HTML),
            ),
            entity_source=entity_source,
        )

    def _extract_from_instance(self, instance):
        user = getattr(instance, self._field_name)
        # NB: even if we could return the instance as concerned entity,
        #     here the user IS the important information.
        # TODO: warn in config that no mail will be sent when user is inactive
        return (user.email if user and user.is_active else '', None)

    def render(self, user):
        source = self._entity_source

        return gettext('To: user «{field}» of: {source}').format(
            field=source.model._meta.get_field(self._field_name).verbose_name,
            source=source.render(user=user, mode=source.HTML),
        )


class RegularEmailFieldRecipient(_BaseFKRecipient):
    """A recipient with is read from a models.EmailField."""
    type_id = 'regular_field'

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

    def _extract_from_instance(self, instance):
        return (getattr(instance, self._field_name), instance)

    def render(self, user):
        source = self._entity_source

        return gettext('To: field «{field}» of: {source}').format(
            field=source.model._meta.get_field(self._field_name).verbose_name,
            source=source.render(user=user, mode=source.HTML),
        )


class ActionRecipientsRegistry:
    _type_id_re = re.compile(r'[A-Za-z0-9_-]*')  # TODO: in creme_core?

    class RegistrationError(Exception):
        pass

    class UnRegistrationError(RegistrationError):
        pass

    def __init__(self, wf_registry=workflow_registry):
        self._recipient_classes = {}
        self._workflow_registry = wf_registry

    @property
    def recipient_classes(self):
        yield from self._recipient_classes.values()

    @classmethod
    def checked_type_id(cls, recipient_class):
        type_id = recipient_class.type_id

        if not type_id:
            raise cls.RegistrationError(
                f'This recipient class has an empty ID: {recipient_class}'
            )

        if cls._type_id_re.fullmatch(type_id) is None:
            raise cls.RegistrationError(
                f'This recipient class uses has an ID with invalid chars: {recipient_class}'
            )

        return type_id

    def register(self,
                 *recipient_classes: type[ActionRecipient],
                 ) -> ActionRecipientsRegistry:
        set_cls = self._recipient_classes.setdefault

        for cls in recipient_classes:
            if set_cls(self.checked_type_id(cls), cls) is not cls:
                raise self.RegistrationError(
                    f'This recipient class uses an ID already used: {cls}'
                )

        return self

    def unregister(self,
                   *recipient_classes: type[ActionRecipient],
                   ) -> ActionRecipientsRegistry:
        for cls in recipient_classes:
            try:
                del self._recipient_classes[cls.type_id]
            except KeyError as e:
                raise self.UnRegistrationError(
                    f'This class is not registered: {cls}'
                ) from e

        return self

    def build_recipient(self, data: dict) -> ActionRecipient:
        # TODO: error
        return self._recipient_classes[data['type']].from_dict(
            data=data, registry=self._workflow_registry,
        )


recipients_registry = ActionRecipientsRegistry().register(
    LiteralRecipient,
    FixedUserRecipient,
    UserFKRecipient,
    RegularEmailFieldRecipient,
)


# Actions ----------------------------------------------------------------------
class EmailSendingAction(WorkflowAction):
    """A WorkflowAction which creates & sends emails from given subject/body.
    The body can use a template variable {{entity}} (which corresponds to
    its WorkflowActionSource 'entity_source').
    """
    type_id = 'emails-email_sending'
    verbose_name = _('Sending an email')

    html_template_name = 'emails/workflows/email-body.html'

    # TODO: docstring
    def __init__(self, *,
                 recipient: ActionRecipient,
                 entity_source: WorkflowActionSource,
                 subject: str,
                 body: str,
                 ):
        self._recipient = recipient
        self._entity_source = entity_source
        self._subject = subject
        self._body = body

    @classmethod
    def config_form_class(cls):
        from .forms.workflows import EmailSendingActionForm
        return EmailSendingActionForm

    @property
    def body(self) -> str:
        return self._body

    @property
    def entity_source(self) -> WorkflowActionSource:
        return self._entity_source

    @property
    def recipient(self) -> ActionRecipient:
        return self._recipient

    @property
    def subject(self) -> str:
        return self._subject

    def execute(self, context):
        recipient, entity_to_link = self._recipient.extract(context)
        if recipient:
            ctxt_entity = self._entity_source.extract(context)
            body = Template(self._body).render(Context({'entity': str(ctxt_entity)}))
            body_html = get_template(self.html_template_name).render({
                'content': Template(self._body.replace('\n', '<br>')).render(Context({
                    'entity': format_html(
                        '<a href="{url}">{label}</a>',
                        url=ctxt_entity.get_absolute_url(),
                        label=ctxt_entity,
                    ),
                })),
            })

            if entity_to_link:
                e_email = EntityEmail.objects.create(
                    user=get_user_model().objects.get_admin(),  # TODO: workflow user!
                    description=gettext('Created by a workflow'),
                    sender=settings.EMAIL_SENDER,
                    recipient=recipient,
                    subject=self._subject,
                    body=body,
                    body_html=body_html,
                )
                Relation.objects.create(
                    user=e_email.user,
                    subject_entity=e_email,
                    type_id=REL_SUB_MAIL_RECEIVED,
                    object_entity=entity_to_link,
                )
            else:
                WorkflowEmail.objects.create(
                    sender=settings.EMAIL_SENDER,
                    recipient=recipient,
                    subject=self._subject,
                    body=body,
                    body_html=body_html,
                )

    def to_dict(self):
        d = super().to_dict()
        d['recipient'] = self._recipient.to_dict()
        d['entity'] = self._entity_source.to_dict()
        d['subject'] = self._subject
        d['body'] = self._body

        return d

    @classmethod
    def from_dict(cls, data, registry):
        # TODO: errors
        return cls(
            recipient=recipients_registry.build_recipient(data['recipient']),
            entity_source=registry.build_action_source(data['entity']),
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


# TODO: factorise with EmailSendingAction
class TemplateSendingAction(WorkflowAction):
    """A WorkflowAction which creates & sends emails, using an instance of
    EmailTemplate to build the subject/body/attachments/signature.
    The template is fill using the Contact/Organisation returned by its
    WorkflowActionSource 'entity_source'.
    """
    type_id = 'emails-template_sending'
    verbose_name = _('Sending an email (from a template)')

    def __init__(self, *,
                 recipient: ActionRecipient,
                 entity_source: WorkflowActionSource,
                 template: EmailTemplate,
                 ):
        self._recipient = recipient
        self._entity_source = entity_source

        if isinstance(template, str):
            self._template_uuid = template
            self._template = None
        else:
            self._template_uuid = str(template.uuid)
            self._template = template

    @classmethod
    def config_form_class(cls):
        from .forms.workflows import TemplateSendingActionForm
        return TemplateSendingActionForm

    @property
    def entity_source(self) -> WorkflowActionSource:
        return self._entity_source

    @property
    def recipient(self) -> ActionRecipient:
        return self._recipient

    # TODO: manage error (EmailTemplate does not exist anymore)
    @property
    def template(self) -> EmailTemplate:
        template = self._template
        if template is None:
            self._template = template = EmailTemplate.objects.get(uuid=self._template_uuid)

        return template

    def execute(self, context):
        recipient, concerned_entity = self._recipient.extract(context)
        if recipient:
            e_template = self.template
            person = self._entity_source.extract(context)
            # TODO: factorise with EmailTemplate
            ctxt = Context({
                var_name: getattr(person, var_name, '')
                for var_name in body_validator.allowed_variables
            })
            body = Template(e_template.body).render(ctxt)
            body_html = Template(e_template.body_html).render(ctxt)

            if concerned_entity:
                e_email = EntityEmail.objects.create(
                    user=get_user_model().objects.get_admin(),  # TODO: workflow user!
                    description=gettext('Created by a workflow'),
                    sender=settings.EMAIL_SENDER,
                    recipient=recipient,
                    subject=e_template.subject,
                    body=body,
                    body_html=body_html,
                    signature=e_template.signature,
                )
                e_email.attachments.set(e_template.attachments.all())

                Relation.objects.create(
                    user=e_email.user,
                    subject_entity=e_email,
                    type_id=REL_SUB_MAIL_RECEIVED,
                    object_entity=concerned_entity,
                )
            else:
                wf_email = WorkflowEmail.objects.create(
                    sender=settings.EMAIL_SENDER,
                    recipient=recipient,
                    subject=e_template.subject,
                    body=body,
                    body_html=body_html,
                    signature=e_template.signature,
                )
                wf_email.attachments.set(e_template.attachments.all())

    def to_dict(self):
        d = super().to_dict()
        d['recipient'] = self._recipient.to_dict()
        d['entity'] = self._entity_source.to_dict()
        d['template'] = str(self.template.uuid)

        return d

    @classmethod
    def from_dict(cls, data, registry):
        # TODO: errors
        return cls(
            recipient=recipients_registry.build_recipient(data['recipient']),
            entity_source=registry.build_action_source(data['entity']),
            template=data['template'],
        )

    def render(self, user):
        return format_html(
            '<div>'
            '{label}'
            ' <ul>'
            '  <li>{recipient}</li>'
            '  <li>{template_label}&nbsp;{link}</li>'
            ' </ul>'
            '</div>',
            label=gettext('Sending an email:'),
            recipient=self._recipient.render(user=user),
            template_label=gettext('Use template:'),
            link=widget_entity_hyperlink(entity=self.template, user=user),
        )
