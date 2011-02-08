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

from logging import debug

from django.db.models import Q, CharField, ForeignKey, ManyToManyField, BooleanField
from django.db import transaction
from django.http import Http404
from django.utils.encoding import force_unicode, smart_str
from django.utils.html import escape
from django.utils.translation import ugettext_lazy as _, ugettext
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.models import User

from creme_property import CremePropertyType
from base import CremeModel, CremeAbstractEntity
from entity import CremeEntity


class RelationType(CremeModel):
    """
    If *_ctypes = null --> all contenttypes are valid.
    If *_properties = null --> all properties are valid.
    """
    id = CharField(primary_key=True, max_length=100)

    subject_ctypes     = ManyToManyField(ContentType,       blank=True, null=True, related_name='relationtype_subjects_set')
    object_ctypes      = ManyToManyField(ContentType,       blank=True, null=True, related_name='relationtype_objects_set')
    subject_properties = ManyToManyField(CremePropertyType, blank=True, null=True, related_name='relationtype_subjects_set')
    object_properties  = ManyToManyField(CremePropertyType, blank=True, null=True, related_name='relationtype_objects_set')

    is_internal = BooleanField(default=False) #still useful ????
    is_custom   = BooleanField(default=False)

    predicate      = CharField(_(u'Predicate'), max_length=100)
    symmetric_type = ForeignKey('self', blank=True, null=True)

    class Meta:
        app_label = 'creme_core'
        verbose_name = _(u'Type of relation')
        verbose_name_plural = _(u'Types of relation')

    def __unicode__(self):
        #from creme_core.i18n import translate_predicate
        sym_type = self.symmetric_type
        symmetric_pred = ugettext(u'No relation') if sym_type is None else sym_type.predicate

        return force_unicode(u'%s / %s' % (self.predicate, symmetric_pred))

    def delete(self):
        sym_type = self.symmetric_type

        RelationPredicate_i18n.objects.filter(relation_type__in=(self.pk, sym_type.pk)).delete()

        super(RelationType, sym_type).delete()
        super(RelationType, self).delete()

    def getCreateLang(self):
        #P = RelationPredicate_i18n.objects.get(predicate=self.predicate)
        #code = P.language_code
        ##print 'LANG CODE : ', code
        #return code
        return 'FRA'

    @staticmethod
    def get_compatible_ones(ct):
        return RelationType.objects.filter((Q(subject_ctypes=ct) | Q(subject_ctypes__isnull=True)) & Q(is_internal=False))

    @staticmethod
    @transaction.commit_manually
    def create(subject_desc, object_desc, is_custom=False, generate_pk=False, is_internal=False):
        """
        @param subject_desc Tuple (string_pk, predicate_string [, sequence_of_cremeEntityClasses [, sequence_of_propertyTypes]])
        @param object_desc See subject_desc
        @param generate_pk If True, 'string_pk' args are used as prefix to generate pks.
        """
        from creme_core.utils import create_or_update_models_instance as create

        padding       = ((), ()) #in case sequence_of_cremeEntityClasses or sequence_of_propertyType not given
        subject_desc += padding
        object_desc  += padding

        pk_subject   = subject_desc[0]
        pk_object    = object_desc[0]
        pred_subject = subject_desc[1]
        pred_object  = object_desc[1]

        if not generate_pk:
            sub_relation_type = create(RelationType, pk_subject, predicate=pred_subject, is_custom=is_custom, is_internal=is_internal)
            obj_relation_type = create(RelationType, pk_object,  predicate=pred_object,  is_custom=is_custom, is_internal=is_internal)
        else:
            from creme_core.utils.id_generator import generate_string_id_and_save

            sub_relation_type = RelationType(predicate=pred_subject, is_custom=is_custom, is_internal=is_internal)
            obj_relation_type = RelationType(predicate=pred_object,  is_custom=is_custom, is_internal=is_internal)

            generate_string_id_and_save(RelationType, [sub_relation_type], pk_subject)
            generate_string_id_and_save(RelationType, [obj_relation_type], pk_object)

        #TODO: i18n.....
        sub_relation_type.predicate_i18n_set.all().delete()
        obj_relation_type.predicate_i18n_set.all().delete()
        create(RelationPredicate_i18n, relation_type_id=pk_subject, language_code='FRA', text=pred_subject)
        create(RelationPredicate_i18n, relation_type_id=pk_subject, language_code='FRA', text=pred_subject)


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

    @staticmethod
    def _is_relation_type_internal(relation_type_id):
        try:
            rt = RelationType.objects.get(pk=relation_type_id)
        except RelationType.DoesNotExist:
            return False
        return rt.is_internal

    @staticmethod
    def _is_relation_type_internal_die(relation_type_id, err_msg=""):
        #TODO: Move from here ??
        if RelationType._is_relation_type_internal(relation_type_id):
            raise Http404(err_msg)


