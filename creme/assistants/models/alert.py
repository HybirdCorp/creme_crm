# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2018  Hybird
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

# from collections import defaultdict

from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db.models import (CharField, TextField, BooleanField, DateTimeField,
        ForeignKey, PositiveIntegerField, CASCADE)
from django.urls import reverse
from django.utils.translation import ugettext_lazy as _

from creme.creme_core.models import CremeModel  # CremeEntity
from creme.creme_core.models.fields import CremeUserForeignKey
# from creme.creme_core.core.function_field import (FunctionField, FunctionFieldResult,
#         FunctionFieldResultsList)


class Alert(CremeModel):
    title        = CharField(_('Title'), max_length=200)
    description  = TextField(_('Description'), blank=True)
    is_validated = BooleanField(_('Validated'), editable=False, default=False)
    reminded     = BooleanField(_('Notification sent'), editable=False, default=False)  # Need by creme_core.core.reminder
    trigger_date = DateTimeField(_('Trigger date'))

    # TODO: use a True ForeignKey to CremeEntity (do not forget to remove the signal handlers)
    entity_content_type = ForeignKey(ContentType, related_name='alert_entity_set', editable=False, on_delete=CASCADE)
    entity_id           = PositiveIntegerField(editable=False).set_tags(viewable=False)
    creme_entity        = GenericForeignKey(ct_field="entity_content_type", fk_field='entity_id')

    user = CremeUserForeignKey(verbose_name=_('Owner user'))

    class Meta:
        app_label = 'assistants'
        verbose_name = _('Alert')
        verbose_name_plural = _('Alerts')

    def __str__(self):
        return self.title

    def get_edit_absolute_url(self):
        return reverse('assistants__edit_alert', args=(self.id,))

    @staticmethod
    def get_alerts(entity):
        return Alert.objects.filter(is_validated=False, entity_id=entity.id).select_related('user')

    @staticmethod
    def get_alerts_for_home(user):
        return Alert.objects.filter(is_validated=False, user__in=[user] + user.teams).select_related('user')

    @staticmethod
    def get_alerts_for_ctypes(ct_ids, user):
        return Alert.objects.filter(entity_content_type__in=ct_ids, user__in=[user] + user.teams, is_validated=False) \
                            .select_related('user')

    def get_related_entity(self):  # For generic views
        return self.creme_entity

    @property
    def to_be_reminded(self):
        return not self.is_validated and not self.reminded


# class _GetAlerts(FunctionField):
#     name         = 'assistants-get_alerts'
#     verbose_name = _(u'Alerts')
#     result_type  = FunctionFieldResultsList
#
#     def __call__(self, entity, user):
#         cache = getattr(entity, '_alerts_cache', None)
#
#         if cache is None:
#             cache = entity._alerts_cache = list(Alert.objects
#                                                      .filter(entity_id=entity.id, is_validated=False)
#                                                      .order_by('trigger_date')
#                                                      .values_list('title', flat=True)
#                                                )
#
#         return FunctionFieldResultsList(FunctionFieldResult(title) for title in cache)
#
#     @classmethod
#     def populate_entities(cls, entities, user):
#         alerts_map = defaultdict(list)
#
#         for title, e_id in Alert.objects.filter(entity_id__in=[e.id for e in entities], is_validated=False) \
#                                         .order_by('trigger_date') \
#                                         .values_list('title', 'entity_id'):
#             alerts_map[e_id].append(title)
#
#         for entity in entities:
#             entity._alerts_cache = alerts_map[entity.id]
#
#
# CremeEntity.function_fields.add(_GetAlerts())
