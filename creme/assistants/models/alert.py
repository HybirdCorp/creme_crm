# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2021  Hybird
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

from django.db import models
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from creme.creme_core import models as creme_models
from creme.creme_core.models import fields as creme_fields


class AlertManager(models.Manager):
    def filter_by_user(self, user):
        return self.filter(user__in=[user, *user.teams])


class Alert(creme_models.CremeModel):
    user = creme_fields.CremeUserForeignKey(verbose_name=_('Owner user'))
    title = models.CharField(_('Title'), max_length=200)
    description = models.TextField(_('Description'), blank=True)
    is_validated = models.BooleanField(_('Validated'), editable=False, default=False)
    trigger_date = models.DateTimeField(_('Trigger date'))

    # Needed by creme_core.core.reminder
    reminded = models.BooleanField(_('Notification sent'), editable=False, default=False)

    entity_content_type = creme_fields.EntityCTypeForeignKey(related_name='+', editable=False)
    entity = models.ForeignKey(
        creme_models.CremeEntity, related_name='assistants_alerts',
        editable=False, on_delete=models.CASCADE,
    ).set_tags(viewable=False)
    creme_entity = creme_fields.RealEntityForeignKey(
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
        return self.creme_entity

    @property
    def to_be_reminded(self):
        return not self.is_validated and not self.reminded
