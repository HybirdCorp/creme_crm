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

from django.db.models import Model, CharField, ForeignKey, ManyToManyField, BooleanField, PositiveIntegerField
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.generic import GenericForeignKey
from django.contrib.auth.models import User
from django.utils.encoding import force_unicode, smart_str
from django.utils.html import escape
from django.utils.translation import ugettext_lazy as _
from django.db.models import Q

from creme_property import CremePropertyType
from creme_model import CremeModel
from entity import CremeEntityWithoutRelation, CremeEntity


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

    can_be_create_with_popup = BooleanField(default=True)
    display_with_other       = BooleanField(default=True)
    is_custom                = BooleanField(default=False)

    predicate      = CharField(_(u'Prédicat'), max_length=100)
    symmetric_type = ForeignKey('self', blank=True, null=True)

    class Meta:
        app_label = 'creme_core'
        verbose_name = _(u'Type de relation')
        verbose_name_plural = _(u'Types de relation')

    def __unicode__(self):
        #from creme_core.i18n import translate_predicate
        sym_type = self.symmetric_type
        symmetric_pred = u'Pas de relation' if sym_type is None else sym_type.predicate

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
    def get_customs():
        return RelationType.objects.filter(is_custom=True)


class RelationPredicate_i18n(CremeModel):
    relation_type = ForeignKey(RelationType, related_name='predicate_i18n_set')
    language_code = CharField(max_length=5)
    text          = CharField(max_length=100)

    class Meta:
        app_label = 'creme_core'


class Relation(CremeEntityWithoutRelation):
    type               = ForeignKey(RelationType, blank=True, null=True)
    symmetric_relation = ForeignKey('self', blank=True, null=True)
    subject_entity     = ForeignKey(CremeEntity, related_name='relations')
    object_entity      = ForeignKey(CremeEntity, related_name='relations_where_is_object')

    _real_entity = None

    class Meta:
        app_label = 'creme_core'
        verbose_name = _(u'Relation')
        verbose_name_plural = _(u'Relations')

    #def __init__ (self , *args , **kwargs):
        #super(Relation, self).__init__(*args, **kwargs)
        ##self.build_custom_fields()

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

    def save(self):
        update = bool(self.pk)

        #self.save_custom_fields()

        super(Relation, self).save()

        if self.symmetric_relation is None:
            sym_relation = self._build_symmetric_relation(update)
            sym_relation.save()
            self.symmetric_relation = sym_relation
            super(Relation, self).save() #update() instead ??

    def delete(self):
        sym_relation = self.symmetric_relation

        if sym_relation is not None:
            sym_relation = sym_relation.get_real_entity()
            sym_relation.symmetric_relation = None
            sym_relation.delete()

        super(Relation, self).delete()

    def get_real_entity(self):
        entity = self._real_entity

        if entity is True:
            return self

        if entity is None:
            ct = self.entity_type

            if ct == ContentType.objects.get_for_model(Relation):
                self._real_entity = True #avoid reference to 'self' (cyclic reference)
                entity = self
            else:
                entity = self._real_entity = ct.get_object_for_this_type(id=self.id)

        return entity

    @staticmethod
    def filter_in(model, filter_predicate, value_for_filter):
        ct_model = ContentType.objects.get_for_model(model)

        #TODO: use values_list()
        #relations = Relation.objects.filter(type=filter_predicate, subject_content_type=ct_model)
        relations = Relation.objects.filter(type=filter_predicate, subject_entity__entity_type=ct_model)
        list_rel_pk = [r.object_entity_id for r in relations]

        from creme_core.models import CremeEntity
        #TODO: use values_list()
        #TODO: merge with previous query
        list_entity = CremeEntity.objects.filter(pk__in=list_rel_pk,
                                                 header_filter_search_field__icontains=value_for_filter)
        #list_entity_pk = [e.id for e in list_entity]

        #TODO: use values_list()
        #list_entities = model.objects.filter(new_relations__type=filter_predicate,
                                             #new_relations__object_id__in=list_entity_pk)
        list_entities = model.objects.filter(relations__type=filter_predicate,
                                             relations__object_entity__in=list_entity)

        list_pk_f = [entity.id for entity in list_entities]

        return Q(id__in=list_pk_f)

    @staticmethod
    def create_relation_with_object(subject, relation_type_id, object_): #really useful ??? (only 'user' attr help)
        relation = Relation()
        relation.subject_entity = subject
        relation.type_id = relation_type_id
        relation.object_entity = object_
        relation.user = User.objects.get(pk=1)
        relation.save()

#    def build_custom_fields (self):
#        pass

