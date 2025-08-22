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

from __future__ import annotations

import logging
from typing import NewType

from django.db.models import Model
from django.template.loader import get_template
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _

logger = logging.getLogger(__name__)

Output = NewType('Output', str)
OUTPUT_WEB   = Output('web')
OUTPUT_EMAIL = Output('email')
_DEFAULT_OUTPUT = Output('')


# Channels ---------------------------------------------------------------------
class NotificationChannelType:
    """The instance of <creme_core.models.NotificationChannel> can have a unique type.
    Each type has:
      - a string ID (so the NotificationChannel instances can store it in DB).
      - a verbose name & a description which are used in configuration UI for example.

    Examples of channel types: "system", "admin", "reminders", "jobs".

    Note: channels created by users does not have a type; their name & description
          are given by the users & store in these channels.
    """
    id: str = ''   # Override in child classes; use generate_id()
    verbose_name: str = 'CHAN'  # Override with a gettext_lazy object
    description: str = '...'  # Override with a gettext_lazy object

    @staticmethod
    def generate_id(app_name: str, name: str) -> str:
        """Helper used to create the value of the class attribute 'id'."""
        return f'{app_name}-{name}'


# Contents ---------------------------------------------------------------------
# TODO: system to group queries (i.e. populate related entities/instances)
class NotificationContent:
    """Class which generates content (subject & body) of notification.
    Instances can be serialized to JSONisable dictionary (& built from dictionary
    of course), so they can be stored in <models.Notification>.

    Why not store all the notification strings in <models.Notification>?
    Retrieving a content class by its ID allows to:
      - get strings translated in the user's language (so you have to define
        different class for different content).
      - only store the ID & the context in DataBase (kind of compression).
    """
    id: str = ''

    class DeserializationError(Exception):
        pass

    def __eq__(self, other):
        return (
            isinstance(other, NotificationContent)
            and self.id == other.id
            and self.as_dict() == other.as_dict()
        )

    @staticmethod
    def generate_id(app_name: str, name: str) -> str:
        """Helper used to create the value of the class attribute 'id'."""
        return f'{app_name}-{name}'

    def as_dict(self) -> dict:
        """Returns a dictionary containing the internal state. This dictionary:
        - can be encoded to JSON.
        - is compatible with the method <from_dict()>.
        """
        return {}

    @classmethod
    def from_dict(cls, data: dict) -> NotificationContent:
        """Build an instance from a dictionary (produced by <as_dict()>).
        So it's a deserialization method.
        @raise DeserializationError
        """
        return cls(**data)

    def get_subject(self, user) -> str:
        raise NotImplementedError

    def get_body(self, user) -> str:
        raise NotImplementedError

    def get_html_body(self, user) -> str:
        raise NotImplementedError


class SimpleNotifContent(NotificationContent):
    """This kind on Content stores all the subject/body strings in its context.
    So the compression & translation feature of NotificationContent are globally
    lost, but you do not have to create a specific content class
    """
    id = NotificationContent.generate_id('creme_core', 'simple')

    def __init__(self, subject: str, body: str, html_body: str = ''):
        self.subject = subject
        self.body = body
        self.html_body = html_body

    def as_dict(self) -> dict:
        d = {
            'subject': self.subject,
            'body': self.body,
        }

        html_body = self.html_body
        if html_body:
            d['html_body'] = html_body

        return d

    def get_subject(self, user):
        return self.subject

    def get_body(self, user):
        return self.body

    def get_html_body(self, user):
        return self.html_body


class StringBaseContent(NotificationContent):
    """Base class of content.
    Generates the subject & bodies from simple strings.
    """
    id = NotificationContent.generate_id('creme_core', 'upgrade')
    # Override these attributes in child classes.
    # Hint: use gettext_lazy()
    subject = '*SUBJECT*'
    body = '*BODY*'
    html_body = '*HTML BODY*'

    def get_subject(self, user):
        # NB: str() to cast gettext_lazy objects
        return str(self.subject)

    def get_body(self, user):
        return str(self.body)

    def get_html_body(self, user):
        return str(self.html_body)


class TemplateBaseContent(NotificationContent):
    """Base class of content.
    Generates the subject & bodies from templates.
    """
    subject_template_name: str = 'OVERRIDE_ME.txt'
    body_template_name: str = 'OVERRIDE_ME.txt'
    html_body_template_name: str = 'OVERRIDE_ME.html'

    def get_context(self, user):
        return {'user': user}

    def get_subject(self, user):
        return get_template(self.subject_template_name).render(self.get_context(user))

    def get_body(self, user):
        return get_template(self.body_template_name).render(self.get_context(user))

    def get_html_body(self, user):
        return get_template(self.html_body_template_name).render(self.get_context(user))


