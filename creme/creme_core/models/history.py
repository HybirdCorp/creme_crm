# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2013  Hybird
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

#from datetime import datetime
from decimal import Decimal
from functools import partial
import logging

from django.db.models import (Model, PositiveSmallIntegerField, CharField, TextField,
                              ForeignKey, SET_NULL, FieldDoesNotExist) #DateTimeField
from django.db.models.signals import post_save, post_init, pre_delete
from django.dispatch import receiver
from django.utils.translation import ugettext_lazy as _, ugettext
from django.utils.simplejson import loads as jsonloads, JSONEncoder
from django.contrib.contenttypes.models import ContentType

from ..global_info import get_global_info, set_global_info
from .entity import CremeEntity
from .relation import RelationType, Relation
from .creme_property import CremePropertyType, CremeProperty
from .fields import CreationDateTimeField, CremeUserForeignKey, CTypeForeignKey


logger = logging.getLogger(__name__)
_get_ct = ContentType.objects.get_for_model
_EXCLUDED_FIELDS = ('modified',) #frozenset(('modified',)) #TODO: add a 'historisable' tag instead ??
_SERIALISABLE_FIELDS = frozenset(('CharField',

                                  'IntegerField', 'BigIntegerField', 'PositiveIntegerField',
                                  'PositiveSmallIntegerField', 'SmallIntegerField',

                                  'BooleanField', 'NullBooleanField',

                                  'DecimalField',

                                  'ForeignKey',

    #Display has to be improved (and value has to be 'jsonified')
        #'DateField'
        #'DateTimeField'
        #'TimeField'

    #To be tested
        #'FloatField'
        #'IPAddressField'
        #'SlugField'

    #Excluded
        #'FilePathField' => not useful
        #'TextField' => too long
        #'FileField' => not serialisable
                                ))


#TODO: in creme_core.utils ??
class _JSONEncoder(JSONEncoder):
    def default(self, o): #TODO: manage datetime here
        if isinstance(o, Decimal):
            return unicode(o)

        return JSONEncoder.default(self, o)


#TODO: factorise with gui.field_printers ?? (html and text mode ??)
_basic_printer = lambda field, val: val

def _fk_printer(field, val):
    if val is None:
        return ''

    model = field.rel.to

    if issubclass(model, CremeEntity):
        return ugettext(u'Entity #%s') % val

    try:
        out = model.objects.get(pk=val)
    except model.DoesNotExist as e:
        logger.info(str(e))
        out = val

    return unicode(out)

_PRINTERS = {
        'BooleanField': (lambda field, val: ugettext(u'True') if val else ugettext(u'False')),
        'ForeignKey':   _fk_printer,
    }


class _HistoryLineTypeRegistry(object):
    __slots__ = ('_hltypes', )

    def __init__(self):
        self._hltypes = {}

    def __call__(self, type_id):
        assert type_id not in self._hltypes, 'ID collision'

        def _aux(cls):
            self._hltypes[type_id] = cls
            cls.type_id = type_id
            return cls

        return _aux

    def __getitem__(self, i):
        return self._hltypes[i]


TYPES_MAP = _HistoryLineTypeRegistry()

TYPE_CREATION     = 1
TYPE_EDITION      = 2
TYPE_DELETION     = 3
TYPE_RELATED      = 4
TYPE_PROP_ADD     = 5
TYPE_RELATION     = 6
TYPE_SYM_RELATION = 7
TYPE_RELATION_DEL = 8
TYPE_SYM_REL_DEL  = 9
TYPE_AUX_CREATION = 10
TYPE_AUX_EDITION  = 11
TYPE_AUX_DELETION = 12
TYPE_PROP_DEL     = 13


