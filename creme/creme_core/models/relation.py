# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2014  Hybird
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

from collections import defaultdict
import logging
#import warnings

from django.db.models import Q, CharField, ForeignKey, ManyToManyField, BooleanField, PROTECT
from django.db import transaction
from django.dispatch import receiver
from django.http import Http404
#from django.utils.encoding import force_unicode, smart_str
#from django.utils.html import escape
from django.utils.translation import ugettext_lazy as _, ugettext
from django.contrib.contenttypes.models import ContentType

from ..signals import pre_merge_related
from .base import CremeModel, CremeAbstractEntity
from .entity import CremeEntity
from .creme_property import CremePropertyType


logger = logging.getLogger(__name__)


class RelationType(CremeModel):
    """
    If *_ctypes = null --> all ContentTypes are valid.
    If *_properties = null --> all CremeProperties are valid.
    """
    id = CharField(primary_key=True, max_length=100) #NB: convention: 'app_name-foobar'
                                                     #BEWARE: 'id' MUST only contain alphanumeric '-' and '_'

    subject_ctypes     = ManyToManyField(ContentType,       blank=True, null=True, related_name='relationtype_subjects_set')
    object_ctypes      = ManyToManyField(ContentType,       blank=True, null=True, related_name='relationtype_objects_set')
    subject_properties = ManyToManyField(CremePropertyType, blank=True, null=True, related_name='relationtype_subjects_set')
    object_properties  = ManyToManyField(CremePropertyType, blank=True, null=True, related_name='relationtype_objects_set')

    is_internal = BooleanField(default=False) # if True, the relations with this type can not be created/deleted directly by the users.
    is_custom   = BooleanField(default=False) # if True, the RelationType can ot be deleted (in creme_config).
    is_copiable = BooleanField(default=True)  # if True, the relations with this type can be copied (ie when cloning or converting an entity)

    predicate      = CharField(_(u'Predicate'), max_length=100)
    symmetric_type = ForeignKey('self', blank=True, null=True)

    class Meta:
        app_label = 'creme_core'
        verbose_name = _(u'Type of relationship')
        verbose_name_plural = _(u'Types of relationship')

    def __unicode__(self):
        sym_type = self.symmetric_type
        symmetric_pred = ugettext(u'No relationship') if sym_type is None else sym_type.predicate
        #return force_unicode(u'%s — %s' % (self.predicate, symmetric_pred))#NB: — == "\xE2\x80\x94" == &mdash;
        return u'%s — %s' % (self.predicate, symmetric_pred) #NB: — == "\xE2\x80\x94" == &mdash;

    def add_subject_ctypes(self, *models):
        get_ct = ContentType.objects.get_for_model
        cts = [get_ct(model) for model in models]
        self.subject_ctypes.add(*cts)
        self.symmetric_type.object_ctypes.add(*cts)

    def delete(self):
        sym_type = self.symmetric_type

        super(RelationType, sym_type).delete()
        super(RelationType, self).delete()

    @staticmethod
    def get_compatible_ones(ct, include_internals=False):
        types = RelationType.objects.filter(Q(subject_ctypes=ct) | Q(subject_ctypes__isnull=True))
        if not include_internals:
            types = types.filter(Q(is_internal=False))
        return types

    @staticmethod
    @transaction.commit_manually
    def create(subject_desc, object_desc, is_custom=False, generate_pk=False, is_internal=False, is_copiable=(True, True)):
        """
        @param subject_desc Tuple (string_pk, predicate_string [, sequence_of_cremeEntityClasses [, sequence_of_propertyTypes]])
        @param object_desc See subject_desc
        @param generate_pk If True, 'string_pk' args are used as prefix to generate pks.
        """
        from creme.creme_core.utils import create_or_update

        padding       = ((), ()) #in case sequence_of_cremeEntityClasses or sequence_of_propertyType not given
        subject_desc += padding
        object_desc  += padding

        if isinstance(is_copiable, bool):
            is_copiable = (is_copiable, is_copiable)

        pk_subject   = subject_desc[0]
        pk_object    = object_desc[0]
        pred_subject = subject_desc[1]
        pred_object  = object_desc[1]

        if not generate_pk:
            sub_relation_type = create_or_update(RelationType, pk_subject, predicate=pred_subject, is_custom=is_custom,
                                                                           is_internal=is_internal, is_copiable=is_copiable[0])
            obj_relation_type = create_or_update(RelationType, pk_object,  predicate=pred_object,  is_custom=is_custom,
                                                                           is_internal=is_internal, is_copiable=is_copiable[1])
        else:
            from creme.creme_core.utils.id_generator import generate_string_id_and_save

            sub_relation_type = RelationType(predicate=pred_subject, is_custom=is_custom,
                                             is_internal=is_internal, is_copiable=is_copiable[0])
            obj_relation_type = RelationType(predicate=pred_object,  is_custom=is_custom,
                                             is_internal=is_internal, is_copiable=is_copiable[1])

            generate_string_id_and_save(RelationType, [sub_relation_type], pk_subject)
            generate_string_id_and_save(RelationType, [obj_relation_type], pk_object)

        sub_relation_type.symmetric_type = obj_relation_type
        obj_relation_type.symmetric_type = sub_relation_type

        #Delete old m2m (TODO: just remove useless ones ???)
        for rt in (sub_relation_type, obj_relation_type):
            rt.subject_ctypes.clear()
            rt.subject_properties.clear()
            rt.object_ctypes.clear()
            rt.object_properties.clear()

        get_ct = ContentType.objects.get_for_model

        for subject_ctype in subject_desc[2]:
            ct = get_ct(subject_ctype)
            sub_relation_type.subject_ctypes.add(ct)
            obj_relation_type.object_ctypes.add(ct)

        for object_ctype in object_desc[2]:
            ct = get_ct(object_ctype)
            sub_relation_type.object_ctypes.add(ct)
            obj_relation_type.subject_ctypes.add(ct)

        for subject_prop in subject_desc[3]:
            sub_relation_type.subject_properties.add(subject_prop)
            obj_relation_type.object_properties.add(subject_prop)

        for object_prop in object_desc[3]:
            sub_relation_type.object_properties.add(object_prop)
            obj_relation_type.subject_properties.add(object_prop)

        sub_relation_type.save()
        obj_relation_type.save()

        transaction.commit()

        return (sub_relation_type, obj_relation_type)

    def is_compatible(self, ctype_id):
        #TODO: check if self.subject_ctypes.all() is already retrieved (prefetch_related)?
        subject_ctypes = frozenset(self.subject_ctypes.values_list('id', flat=True))

        return not subject_ctypes or ctype_id in subject_ctypes

    def is_not_internal_or_die(self):
        if self.is_internal:
            raise Http404(ugettext("You can't add/delete the relationships with this type (internal type)"))