class RelationPredicate_i18n(CremeModel):
    relation_type = ForeignKey(RelationType, related_name='predicate_i18n_set')
    language_code = CharField(max_length=5)
    text          = CharField(max_length=100)

    class Meta:
        app_label = 'creme_core'


class Relation(CremeAbstractEntity):
    type               = ForeignKey(RelationType, blank=True, null=True)
    symmetric_relation = ForeignKey('self', blank=True, null=True)
    subject_entity     = ForeignKey(CremeEntity, related_name='relations')
    object_entity      = ForeignKey(CremeEntity, related_name='relations_where_is_object')

    class Meta:
        app_label = 'creme_core'
        verbose_name = _(u'Relation')
        verbose_name_plural = _(u'Relations')

    def __unicode__(self):
        subject = self.subject_entity
        object_ = self.object_entity
        str_ = u'<a href="%s">%s</a> -- %s --> <a href="%s">%s</a>' % (
                                subject.get_absolute_url(), escape(subject),
                                escape(self.type),
                                object_.get_absolute_url(), escape(object_)
                            )

        return force_unicode(smart_str(str_)) #hum....

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
        except Exception, e:
            debug('Error in creme_core.Relation.save(): %s', e)
            transaction.rollback()
        else:
            transaction.commit()

    def _collect_sub_objects(self, seen_objs, parent=None, nullable=False):
        pk_val = self._get_pk_val()

        if self.symmetric_relation is not None:
            seen_objs.add(self.symmetric_relation.__class__, self.symmetric_relation._get_pk_val(), self.symmetric_relation, parent, nullable)

        seen_objs.add(self.__class__, pk_val, self, parent, nullable)

    def delete(self):
        sym_relation = self.symmetric_relation

        if sym_relation is not None:
            sym_relation = sym_relation.get_real_entity()
            sym_relation.symmetric_relation = None
            sym_relation.delete()

        super(Relation, self).delete()

    def get_real_entity(self):
        return self._get_real_entity(Relation)

    @staticmethod
    def populate_real_object_entities(relations):
        """Faster than call get_real_entity() on each relation.object_entity.
        @param relations Iterable of Relation objects.
        tips: better if object_entity attribute is already populated
        -> (eg: use select_related('object_entity') on the queryset)
        """
        CremeAbstractEntity.populate_real_entities([relation.object_entity for relation in relations])

    @staticmethod
    def filter_in(model, filter_predicate, value_for_filter):
        return Q(relations__type=filter_predicate, relations__object_entity__header_filter_search_field__icontains=value_for_filter)

#        list_rel_pk = Relation.objects.filter(type=filter_predicate).values_list('object_entity', flat=True)
#        list_entity = CremeEntity.objects.filter(pk__in=list_rel_pk,
#                                                 header_filter_search_field__icontains=value_for_filter)
#        list_pk_f = model.objects.filter(relations__type=filter_predicate,
#                                             relations__object_entity__in=list_entity).values_list('id', flat=True)
#        return Q(id__in=list_pk_f)

    @staticmethod
    def create(subject, relation_type_id, object_, user_id=1): #really useful ??? (only 'user' attr help)
        relation = Relation()
        relation.subject_entity = subject
        relation.type_id = relation_type_id
        relation.object_entity = object_
        relation.user_id = user_id
        relation.save()

    def update_links(self, subject_entity=None, object_entity=None, save=False):
        """Beware: use this method if you have to update the related entities of a relation.
        @param subject_entity Give the param if you want to update the value of the relation's subject.
        @param object_entity Give the param if you want to update the value of the relation's object.
        @param save Save the relation if needed. Default to False.
        """
        changed = False

        if subject_entity is not None:
            if self.subject_entity_id != subject_entity.id:
                self.subject_entity = subject_entity
                self.symmetric_relation.object_entity = subject_entity
                changed = True

        if object_entity is not None:
            if self.object_entity_id != object_entity.id:
                self.object_entity = object_entity
                self.symmetric_relation.subject_entity = object_entity
                changed = True

        if save and changed:
            self.save()