class _HistoryLineType(object):
    type_id           = None #overload with TYPE_*
    verbose_name      = u'OVERLOAD ME'
    has_related_line  = False
    is_about_relation = False

    @classmethod
    def _build_fields_modifs(cls, instance):
        modifs = []
        backup = getattr(instance, '_instance_backup', None)

        if backup is not None:
            old_instance = instance.__class__()
            old_instance.__dict__ = backup
            excluded_fields = _EXCLUDED_FIELDS if isinstance(instance, CremeEntity) else ()

            for field in instance._meta.fields:
                fname = field.name

                if fname in excluded_fields or not field.get_tag('viewable'):
                    continue

                old_value = getattr(old_instance, fname)
                new_value = getattr(instance, fname)

                if isinstance(field, ForeignKey):
                    old_value = old_value and old_value.pk
                    new_value = new_value and new_value.pk

                if old_value != new_value:
                    if not new_value and not old_value: #ignore useless changes like : None -> ""
                        continue

                    if field.get_internal_type() not in _SERIALISABLE_FIELDS:
                        modif = (fname,)
                    elif old_value:
                        modif = (fname, old_value, new_value)
                    else:
                        modif = (fname, new_value)

                    modifs.append(modif)

        return modifs

    @staticmethod
    def _create_entity_backup(entity):
        entity._instance_backup = entity.__dict__.copy()

    def _get_printer(self, field):
        return _PRINTERS.get(field.get_internal_type(), _basic_printer)

    def _verbose_modifications_4_fields(self, model_class, modifications):
        get_field = model_class._meta.get_field

        for modif in modifications:
            field_name = modif[0]
            try:
                field = get_field(field_name)
            except FieldDoesNotExist:
                vmodif = ugettext(u'Set field “%(field)s”') % {'field': field_name}
            else:
                field_vname = field.verbose_name
                lenght = len(modif)

                if lenght == 1:
                    vmodif = ugettext(u'Set field “%(field)s”') % {'field': field_vname}
                elif lenght == 2:
                    vmodif = ugettext(u'Set field “%(field)s” to “%(value)s”') % {
                                        'field': field_vname,
                                        'value': self._get_printer(field)(field, modif[1]),
                                       }
                else: #lenght == 3
                    printer = self._get_printer(field)
                    vmodif = ugettext(u'Set field “%(field)s” from “%(oldvalue)s” to “%(value)s”') % {
                                            'field':    field_vname,
                                            'oldvalue': printer(field, modif[1]), #TODO: improve for fk ???
                                            'value':    printer(field, modif[2]),
                                        }

            yield vmodif

    def verbose_modifications(self, modifications, entity_ctype):
        for m in self._verbose_modifications_4_fields(entity_ctype.model_class(),
                                                      modifications
                                                     ):
            yield m

@TYPES_MAP(TYPE_CREATION)
class _HLTEntityCreation(_HistoryLineType):
    verbose_name = _(u'Creation')

    @classmethod
    def create_line(cls, entity):
        HistoryLine._create_line_4_instance(entity, cls.type_id, date=entity.created)
        #we do not backup here, in order to keep a kind of 'creation session'.
        # So when you create a CremeEntity, while you still use the same
        # python object, multiple save() will not generate several
        # HistoryLine objects.


@TYPES_MAP(TYPE_EDITION)
class _HLTEntityEdition(_HistoryLineType):
    verbose_name = _(u'Edition')

    @classmethod
    def create_lines(cls, entity):
        modifs = _HistoryLineType._build_fields_modifs(entity)

        if modifs:
            hline = HistoryLine._create_line_4_instance(entity, cls.type_id,
                                                        date=entity.modified,
                                                        modifs=modifs,
                                                       )
            _HLTRelatedEntity.create_lines(entity, hline)
            cls._create_entity_backup(entity)


@TYPES_MAP(TYPE_DELETION)
class _HLTEntityDeletion(_HistoryLineType):
    verbose_name = _(u'Deletion')

    @classmethod
    def create_line(cls, entity):
        HistoryLine.objects.create(entity_ctype=entity.entity_type,
                                   entity_owner=entity.user,
                                   type=cls.type_id,
                                   value=HistoryLine._encode_attrs(entity),
                                  )


@TYPES_MAP(TYPE_RELATED)
class _HLTRelatedEntity(_HistoryLineType):
    verbose_name     = _(u'Related modification')
    has_related_line = True

    @classmethod
    def create_lines(cls, entity, related_line):
        items = HistoryConfigItem.objects.values_list('relation_type', flat=True) #TODO: cache ??
        relations = Relation.objects.filter(subject_entity=entity.id, type__in=items) \
                                    .select_related('object_entity')

        if relations:
            object_entities = [r.object_entity for r in relations]
            create_line = partial(HistoryLine._create_line_4_instance,
                                  ltype=cls.type_id, date=entity.modified,
                                  related_line_id=related_line.id,
                                 )

            CremeEntity.populate_real_entities(object_entities) #optimisation

            for related_entity in object_entities:
                create_line(related_entity.get_real_entity())


