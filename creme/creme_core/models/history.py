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
from logging import debug

from django.db.models import Model, PositiveSmallIntegerField, CharField, TextField, DateTimeField, ForeignKey, SET_NULL
from django.db.models.signals import post_save, post_init, pre_delete
from django.utils.translation import ugettext_lazy as _
from django.utils.simplejson import loads as jsonloads, dumps as jsondumps
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.models import User

from creme_core.models import CremeEntity


_get_ct = ContentType.objects.get_for_model
_EXCLUDED_FIELDS = frozenset(('id', 'entity_type', 'is_deleted', 'is_actived',
                              'cremeentity_ptr', 'header_filter_search_field',
                              'created', 'modified',
                            ))
_SERIALISABLE_FIELDS = frozenset(('CharField',

                                  'IntegerField', 'BigIntegerField', 'PositiveIntegerField',
                                  'PositiveSmallIntegerField', 'SmallIntegerField',

                                  'BooleanField', 'NullBooleanField',

                                  'ForeignKey',

    #Display has to be improved
        #'DateField'

    #To be tested
        #'DateTimeField'
        #'TimeField'

        #'FilePathField'

        #'DecimalField'
        #'FloatField'
        #'IPAddressField'
        #'SlugField'

    #Excluded
        #'TextField' => too long
        #'FileField' => not serialisable
                                ))



class HistoryLine(Model):
    entity       = ForeignKey(CremeEntity, null=True, on_delete=SET_NULL)
    entity_ctype = ForeignKey(ContentType)  #we do not use entity.entity_type because we keep history of the deleted entities
    entity_owner = ForeignKey(User)         #we do not use entity.user because we keep history of the deleted entities
    username     = CharField(max_length=30) #not a Fk to a User object because we want to keep the same line after the deletion of a User.
    date         = DateTimeField()
    type         = PositiveSmallIntegerField() #see TYPE_*
    value        = TextField(null=True) #TODO: use a JSONField ? (see EntityFilter)

    _entity_repr = None
    _modifications = None

    TYPE_CREATION = 1
    TYPE_EDITION  = 2
    TYPE_DELETION = 3

    _TYPE_MAP = {
            TYPE_CREATION: _(u'Creation'),
            TYPE_EDITION:  _(u'Edition'),
            TYPE_DELETION: _(u'Deletion'),
        }

    class Meta:
        app_label = 'creme_core'

    def __repr__(self):
        return 'HistoryLine(entity_id=%s, entity_owner_id=%s, date=%s, type=%s, value=%s)' %(
                    self.entity_id, self.entity_owner_id, self.date, self.type, self.value
                )

    @staticmethod
    def _encode_attrs(instance, modifs=()):
        value = [unicode(instance)]

        try:
            attrs = jsondumps(value + list(modifs))
        except TypeError, e:
            debug('HistoryLine: ' + str(e))
            attrs = jsondumps(value)

        return attrs

    def _read_attrs(self):
        value = jsonloads(self.value)
        self._entity_repr   = value.pop(0)
        self._modifications = value

    @property
    def entity_repr(self):
        if self._entity_repr is None:
            self._read_attrs()

        return self._entity_repr

    def get_type_str(self):
        return HistoryLine._TYPE_MAP[self.type]

    @property
    def modifications(self):
        if self._modifications is None:
            self._read_attrs()

        return self._modifications

    @staticmethod
    def _create_line_4_instance(instance, ltype, modifs=()):
        HistoryLine.objects.create(entity=instance,
                                   entity_ctype=instance.entity_type,
                                   entity_owner=instance.user,
                                   date=instance.modified,
                                   type=ltype,
                                   value=HistoryLine._encode_attrs(instance, modifs=modifs)
                                  )

    @staticmethod
    def _log_creation_edition(sender, instance, created, **kwargs):
        if not isinstance(instance, CremeEntity):
            return

        if created:
            HistoryLine._create_line_4_instance(instance, HistoryLine.TYPE_CREATION)
        else:
            backup = getattr(instance, '_instance_backup', None)
            if backup is None:
                return

            modifs = []
            old_instance = instance.__class__()
            old_instance.__dict__ = backup

            for field in instance._meta.fields:
                fname = field.name

                if fname in _EXCLUDED_FIELDS: continue

                old_value = getattr(old_instance, fname)
                new_value = getattr(instance, fname)

                if isinstance(field, ForeignKey):
                    old_value = old_value and old_value.pk
                    new_value = new_value and new_value.pk

                if old_value != new_value:
                    if field.get_internal_type() not in _SERIALISABLE_FIELDS:
                        modif = (fname,)
                    elif old_value:
                        modif = (fname, old_value, new_value)
                    else:
                        modif = (fname, new_value)

                    modifs.append(modif)

            if modifs:
                HistoryLine._create_line_4_instance(instance, HistoryLine.TYPE_EDITION, modifs=modifs)

    @staticmethod
    def _log_deletion(sender, instance, **kwargs):
        if isinstance(instance, CremeEntity) and instance.entity_type_id == _get_ct(instance).id: #TODO: factorise ??
            HistoryLine.objects.create(entity_ctype=instance.entity_type,
                                       entity_owner=instance.user,
                                       date=datetime.now(),
                                       type=HistoryLine.TYPE_DELETION,
                                       value=HistoryLine._encode_attrs(instance),
                                      )

    @staticmethod
    def _prepare_edition(sender, instance, **kwargs):
        if isinstance(instance, CremeEntity) and instance.id and instance.entity_type_id == _get_ct(instance).id:
            instance._instance_backup = instance.__dict__.copy()


post_init.connect(HistoryLine._prepare_edition,      dispatch_uid='creme_core-historyline._prepare_edition')
post_save.connect(HistoryLine._log_creation_edition, dispatch_uid='creme_core-historyline._log_creation_edition') # "sender=CremeEntity" does not work with classes that inherit CremeEntity
pre_delete.connect(HistoryLine._log_deletion,        dispatch_uid='creme_core-historyline._log_deletion')
