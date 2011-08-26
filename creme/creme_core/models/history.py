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
from logging import debug, info

from django.db.models import Model, PositiveSmallIntegerField, CharField, TextField, DateTimeField, ForeignKey, SET_NULL
from django.db.models.signals import post_save, post_init, pre_delete
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy as _, ugettext
from django.utils.simplejson import loads as jsonloads, dumps as jsondumps
from django.contrib.contenttypes.models import ContentType

from creme_core.models import CremeEntity, RelationType, Relation
from creme_core.global_info import get_global_info
from creme_core.models.fields import CremeUserForeignKey


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

#TODO: factorise with gui.field_printers ?? (html and text mode ??)
_basic_printer = lambda field, val: val

def _fk_printer(field, val):
    model = field.rel.to

    if issubclass(model, CremeEntity):
        return ugettext(u'Entity #%s') % val

    try:
        out = model.objects.get(pk=val)
    except model.DoesNotExist, e:
        info(str(e))
        out = val

    return unicode(out)

_PRINTERS = {
        'BooleanField': (lambda field, val: ugettext(u'True') if val else ugettext(u'False')),
        'ForeignKey':   _fk_printer,
    }

class HistoryLine(Model):
    entity       = ForeignKey(CremeEntity, null=True, on_delete=SET_NULL)
    entity_ctype = ForeignKey(ContentType)  #we do not use entity.entity_type because we keep history of the deleted entities
    entity_owner = CremeUserForeignKey()    #we do not use entity.user because we keep history of the deleted entities
    username     = CharField(max_length=30) #not a Fk to a User object because we want to keep the same line after the deletion of a User.
    date         = DateTimeField()
    type         = PositiveSmallIntegerField() #see TYPE_*
    value        = TextField(null=True) #TODO: use a JSONField ? (see EntityFilter)

    _entity_repr = None
    _modifications = None
    _related_line_id = None
    _related_line = False

    TYPE_CREATION = 1
    TYPE_EDITION  = 2
    TYPE_DELETION = 3
    TYPE_RELATED  = 4

    _TYPE_MAP = {
            TYPE_CREATION: _(u'Creation'),
            TYPE_EDITION:  _(u'Edition'),
            TYPE_DELETION: _(u'Deletion'),
            TYPE_RELATED:  _(u'Related modification'),
        }

    class Meta:
        app_label = 'creme_core'

    def __repr__(self):
        return 'HistoryLine(entity_id=%s, entity_owner_id=%s, date=%s, type=%s, value=%s)' % (
                    self.entity_id, self.entity_owner_id, self.date, self.type, self.value
                )

    @staticmethod
    def _encode_attrs(instance, modifs=(), related_line_id=None):
        value = [unicode(instance)]
        if related_line_id:
            value.append(related_line_id)

        try:
            attrs = jsondumps(value + list(modifs))
        except TypeError, e:
            debug('HistoryLine: ' + str(e))
            attrs = jsondumps(value)

        return attrs

    def _read_attrs(self):
        value = jsonloads(self.value)
        self._entity_repr   = value.pop(0)

        if self.type == HistoryLine.TYPE_RELATED:
            self._modifications = []
            self._related_line_id = value[0]
        else:
            self._modifications = value
            self._related_line_id = 0

    @property
    def entity_repr(self): #TODO factorise ?
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

    @property
    def verbose_modifications(self): #TODO: use a templatetag instead ??
        vmodifs = []

        get_field = self.entity_ctype.model_class()._meta.get_field

        for modif in self.modifications:
            field = get_field(modif[0])
            field_name = field.verbose_name

            if len(modif) == 1:
                vmodif = mark_safe(ugettext(u'Set field “%(field)s”') % {
                                        'field': field_name,
                                    })
            elif len(modif) == 2:
                vmodif = mark_safe(ugettext(u'Set field “%(field)s” to “%(value)s”') % {
                                        'field': field_name,
                                        'value': _PRINTERS.get(field.get_internal_type(), _basic_printer)(field, modif[1]),
                                    })
            else:
                printer = _PRINTERS.get(field.get_internal_type(), _basic_printer)
                vmodif = mark_safe(ugettext(u'Set field “%(field)s” from “%(oldvalue)s” to “%(value)s”') % {
                                        'field':    field_name,
                                        'oldvalue': printer(field, modif[1]), #TODO: improve for fk ???
                                        'value':    printer(field, modif[2]),
                                    })

            vmodifs.append(vmodif)

        return vmodifs

    def _get_related_line_id(self):
        if self._related_line_id is None:
            self._read_attrs()

        return self._related_line_id

    @property
    def related_line(self):
        if self._related_line is False:
            self._related_line = None
            line_id = self._get_related_line_id()

            if line_id:
                try:
                    self._related_line = HistoryLine.objects.get(pk=line_id)
                except HistoryLine.DoesNotExist:
                    pass

        return self._related_line

    @staticmethod
    def _create_line_4_instance(instance, ltype, date=None, modifs=(), related_line_id=None):
        return HistoryLine.objects.create(entity=instance,
                                          entity_ctype=instance.entity_type,
                                          entity_owner=instance.user,
                                          username=get_global_info('username') or '',
                                          date=date or instance.modified,
                                          type=ltype,
                                          value=HistoryLine._encode_attrs(instance,
                                                                          modifs=modifs,
                                                                          related_line_id=related_line_id,
                                                                         )
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
                create_line = HistoryLine._create_line_4_instance

                hline = create_line(instance, HistoryLine.TYPE_EDITION, modifs=modifs)
                relations = Relation.objects.filter(subject_entity=instance.id,
                                                    type__in=HistoryConfigItem.objects.values_list('relation_type', flat=True)
                                                   ) \
                                            .select_related('object_entity')

                if relations:
                    object_entities = [r.object_entity for r in relations]
                    now = datetime.now()

                    CremeEntity.populate_real_entities(object_entities) #optimisation

                    for entity in object_entities:
                        create_line(entity.get_real_entity(), HistoryLine.TYPE_RELATED, date=now, related_line_id=hline.id)

    @staticmethod
    def _log_deletion(sender, instance, **kwargs):
        if isinstance(instance, CremeEntity) and instance.entity_type_id == _get_ct(instance).id: #TODO: factorise ??
            HistoryLine.objects.create(entity_ctype=instance.entity_type,
                                       entity_owner=instance.user,
                                       username=get_global_info('username') or '',
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


class HistoryConfigItem(Model):
    relation_type = ForeignKey(RelationType, unique=True)

    class Meta:
        app_label = 'creme_core'