@TYPES_MAP(TYPE_PROP_ADD)
class _HLTPropertyCreation(_HistoryLineType):
    verbose_name = _(u'Property creation')
    _fmt = _(u'Add property “%s”')

    @classmethod
    def create_line(cls, prop):
        HistoryLine._create_line_4_instance(prop.creme_entity, cls.type_id,
                                            modifs=[prop.type_id]
                                           )

    def verbose_modifications(self, modifications, entity_ctype):
        ptype_id = modifications[0]

        try:
            ptype_text = CremePropertyType.objects.get(pk=ptype_id).text #TODO: use cache ?
        except CremePropertyType.DoesNotExist:
            ptype_text = ptype_id

        yield self._fmt % ptype_text


@TYPES_MAP(TYPE_PROP_DEL)
class _HLTPropertyDeletion(_HLTPropertyCreation):
    verbose_name = _(u'Property deletion')
    _fmt = _(u'Delete property “%s”')

    @classmethod
    def create_line(cls, prop):
        HistoryLine._create_line_4_instance(prop.creme_entity, cls.type_id,
                                            modifs=[prop.type_id],
                                           )


@TYPES_MAP(TYPE_RELATION)
class _HLTRelation(_HistoryLineType):
    verbose_name      = _(u'Relationship')
    has_related_line  = True
    is_about_relation = True
    _fmt = _(u'Add a relationship “%s”')

    @classmethod
    def _create_lines(cls, relation, sym_cls, date=None):
        create_line = partial(HistoryLine._create_line_4_instance, date=date)
        hline     = create_line(relation.subject_entity, cls.type_id)
        hline_sym = create_line(relation.object_entity, sym_cls.type_id,
                                modifs=[relation.type.symmetric_type_id],
                                related_line_id=hline.id,
                               )
        hline.value = HistoryLine._encode_attrs(hline.entity, modifs=[relation.type_id],
                                                related_line_id=hline_sym.id
                                               )
        hline.save()

    @classmethod
    def create_lines(cls, relation, created):
        if '-subject_' in relation.type_id and not created:
            cls._create_lines(relation, _HLTSymRelation, relation.modified)

    def verbose_modifications(self, modifications, entity_ctype):
        rtype_id = modifications[0]

        try:
            predicate = RelationType.objects.get(pk=rtype_id).predicate #TODO: use cache ?
        except RelationType.DoesNotExist:
            predicate = rtype_id

        yield self._fmt % predicate


@TYPES_MAP(TYPE_SYM_RELATION)
class _HLTSymRelation(_HLTRelation):
    pass


@TYPES_MAP(TYPE_RELATION_DEL)
class _HLTRelationDeletion(_HLTRelation):
    verbose_name = _(u'Relationship deletion')
    _fmt = _(u'Delete a relationship “%s”')

    @classmethod
    def create_lines(cls, relation):
        if '-subject_' in relation.type_id:
            cls._create_lines(relation, _HLTSymRelationDeletion)


@TYPES_MAP(TYPE_SYM_REL_DEL)
class _HLTSymRelationDeletion(_HLTRelationDeletion):
    pass


@TYPES_MAP(TYPE_AUX_CREATION)
class _HLTAuxCreation(_HistoryLineType):
    verbose_name = _(u'Auxiliary (creation)')

    @staticmethod
    def _model_info(ct_id):
        model_class = ContentType.objects.get_for_id(ct_id).model_class()
        return model_class, model_class._meta.verbose_name

    @staticmethod
    def _build_modifs(related):
        return [_get_ct(related).id, related.pk, unicode(related)]

    @classmethod
    def create_line(cls, related):
        HistoryLine._create_line_4_instance(related.get_related_entity(),
                                            cls.type_id,
                                            modifs=cls._build_modifs(related),
                                           )

    def verbose_modifications(self, modifications, entity_ctype):
        ct_id, aux_id, str_obj = modifications #TODO; use aux_id to display an up-to-date value ??

        yield ugettext(u'Add <%(type)s>: “%(value)s”') % {
                        'type':  self._model_info(ct_id)[1],
                        'value': str_obj,
                    }