#        self._meta.custom_fields = {}
#        debug ( self)
#        debug ( self.predicate )
#
#        Q1 = Q (for_relation1=self.predicate )
#        Q2 = Q (for_relation2=self.predicate )
#        QTotal = Q1 | Q2
#        List_Custom_Fields =  RelationCustomFields.objects.filter ( QTotal  )
#        debug ( List_Custom_Fields)
#        for CF in List_Custom_Fields:
#            List_CFV =  RelationCustomFieldsValue.objects.filter(custom_field= CF , creme_relation = self)
#
#            if List_CFV.count() > 0:
#                self.__dict__[ str(CF.name) ] = List_CFV[0].value_field
#            else :
#                 self.__dict__[ str(CF.name) ] = CF.default_value
#            self._meta.custom_fields[ str(CF.name) ] = CharField(max_length=100, default = CF.default_value)

#    def save_custom_fields (self ):
#
#        List_Recherche = [self.predicate, self.relation_symetrique.predicate]
#        List_Recherche = [self.predicate ]
#        if not self.pk :
#            for key, value in self._meta.custom_fields.iteritems():
#                CFV =  RelationCustomFieldsValue ( custom_field= RelationCustomFields.objects.get ( name=key ,
#                                                                                                    for_relation__in = List_Recherche ) ,
#                                                   creme_relation=self ,
#                                                   value_field=self.__dict__[ key ] )
#                CFV.save ()
#        else :
#            for key, value in self._meta.custom_fields.iteritems():
#                current_custom_field= RelationCustomFields.objects.get ( name=key , for_relation__in = List_Recherche )
#                queryset_cfv =   RelationCustomFieldsValue.objects.filter(creme_relation=self , custom_field=current_custom_field  )
#                if  queryset_cfv.count () > 0 :
#                    CFV = queryset_cfv[0]
#                    CFV.value_field=self.__dict__[ key ]
#                    CFV.save ()
#                else :
#                    if value.default ==  self.__dict__[ key ]:
#                        pass
#                    else:
#                        CFV =  RelationCustomFieldsValue ( custom_field= RelationCustomFields.objects.get ( name=key , for_relation__in = List_Recherche ) ,
#                                                           creme_relation=self ,
#                                                           value_field=self.__dict__[ key ] )
#                        CFV.save ()
#
#
#


#class RelationCustomFields(Model):
#    name = CharField(max_length=100)
#    for_relation1 = ForeignKey(RelationType, related_name="customfiels_relation1_set")
#    for_relation2 = ForeignKey(RelationType, related_name="customfiels_relation2_set")
#    type_champ = CharField(max_length=100)
#    list_or_not = BooleanField()
#    default_value = CharField(max_length=100, blank=True, null=True)
#    extra_args = CharField(max_length=500, blank=True, null=True)
#
#    def __unicode__(self):
#        return self.name
#
#    class Meta:
#        app_label = 'creme_core'
#
#
#class ValueOfRelationCustomFieldsList (Model):
#    custom_field = ForeignKey(RelationCustomFields)
#    value_field = CharField(max_length=100)
#
#    class Meta:
#        app_label = 'creme_core'
#
#
#class RelationCustomFieldsValue(Model):
#    custom_field = ForeignKey(RelationCustomFields)
#    creme_relation = ForeignKey(Relation)
#    value_field = CharField(max_length=100)
#
#    def __unicode__(self):
#        return force_unicode(self.id)
#
#    class Meta:
#        app_label = 'creme_core'


def create_relation_type(subject_desc, object_desc, display_with_other=True, is_custom=False, generate_pk=False):
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
        sub_relation_type = create(RelationType, pk_subject, predicate=pred_subject, display_with_other=display_with_other, is_custom=is_custom)
        obj_relation_type = create(RelationType, pk_object,  predicate=pred_object,  display_with_other=display_with_other, is_custom=is_custom)
    else:
        from creme_core.utils.id_generator import generate_string_id_and_save

        sub_relation_type = RelationType(predicate=pred_subject, display_with_other=display_with_other, is_custom=is_custom)
        obj_relation_type = RelationType(predicate=pred_object,  display_with_other=display_with_other, is_custom=is_custom)

        generate_string_id_and_save(RelationType, [sub_relation_type], pk_subject)
        generate_string_id_and_save(RelationType, [obj_relation_type], pk_object)

    #TODO: i18n.....
    sub_relation_type.predicate_i18n_set.all().delete()
    obj_relation_type.predicate_i18n_set.all().delete()
    create(RelationPredicate_i18n, relation_type_id=pk_subject, language_code='FRA', text=pred_subject)
    create(RelationPredicate_i18n, relation_type_id=pk_subject, language_code='FRA', text=pred_subject)


    sub_relation_type.symmetric_type = obj_relation_type
    obj_relation_type.symmetric_type = sub_relation_type


    #Delete old m2m (TODO: just remove useless ???)
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

    return (sub_relation_type, obj_relation_type)
