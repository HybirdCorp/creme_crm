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

import pickle

from datetime import datetime

from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save, post_delete
from django.utils.translation import ugettext_lazy as _
from django.conf import settings

from creme_core.models import CremeModel, CremeEntity, Relation
from creme_core.models.fields import CreationDateTimeField

from activities.models import Meeting, Activity

from persons.models.contact import Contact

from activesync.utils import generate_guid

LIMIT_SYNC_KEY_HISTORY = settings.LIMIT_SYNC_KEY_HISTORY

CREATE = 1
UPDATE = 3
DELETE = 4

IN_CREME  = 1
ON_SERVER = 2

USER_HISTORY_TYPE = (
    (CREATE, _(u"Creation")),
    (UPDATE, _(u"Update")),
    (DELETE, _(u"Deletion")),
)

USER_HISTORY_TYPE_VERBOSE = dict(USER_HISTORY_TYPE)

USER_HISTORY_TYPE_IMG = {
    CREATE: "images/add_22.png",
    UPDATE: "images/edit_22.png",
    DELETE: "images/delete_22.png",
}

USER_HISTORY_WHERE = (
    (IN_CREME, _(u"In Creme")),
    (ON_SERVER, _(u"On server")),
)

USER_HISTORY_WHERE_IMG = {
    IN_CREME:  "images/creme_22.png",
    ON_SERVER: "images/organisation_22.png",#TODO: Change this icon for a server icon
}

USER_HISTORY_WHERE_VERBOSE = dict(USER_HISTORY_WHERE)

class CremeExchangeMapping(CremeModel):
    creme_entity_id    = models.IntegerField(u'Creme entity pk', unique=True)
    creme_entity_ct    = models.ForeignKey(ContentType, verbose_name=u'Creme entity ct')#For filtering when the entity was deleted
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
    client_id          = models.CharField(u'Creme Client ID',   max_length=32,  default=lambda :generate_guid(), unique=True)
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

    def purge(self):
        SyncKeyHistory.objects.filter(client=self).delete()
        CremeExchangeMapping.objects.filter(user=self.user).delete()
        AS_Folder.objects.filter(client=self).delete()
        self.delete()


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

            ids_to_delete = list(ids_to_delete)#Forcing the retrieve for MySQL v5.1.49 which "doesn't yet support 'LIMIT & IN/ALL/ANY/SOME subquery"

            SyncKeyHistory.objects.filter(id__in=ids_to_delete).delete()

        super(SyncKeyHistory, self).save(*args, **kwargs)


    @staticmethod
    def _get_previous_key(client):
        #keys = SyncKeyHistory.objects.filter(client=client).order_by('-created')[:2]
        keys = SyncKeyHistory.objects.filter(client=client).order_by('-created')

        if keys:
            keys[0].delete()
#            if len(keys) == 2:
#                return keys[1]
            for key in keys.all() :
                if key == '1' or key == '0':
                    key.delete()
                else:
                    return key

        return 0

    @staticmethod
    def back_to_previous_key(client):
        client.sync_key = SyncKeyHistory._get_previous_key(client)
        client.save()

    def __unicode__(self):
        return u"<SyncKeyHistory for <%s>, key=<%s>, created=<%s>>" % (self.client, self.sync_key, self.created)


class UserSynchronizationHistory(CremeModel):
    user           = models.ForeignKey(User, verbose_name=u'user')
    entity_repr    = models.CharField(u'Entity', max_length=200, default=None, blank=True, null=True)#Saving the representation of the entity in case it was deleted
    entity_pk      = models.IntegerField(u'Entity pk', max_length=50, blank=True, null=True)#Saving the pk of the entity
    entity_ct      = models.ForeignKey(ContentType, verbose_name=u'What', null=True, blank=True)
    created        = CreationDateTimeField(_('Creation date'), default=lambda: datetime.now())
    entity_changes = models.TextField(_(u'Entity changes'), default=lambda: pickle.dumps({}))
    type           = models.IntegerField(u'', max_length=1, choices=USER_HISTORY_TYPE)
    where          = models.IntegerField(u'', max_length=1, choices=USER_HISTORY_WHERE)

    _entity = None

    class Meta:
        app_label = 'activesync'
        verbose_name = u"History"
        verbose_name_plural = u"History"

    def __unicode__(self):
        return u"<UserSynchronizationHistory user=%s, entity_repr=%s>" % (self.user, self.entity_repr)

    def _get_entity(self):
        if self.entity_pk is None:
            return

        _entity = self._entity

        if _entity is not None:
            return _entity  #TODO: refactor (remove this 'return')

        try:
            _entity = self._entity = CremeEntity.objects.get(pk=self.entity_pk).get_real_entity()
        except CremeEntity.DoesNotExist:
            pass
        return _entity

    def _set_entity(self, entity):
        self.entity_pk   = entity.pk
        self.entity_repr = unicode(entity)
        self.entity_ct   = entity.entity_type
