# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2011  Hybird
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

from django.db.models import CharField, TextField, BooleanField, DateTimeField, ForeignKey, PositiveIntegerField
from django.db.models.signals import pre_delete
from django.utils.translation import ugettext_lazy as _
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.generic import GenericForeignKey
from django.contrib.auth.models import User

from creme_core.models import CremeModel, CremeEntity


class Alert(CremeModel):
    title               = CharField(max_length=200)
    description         = TextField(_(u'Description'), blank=True, null=True)
    is_validated        = BooleanField(_('Validated'), editable=False)
    trigger_date        = DateTimeField(_(u"Trigger date"))

    entity_content_type = ForeignKey(ContentType, related_name="alert_entity_set", editable=False)
    entity_id           = PositiveIntegerField(editable=False)
    creme_entity        = GenericForeignKey(ct_field="entity_content_type", fk_field="entity_id")

    user                = ForeignKey(User, verbose_name=_(u'Assigned to'))

    class Meta:
        app_label = 'assistants'
        verbose_name = _('Alert')
        verbose_name_plural = _(u'Alerts')

    @staticmethod
    def get_alerts(entity):
        return Alert.objects.filter(is_validated=False, entity_id=entity.id).select_related('user')

    @staticmethod
    def get_alerts_for_home(user):
        return Alert.objects.filter(is_validated=False, user=user).select_related('user')

    @staticmethod
    def get_alerts_for_ctypes(ct_ids, user):
        return Alert.objects.filter(entity_content_type__in=ct_ids, user=user, is_validated=False).select_related('user')

    def get_related_entity(self): #for generic views
        return self.creme_entity


#TODO: can delete this with  a WeakForeignKey ??
def dispose_entity_alerts(sender, instance, **kwargs):
    Alert.objects.filter(entity_id=instance.id).delete()

pre_delete.connect(dispose_entity_alerts, sender=CremeEntity)