#TODO: remove CremeAbstractEntity inheritage (user/modified not useful any more ??) ??
class Relation(CremeAbstractEntity):
    type               = ForeignKey(RelationType, blank=True, null=True)
    symmetric_relation = ForeignKey('self', blank=True, null=True)
    subject_entity     = ForeignKey(CremeEntity, related_name='relations', on_delete=PROTECT)
    object_entity      = ForeignKey(CremeEntity, related_name='relations_where_is_object', on_delete=PROTECT)

    class Meta:
        app_label = 'creme_core'
        verbose_name = _(u'Relationship')
        verbose_name_plural = _(u'Relationships')

    def __unicode__(self):
        #TODO: as_a() method ?? (mark_safe)
        #subject = self.subject_entity
        #object_ = self.object_entity
        #str_ = u'<a href="%s">%s</a> -- %s --> <a href="%s">%s</a>' % (
                                #subject.get_absolute_url(), escape(subject),
                                #escape(self.type),
                                #object_.get_absolute_url(), escape(object_)
                            #)

        #return force_unicode(smart_str(str_)) #hum....
        return u'«%s» %s «%s»' % (self.subject_entity, self.type, self.object_entity)

    def _build_symmetric_relation(self, update):
        """Overload me in child classes.
        @param update Boolean: True->updating object ; False->creating object.
        """
        if update:
            sym_relation = self.symmetric_relation
            assert sym_relation
        else:
            sym_relation = Relation(user=self.user,
                                    type=self.type.symmetric_type,
                                    symmetric_relation=self,
                                    subject_entity=self.object_entity,
                                    object_entity=self.subject_entity,
                                   )

        return sym_relation

    @transaction.commit_manually
    def save(self, using='default', force_insert=False):
        try:
            update = bool(self.pk)

            super(Relation, self).save(using=using, force_insert=force_insert)

            sym_relation = self._build_symmetric_relation(update)
            super(Relation, sym_relation).save(using=using, force_insert=force_insert)

            if self.symmetric_relation is None:
                self.symmetric_relation = sym_relation
                super(Relation, self).save(using=using, force_insert=False)
        except Exception:
            logger.exception('Error in creme_core.Relation.save()')
            transaction.rollback()
        else:
            transaction.commit()

    def _collect_sub_objects(self, seen_objs, parent=None, nullable=False):
        pk_val = self._get_pk_val()

        if self.symmetric_relation is not None:
            seen_objs.add(self.symmetric_relation.__class__, self.symmetric_relation._get_pk_val(), self.symmetric_relation, parent, nullable)

        seen_objs.add(self.__class__, pk_val, self, parent, nullable)

