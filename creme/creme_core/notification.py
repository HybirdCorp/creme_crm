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

from datetime import datetime

from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext_lazy

from creme.documents import get_document_model

from .core.notification import (
    NotificationChannelType,
    RelatedToModelBaseContent,
    TemplateBaseContent,
)
from .utils import dates


# Channels ---------------------------------------------------------------------
class SystemChannelType(NotificationChannelType):
    id = NotificationChannelType.generate_id('creme_core', 'system')
    verbose_name = pgettext_lazy('creme_core-channels', 'System')
    description = _('System upgrades…')


class AdministrationChannelType(NotificationChannelType):
    id = NotificationChannelType.generate_id('creme_core', 'administration')
    verbose_name = pgettext_lazy('creme_core-channels', 'Administration')
    description = _('Important changes on your user like password change.')


class JobsChannelType(NotificationChannelType):
    id = NotificationChannelType.generate_id('creme_core', 'jobs')
    verbose_name = _('Jobs')
    description = _('End of some long jobs (like CSV import).')


class RemindersChannelType(NotificationChannelType):
    id = NotificationChannelType.generate_id('creme_core', 'reminders')
    verbose_name = _('Reminders')
    description = _(
        'The reminder feature is used by Alerts & ToDos (from the app Assistants) for example.'
    )


# Contents ---------------------------------------------------------------------
class UpgradeAnnouncement(TemplateBaseContent):
    id = TemplateBaseContent.generate_id('creme_core', 'upgrade')
    subject_template_name: str = 'creme_core/notifications/upgrade_announcement/subject.txt'
    body_template_name: str = 'creme_core/notifications/upgrade_announcement/body.txt'
    html_body_template_name: str = 'creme_core/notifications/upgrade_announcement/body.html'

    def __init__(self, start: datetime, message=''):
        self.start = start
        self.message = message

    def as_dict(self):
        d = {'start': dates.dt_to_ISO8601(self.start)}

        msg = self.message
        if msg:
            d['message'] = msg

        return d

    @classmethod
    def from_dict(cls, data):
        try:
            start = dates.dt_from_ISO8601(data['start'])
        except (KeyError, TypeError, ValueError) as e:
            raise cls.DeserializationError(
                f'{cls.__name__}.from_dict(): bad "start" argument'
            ) from e

        message = data.get('message', '')
        if not isinstance(message, str):
            raise cls.DeserializationError(
                f'{cls.__name__}.from_dict(): bad "message" argument'
            )

        return cls(start=start, message=message)

    def get_context(self, user):
        ctxt = super().get_context(user)
        ctxt['start'] = self.start
        ctxt['message'] = self.message

        return ctxt


class MassImportDoneContent(RelatedToModelBaseContent):
    id = RelatedToModelBaseContent.generate_id('creme_core', 'mass_import_done')
    subject_template_name: str = 'creme_core/notifications/mass_import/subject.txt'
    body_template_name: str = 'creme_core/notifications/mass_import/body.txt'
    html_body_template_name: str = 'creme_core/notifications/mass_import/body.html'

    model = get_document_model()
