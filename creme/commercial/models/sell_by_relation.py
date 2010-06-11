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

from django.db.models import Model, CharField, BooleanField, DateTimeField, PositiveIntegerField
from django.utils.encoding import force_unicode
from django.utils.translation import ugettext_lazy as _
from django.contrib.auth.models import User

from creme_core.models import RelationType, Relation

from commercial.constants import REL_SUB_SOLD_BY


class SellByRelation(Relation):
    """ relation 'a vendu / a été vendu par' entre un commercial et une fiche. 
    """
    commission_paye = BooleanField (blank=True, default=False)
    int_value =       PositiveIntegerField( default=0)
    char_value =      CharField(max_length=100, blank=True)
    date_paiement =   DateTimeField(_(u'Date de paiement'), blank=True, null=True,)

    class Meta:
        app_label = "commercial"

    def __unicode__(self):
        commission_is_paid = 'Oui' if self.commission_paye else 'Non'

        subject = self.subject_creme_entity
        object_ = self.object_creme_entity

        str_ = '<a href="%s">%s</a> -- %s  --> <a href="%s">%s</a> commission payée: %s' % (
                        subject.get_absolute_url(), subject,
                        self.type,
                        object_.get_absolute_url(), object_,
                        commission_is_paid
                    )
        return force_unicode(str_)

    def delete_relation(self):
        debug(' SellByRelation: delete_relation %s ', self.id)

        sym_relation = self.symmetric_relation
        sym_sellbyrelation = sym_relation.sellbyrelation if sym_relation is not None else None

        try :
            self.subject_creme_entity.new_relations.remove(self)
        except : 
            pass
        Model.delete(self) ##WTF ??!!!!!!

        debug(' SellByRelation , aprés model.delete %s ', sym_sellbyrelation)

        if sym_sellbyrelation is not None:
            debug(' SellByRelation , rel_symetrique toujours not none ')
            sym_sellbyrelation.symmetric_relation = None
            super(SellByRelation, sym_sellbyrelation).save()
            try :
                sym_sellbyrelation.subject_creme_entity.new_relations.remove(sym_relation)
            except Exception, e:
                debug('Exception in SellByRelation.delete_relation(): %s', e)
            sym_sellbyrelation.delete ()

    def delete (self):
        self.delete_relation()

    def save_only_info_sup (self ):
        super(SellByRelation, self).save()

    def save ( self):
        update = bool(self.pk)

        super(SellByRelation, self).save()

        sym_relation = self.symmetric_relation

        if sym_relation is not None:
            sellbyrelation = sym_relation.sellbyrelation
            sellbyrelation.commission_paye = self.commission_paye
            sellbyrelation.int_value       = self.int_value
            sellbyrelation.char_value      = self.char_value
            sellbyrelation.date_paiement   = self.date_paiement
            sellbyrelation.save_only_info_sup()

        #debug('saving une SellByRelation: %s ', self.pk)

        if not update  :
            #if self.predicate.type_relation is not None:
            #if self.type.predicate is not None:
            if self.type is not None:
                #debug('on save une SellByRelation, on l add a la subject creme entity ')
                self.subject_creme_entity.new_relations.add(self)

            if self.type.symmetric_type is not None and sym_relation is None:
                sym_relation = SellByRelation(type=self.type.symmetric_type,
                                              subject_content_type=self.object_content_type,
                                              subject_id=self.object_id,
                                              object_content_type=self.subject_content_type,
                                              object_id=self.subject_id,
                                              symmetric_relation= self,
                                              user=self.user,
                                              commission_paye=self.commission_paye,
                                              int_value=self.int_value,
                                              char_value=self.char_value,
                                              date_paiement=self.date_paiement
                                             )
                sym_relation.save()
                self.symmetric_relation = sym_relation
                self.save ()

    @staticmethod
    def create_SellByRelation_with_object(subject, object, commission_paye, int_value=0, char_value=""):
        relation = SellByRelation ()
        relation.subject_creme_entity = subject
        #relation.predicate = RelationType.objects.get(type_relation__id=REL_SUB_SOLD_BY)
        relation.type = RelationType.objects.get(pk=REL_SUB_SOLD_BY)

        relation.object_creme_entity = object
        relation.commission_paye = commission_paye 
        relation.int_value = int_value
        #relation.stagiaires_number = stagiaires_number
        relation.char_value = char_value

        relation.user = User.objects.get(pk=1)
        relation.save()