@TYPES_MAP(TYPE_AUX_EDITION)
class _HLTAuxEdition(_HLTAuxCreation):
    verbose_name = _(u'Auxiliary (edition)')

    @classmethod
    def create_line(cls, related):
        #TODO: factorise better ?
        #fields_modifs = _HistoryLineType._build_fields_modifs(related)
        fields_modifs = cls._build_fields_modifs(related)

        if fields_modifs:
            HistoryLine._create_line_4_instance(
                    related.get_related_entity(),
                    cls.type_id,
                    modifs=[cls._build_modifs(related)] + fields_modifs,
                )

    def verbose_modifications(self, modifications, entity_ctype):
        ct_id, aux_id, str_obj = modifications[0] #TODO; idem (see _HLTAuxCreation)
        model_class, verbose_name = self._model_info(ct_id)

        yield ugettext(u'Edit <%(type)s>: “%(value)s”') % {
                        'type':  verbose_name,
                        'value': str_obj,
                    }

        for m in self._verbose_modifications_4_fields(model_class, modifications[1:]):
            yield m


@TYPES_MAP(TYPE_AUX_DELETION)
class _HLTAuxDeletion(_HLTAuxCreation):
    verbose_name = _(u'Auxiliary (deletion)')

    @staticmethod
    def _build_modifs(related):
        return [_get_ct(related).id, unicode(related)]

    def verbose_modifications(self, modifications, entity_ctype):
        ct_id, str_obj = modifications

        yield ugettext(u'Delete <%(type)s>: “%(value)s”') % {
                        'type':  self._model_info(ct_id)[1],
                        'value': str_obj,
                    }


#TODO: manage the related objects edition (Alerts, Lines...)
class HistoryLine(Model):
    entity       = ForeignKey(CremeEntity, null=True, on_delete=SET_NULL)
    #entity_ctype = ForeignKey(ContentType)  #we do not use entity.entity_type because we keep history of the deleted entities
    entity_ctype = CTypeForeignKey()  #we do not use entity.entity_type because we keep history of the deleted entities
    entity_owner = CremeUserForeignKey()    #we do not use entity.user because we keep history of the deleted entities
    username     = CharField(max_length=30) #not a Fk to a User object because we want to keep the same line after the deletion of a User.
    #date         = DateTimeField()
    date         = CreationDateTimeField()
    type         = PositiveSmallIntegerField() #see TYPE_*
    value        = TextField(null=True) #TODO: use a JSONField ? (see EntityFilter)

    _line_type = None
    _entity_repr = None
    _modifications = None
    _related_line_id = None
    _related_line = False

    class Meta:
        app_label = 'creme_core'

    def __repr__(self):
        return 'HistoryLine(entity_id=%s, entity_owner_id=%s, date=%s, type=%s, value=%s)' % (
                    self.entity_id, self.entity_owner_id, self.date, self.type, self.value
                )

    @staticmethod
    def disable(instance):
        instance._hline_disabled = True

    @staticmethod
    def _encode_attrs(instance, modifs=(), related_line_id=None):
        value = [unicode(instance)]
        if related_line_id:
            value.append(related_line_id)

        encode = _JSONEncoder().encode

        try:
            attrs = encode(value + list(modifs))
        except TypeError as e:
            logger.warn('HistoryLine: %s', e)
            attrs = encode(value)

        return attrs

    def _read_attrs(self):
        value = jsonloads(self.value)
        self._entity_repr = value.pop(0)
        self._related_line_id = value.pop(0) if self.line_type.has_related_line else 0
        self._modifications = value

    @property
    def entity_repr(self):
        if self._entity_repr is None:
            self._read_attrs()

        return self._entity_repr

    def get_type_str(self):
        return self.line_type.verbose_name

    @property
    def line_type(self):
        _line_type = self._line_type

        if _line_type is None:
            self._line_type = _line_type = TYPES_MAP[self.type]()

        return _line_type

    @property
    def modifications(self):
        if self._modifications is None:
            self._read_attrs()

        return self._modifications

    @property
    def verbose_modifications(self):
        try:
            return list(self.line_type.verbose_modifications(self.modifications,
                                                             self.entity_ctype,
                                                            )
                       )
        except Exception:
            logger.exception('Error in %s', self.__class__.__name__)
            return ['??']

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
        """Builder.
        @param ltype See TYPE_*
        @param date If not given, will be 'now'.
        @param modifs List of tuples containing JSONifiable values.
        @param related_line_id HistoryLine.id
        """
        kwargs = {'entity': instance,
                  'entity_ctype': instance.entity_type,
                  'entity_owner': instance.user,
                  'type': ltype,
                  'value': HistoryLine._encode_attrs(instance, modifs=modifs,
                                                     related_line_id=related_line_id,
                                                    ),
                 }
        if date: kwargs['date'] = date

        return HistoryLine.objects.create(**kwargs)

    def save(self, *args, **kwargs):
        self.username = get_global_info('username') or ''
        super(HistoryLine, self).save(*args, **kwargs)


