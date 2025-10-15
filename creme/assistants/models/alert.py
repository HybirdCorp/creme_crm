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

from datetime import datetime, time

from django.db import models
from django.urls import reverse
from django.utils.timezone import make_aware
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext_lazy

import creme.creme_core.models as core_models
import creme.creme_core.models.fields as core_fields


class AlertManager(models.Manager):
    def filter_by_user(self, user):
        return self.filter(user__in=[user, *user.teams])


class Alert(core_models.CremeModel):
    user = core_fields.CremeUserForeignKey(
        verbose_name=_('Owner user'), null=True, blank=True,
    ).set_null_label(pgettext_lazy('assistants-owner', '*auto*'))
    title = models.CharField(_('Title'), max_length=200)
    description = models.TextField(_('Description'), blank=True)
    is_validated = models.BooleanField(_('Validated'), editable=False, default=False)

    # Not viewable by users, For administrators currently.
    creation_date = core_fields.CreationDateTimeField().set_tags(viewable=False)
    modification_date = core_fields.ModificationDateTimeField().set_tags(viewable=False)

    trigger_date = models.DateTimeField(_('Trigger date'), null=True, editable=False)
    trigger_offset = models.JSONField(default=dict, editable=False)

    # Needed by creme_core.core.reminder
    reminded = models.BooleanField(_('Notification sent'), editable=False, default=False)

    entity_content_type = core_fields.EntityCTypeForeignKey(related_name='+', editable=False)
    entity = models.ForeignKey(
        core_models.CremeEntity,
        related_name='assistants_alerts',
        editable=False, on_delete=models.CASCADE,
    ).set_tags(viewable=False)
    real_entity = core_fields.RealEntityForeignKey(
        ct_field='entity_content_type', fk_field='entity',
    )

    objects = AlertManager()

    creation_label = _('Create an alert')
    save_label     = _('Save the alert')

    class Meta:
        app_label = 'assistants'
        verbose_name = _('Alert')
        verbose_name_plural = _('Alerts')

    def __str__(self):
        return self.title

    def get_edit_absolute_url(self):
        return reverse('assistants__edit_alert', args=(self.id,))

    def get_related_entity(self):  # For generic views
        return self.real_entity

    @property
    def to_be_reminded(self):
        return not self.is_validated and not self.reminded

    # TODO: staticmethod? move in a new abstraction DateOffset?
    def trigger_date_from_offset(self, cell, sign, period, entity=None):
        # TODO?
        # if not isinstance(cell, EntityCellRegularField):
        #     return None
        origin = cell.field_info.value_from(entity or self.real_entity)

        if origin:
            if not isinstance(origin, datetime):
                origin = make_aware(datetime.combine(origin, time()))

            return origin + (sign * period.as_timedelta())

        return None
