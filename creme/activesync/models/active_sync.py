# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2010  Hybird
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
from django.contrib.auth.models import User
from django.db.models.signals import post_save, post_delete
from django.utils.translation import ugettext_lazy as _
from creme_config.models.setting import SettingKey

from creme_core.models import CremeModel, CremeEntity
from creme_core.models.fields import CreationDateTimeField

from persons.models.contact import Contact

from activesync.utils import generate_guid
from activesync.config import LIMIT_SYNC_KEY_HISTORY
from activesync.constants import USER_MOBILE_SYNC_SERVER_URL

class CremeExchangeMapping(CremeModel):
    creme_entity_id    = models.IntegerField(u'Creme entity pk', unique=True)
    exchange_entity_id = models.CharField(u'Exchange entity pk', max_length=64, unique=True)
    synced             = models.BooleanField(u'Already synced on server', default=False)
    is_creme_modified  = models.BooleanField(u'Modified by creme?',       default=False)
    was_deleted        = models.BooleanField(u'Was deleted by creme?',    default=False)#Seems redundant with is_deleted but isn't in case of TRUE_DELETE
    user               = models.ForeignKey(User, verbose_name=u'Belongs to')
    creme_entity_repr  = models.CharField(u'Verbose entity representation', max_length=200, null=True, blank=True, default=u"")#IHM/User purposes

    def __unicode__(self):
        return u"<CremeExchangeMapping ce_id: <%s>, ex_id: <%s>, belongs to %s>" % (self.creme_entity_id, self.exchange_entity_id, self.user)

    class Meta:
        app_label = 'activesync'
        verbose_name = u""
        verbose_name_plural = u""

    def get_entity(self):
        entity = None
        if not self.creme_entity_id:
            return entity

        try:
            entity = CremeEntity.objects.get(pk=self.creme_entity_id).get_real_entity()
        except CremeEntity.DoesNotExist:
            pass
        
        return entity


class CremeClient(CremeModel):
    user               = models.ForeignKey(User, verbose_name=u'Assigned to', unique=True)
    client_id          = models.CharField(u'Creme Client ID',   max_length=32,  default=generate_guid(), unique=True)
    policy_key         = models.CharField(u'Last policy key',   max_length=200, default=0)
    sync_key           = models.CharField(u'Last sync key',     max_length=200, default=None, blank=True, null=True)
    folder_sync_key    = models.CharField(u'Last folder sync key', max_length=200, default=None, blank=True, null=True)
    contact_folder_id  = models.CharField(u'Contact folder id', max_length=64,  default=None, blank=True, null=True)
    last_sync          = models.DateTimeField(_(u'Last sync'), blank=True, null=True)

    def __unicode__(self):
        return u"<CremeClient for <%s> >" % self.user

    class Meta:
        app_label = 'activesync'
        verbose_name = u""
        verbose_name_plural = u""


class SyncKeyHistory(CremeModel):
    client   = models.ForeignKey(CremeClient, verbose_name=u'client')
    sync_key = models.CharField(u'sync key', max_length=200, default=None, blank=True, null=True)
    created  = CreationDateTimeField(_('Creation date'))

    class Meta:
        app_label = 'activesync'
        verbose_name = u""
        verbose_name_plural = u""

    def save(self, *args, **kwargs):
        client_synckeys = SyncKeyHistory.objects.filter(client=self.client)
        client_synckeys_count = client_synckeys.count()
        if client_synckeys_count > LIMIT_SYNC_KEY_HISTORY:
            ids_to_delete = client_synckeys.order_by('created')[:client_synckeys_count-LIMIT_SYNC_KEY_HISTORY].values_list('id',flat=True)
            SyncKeyHistory.objects.filter(id__in=ids_to_delete).delete()

        super(SyncKeyHistory, self).save(*args, **kwargs)


    @staticmethod
    def _get_previous_key(client):
        keys = SyncKeyHistory.objects.filter(client=client).order_by('-created')[:2]

        if keys:
            keys[0].delete()
            if len(keys) == 2:
                return keys[1]
        return 0

    @staticmethod
    def back_to_previous_key(client):
        client.sync_key = SyncKeyHistory._get_previous_key(client)
        client.save()

    def __unicode__(self):
        return u"<SyncKeyHistory for <%s>, key=<%s>, created=<%s>>" % (self.client, self.sync_key, self.created)


from activesync.signals import post_save_activesync_handler, post_delete_activesync_handler
post_save.connect(post_save_activesync_handler,     sender=Contact)
post_delete.connect(post_delete_activesync_handler, sender=Contact)