#TODO: method of CremeEntity ??
def _final_entity(entity):
    "Is the instance an instance of a 'leaf' class"
    return entity.entity_type_id == _get_ct(entity).id

@receiver(post_init)
def _prepare_log(sender, instance, **kwargs):
    if hasattr(instance, 'get_related_entity'):
        _HistoryLineType._create_entity_backup(instance)
    elif isinstance(instance, CremeEntity) and instance.id and _final_entity(instance):
        _HistoryLineType._create_entity_backup(instance)
    #TODO: replace with this code
    #      problem with billing lines : the update view does not retrieve
    #      final class, so 'instance.entity_type_id == _get_ct(instance).id'
    #      test avoid the creation of a line --> find a better way to test if a final object is alive ?
    #if isinstance(instance, CremeEntity):
        #if not instance.id or instance.entity_type_id != _get_ct(instance).id:
            #return
    #elif not hasattr(instance, 'get_related_entity'):
        #return

    #_HistoryLineType._create_entity_backup(instance)

@receiver(post_save)
def _log_creation_edition(sender, instance, created, **kwargs):
    #TODO ?
    #if getattr(instance, '_hline_disabled', False): #see HistoryLine.disable
        #return

    try:
        if isinstance(instance, CremeProperty):
            _HLTPropertyCreation.create_line(instance)
        elif isinstance(instance, Relation):
            _HLTRelation.create_lines(instance, created)
        elif hasattr(instance, 'get_related_entity'):
            if created:
                _HLTAuxCreation.create_line(instance)
            else:
                _HLTAuxEdition.create_line(instance)
        elif isinstance(instance, CremeEntity):
            if created:
                _HLTEntityCreation.create_line(instance)
            else:
                _HLTEntityEdition.create_lines(instance)
    except Exception:
        logger.exception('Error in _log_creation_edition() ; HistoryLine may not be created.')

def _get_deleted_entity_ids():
    del_ids = get_global_info('deleted_entity_ids')

    if del_ids is None:
        del_ids = set()
        set_global_info(deleted_entity_ids=del_ids)

    return del_ids

@receiver(pre_delete)
def _log_deletion(sender, instance, **kwargs):
    if getattr(instance, '_hline_disabled', False): #see HistoryLine.disable
        return

    # when we are dealing whith CremeEntities, we check that we are dealing
    # with the final class, because the signal is send several times, with
    # several 'level' of class. We don't want to create several HistoryLines
    # (and some things are deleted by higher levels that make objects
    # inconsistant & that can cause 'crashes').
    try:
        if isinstance(instance, CremeProperty):
            _HLTPropertyDeletion.create_line(instance)
        elif isinstance(instance, Relation):
            _HLTRelationDeletion.create_lines(instance)
        elif hasattr(instance, 'get_related_entity'):
            if not isinstance(instance, CremeEntity) or _final_entity(instance):
                entity = instance.get_related_entity()

                if entity is None:
                    logger.debug('_log_deletion(): an auxiliary entity seems orphan (id=%s)'
                                 ' -> can not create HistoryLine',
                                 instance.id,
                                )
                elif entity.id not in _get_deleted_entity_ids():
                    _HLTAuxDeletion.create_line(instance)
        elif isinstance(instance, CremeEntity) and _final_entity(instance):
            _get_deleted_entity_ids().add(instance.id)
            _HLTEntityDeletion.create_line(instance)
    except Exception:
        logger.exception('Error in _log_deletion() ; HistoryLine may not be created.')


class HistoryConfigItem(Model):
    relation_type = ForeignKey(RelationType, unique=True)

    class Meta:
        app_label = 'creme_core'