#Commented 31/05/2011
#    def delete(self):
#        sym_relation = self.symmetric_relation
#
#        if sym_relation is not None:
#            sym_relation = sym_relation.get_real_entity()
#            sym_relation.symmetric_relation = None
#            sym_relation.delete()
#
#        super(Relation, self).delete()

    def get_real_entity(self):
        return self._get_real_entity(Relation)

    @staticmethod
    def populate_real_object_entities(relations, user=None): #TODO: user is useless
        """Faster than call get_real_entity() on each relation.object_entity.
        @param relations Iterable of Relation objects.
        @param user If given, real entities are populated with credentials related to this user.
        tips: better if object_entity attribute is already populated
        -> (eg: use select_related('object_entity') on the queryset)
        """
        CremeEntity.populate_real_entities([relation.object_entity for relation in relations])

    @staticmethod
    def filter_in(model, filter_predicate, value_for_filter):
        return Q(relations__type=filter_predicate, relations__object_entity__header_filter_search_field__icontains=value_for_filter)

    #def update_links(self, subject_entity=None, object_entity=None, save=False):
        #"""Deprecated
        #Beware: use this method if you have to update the related entities of a relation.
        #@param subject_entity Give the param if you want to update the value of the relation's subject.
        #@param object_entity Give the param if you want to update the value of the relation's object.
        #@param save Save the relation if needed. Default to False.
        #"""
        #warnings.warn("Relation.update_links() method is deprecated; "
                      #"delete your old Relation instace and create a new one instead",
                      #DeprecationWarning
                     #)

        #changed = False

        #if subject_entity is not None:
            #if self.subject_entity_id != subject_entity.id:
                #self.subject_entity = subject_entity
                #self.symmetric_relation.object_entity = subject_entity
                #changed = True

        #if object_entity is not None:
            #if self.object_entity_id != object_entity.id:
                #self.object_entity = object_entity
                #self.symmetric_relation.subject_entity = object_entity
                #changed = True

        #if save and changed:
            #self.save()


class SemiFixedRelationType(CremeModel):
    predicate     = CharField(_(u'Predicate'), max_length=100, unique=True)
    relation_type = ForeignKey(RelationType)
    object_entity = ForeignKey(CremeEntity)

    class Meta:
        app_label = 'creme_core'
        unique_together = ('relation_type', 'object_entity')
        verbose_name = _(u'Semi-fixed type of relationship')
        verbose_name_plural = _(u'Semi-fixed types of relationship')

    def __unicode__(self):
        return self.predicate


@receiver(pre_merge_related)
def _handle_merge(sender, other_entity, **kwargs):
    """Delete 'Duplicated' Relations (ie: exist in the removed entity & the
    remaining entity).
    """

    #sender_id = sender.id
    #rel_filter = sender.relations.filter

    #for relation in other_entity.relations.all():
        #if rel_filter(subject_entity=sender_id, type=relation.type_id,
                      #object_entity=relation.object_entity_id
                     #).exists():
            #relation.delete()
        ##else:
            ##relation.update_links(subject_entity=sender)

    from .history import HistoryLine

    # TRICK: We use the related accessor 'relations_where_is_object' instead
    # of 'relations' because HistoryLine creates lines for relation with
    # types '*-subject_*' (symmetric with types '*-object_*')
    # If we'd use 'sender.relations' we should disable/delete
    # 'relation.symmetric_relation' that would take an additional query.
    relations_info = defaultdict(list)
    for rtype_id, entity_id in sender.relations_where_is_object \
                                     .values_list('type', 'subject_entity'):
        relations_info[rtype_id].append(entity_id)

    rel_filter = other_entity.relations_where_is_object.filter
    for rtype_id, entity_ids in relations_info.iteritems():
        for relation in rel_filter(type=rtype_id, subject_entity__in=entity_ids):
            HistoryLine.disable(relation)
            relation.delete()