# TODO: move to utils/core? (+unit tests)
class _LazyModelRef:
    """Stores a reference to a <django.db.models.Model> instance.
    It contains the ID of this instance, & can try to retrieve if it's possible.
    """
    def __init__(self, *, model=Model, instance: Model | int):
        self._model = model

        if isinstance(instance, Model):
            self._instance = instance
            self._instance_id = instance.id
        else:
            self._instance = None
            self._instance_id = instance

    @property
    def instance_id(self):
        return self._instance_id

    @cached_property
    def instance(self) -> Model | None:
        instance = self._instance
        if instance is None:
            instance = self._model.objects.filter(id=self._instance_id).first()

        return instance


class RelatedToModelBaseContent(TemplateBaseContent):
    """Base class of content.
    This kind of content is related to a <django.db.models.Model> instance.
    """
    subject_template_name: str = 'creme_core/notifications/related_to_model/subject.txt'
    body_template_name: str = 'creme_core/notifications/related_to_model/body.txt'
    html_body_template_name: str = 'creme_core/notifications/related_to_model/body.html'

    # TODO: accept natural-key?
    model = Model  # OVERRIDE in child classes

    def __init__(self, instance: Model | int):
        self.ref = _LazyModelRef(model=self.model, instance=instance)

    def as_dict(self) -> dict:
        return {'instance': self.ref.instance_id}

    def get_context(self, user):
        ctxt = super().get_context(user)
        ctxt['object'] = self.ref.instance

        return ctxt


# Registry ---------------------------------------------------------------------
# TODO: possibility to deactivate an output?
class NotificationRegistry:
    """Registry usd by the Notification system.
    It contains the different classes of:
      - NotificationChannelType
      - NotificationContent
    """
    class RegistrationError(Exception):
        pass

    class FallbackContent(StringBaseContent):
        subject = _('Notification (type cannot be determined)')
        body = html_body = _('Please contact your administrator')

        def __init__(self, **kwargs):
            pass

    def __init__(self) -> None:
        self._outputs: dict[str, str] = {}
        self._channel_classes: dict[str, type[NotificationChannelType]] = {}
        self._content_classes: dict[Output, dict[str, type[NotificationContent]]] = {
            _DEFAULT_OUTPUT: {},
        }

    def get_channel_type(self, channel_type_id: str) -> NotificationChannelType | None:
        cls = self._channel_classes.get(channel_type_id)
        if cls is None:
            logger.warning('The channel type "%s" is invalid.', channel_type_id)

            return None

        return cls()

    def get_content_class(self, *,
                          output: Output | str,
                          content_id: str,
                          ) -> type[NotificationContent]:
        content_classes = self._content_classes

        output_contents = content_classes.get(output)
        if output_contents is None:
            raise KeyError(f'This output is not registered: {output}')

        try:
            return output_contents[content_id]
        except KeyError:
            pass

        try:
            return content_classes[_DEFAULT_OUTPUT][content_id]
        except KeyError:
            pass

        logger.critical(
            'the notification content ID "%s" is invalid (have you deleted the '
            'content class without cleaning the data base?)',
            content_id,
        )

        return self.FallbackContent

    @property
    def output_choices(self):
        yield from self._outputs.items()

    def register_channel_types(
        self,
        *channel_types: type[NotificationChannelType],
    ) -> NotificationRegistry:
        current_types = self._channel_classes

        for channel_type in channel_types:
            type_id = channel_type.id

            if not type_id:
                raise self.RegistrationError(
                    f'Channel type class with empty id: {channel_type}',
                )

            if type_id in current_types:
                raise self.RegistrationError(
                    f"Duplicated channel type's id or type registered twice: {type_id}"
                )

            current_types[channel_type.id] = channel_type

        return self

    def register_content(
        self, *, content_cls: type[NotificationContent], output: Output = _DEFAULT_OUTPUT,
    ) -> NotificationRegistry:
        content_id = content_cls.id
        if not content_id:
            raise self.RegistrationError(
                f'Notification content class with empty id: {content_cls}',
            )

        content_classes = self._content_classes
        try:
            output_contents = content_classes[output]
        except KeyError as e:
            raise self.RegistrationError(
                f'Notification output is not registered: {output}',
            ) from e

        if content_id in output_contents:
            raise self.RegistrationError(
                f"""Duplicated content's id or content registered twice for"""
                f"""output "{output}": {content_id}"""
            )

        output_contents[content_id] = content_cls
        if content_id:
            content_classes[_DEFAULT_OUTPUT].setdefault(content_id, content_cls)

        return self

    def register_output(self, value: Output, label: str) -> NotificationRegistry:
        if not value:
            raise self.RegistrationError('Notification output is empty')

        outputs = self._outputs

        if value in outputs:
            raise self.RegistrationError(f'Duplicated output: {value}')

        outputs[value] = label
        self._content_classes[value] = {}

        return self


notification_registry = NotificationRegistry()