#        self._entity     = entity

    entity = property(_get_entity, _set_entity); del _get_entity, _set_entity

    @staticmethod
    def populate_entities(histories):
#        entities_pks = histories.values_list('entity_pk', flat=True)
        entities_pks = [history.entity_pk for history in histories]
#        entities = CremeEntity.objects.filter(pk__in=entities_pks)
        entities = CremeEntity.objects.filter(pk__in=set(entities_pks))#Forcing the retrieve for MySQL <= v5.1.49 which "doesn't yet support 'LIMIT & IN/ALL/ANY/SOME subquery"
        CremeEntity.populate_real_entities(entities)
        entities_map = dict((entity.pk, entity.get_real_entity()) for entity in entities)

        for hist in histories:
            hist._entity = entities_map.get(hist.entity_pk)

    #TODO: Optimize db queries
    def _get_changes(self):
        changes = pickle.loads(self.entity_changes.encode('utf-8'))
        get_for_id = ContentType.objects.get_for_id

        for k, v in changes.iteritems():
            if isinstance(v, dict):
                model_class = get_for_id(v['ct_id']).model_class()
                try:
                    changes[k] = model_class._default_manager.get(pk=v['pk'])
                except model_class.DoesNotExist:
                    changes[k] = _(u"This entity doesn't exist anymore")
        return changes


    def _set_changes(self, entity_changes):
        """ Set changes in self.entity_changes
            @params entity_changes has to be an iterable of (key, value) => [('a',1),...] or .iteritems(), etc.
            if a value is None the key is deleted
            if a value is a django 'Model' it will be transformed into a dict {'ct_id': ContentType id, 'pk': Its pk}
        """
        changes = self.changes

        get_for_model = ContentType.objects.get_for_model
        django_model = models.Model

        for k_change, v_change in entity_changes:
            if v_change is not None:
                if isinstance(v_change, django_model):
                    v_change = {'ct_id': get_for_model(v_change).id, 'pk': v_change.pk}
                changes[k_change] = v_change

            elif changes.has_key(k_change):
                del changes[k_change]

        self.entity_changes = pickle.dumps(changes)

    changes = property(_get_changes, _set_changes); del _get_changes, _set_changes

    @staticmethod
    def _add(user, entity, where, type, entity_changes=None):
        ush = UserSynchronizationHistory(user=user, where=where, type=type)

        if entity_changes is not None:
            ush.changes = entity_changes

        if isinstance(entity, CremeEntity):
            ush.entity = entity
        else:
            repr, ct = entity
            ush.entity_repr = unicode(repr)
            ush.entity_ct   = ct

        ush.save()
        return ush

    @staticmethod
    def add_create(user, entity, where):
        return UserSynchronizationHistory._add(user, entity, where, CREATE)

    @staticmethod
    def add_update(user, entity, where, entity_changes):
        return UserSynchronizationHistory._add(user, entity, where, UPDATE, entity_changes)

    @staticmethod
    def add_delete(user, entity, where):
        return UserSynchronizationHistory._add(user, entity, where, DELETE)


class AS_Folder(CremeModel):
    client       = models.ForeignKey(CremeClient, verbose_name=u'client')
    server_id    = models.CharField(u'Server id',    max_length=200)#Folder id on server
    parent_id    = models.CharField(u'Server id',    max_length=200, blank=True, null=True)#Parent id of this folder on the server
    display_name = models.CharField(u'Display name', max_length=200, default="")
    type         = models.IntegerField(u'Type',      max_length=2)
    sync_key     = models.CharField(u'sync key',     max_length=200, default=None, blank=True, null=True)
    as_class     = models.CharField(u'class',        max_length=25, default=None, blank=True, null=True)
    entity_id    = models.CharField(u'Entity id',    max_length=200, default=None, blank=True, null=True)#A reference to something in Creme (currently used for Calendars mapping)

    def __unicode__(self):
        return u"<AS_Folder for <%s> >" % self.client.user

    class Meta:
        app_label = 'activesync'
        verbose_name = u""
        verbose_name_plural = u""

    def get_parent(self):
        if self.parent_id is not None: #TODO: WTF ??!
            return None

        try:
            return AS_Folder.objects.get(server_id=self.parent_id)
        except:
            return None




from activesync.signals import post_save_activesync_handler, post_delete_activesync_handler, post_save_relation_employed_by, post_delete_relation_employed_by
post_save.connect(post_save_activesync_handler,     sender=Contact)
post_save.connect(post_save_activesync_handler,     sender=Meeting)
post_delete.connect(post_delete_activesync_handler, sender=Contact)
post_delete.connect(post_delete_activesync_handler, sender=Meeting)
post_save.connect(post_save_activesync_handler,     sender=Activity)
post_save.connect(post_save_relation_employed_by, sender=Relation)
post_delete.connect(post_delete_relation_employed_by, sender=Relation)

